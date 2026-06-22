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


def _master_stream(contents: list[str], errors: list[str] | None = None):
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


def _worker_executor(failures: dict[str, str] | None = None, captured_tasks: list[tuple[str, str]] | None = None):
    failures = failures or {}

    def _execute(role_id: str, task: str, timeout: int, session_id: str = "", model: str = "", project_dir: str = ""):
        if captured_tasks is not None:
            captured_tasks.append((role_id, task))
        if role_id in failures:
            raise RuntimeError(failures[role_id])
        return f"{role_id} result", session_id

    return _execute


@pytest.mark.asyncio
async def test_hierarchical_flow_runs_master_workers_and_summary():
    flow = create_flow(
        name="hierarchical happy path",
        flow_type="hierarchical",
        role_ids=["master", "worker-A", "worker-B"],
    )
    captured_worker_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_master_stream([
        "master plan",
        "final summary",
    ])), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_worker_executor(captured_tasks=captured_worker_tasks)):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert event_types[0] == "run_started"
    assert event_types[-1] == "run_completed"
    assert event_types.count("role_completed") == 4  # master plan, two workers, master summary
    assert not any(event.type == "role_failed" for event in events)

    completed = [(event.role_id, event.content) for event in events if event.type == "role_completed"]
    assert completed[0] == ("master", "master plan")
    assert completed[-1] == ("master", "final summary")
    assert {role_id for role_id, _ in captured_worker_tasks} == {"worker-A", "worker-B"}
    assert all("master plan" in task for _, task in captured_worker_tasks)

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert [message.type for message in messages] == [
        "master_plan_task",
        "master_plan_result",
        "worker_task",
        "worker_task",
        "worker_result",
        "worker_result",
        "master_summary_task",
        "master_summary_result",
    ]
    assert all(message.status in {"sent", "received"} for message in messages)


@pytest.mark.asyncio
async def test_hierarchical_worker_failure_is_summarized_not_aborted():
    flow = create_flow(
        name="hierarchical worker failure",
        flow_type="hierarchical",
        role_ids=["master", "worker-A", "worker-B"],
    )
    captured_worker_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_master_stream([
        "master plan",
        "summary despite worker failure",
    ])), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_worker_executor(
        failures={"worker-B": "worker B failed"},
        captured_tasks=captured_worker_tasks,
    )):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    assert events[-1].type == "run_completed"
    assert any(event.type == "role_failed" and event.role_id == "worker-B" for event in events)
    assert any(event.type == "role_completed" and event.role_id == "master" and event.content == "summary despite worker failure" for event in events)

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    failed_worker = [message for message in messages if message.type == "worker_result" and message.status == "failed"]
    assert len(failed_worker) == 1
    assert failed_worker[0].role_id == "worker-B"
    assert failed_worker[0].payload["error"] == "worker B failed"


@pytest.mark.asyncio
async def test_hierarchical_master_failure_stops_before_workers():
    flow = create_flow(
        name="hierarchical master failure",
        flow_type="hierarchical",
        role_ids=["master", "worker-A"],
    )
    captured_worker_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_master_stream(
        contents=["unused"],
        errors=["master failed"],
    )), patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_worker_executor(captured_tasks=captured_worker_tasks)):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    assert events[-1].type == "run_failed"
    assert any(event.type == "role_failed" and event.role_id == "master" for event in events)
    assert captured_worker_tasks == []

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert [(message.type, message.status, message.role_id) for message in messages] == [
        ("master_plan_task", "sent", "master"),
        ("master_plan_result", "failed", "master"),
    ]


def test_hierarchical_flow_requires_master_and_worker():
    with pytest.raises(ValueError, match="master and at least one worker"):
        create_flow(name="invalid hierarchical", flow_type="hierarchical", role_ids=["master"])
