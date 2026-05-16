"""Bookkeeping for ``flow_runs`` — one row per orchestrator execution.

Phase 2 only persists the lifecycle (pending → running → succeeded/failed)
and final outputs. The streaming layer in Phase 3 writes intermediate
deltas straight to SSE; only the resolved per-role chunks land here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from . import db


@dataclass
class RoleOutput:
    role_id: str
    content: str
    latency_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "content": self.content,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class FlowRun:
    id: int
    flow_id: int
    input_text: str
    status: str
    error: str
    outputs: List[Dict]
    started_at: str
    finished_at: Optional[str]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "flow_id": self.flow_id,
            "input_text": self.input_text,
            "status": self.status,
            "error": self.error,
            "outputs": self.outputs,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


def _row_to_run(row) -> FlowRun:
    return FlowRun(
        id=row["id"],
        flow_id=row["flow_id"],
        input_text=row["input_text"],
        status=row["status"],
        error=row["error"] or "",
        outputs=json.loads(row["outputs"] or "[]"),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


def create(flow_id: int, input_text: str) -> FlowRun:
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO flow_runs (flow_id, input_text, status, outputs)
               VALUES (?, ?, 'pending', '[]')""",
            (flow_id, input_text),
        )
        run_id = cur.lastrowid
    return get(run_id)


def get(run_id: int) -> FlowRun:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM flow_runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"run not found: {run_id}")
    return _row_to_run(row)


def list_for_flow(flow_id: int, limit: int = 50) -> List[FlowRun]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM flow_runs WHERE flow_id = ? ORDER BY started_at DESC LIMIT ?",
            (flow_id, limit),
        )
        rows = cur.fetchall()
    return [_row_to_run(r) for r in rows]


def mark_running(run_id: int) -> None:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE flow_runs SET status = 'running' WHERE id = ?", (run_id,),
        )


def append_output(run_id: int, output: RoleOutput) -> None:
    """Append one role's resolved output. Atomic via the in-process lock."""
    with db.cursor() as cur:
        cur.execute("SELECT outputs FROM flow_runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(f"run not found: {run_id}")
        outputs = json.loads(row["outputs"] or "[]")
        outputs.append(output.to_dict())
        cur.execute(
            "UPDATE flow_runs SET outputs = ? WHERE id = ?",
            (json.dumps(outputs, ensure_ascii=False), run_id),
        )


def finalize(run_id: int, status: str, error: str = "") -> None:
    if status not in {"succeeded", "failed", "cancelled"}:
        raise ValueError(f"invalid terminal status: {status}")
    with db.cursor() as cur:
        cur.execute(
            "UPDATE flow_runs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
            (status, error, datetime.utcnow().isoformat(sep=" ", timespec="seconds"), run_id),
        )
