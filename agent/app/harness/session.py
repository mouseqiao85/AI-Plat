"""Session lifecycle subsystem for agent-platform."""
from __future__ import annotations

import asyncio
import time
import uuid
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

IDLE_TIMEOUT = 60 * 60
MAX_DURATION = 120 * 60
PAUSE_TIMEOUT = 24 * 60 * 60
MAX_SESSIONS_TOTAL = 100
MAX_SESSIONS_PER_USER = 20


class SessionStatus(str, Enum):
    INITIAL = "initial"
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING = "waiting"
    ERROR = "error"
    ENDED = "ended"


@dataclass
class Session:
    session_id: str
    user_id: int
    status: SessionStatus = SessionStatus.INITIAL
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    paused_at: Optional[float] = None
    current_node: str = "start"
    current_step: int = 0
    turn_count: int = 0
    tool_calls: int = 0
    error_count: int = 0
    sandbox_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def activate(self) -> None:
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

    def is_idle_expired(self) -> bool:
        return self.status == SessionStatus.ACTIVE and (time.time() - self.last_active) > IDLE_TIMEOUT

    def is_max_duration_exceeded(self) -> bool:
        return (time.time() - self.created_at) > MAX_DURATION

    def duration(self) -> float:
        return time.time() - self.created_at


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[int, list] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, user_id: int, metadata: Optional[Dict[str, Any]] = None) -> Session:
        from app.harness.sandbox import get_sandbox_manager
        async with self._lock:
            self._evict_expired()
            total = len(self._sessions)
            if total >= MAX_SESSIONS_TOTAL:
                raise RuntimeError(f"系统并发会话已达上限（{MAX_SESSIONS_TOTAL}）")
            user_active = len(self._user_sessions.get(user_id, []))
            if user_active >= MAX_SESSIONS_PER_USER:
                raise RuntimeError(f"您已有 {user_active} 个活跃会话（上限 {MAX_SESSIONS_PER_USER}）")
            session_id = str(uuid.uuid4())
            session = Session(session_id=session_id, user_id=user_id, metadata=metadata or {})
            self._sessions[session_id] = session
            self._user_sessions.setdefault(user_id, []).append(session_id)
        sandbox_mgr = get_sandbox_manager()
        sandbox = await sandbox_mgr.create_sandbox(session_id)
        session.sandbox_path = str(sandbox.path)
        logger.info("session_created session_id=%s user_id=%d sandbox=%s", session_id, user_id, session.sandbox_path)
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        from app.harness.sandbox import get_sandbox_manager
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                session.end()
                uid = session.user_id
                if uid in self._user_sessions:
                    try:
                        self._user_sessions[uid].remove(session_id)
                    except ValueError:
                        pass
        if session:
            sandbox_mgr = get_sandbox_manager()
            await sandbox_mgr.remove_sandbox(session_id)

    def _evict_expired(self) -> None:
        expired = [
            sid for sid, s in list(self._sessions.items())
            if s.status == SessionStatus.ENDED or s.is_idle_expired() or s.is_max_duration_exceeded()
        ]
        for sid in expired:
            s = self._sessions.pop(sid, None)
            if s:
                s.end()
                uid = s.user_id
                if uid in self._user_sessions:
                    try:
                        self._user_sessions[uid].remove(sid)
                    except ValueError:
                        pass

    async def force_cleanup_zombies(self) -> int:
        """Remove ACTIVE sessions that exceed idle timeout (zombie cleanup)."""
        async with self._lock:
            now = time.time()
            zombie = [
                sid for sid, s in list(self._sessions.items())
                if s.status in (SessionStatus.ACTIVE,)
                and (now - s.last_active) > IDLE_TIMEOUT
            ]
            for sid in zombie:
                s = self._sessions.pop(sid, None)
                if s:
                    s.end()
                    uid = s.user_id
                    if uid in self._user_sessions:
                        try:
                            self._user_sessions[uid].remove(sid)
                        except ValueError:
                            pass
            return len(zombie)

    async def total_count(self) -> int:
        async with self._lock:
            return len(self._sessions)


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
