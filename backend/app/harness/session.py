"""会话生命周期子系统

Manages the full lifecycle of agent sessions:
- State machine: initial → active → paused / waiting / error → ended
- Per-user concurrency limits
- Idle / max-duration / pause timeout enforcement
- Runtime metrics (turn_count, tool_calls, errors)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Timeouts (seconds) ──────────────────────────────────────────────────────
IDLE_TIMEOUT     = 60 * 60   # 60 min  – no user activity
MAX_DURATION     = 120 * 60  # 2 hours – hard wall-clock limit
PAUSE_TIMEOUT    = 24 * 60 * 60  # 24 hours – resumed before this or discarded

# ── Concurrency limits ───────────────────────────────────────────────────────
MAX_SESSIONS_TOTAL = 100
MAX_SESSIONS_PER_USER = 20


class SessionStatus(str, Enum):
    INITIAL  = "initial"
    ACTIVE   = "active"
    PAUSED   = "paused"
    WAITING  = "waiting"   # waiting for tool result
    ERROR    = "error"
    ENDED    = "ended"


@dataclass
class Session:
    session_id: str
    user_id: int
    status: SessionStatus = SessionStatus.INITIAL

    # Timestamps
    created_at: float  = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    paused_at: Optional[float] = None

    # Execution position
    current_node: str = "start"
    current_step: int = 0

    # Metrics
    turn_count: int  = 0
    tool_calls: int  = 0
    error_count: int = 0

    # Arbitrary metadata (skill_name, conversation_id …)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Lifecycle transitions ────────────────────────────────────────────────

    def activate(self) -> None:
        self.status = SessionStatus.ACTIVE
        self.last_active = time.time()

    def mark_waiting(self) -> None:
        self.status = SessionStatus.WAITING

    def resume_from_waiting(self) -> None:
        if self.status == SessionStatus.WAITING:
            self.status = SessionStatus.ACTIVE
            self.last_active = time.time()

    def pause(self) -> None:
        self.status = SessionStatus.PAUSED
        self.paused_at = time.time()

    def resume(self) -> None:
        self.status = SessionStatus.ACTIVE
        self.paused_at = None
        self.last_active = time.time()

    def end(self) -> None:
        self.status = SessionStatus.ENDED

    def mark_error(self) -> None:
        self.status = SessionStatus.ERROR
        self.error_count += 1

    # ── Timeout checks ───────────────────────────────────────────────────────

    def is_idle_expired(self) -> bool:
        return (
            self.status == SessionStatus.ACTIVE
            and (time.time() - self.last_active) > IDLE_TIMEOUT
        )

    def is_max_duration_exceeded(self) -> bool:
        return (time.time() - self.created_at) > MAX_DURATION

    def is_pause_expired(self) -> bool:
        return (
            self.status == SessionStatus.PAUSED
            and self.paused_at is not None
            and (time.time() - self.paused_at) > PAUSE_TIMEOUT
        )

    def duration(self) -> float:
        return time.time() - self.created_at


class SessionManager:
    """Singleton-friendly manager for in-process session tracking.

    In production this would sync state to Redis; here it uses an in-memory
    dict, which is sufficient for a single-process uvicorn deployment.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}   # session_id → Session
        self._user_sessions: Dict[int, list] = {} # user_id → [session_id]

    # ── Creation ─────────────────────────────────────────────────────────────

    def create_session(
        self,
        user_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Create a new session for the user, enforcing concurrency limits."""
        # Evict expired sessions first
        self._evict_expired()

        total = len(self._sessions)
        if total >= MAX_SESSIONS_TOTAL:
            raise RuntimeError(f"系统并发会话已达上限（{MAX_SESSIONS_TOTAL}），请稍后重试")

        user_active = len(self._user_sessions.get(user_id, []))
        if user_active >= MAX_SESSIONS_PER_USER:
            raise RuntimeError(
                f"您已有 {user_active} 个活跃会话（上限 {MAX_SESSIONS_PER_USER}），"
                "请关闭旧会话后再试"
            )

        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._user_sessions.setdefault(user_id, []).append(session_id)

        logger.info("session_created", session_id=session_id, user_id=user_id)
        return session

    # ── Retrieval ────────────────────────────────────────────────────────────

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def get_user_sessions(self, user_id: int) -> list:
        ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in ids if sid in self._sessions]

    # ── Closing ──────────────────────────────────────────────────────────────

    def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            session.end()
            uid = session.user_id
            if uid in self._user_sessions:
                try:
                    self._user_sessions[uid].remove(session_id)
                except ValueError:
                    pass
            logger.info(
                "session_closed",
                session_id=session_id,
                turns=session.turn_count,
                duration=round(session.duration(), 1),
            )

    # ── Metrics ──────────────────────────────────────────────────────────────

    def metrics(self) -> Dict[str, Any]:
        sessions = list(self._sessions.values())
        total = len(sessions)
        ended = sum(1 for s in sessions if s.status == SessionStatus.ENDED)
        errors = sum(1 for s in sessions if s.status == SessionStatus.ERROR)
        avg_dur = (
            sum(s.duration() for s in sessions) / total if total else 0.0
        )
        return {
            "active_sessions": total - ended,
            "total_sessions": total,
            "error_sessions": errors,
            "avg_duration_s": round(avg_dur, 1),
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        expired = [
            sid for sid, s in list(self._sessions.items())
            if s.status == SessionStatus.ENDED
            or s.is_idle_expired()
            or s.is_max_duration_exceeded()
            or s.is_pause_expired()
        ]
        for sid in expired:
            self.close_session(sid)


# ── Module-level singleton ────────────────────────────────────────────────────
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
