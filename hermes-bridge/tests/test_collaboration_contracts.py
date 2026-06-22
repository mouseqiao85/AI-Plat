from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from typing import Dict
from unittest.mock import patch

import pytest

_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge import db, flows, orchestrator, runs


@pytest.fixture(autouse=True)
def _temp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["ORCHESTRATOR_DB"] = tmp.name
    db._conn = None
    db.init()
    yield
    db._conn.close()
    os.unlink(tmp.name)


def test_competitive_candidate_task_injects_role_contract():
    task = orchestrator._competitive_candidate_task(
        "",
        user_input="Choose an architecture",
        candidate_id="risk-reviewer",
        role_order=["risk-reviewer"],
        flow_spec={
            "role_contracts": {
                "risk-reviewer": {
                    "stance_name": "Risk reviewer",
                    "must_challenge": "happy-path architecture decisions",
                    "output_schema": ["Risk position", "Blocking concerns"],
                }
            }
        },
    )

    assert "ROLE CONTRACT (binding for this run)" in task
    assert "Risk reviewer" in task
    assert "happy-path architecture decisions" in task
    assert "Risk position, Blocking concerns" in task
    assert "Self-critique" in task


def test_competitive_consensus_task_injects_adjudication_contract():
    task = orchestrator._competitive_consensus_task(
        user_input="Choose an architecture",
        candidate_results=[
            {"role_id": "builder", "content": "Build with A", "error": None},
            {"role_id": "skeptic", "content": "A has risks", "error": None},
        ],
        flow_spec={
            "adjudication": {
                "decision_rule": "prefer the option with the strongest migration story",
                "rubric": ["Migration safety", "User value"],
            }
        },
    )

    assert "ADJUDICATION CONTRACT (binding)" in task
    assert "prefer the option with the strongest migration story" in task
    assert "Migration safety" in task
    assert "Score matrix" in task
    assert "Disagreement map" in task
    assert "Minority report" in task


def test_peer_conflict_no_longest_answer_fallback():
    result = orchestrator._resolve_peer_conflict(
        [
            {"role_id": "short", "content": "Short answer.", "error": None},
            {"role_id": "long", "content": "Long answer. " * 50, "error": None},
        ],
        ["short", "long"],
    )

    assert result["strategy"] == "requires_resolver"
    assert result["winner"] == ""
    assert result["content"] == ""


def _create_peer_run() -> int:
    flow = flows.create(
        name="peer contract test",
        flow_type="peer_to_peer",
        role_ids=["alpha", "beta"],
    )
    return runs.create(flow.id, "Pick the better plan").id


@pytest.mark.asyncio
async def test_peer_to_peer_tied_votes_calls_resolver():
    calls = []

    async def fake_execute_role(role_id: str, task: str, **kwargs) -> Dict:
        calls.append((role_id, task))
        if role_id == "alpha":
            if "Your initial answer" in task:
                return {"content": "Alpha review\nVOTE: alpha", "latency_ms": 1, "error": None}
            return {"content": "Alpha initial full argument", "latency_ms": 1, "error": None}
        if role_id == "beta":
            if "Your initial answer" in task:
                return {"content": "Beta review\nVOTE: beta", "latency_ms": 1, "error": None}
            return {"content": "Beta initial full argument", "latency_ms": 1, "error": None}
        return {
            "content": "Decision\nWINNER: synthesis\nFinal synthesis",
            "latency_ms": 1,
            "error": None,
        }

    with patch("bridge.orchestrator._execute_role", side_effect=fake_execute_role):
        events = []
        async for event in orchestrator._run_peer_to_peer(
            ["alpha", "beta"],
            "Pick the better plan",
            "",
            run_id=_create_peer_run(),
        ):
            events.append(event)

    resolver_calls = [call for call in calls if call[0] == "orchestrator/resolver"]
    assert len(resolver_calls) == 1
    assert "ADJUDICATION CONTRACT (binding)" in resolver_calls[0][1]
    assert "Alpha review" in resolver_calls[0][1]
    assert "Beta review" in resolver_calls[0][1]

    resolved = [event for event in events if event.type == "conflict_resolved"]
    assert len(resolved) == 1
    assert resolved[0].extra["strategy"] == "llm_resolver"
    assert resolved[0].extra["winner"] == "synthesis"


@pytest.mark.asyncio
async def test_peer_to_peer_resolver_failure_reports_no_safe_winner():
    async def fake_execute_role(role_id: str, task: str, **kwargs) -> Dict:
        if role_id == "alpha":
            if "Your initial answer" in task:
                return {"content": "Alpha review\nVOTE: alpha", "latency_ms": 1, "error": None}
            return {"content": "Alpha initial", "latency_ms": 1, "error": None}
        if role_id == "beta":
            if "Your initial answer" in task:
                return {"content": "Beta review\nVOTE: beta", "latency_ms": 1, "error": None}
            return {"content": "Beta initial", "latency_ms": 1, "error": None}
        return {"content": "", "latency_ms": 1, "error": "resolver unavailable"}

    with patch("bridge.orchestrator._execute_role", side_effect=fake_execute_role):
        events = []
        async for event in orchestrator._run_peer_to_peer(
            ["alpha", "beta"],
            "Pick the better plan",
            "",
            run_id=_create_peer_run(),
        ):
            events.append(event)

    resolved = [event for event in events if event.type == "conflict_resolved"]
    assert len(resolved) == 1
    assert resolved[0].extra["strategy"] == "llm_resolver_failed"
    assert resolved[0].extra["winner"] == ""
    assert "does not use answer length as a fallback decision rule" in resolved[0].content
