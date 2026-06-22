from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge import db, runs as runs_mod
from bridge.collaboration import CollaborationMessage
from bridge.flows import create as create_flow
from bridge.orchestrator import GRAPHRAG_QUERY_MAX_CHARS, _execute_graphrag_node, render_prompt, run_flow


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


def _dag_executor(outputs: dict[str, str], captured_tasks: list[tuple[str, str]]):
    def _execute(role_id: str, task: str, timeout: int, session_id: str = "",
                 model: str = "", project_dir: str = "", sandbox_policy=None):
        captured_tasks.append((role_id, task))
        return outputs.get(role_id, f"{role_id} output"), session_id

    return _execute


@pytest.mark.asyncio
async def test_dag_flow_runs_topological_levels_and_hands_off_upstream_outputs():
    flow = create_flow(
        name="dag happy path",
        flow_type="dag",
        role_ids=["research", "design", "build", "review"],
        flow_spec={
            "nodes": [
                {"id": "research", "role_id": "research", "label": "Research"},
                {"id": "design", "role_id": "design", "label": "Design"},
                {"id": "build", "role_id": "build", "label": "Build"},
                {"id": "review", "role_id": "review", "label": "Review"},
            ],
            "edges": [
                {"from": "research", "to": "build"},
                {"from": "design", "to": "build"},
                {"from": "build", "to": "review"},
            ],
        },
    )
    captured_tasks: list[tuple[str, str]] = []

    with patch("bridge.orchestrator.hermes_cli.execute_skill_direct", side_effect=_dag_executor(
        {
            "research": "research output",
            "design": "design output",
            "build": "build output",
            "review": "review output",
        },
        captured_tasks,
    )):
        events = []
        async for event in run_flow(flow.id, "ship a dag feature"):
            events.append(event)

    event_types = [event.type for event in events]
    assert event_types[0] == "run_started"
    assert event_types[-1] == "run_completed"
    completed = [event for event in events if event.type == "role_completed"]
    assert [event.role_id for event in completed] == ["research", "design", "build", "review"]

    build_task = next(task for role_id, task in captured_tasks if role_id == "build")
    assert "research output" in build_task
    assert "design output" in build_task
    review_task = next(task for role_id, task in captured_tasks if role_id == "review")
    assert "build output" in review_task

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    message_types = [message.type for message in messages]
    assert message_types.count("dag_node_task") == 4
    assert message_types.count("dag_node_result") == 4
    assert message_types.count("dag_edge_handoff") == 3


def test_dag_flow_rejects_cycles():
    with pytest.raises(ValueError, match="cycle"):
        create_flow(
            name="cyclic dag",
            flow_type="dag",
            role_ids=["a", "b"],
            flow_spec={
                "nodes": [
                    {"id": "a", "role_id": "a"},
                    {"id": "b", "role_id": "b"},
                ],
                "edges": [
                    {"from": "a", "to": "b"},
                    {"from": "b", "to": "a"},
                ],
            },
        )


def test_dag_flow_requires_node_roles_to_match_role_ids():
    with pytest.raises(ValueError, match="role_ids"):
        create_flow(
            name="bad dag",
            flow_type="dag",
            role_ids=["a"],
            flow_spec={
                "nodes": [{"id": "a", "role_id": "other"}],
                "edges": [],
            },
        )


def test_dag_flow_preserves_collaboration_contract_fields():
    flow = create_flow(
        name="dag contracts",
        flow_type="dag",
        role_ids=["review"],
        flow_spec={
            "nodes": [{"id": "review", "type": "role", "role_id": "review"}],
            "edges": [],
            "role_contracts": {
                "review": {
                    "stance_name": "Risk reviewer",
                    "must_challenge": "unsupported assumptions",
                },
            },
            "adjudication": {
                "decision_rule": "prefer evidence-backed conclusions",
                "rubric": ["Evidence", "Risk"],
            },
        },
    )

    assert flow.flow_spec["nodes"][0]["role_id"] == "review"
    assert flow.flow_spec["role_contracts"]["review"]["stance_name"] == "Risk reviewer"
    assert flow.flow_spec["adjudication"]["rubric"] == ["Evidence", "Risk"]


def test_migration_repairs_flow_runs_foreign_key_to_dialog_flows_old():
    db._conn.close()
    db._conn = None

    conn = sqlite3.connect(str(db.DB_PATH))
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE flow_runs")
        conn.execute("DROP TABLE dialog_flows")
        conn.execute(
            """
            CREATE TABLE dialog_flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER DEFAULT 0,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                flow_type TEXT NOT NULL CHECK (flow_type IN ('sequential','parallel','hierarchical','competitive','pipeline','peer_to_peer','dag')),
                role_ids TEXT NOT NULL,
                scenario_id TEXT DEFAULT '',
                prompt_template TEXT DEFAULT '',
                model TEXT DEFAULT 'deepseek-v4-flash',
                sandbox_policy TEXT DEFAULT '{}',
                flow_spec TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE flow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_id INTEGER NOT NULL,
                input_text TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT DEFAULT '',
                outputs TEXT NOT NULL DEFAULT '[]',
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                finished_at DATETIME,
                project_dir TEXT DEFAULT '',
                FOREIGN KEY (flow_id) REFERENCES dialog_flows_old(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    db.init()
    flow = create_flow(name="repair delete", flow_type="dag", role_ids=["review"], flow_spec={
        "nodes": [{"id": "review", "type": "role", "role_id": "review"}],
        "edges": [],
    })
    runs_mod.create(flow.id, "input")

    from bridge import flows as flows_mod

    flows_mod.delete(flow.id)
    with pytest.raises(KeyError):
        flows_mod.get(flow.id)


def test_delete_flow_removes_run_events_and_collaboration_messages():
    flow = create_flow(name="delete flow messages", flow_type="dag", role_ids=["review"], flow_spec={
        "nodes": [{"id": "review", "type": "role", "role_id": "review"}],
        "edges": [],
    })
    run = runs_mod.create(flow.id, "input")
    runs_mod.append_event(run.id, {"type": "run_started", "run_id": run.id})
    runs_mod.append_collaboration_message(CollaborationMessage(
        run_id=run.id,
        from_agent="a",
        to_agent="b",
        type="role_task",
        payload={},
        status="sent",
        role_id="review",
    ))

    from bridge import flows as flows_mod

    flows_mod.delete(flow.id)

    with db.cursor() as cur:
        assert cur.execute("SELECT COUNT(*) FROM flow_run_events WHERE run_id = ?", (run.id,)).fetchone()[0] == 0
        assert cur.execute("SELECT COUNT(*) FROM collaboration_messages WHERE run_id = ?", (run.id,)).fetchone()[0] == 0


def test_create_run_clears_stale_child_rows_for_reused_id():
    flow = create_flow(name="stale child cleanup", flow_type="dag", role_ids=["review"], flow_spec={
        "nodes": [{"id": "review", "type": "role", "role_id": "review"}],
        "edges": [],
    })
    assert db._conn is not None
    db._conn.execute("PRAGMA foreign_keys=OFF")
    with db.cursor() as cur:
        cur.execute("INSERT INTO flow_run_events (run_id, seq, event_type, payload) VALUES (1, 1, 'old', '{}')")
        cur.execute(
            """INSERT INTO collaboration_messages
               (run_id, seq, from_agent, to_agent, type, payload, status, role_id)
               VALUES (1, 1, 'old', 'old', 'old_message', '{}', 'sent', 'old')"""
        )
    db._conn.execute("PRAGMA foreign_keys=ON")

    run = runs_mod.create(flow.id, "input")

    assert run.id == 1
    with db.cursor() as cur:
        assert cur.execute("SELECT COUNT(*) FROM flow_run_events WHERE run_id = ?", (run.id,)).fetchone()[0] == 0
        assert cur.execute("SELECT COUNT(*) FROM collaboration_messages WHERE run_id = ?", (run.id,)).fetchone()[0] == 0


def test_create_run_strips_binary_attachment_body():
    flow = create_flow(name="binary attachment cleanup", flow_type="dag", role_ids=["review"], flow_spec={
        "nodes": [{"id": "review", "type": "role", "role_id": "review"}],
        "edges": [],
    })
    run = runs_mod.create(flow.id, "生成方案\n\n---\n**附件: test.docx**\n\nPK\x03\x04binary-docx-content")

    assert "PK" not in run.input_text
    assert "二进制附件内容已移除" in run.input_text


def test_create_run_strips_binary_attachment_body_with_corrupted_header():
    flow = create_flow(name="binary attachment cleanup", flow_type="dag", role_ids=["review"], flow_spec={
        "nodes": [{"id": "review", "type": "role", "role_id": "review"}],
        "edges": [],
    })
    run = runs_mod.create(flow.id, "生成方案\n\n---\n**??: test.docx**\n\nPK\x03\x04binary-docx-content")

    assert "PK" not in run.input_text
    assert "binary-docx-content" not in run.input_text
    assert "二进制附件内容已移除" in run.input_text


def test_render_prompt_preserves_non_placeholder_braces():
    rendered = render_prompt(
        "Query {input}; keep {graphrag}; prior {prior}",
        user_input="hello",
        prior="context",
    )

    assert rendered == "Query hello; keep {graphrag}; prior context"


@pytest.mark.asyncio
async def test_dag_flow_runs_graphrag_node_and_passes_context_downstream():
    flow = create_flow(
        name="dag graphrag",
        flow_type="dag",
        role_ids=["writer"],
        flow_spec={
            "nodes": [
                {"id": "kg", "type": "graphrag", "label": "Knowledge", "query_template": "lookup {input}", "max_hits": 2},
                {"id": "writer", "type": "role", "role_id": "writer", "label": "Writer"},
            ],
            "edges": [{"from": "kg", "to": "writer"}],
        },
    )
    captured_tasks: list[tuple[str, str]] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/knowledge-graph/graphrag"
        assert request.url.params["q"] == "lookup explain CSM-27"
        assert request.url.params["limit"] == "2"
        return httpx.Response(200, json={
            "query": "lookup explain CSM-27",
            "contexts": [{"node": {"title": "CSM-27"}, "relations": []}],
        })

    original_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(http_handler)
        return original_client(*args, **kwargs)

    with patch("httpx.AsyncClient", side_effect=patched_client), patch(
        "bridge.orchestrator.hermes_cli.execute_skill_direct",
        side_effect=_dag_executor({"writer": "writer output"}, captured_tasks),
    ):
        events = []
        async for event in run_flow(flow.id, "explain CSM-27"):
            events.append(event)

    completed = [event for event in events if event.type == "role_completed"]
    assert [event.role_id for event in completed] == ["graphrag:kg", "writer"]
    assert "CSM-27" in completed[0].content

    writer_task = next(task for role_id, task in captured_tasks if role_id == "writer")
    assert "GraphRAG knowledge context" in writer_task
    assert "CSM-27" in writer_task

    messages = runs_mod.list_collaboration_messages(events[0].run_id)
    assert [message.role_id for message in messages if message.type == "dag_node_task"] == ["graphrag:kg", "writer"]
    kg_result = next(message for message in messages if message.type == "dag_node_result" and message.role_id == "graphrag:kg")
    assert kg_result.payload["metadata"]["query"] == "lookup explain CSM-27"
    assert kg_result.payload["metadata"]["hit_count"] == 1
    kg_handoff = next(message for message in messages if message.type == "dag_edge_handoff" and message.payload["from_node"] == "kg")
    assert kg_handoff.payload["metadata"]["hit_count"] == 1


@pytest.mark.asyncio
async def test_graphrag_node_truncates_oversized_query_before_request():
    seen: dict[str, str] = {}

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen["q"] = request.url.params["q"]
        return httpx.Response(200, json={"query": seen["q"], "contexts": []})

    original_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(http_handler)
        return original_client(*args, **kwargs)

    node = {"id": "kg", "type": "graphrag", "query_template": "{input}", "max_hits": 1}
    with patch("httpx.AsyncClient", side_effect=patched_client):
        result = await _execute_graphrag_node(node, user_input="x" * (GRAPHRAG_QUERY_MAX_CHARS * 3), upstream_results=[])

    assert result["error"] is None
    assert result["metadata"]["query_truncated"] is True
    assert len(seen["q"]) <= GRAPHRAG_QUERY_MAX_CHARS + 64
