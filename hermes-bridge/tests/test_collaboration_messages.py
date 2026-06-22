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
from bridge.collaboration import CollaborationMessage
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


def _make_stream_gen(role_behaviors: dict):
    def _gen(role_id: str, task: str, timeout: int = 600,
             session_id: str = "", model: str = "", project_dir: str = ""):
        behavior = role_behaviors.get(role_id, {"content": f"output from {role_id}"})
        if "error" in behavior:
            raise RuntimeError(behavior["error"])
        content = behavior.get("content", f"output from {role_id}")
        yield content, session_id, False
        yield content, session_id, True

    return _gen


def test_collaboration_message_round_trips_and_validates_transitions():
    message = CollaborationMessage(
        id=10,
        run_id=1,
        seq=2,
        from_agent="orchestrator",
        to_agent="role-A",
        type="role_task",
        payload={"task_preview": "hello"},
        priority=3,
        timeout_ms=1000,
        status="queued",
        role_id="role-A",
        output_index=0,
        created_at="2026-06-02 00:00:00",
        updated_at="2026-06-02 00:00:00",
    )

    assert CollaborationMessage.from_dict(message.to_dict()).to_dict() == message.to_dict()

    message.transition("sent").transition("received")
    assert message.status == "received"

    with pytest.raises(ValueError, match="cannot transition"):
        message.transition("failed")

    with pytest.raises(ValueError, match="status must be one of"):
        CollaborationMessage(
            run_id=1,
            from_agent="a",
            to_agent="b",
            type="x",
            status="done",
        )


def test_collaboration_messages_persist_with_flow_run():
    flow = create_flow(name="message persistence", flow_type="sequential", role_ids=["role-A"])
    run = runs_mod.create(flow.id, "hello")

    created = runs_mod.append_collaboration_message(CollaborationMessage(
        run_id=run.id,
        from_agent="orchestrator",
        to_agent="role-A",
        type="role_task",
        payload={"task_preview": "hello"},
        status="sent",
        role_id="role-A",
    ))

    assert created.id is not None
    assert created.seq == 1
    assert created.status == "sent"

    updated = runs_mod.update_collaboration_message_status(created.id, "received")
    assert updated.status == "received"

    messages = runs_mod.list_collaboration_messages(run.id)
    assert len(messages) == 1
    assert messages[0].to_dict()["payload"] == {"task_preview": "hello"}
    assert messages[0].status == "received"


@pytest.mark.asyncio
async def test_sequential_flow_persists_collaboration_messages_without_changing_events():
    flow = create_flow(
        name="sequential collaboration messages",
        flow_type="sequential",
        role_ids=["role-A", "role-B"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct_stream") as mock_exec:
        mock_exec.side_effect = lambda role_id, task, **kwargs: _make_stream_gen({
            "role-A": {"content": "A output"},
            "role-B": {"content": "B output"},
        })(role_id, task, **kwargs)

        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert event_types == [
        "run_started",
        "role_started",
        "role_output",
        "role_completed",
        "role_started",
        "role_output",
        "role_completed",
        "run_completed",
    ]

    run_id = events[0].run_id
    messages = runs_mod.list_collaboration_messages(run_id)
    assert [(msg.from_agent, msg.to_agent, msg.type, msg.status) for msg in messages] == [
        ("orchestrator", "role-A", "role_task", "sent"),
        ("role-A", "orchestrator", "role_result", "received"),
        ("orchestrator", "role-B", "role_task", "sent"),
        ("role-B", "orchestrator", "role_result", "received"),
    ]
    assert messages[1].output_index == 0
    assert messages[3].output_index == 1
    assert messages[2].payload["task_preview"].startswith("Prior reviewer output")


@pytest.mark.asyncio
async def test_parallel_flow_persists_failed_collaboration_message():
    flow = create_flow(
        name="parallel collaboration messages",
        flow_type="parallel",
        role_ids=["role-A", "role-B"],
    )

    def execute_skill_direct(role_id, task, timeout, session_id="", model="", project_dir=""):
        if role_id == "role-B":
            raise RuntimeError("B failed")
        return "A output", session_id

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=execute_skill_direct):
        events = []
        async for event in run_flow(flow.id, "user input"):
            events.append(event)

    run_id = events[0].run_id
    messages = runs_mod.list_collaboration_messages(run_id)
    result_messages = [msg for msg in messages if msg.type == "role_result"]

    assert len(messages) == 4
    assert {msg.role_id for msg in messages if msg.type == "role_task"} == {"role-A", "role-B"}
    assert {msg.status for msg in result_messages} == {"received", "failed"}
    failed = [msg for msg in result_messages if msg.status == "failed"][0]
    assert failed.role_id == "role-B"
    assert failed.payload["error"] == "B failed"
