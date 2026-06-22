"""Collaboration message protocol for multi-agent flow orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

MESSAGE_STATUSES = {"queued", "sent", "received", "failed", "timed_out"}
TERMINAL_STATUSES = {"received", "failed", "timed_out"}
ALLOWED_TRANSITIONS = {
    "queued": {"queued", "sent", "failed", "timed_out"},
    "sent": {"sent", "received", "failed", "timed_out"},
    "received": {"received"},
    "failed": {"failed"},
    "timed_out": {"timed_out"},
}


@dataclass
class CollaborationMessage:
    """A persisted message exchanged during a Flow run.

    ``from_agent`` and ``to_agent`` may be role ids or orchestrator-level
    actors such as ``orchestrator``. ``role_id`` and ``output_index`` keep the
    message tied to the legacy run output model used by sequential/parallel
    flows.
    """

    run_id: int
    from_agent: str
    to_agent: str
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_ms: Optional[int] = None
    status: str = "queued"
    role_id: Optional[str] = None
    output_index: Optional[int] = None
    id: Optional[int] = None
    seq: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.run_id <= 0:
            raise ValueError("run_id must be positive")
        if not self.from_agent:
            raise ValueError("from_agent cannot be empty")
        if not self.to_agent:
            raise ValueError("to_agent cannot be empty")
        if not self.type:
            raise ValueError("type cannot be empty")
        if self.status not in MESSAGE_STATUSES:
            raise ValueError(f"status must be one of {sorted(MESSAGE_STATUSES)}")
        if self.timeout_ms is not None and self.timeout_ms < 0:
            raise ValueError("timeout_ms cannot be negative")
        if self.output_index is not None and self.output_index < 0:
            raise ValueError("output_index cannot be negative")
        if self.seq is not None and self.seq <= 0:
            raise ValueError("seq must be positive")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be a dict")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "seq": self.seq,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "type": self.type,
            "payload": self.payload,
            "priority": self.priority,
            "timeout_ms": self.timeout_ms,
            "status": self.status,
            "role_id": self.role_id,
            "output_index": self.output_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollaborationMessage":
        return cls(
            id=data.get("id"),
            run_id=int(data["run_id"]),
            seq=data.get("seq"),
            from_agent=str(data["from_agent"]),
            to_agent=str(data["to_agent"]),
            type=str(data["type"]),
            payload=dict(data.get("payload") or {}),
            priority=int(data.get("priority") or 0),
            timeout_ms=data.get("timeout_ms"),
            status=str(data.get("status") or "queued"),
            role_id=data.get("role_id"),
            output_index=data.get("output_index"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def transition(self, next_status: str) -> "CollaborationMessage":
        if next_status not in MESSAGE_STATUSES:
            raise ValueError(f"status must be one of {sorted(MESSAGE_STATUSES)}")
        if next_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"cannot transition message from {self.status} to {next_status}")
        self.status = next_status
        self.updated_at = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
        return self
