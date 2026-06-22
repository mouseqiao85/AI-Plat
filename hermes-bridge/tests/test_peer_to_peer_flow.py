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


def _peer_executor(outputs: dict[tuple[str, int], str], failures: dict[tuple[str, int], str] | None = None):
    calls: dict[str, int] = {}
    failures = failures or {}

    def _execute(role_id: str, task: str, timeout: int, session_id: str = "", model: str = "", project_dir: str = "", sandbox_policy=None):
        call_idx = calls.get(role_id, 0)
        calls[role_id] = call_idx + 1
        key = (role_id, call_idx)
        if key in failures:
            raise RuntimeError(failures[key])
        return outputs.get(key, f"{role_id} call {call_idx}"), session_id

    return _execute


@pytest.mark.asyncio
async def test_peer_to_peer_flow_broadcasts_reviews_and_resolves_by_majority_vote():
    flow = create_flow(
        name="peer happy path",
        flow_type="peer_to_peer",
        role_ids=["peer-A", "peer-B", "peer-C"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_peer_executor({
        ("peer-A", 0): "A initial",
        ("peer-B", 0): "B initial",
        ("peer-C", 0): "C initial",
        ("peer-A", 1): "A revised\nVOTE: peer-B",
        ("peer-B", 1): "B revised winner\nVOTE: peer-B",
        ("peer-C", 1): "C revised\nVOTE: peer-A",
    })):
        events = []
        async for event in run_flow(flow.id, "choose best plan"):
            events.append(event)

    event_types = [event.type for event in events]
    assert event_types[0] == "run_started"
    assert event_types[-1] == "run_completed"
    assert "conflict_resolved" in event_types
    resolved = [event for event in events if event.type == "conflict_resolved"][0]
    assert resolved.extra["winner"] == "peer-B"
    assert resolved.extra["strategy"] == "majority_vote"
    assert "B revised winner" in resolved.content

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    message_types = [message.type for message in messages]
    assert message_types.count("peer_initial_task") == 3
    assert message_types.count("peer_initial_result") == 3
    assert message_types.count("peer_broadcast") == 6
    assert message_types.count("peer_review_task") == 3
    assert message_types.count("peer_review_result") == 3
    assert message_types.count("conflict_resolution_result") == 1


@pytest.mark.asyncio
async def test_peer_to_peer_flow_resolves_with_partial_initial_failure():
    flow = create_flow(
        name="peer partial failure",
        flow_type="peer_to_peer",
        role_ids=["peer-A", "peer-B", "peer-C"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_peer_executor(
        {
            ("peer-A", 0): "A initial",
            ("peer-C", 0): "C initial",
            ("peer-A", 1): "A review\nVOTE: peer-A",
            ("peer-C", 1): "C review\nVOTE: peer-A",
        },
        failures={("peer-B", 0): "B failed"},
    )):
        events = []
        async for event in run_flow(flow.id, "input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert "role_failed" in event_types
    assert "conflict_resolved" in event_types
    assert event_types[-1] == "run_completed"

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert any(message.type == "peer_initial_result" and message.role_id == "peer-B" and message.status == "failed" for message in messages)
    assert [message.type for message in messages].count("peer_broadcast") == 2


@pytest.mark.asyncio
async def test_peer_to_peer_flow_fails_when_all_initials_fail():
    flow = create_flow(
        name="peer all fail",
        flow_type="peer_to_peer",
        role_ids=["peer-A", "peer-B"],
    )

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_peer_executor(
        {},
        failures={("peer-A", 0): "A failed", ("peer-B", 0): "B failed"},
    )):
        events = []
        async for event in run_flow(flow.id, "input"):
            events.append(event)

    event_types = [event.type for event in events]
    assert "run_failed" in event_types
    assert "conflict_resolved" not in event_types
    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert [message.type for message in messages].count("peer_review_task") == 0


def test_peer_to_peer_flow_requires_at_least_two_roles():
    with pytest.raises(ValueError, match="peer_to_peer flow requires"):
        create_flow(name="invalid peer", flow_type="peer_to_peer", role_ids=["peer-A"])
