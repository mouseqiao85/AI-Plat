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


def _stream_executor(outputs: dict[str, str], failures: dict[str, str] | None = None, captured_tasks: list[tuple[str, str]] | None = None):
    failures = failures or {}

    def _gen(role_id: str, task: str, timeout: int = 600,
             session_id: str = "", model: str = "", project_dir: str = "",
             sandbox_policy=None):
        if captured_tasks is not None:
            captured_tasks.append((role_id, task))
        if role_id in failures:
            raise RuntimeError(failures[role_id])
        content = outputs.get(role_id, f"{role_id} output")
        yield content, session_id, False
        yield content, session_id, True

    return _gen


@pytest.mark.asyncio
async def test_pipeline_flow_runs_stages_and_persists_queue_messages():
    flow = create_flow(
        name="pipeline happy path",
        flow_type="pipeline",
        role_ids=["stage-A", "stage-B", "stage-C"],
    )
    captured_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_stream_executor(
        {
            "stage-A": "cleaned data",
            "stage-B": "enriched data",
            "stage-C": "final report",
        },
        captured_tasks=captured_tasks,
    )):
        events = []
        async for event in run_flow(flow.id, "raw input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert event_types[0] == "run_started"
    assert event_types[-1] == "run_completed"
    assert [event.role_id for event in events if event.type == "role_completed"] == ["stage-A", "stage-B", "stage-C"]
    assert "cleaned data" in captured_tasks[1][1]
    assert "enriched data" in captured_tasks[2][1]

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    message_types = [message.type for message in messages]
    assert message_types.count("pipeline_stage_task") == 3
    assert message_types.count("pipeline_stage_result") == 3
    assert message_types.count("pipeline_queue_item") == 2
    queue_messages = [message for message in messages if message.type == "pipeline_queue_item"]
    assert queue_messages[0].from_agent == "stage-A"
    assert queue_messages[0].to_agent == "stage-B"
    assert queue_messages[0].payload["queue"] == "stage-1"


@pytest.mark.asyncio
async def test_pipeline_flow_fails_fast_on_stage_failure():
    flow = create_flow(
        name="pipeline fail fast",
        flow_type="pipeline",
        role_ids=["stage-A", "stage-B", "stage-C"],
    )
    captured_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream", side_effect=_stream_executor(
        {"stage-A": "stage A output", "stage-C": "should not run"},
        failures={"stage-B": "stage B failed"},
        captured_tasks=captured_tasks,
    )):
        events = []
        async for event in run_flow(flow.id, "input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert "run_failed" in event_types
    assert "run_completed" not in event_types
    assert any(event.type == "role_failed" and event.role_id == "stage-B" for event in events)
    assert "stage-C" not in [role_id for role_id, _ in captured_tasks]

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    failed_results = [message for message in messages if message.type == "pipeline_stage_result" and message.status == "failed"]
    assert len(failed_results) == 1
    assert failed_results[0].role_id == "stage-B"


def test_pipeline_flow_requires_at_least_two_roles():
    with pytest.raises(ValueError, match="pipeline flow requires"):
        create_flow(name="invalid pipeline", flow_type="pipeline", role_ids=["stage-A"])
