"""CRUD for ``dialog_flows`` — a saved recipe of (roles, scenario, ordering)
that the orchestrator can replay against new inputs.

Flow shapes:
- ``sequential`` — pipe role₁'s output into role₂'s prompt, etc.
- ``parallel``   — fan out the same input to every role; collect responses.

DAG flows are deliberately deferred until the linear cases are validated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from . import db


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
    created_at: str
    updated_at: str

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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Validation ───────────────────────────────────────────────────────────────

VALID_TYPES = {"sequential", "parallel"}


def _validate(name: str, flow_type: str, role_ids: List[str]) -> None:
    if not name or not name.strip():
        raise ValueError("flow name cannot be empty")
    if flow_type not in VALID_TYPES:
        raise ValueError(f"flow_type must be one of {sorted(VALID_TYPES)}")
    if not role_ids:
        raise ValueError("role_ids cannot be empty")
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
    owner_id: int = 0,
) -> DialogFlow:
    _validate(name, flow_type, role_ids)
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO dialog_flows
               (owner_id, name, description, flow_type, role_ids, scenario_id, prompt_template, model)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                owner_id, name.strip(), description, flow_type,
                json.dumps(role_ids), scenario_id, prompt_template, model or "deepseek-v4-flash",
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
) -> DialogFlow:
    current = get(flow_id)
    new_name = name if name is not None else current.name
    new_type = flow_type if flow_type is not None else current.flow_type
    new_roles = role_ids if role_ids is not None else current.role_ids
    _validate(new_name, new_type, new_roles)

    with db.cursor() as cur:
        cur.execute(
            """UPDATE dialog_flows SET
                 name = ?, description = ?, flow_type = ?, role_ids = ?,
                 scenario_id = ?, prompt_template = ?, model = ?,
                 updated_at = ?
               WHERE id = ?""",
            (
                new_name.strip(),
                description if description is not None else current.description,
                new_type,
                json.dumps(new_roles),
                scenario_id if scenario_id is not None else current.scenario_id,
                prompt_template if prompt_template is not None else current.prompt_template,
                model if model is not None else current.model,
                datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
                flow_id,
            ),
        )
    return get(flow_id)


def delete(flow_id: int) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM flow_runs WHERE flow_id = ?", (flow_id,))
        cur.execute("DELETE FROM dialog_flows WHERE id = ?", (flow_id,))
