"""Session lifecycle manager for agent workflows.

Tracks all active workflow sessions and provides automatic cleanup
of orphaned processes and timed-out sessions.

Usage:
    manager = get_session_manager()
    manager.register(session_id, state, timeout=600)
    manager.register_child_pid(session_id, pid)
    manager.cleanup_stale()  # called periodically by a background thread
"""

import logging
import os
import signal
import time
from dataclasses import dataclass, field
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    """Runtime record for a single active workflow session."""
    session_id: str
    pid: int                   # Main process PID that owns this session
    created_at: float          # Unix timestamp when session started
    timeout_at: float          # Unix timestamp when session expires
    child_pids: set = field(default_factory=set)  # Sub-process PIDs to kill on cleanup
    conversation_id: int = 0
    user_id: int = 0
    intent: str = ""

    @property
    def age(self) -> float:
        """Seconds since session was created."""
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        """True if the session has exceeded its TTL."""
        return time.time() > self.timeout_at


class SessionManager:
    """Manages all active workflow sessions.

    Thread-safe for reads (single-threaded cleanup), callers must not
    mutate returned SessionRecord objects from different threads.
    """

    def __init__(self):
        self._sessions: dict[str, SessionRecord] = {}

    # ── Registration ──────────────────────────────────────────────────

    def register(self, session_id: str, timeout_at: float,
                 pid: int = 0, conversation_id: int = 0,
                 user_id: int = 0, intent: str = "") -> SessionRecord:
        """Create and store a new session record.

        If a record already exists for this session_id, the old one is
        returned unchanged (no double-registration).
        """
        if session_id in self._sessions:
            return self._sessions[session_id]

        now = time.time()
        record = SessionRecord(
            session_id=session_id,
            pid=pid or os.getpid(),
            created_at=now,
            timeout_at=timeout_at,
            conversation_id=conversation_id,
            user_id=user_id,
            intent=intent,
        )
        self._sessions[session_id] = record
        logger.info(
            "session registered: %s | intent=%s | TTL=%.0fs | expire=%s",
            session_id[:12], intent, timeout_at - now,
            time.strftime("%H:%M:%S", time.localtime(timeout_at)),
        )
        return record

    def unregister(self, session_id: str) -> None:
        """Remove a completed session."""
        record = self._sessions.pop(session_id, None)
        if record:
            logger.info("session unregistered: %s (age=%.1fs)", session_id[:12], record.age)

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    # ── Child PID tracking ────────────────────────────────────────────

    def register_child_pid(self, session_id: str, pid: int) -> bool:
        """Track a child process spawned by this session.

        Returns True if session exists and PID was recorded.
        """
        record = self._sessions.get(session_id)
        if record is None:
            logger.warning("child pid %d for unknown session %s", pid, session_id[:12])
            return False
        record.child_pids.add(pid)
        logger.debug("child pid %d registered for session %s", pid, session_id[:12])
        return True

    def clear_child_pids(self, session_id: str) -> None:
        """Remove all child PID tracking for a session (after successful completion)."""
        record = self._sessions.get(session_id)
        if record:
            record.child_pids.clear()

    # ── Cleanup ───────────────────────────────────────────────────────

    def cleanup_stale(self) -> int:
        """Kill orphan child processes for timed-out sessions.

        Returns the count of sessions that were terminated.
        """
        terminated = 0
        for session_id, record in list(self._sessions.items()):
            if not record.is_expired:
                continue

            logger.warning(
                "session %s EXPIRED | age=%.1fs | children=%d pids=%s",
                session_id[:12], record.age,
                len(record.child_pids), sorted(record.child_pids),
            )

            # Kill orphan child processes
            for pid in record.child_pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    logger.info("  killed child pid %d for session %s", pid, session_id[:12])
                except ProcessLookupError:
                    pass  # Already dead
                except PermissionError:
                    logger.warning("  no permission to kill child pid %d", pid)

            # Remove from tracking
            del self._sessions[session_id]
            terminated += 1

        return terminated

    def kill_all(self) -> int:
        """Force-kill all active sessions. Called during graceful shutdown."""
        count = 0
        for session_id, record in list(self._sessions.items()):
            for pid in record.child_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            count += 1
        self._sessions.clear()
        logger.info("session_manager kill_all: %d sessions terminated", count)
        return count

    def active_count(self) -> int:
        """Number of currently tracked active sessions."""
        return len(self._sessions)

    def list_sessions(self) -> list[dict]:
        """Snapshot of all active sessions (for admin/debug)."""
        return [
            {
                "session_id": s.session_id[:12],
                "age_s": round(s.age, 1),
                "remaining_s": round(s.timeout_at - time.time(), 1),
                "children": len(s.child_pids),
                "intent": s.intent,
                "conversation_id": s.conversation_id,
            }
            for s in self._sessions.values()
        ]


# Global singleton
_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


def reset_session_manager() -> None:
    """Reset the singleton (for testing)."""
    global _manager
    _manager = None
