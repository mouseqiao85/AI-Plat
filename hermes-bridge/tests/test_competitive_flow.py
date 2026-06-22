from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge import db, runs as runs_mod
from bridge.flows import create as create_flow
from bridge.orchestrator import run_flow


@pytest.fixture(autouse=True)
def _temp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["ORCHESTRATOR_DB"] = tmp.name
    db.DB_PATH = Path(tmp.name)
    db._conn = None
    db.init()
    yield
    db._conn.close()
    db._conn = None
    os.unlink(tmp.name)


def _consensus_stream(contents: list[str], errors: list[str] | None = None):
    state = {"calls": 0}
    errors = errors or []

    def _gen(role_id: str, task: str, timeout: int = 600,
             session_id: str = "", model: str = "", project_dir: str = ""):
        call_idx = state["calls"]
        state["calls"] += 1
        if call_idx < len(errors) and errors[call_idx]:
            raise RuntimeError(errors[call_idx])
        content = contents[call_idx] if call_idx < len(contents) else contents[-1]
        yield content, session_id, False
        yield content, session_id, True

    return _gen


def _candidate_executor(failures: dict[str, str] | None = None, captured_tasks: list[tuple[str, str]] | None = None):
    failures = failures or {}

    def _execute(role_id: str, task: str, timeout: int, session_id: str = "", model: str = "", project_dir: str = ""):
        if captured_tasks is not None:
            captured_tasks.append((role_id, task))
        if role_id in failures:
            raise RuntimeError(failures[role_id])
        return f"{role_id} proposal", session_id

    return _execute


def _candidate_executor_with_dirs(captured_dirs: dict[str, str]):
    def _execute(role_id: str, task: str, timeout: int, session_id: str = "", model: str = "", project_dir: str = ""):
        captured_dirs[role_id] = project_dir
        return f"{role_id} proposal", session_id

    return _execute


@pytest.mark.asyncio
async def test_competitive_flow_runs_candidates_then_consensus():
    flow = create_flow(
        name="competitive happy path",
        flow_type="competitive",
        role_ids=["judge", "candidate-A", "candidate-B"],
    )
    captured_candidate_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_consensus_stream([
        "final decision with rationale",
    ])), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_candidate_executor(captured_tasks=captured_candidate_tasks)):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert event_types[0] == "run_started"
    assert event_types[-1] == "run_completed"
    assert event_types.count("role_completed") == 3  # two candidates and final judge
    assert not any(event.type == "role_failed" for event in events)

    completed = [(event.role_id, event.content) for event in events if event.type == "role_completed"]
    assert set(completed[:2]) == {("candidate-A", "candidate-A proposal"), ("candidate-B", "candidate-B proposal")}
    assert completed[-1] == ("judge", "final decision with rationale")
    assert {role_id for role_id, _ in captured_candidate_tasks} == {"candidate-A", "candidate-B"}
    assert all("competitive multi-agent flow" in task for _, task in captured_candidate_tasks)

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert [message.type for message in messages] == [
        "candidate_task",
        "candidate_task",
        "candidate_result",
        "candidate_result",
        "consensus_task",
        "consensus_result",
    ]
    assert all(message.status in {"sent", "received"} for message in messages)
    assert all(message.to_agent == "judge" for message in messages if message.type == "candidate_result")


@pytest.mark.asyncio
async def test_competitive_candidate_failure_does_not_abort_consensus():
    flow = create_flow(
        name="competitive candidate failure",
        flow_type="competitive",
        role_ids=["judge", "candidate-A", "candidate-B"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_consensus_stream([
        "decision despite failed candidate",
    ])), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_candidate_executor(
        failures={"candidate-B": "candidate B failed"},
    )):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    assert events[-1].type == "run_completed"
    assert any(event.type == "role_failed" and event.role_id == "candidate-B" for event in events)
    assert any(event.type == "role_completed" and event.role_id == "judge" and event.content == "decision despite failed candidate" for event in events)

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    failed_candidate = [message for message in messages if message.type == "candidate_result" and message.status == "failed"]
    assert len(failed_candidate) == 1
    assert failed_candidate[0].role_id == "candidate-B"
    assert failed_candidate[0].payload["error"] == "candidate B failed"


@pytest.mark.asyncio
async def test_competitive_consensus_failure_marks_run_failed():
    flow = create_flow(
        name="competitive consensus failure",
        flow_type="competitive",
        role_ids=["judge", "candidate-A"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_consensus_stream(
        contents=["unused"],
        errors=["judge failed"],
    )), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_candidate_executor()):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    assert events[-1].type == "run_failed"
    assert any(event.type == "role_completed" and event.role_id == "candidate-A" for event in events)
    assert any(event.type == "role_failed" and event.role_id == "judge" for event in events)

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert messages[-2].type == "consensus_task"
    assert messages[-1].type == "consensus_result"
    assert messages[-1].status == "failed"
    assert messages[-1].payload["error"] == "judge failed"


def test_competitive_flow_requires_consensus_and_candidate():
    with pytest.raises(ValueError, match="consensus agent and at least one candidate"):
        create_flow(name="invalid competitive", flow_type="competitive", role_ids=["judge"])


@pytest.mark.asyncio
async def test_competitive_candidates_use_isolated_workspaces():
    flow = create_flow(
        name="competitive isolated workspaces",
        flow_type="competitive",
        role_ids=["judge", "candidate-A", "candidate-B"],
    )
    captured_dirs: dict[str, str] = {}

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_consensus_stream([
        "final decision",
    ])), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_candidate_executor_with_dirs(captured_dirs)):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    assert events[-1].type == "run_completed"
    assert set(captured_dirs) == {"candidate-A", "candidate-B"}
    assert captured_dirs["candidate-A"] != captured_dirs["candidate-B"]
    assert captured_dirs["candidate-A"].endswith(os.path.join("work", "candidate-A"))
    assert captured_dirs["candidate-B"].endswith(os.path.join("work", "candidate-B"))
