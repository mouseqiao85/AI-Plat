"""CRUD for ``dialog_flows`` — a saved recipe of (roles, scenario, ordering)
that the orchestrator can replay against new inputs.

Flow shapes:
- ``sequential``   — pipe role₁'s output into role₂'s prompt, etc.
- ``parallel``     — fan out the same input to every role; collect responses.
- ``hierarchical`` — first role is the master; remaining roles are workers.
- ``competitive``  — first role is the consensus judge; remaining roles are candidates.
- ``pipeline``     — run ordered stages with explicit queue handoff messages.
- ``peer_to_peer`` — peers broadcast and review each other's outputs before resolution.

Full DAG/canvas editing is deliberately deferred until these collaboration cases are validated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from . import db
from .sandbox_policy import normalize_policy


@dataclass
class DialogFlow:
    id: int
    owner_id: int
    name: str
    description: str
    flow_type: str
    role_ids: List[str]
    scenario_id: str
    prompt_template: str
    model: str
    sandbox_policy: Dict
    flow_spec: Dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "flow_type": self.flow_type,
            "role_ids": self.role_ids,
            "scenario_id": self.scenario_id,
            "prompt_template": self.prompt_template,
            "model": self.model,
            "sandbox_policy": self.sandbox_policy,
            "flow_spec": self.flow_spec,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Validation ───────────────────────────────────────────────────────────────

VALID_TYPES = {"sequential", "parallel", "hierarchical", "competitive", "pipeline", "peer_to_peer", "dag"}


def normalize_dag_spec(role_ids: List[str], flow_spec: Optional[Dict]) -> Dict:
    """Return a normalized DAG spec and reject invalid/cyclic graphs.

    The public schema is intentionally small:
    {
      "nodes": [
        {"id": "node-a", "type": "role", "role_id": "codex", "label": "Build"},
        {"id": "kg", "type": "graphrag", "query_template": "{input}", "max_hits": 3}
      ],
      "edges": [{"from": "node-a", "to": "node-b"}]
    }

    If nodes are omitted, role_ids are used as node ids and role ids. If edges
    are omitted, every node is treated as a root node and may run in parallel.
    """
    spec = flow_spec if isinstance(flow_spec, dict) else {}
    raw_nodes = spec.get("nodes")
    raw_edges = spec.get("edges")

    if raw_nodes is None:
        nodes = [{"id": role_id, "type": "role", "role_id": role_id, "label": role_id} for role_id in role_ids]
    elif isinstance(raw_nodes, list):
        nodes = []
        for idx, item in enumerate(raw_nodes):
            if not isinstance(item, dict):
                raise ValueError("dag nodes must be objects")
            node_id = str(item.get("id") or "").strip()
            node_type = str(item.get("type") or "role").strip().lower()
            if not node_id:
                raise ValueError(f"dag node at index {idx} is missing id")
            if node_type not in {"role", "graphrag"}:
                raise ValueError("dag node type must be role or graphrag")
            label = str(item.get("label") or node_id).strip()
            if node_type == "role":
                role_id = str(item.get("role_id") or item.get("role") or "").strip()
                if not role_id:
                    raise ValueError(f"dag node {node_id} is missing role_id")
                nodes.append({
                    "id": node_id,
                    "type": "role",
                    "role_id": role_id,
                    "label": label,
                    "prompt_template": str(item.get("prompt_template") or ""),
                })
            else:
                try:
                    max_hits = int(item.get("max_hits") or 3)
                except (TypeError, ValueError):
                    raise ValueError(f"dag graphrag node {node_id} has invalid max_hits") from None
                max_hits = max(1, min(max_hits, 10))
                nodes.append({
                    "id": node_id,
                    "type": "graphrag",
                    "label": label or "GraphRAG",
                    "query_template": str(item.get("query_template") or "{input}"),
                    "max_hits": max_hits,
                })
    else:
        raise ValueError("dag flow_spec.nodes must be a list")

    if not nodes:
        raise ValueError("dag flow requires at least one node")
    if len(nodes) > 20:
        raise ValueError("a single dag flow may include at most 20 nodes")

    node_ids = [node["id"] for node in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise ValueError("dag node ids must be unique")

    node_role_ids = [node["role_id"] for node in nodes if node.get("type") == "role"]
    if role_ids and set(node_role_ids) != set(role_ids):
        raise ValueError("dag node role_ids must match role_ids")
    if not role_ids:
        role_ids = node_role_ids

    if raw_edges is None:
        edges = []
    elif isinstance(raw_edges, list):
        valid_node_ids = set(node_ids)
        seen_edges = set()
        edges = []
        for idx, item in enumerate(raw_edges):
            if not isinstance(item, dict):
                raise ValueError("dag edges must be objects")
            from_id = str(item.get("from") or item.get("source") or "").strip()
            to_id = str(item.get("to") or item.get("target") or "").strip()
            if not from_id or not to_id:
                raise ValueError(f"dag edge at index {idx} must include from and to")
            if from_id == to_id:
                raise ValueError("dag edges cannot point to the same node")
            if from_id not in valid_node_ids or to_id not in valid_node_ids:
                raise ValueError("dag edge references an unknown node")
            key = (from_id, to_id)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append({"from": from_id, "to": to_id})
    else:
        raise ValueError("dag flow_spec.edges must be a list")

    _validate_dag_acyclic(node_ids, edges)
    normalized = dict(spec)
    normalized["nodes"] = nodes
    normalized["edges"] = edges
    return normalized


def _validate_dag_acyclic(node_ids: List[str], edges: List[Dict]) -> None:
    outgoing = {node_id: [] for node_id in node_ids}
    indegree = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1

    ready = [node_id for node_id in node_ids if indegree[node_id] == 0]
    visited = 0
    while ready:
        node_id = ready.pop(0)
        visited += 1
        for child in outgoing[node_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if visited != len(node_ids):
        raise ValueError("dag flow_spec contains a cycle")


def _validate(name: str, flow_type: str, role_ids: List[str], flow_spec: Optional[Dict] = None) -> None:
    if not name or not name.strip():
        raise ValueError("flow name cannot be empty")
    if flow_type not in VALID_TYPES:
        raise ValueError(f"flow_type must be one of {sorted(VALID_TYPES)}")
    if not role_ids:
        raise ValueError("role_ids cannot be empty")
    if flow_type == "hierarchical" and len(role_ids) < 2:
        raise ValueError("hierarchical flow requires a master and at least one worker")
    if flow_type == "competitive" and len(role_ids) < 2:
        raise ValueError("competitive flow requires a consensus agent and at least one candidate")
    if flow_type == "pipeline" and len(role_ids) < 2:
        raise ValueError("pipeline flow requires at least two stage roles")
    if flow_type == "peer_to_peer" and len(role_ids) < 2:
        raise ValueError("peer_to_peer flow requires at least two peer roles")
    if flow_type == "dag":
        normalize_dag_spec(role_ids, flow_spec)
    if len(role_ids) > 20:
        raise ValueError("a single flow may include at most 20 roles")
    if len(set(role_ids)) != len(role_ids):
        raise ValueError("role_ids must be unique within a flow")


# ── Row mapping ──────────────────────────────────────────────────────────────

def _row_to_flow(row) -> DialogFlow:
    raw_ids = row["role_ids"]
    try:
        parsed = json.loads(raw_ids) if raw_ids else []
    except (TypeError, ValueError):
        parsed = []
    if not isinstance(parsed, list):
        parsed = []
    try:
        raw_policy = row["sandbox_policy"]
    except (KeyError, IndexError):
        raw_policy = "{}"
    try:
        sandbox_policy = normalize_policy(json.loads(raw_policy or "{}"))
    except (TypeError, ValueError):
        sandbox_policy = normalize_policy(None)
    try:
        raw_spec = row["flow_spec"]
    except (KeyError, IndexError):
        raw_spec = "{}"
    try:
        flow_spec = json.loads(raw_spec or "{}")
    except (TypeError, ValueError):
        flow_spec = {}
    if not isinstance(flow_spec, dict):
        flow_spec = {}
    return DialogFlow(
        id=row["id"],
        owner_id=row["owner_id"],
        name=row["name"] or "",
        description=row["description"] or "",
        flow_type=row["flow_type"] or "sequential",
        role_ids=[str(x) for x in parsed],
        scenario_id=row["scenario_id"] or "",
        prompt_template=row["prompt_template"] or "",
        model=row["model"] or "deepseek-v4-flash",
        sandbox_policy=sandbox_policy,
        flow_spec=flow_spec,
        created_at=row["created_at"] or "",
        updated_at=row["updated_at"] or "",
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create(
    *,
    name: str,
    flow_type: str,
    role_ids: List[str],
    description: str = "",
    scenario_id: str = "",
    prompt_template: str = "",
    model: str = "",
    sandbox_policy: Optional[Dict] = None,
    flow_spec: Optional[Dict] = None,
    owner_id: int = 0,
) -> DialogFlow:
    _validate(name, flow_type, role_ids, flow_spec)
    normalized_policy = normalize_policy(sandbox_policy)
    normalized_spec = flow_spec if isinstance(flow_spec, dict) else {}
    if flow_type == "dag":
        normalized_spec = normalize_dag_spec(role_ids, normalized_spec)
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO dialog_flows
               (owner_id, name, description, flow_type, role_ids, scenario_id, prompt_template, model, sandbox_policy, flow_spec)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                owner_id, name.strip(), description, flow_type,
                json.dumps(role_ids), scenario_id, prompt_template, model or "deepseek-v4-flash",
                json.dumps(normalized_policy, ensure_ascii=False),
                json.dumps(normalized_spec, ensure_ascii=False),
            ),
        )
        flow_id = cur.lastrowid
    return get(flow_id)


def get(flow_id: int) -> DialogFlow:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM dialog_flows WHERE id = ?", (flow_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"flow not found: {flow_id}")
    return _row_to_flow(row)


def list_flows(owner_id: Optional[int] = None) -> List[DialogFlow]:
    with db.cursor() as cur:
        if owner_id is None:
            cur.execute("SELECT * FROM dialog_flows ORDER BY updated_at DESC")
        else:
            cur.execute(
                "SELECT * FROM dialog_flows WHERE owner_id = ? ORDER BY updated_at DESC",
                (owner_id,),
            )
        rows = cur.fetchall()
    return [_row_to_flow(r) for r in rows]


def update(
    flow_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    flow_type: Optional[str] = None,
    role_ids: Optional[List[str]] = None,
    scenario_id: Optional[str] = None,
    prompt_template: Optional[str] = None,
    model: Optional[str] = None,
    sandbox_policy: Optional[Dict] = None,
    flow_spec: Optional[Dict] = None,
) -> DialogFlow:
    current = get(flow_id)
    new_name = name if name is not None else current.name
    new_type = flow_type if flow_type is not None else current.flow_type
    new_roles = role_ids if role_ids is not None else current.role_ids
    new_spec = flow_spec if isinstance(flow_spec, dict) else current.flow_spec
    _validate(new_name, new_type, new_roles, new_spec)
    new_policy = normalize_policy(sandbox_policy if sandbox_policy is not None else current.sandbox_policy)
    if new_type == "dag":
        new_spec = normalize_dag_spec(new_roles, new_spec)

    with db.cursor() as cur:
        cur.execute(
            """UPDATE dialog_flows SET
                 name = ?, description = ?, flow_type = ?, role_ids = ?,
                 scenario_id = ?, prompt_template = ?, model = ?, sandbox_policy = ?,
                 flow_spec = ?, updated_at = ?
               WHERE id = ?""",
            (
                new_name.strip(),
                description if description is not None else current.description,
                new_type,
                json.dumps(new_roles),
                scenario_id if scenario_id is not None else current.scenario_id,
                prompt_template if prompt_template is not None else current.prompt_template,
                model if model is not None else current.model,
                json.dumps(new_policy, ensure_ascii=False),
                json.dumps(new_spec, ensure_ascii=False),
                datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
                flow_id,
            ),
        )
    return get(flow_id)


def delete(flow_id: int) -> None:
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM collaboration_messages WHERE run_id IN (SELECT id FROM flow_runs WHERE flow_id = ?)",
            (flow_id,),
        )
        cur.execute(
            "DELETE FROM flow_run_events WHERE run_id IN (SELECT id FROM flow_runs WHERE flow_id = ?)",
            (flow_id,),
        )
        cur.execute("DELETE FROM flow_runs WHERE flow_id = ?", (flow_id,))
        cur.execute("DELETE FROM dialog_flows WHERE id = ?", (flow_id,))
