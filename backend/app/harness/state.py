"""状态子系统

Multi-tier agent state management:
- In-process AgentState dataclass (conversation, task plan, context, metadata)
- StateManager: create / get / update / checkpoint / restore operations
- In-memory checkpointing with optional Redis persistence (TTL 30 min)
- StateMonitor for runtime metrics
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Redis key prefix and TTL for session checkpoints
_CP_KEY_PREFIX = "session_checkpoint"
_CP_TTL_SECONDS = 30 * 60  # 30 minutes


# ── Message types ─────────────────────────────────────────────────────────────

@dataclass
class Message:
    role: str          # "user" | "assistant" | "tool"
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None


# ── Task plan step ────────────────────────────────────────────────────────────

@dataclass
class PlanStep:
    step: int
    action: str        # tool name or sub-task label
    description: str = ""   # human-readable step description
    status: str = "pending"   # pending | running | completed | failed
    result: Any = None
    error: Optional[str] = None


# ── Core AgentState ───────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Runtime state for a single agent session."""

    session_id: str
    user_id: int

    # Conversation history
    messages: List[Message] = field(default_factory=list)
    turn_count: int = 0

    # Task execution
    current_task: str = ""
    plan: List[PlanStep] = field(default_factory=list)
    plan_id: Optional[str] = None     # unique ID for the current execution plan
    current_step: int = 0
    tool_results: Dict[str, Any] = field(default_factory=dict)
    child_workers: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Phase 3: worker tracking

    # User context
    user_tier: str = "free"
    skill_name: Optional[str] = None
    system_prompt: str = ""

    # Validation / safety
    input_valid: bool = True
    safety_passed: bool = True
    retry_count: int = 0

    # Metadata
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    checkpoints: List[str] = field(default_factory=list)

    # ── Convenience helpers ───────────────────────────────────────────────────

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        self.messages.append(Message(role=role, content=content, **kwargs))
        self.last_active = time.time()
        if role == "user":
            self.turn_count += 1

    def add_plan_step(self, action: str, description: str = "") -> PlanStep:
        step_no = len(self.plan) + 1
        step = PlanStep(step=step_no, action=action, description=description)
        self.plan.append(step)
        return step

    def mark_step_done(self, action: str, result: Any = None) -> None:
        for s in self.plan:
            if s.action == action and s.status == "running":
                s.status = "completed"
                s.result = result
                break

    def mark_step_failed(self, action: str, error: str) -> None:
        for s in self.plan:
            if s.action == action:
                s.status = "failed"
                s.error = error
                break

    def active_steps(self) -> List[PlanStep]:
        return [s for s in self.plan if s.status in ("pending", "running")]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise state to a plain dict (JSON-compatible)."""
        d = asdict(self)
        return d


# ── Checkpoint ────────────────────────────────────────────────────────────────

@dataclass
class Checkpoint:
    checkpoint_id: str
    session_id: str
    step: int
    state_snapshot: Dict[str, Any]
    created_at: float = field(default_factory=time.time)


# ── StateMonitor ──────────────────────────────────────────────────────────────

class StateMonitor:
    """Lightweight metrics collector for the state subsystem."""

    def __init__(self) -> None:
        self._metrics: Dict[str, int] = {
            "active_sessions": 0,
            "total_checkpoints": 0,
            "recovery_count": 0,
            "state_updates": 0,
        }

    def on_session_created(self) -> None:
        self._metrics["active_sessions"] += 1

    def on_session_ended(self) -> None:
        self._metrics["active_sessions"] = max(
            0, self._metrics["active_sessions"] - 1
        )

    def on_checkpoint(self, session_id: str, step: int) -> None:
        self._metrics["total_checkpoints"] += 1
        logger.debug("state_checkpoint", session_id=session_id, step=step)

    def on_recovery(self, session_id: str) -> None:
        self._metrics["recovery_count"] += 1
        logger.info("state_recovered", session_id=session_id)

    def on_update(self) -> None:
        self._metrics["state_updates"] += 1

    def get_stats(self) -> Dict[str, int]:
        return dict(self._metrics)


# ── StateManager ──────────────────────────────────────────────────────────────

class StateManager:
    """Create, update, checkpoint, and restore agent states.

    Checkpoints are kept in-process and optionally persisted to Redis
    (TTL 30 min) so that they survive across uvicorn worker restarts.
    Pass a redis client via `attach_redis()` to enable persistence.
    """

    _CHECKPOINT_LIMIT = 20   # keep at most N checkpoints per session

    def __init__(self) -> None:
        self._states: Dict[str, AgentState] = {}           # session_id → state
        self._checkpoints: Dict[str, List[Checkpoint]] = {} # session_id → [cp]
        self.monitor = StateMonitor()
        self._redis: Any = None   # optional Redis client

    def attach_redis(self, redis_client: Any) -> None:
        """Attach a Redis client for cross-process checkpoint persistence."""
        self._redis = redis_client

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def create(
        self,
        session_id: str,
        user_id: int,
        user_tier: str = "free",
        skill_name: Optional[str] = None,
    ) -> AgentState:
        """Create and register a new AgentState."""
        state = AgentState(
            session_id=session_id,
            user_id=user_id,
            user_tier=user_tier,
            skill_name=skill_name,
        )
        self._states[session_id] = state
        self._checkpoints[session_id] = []
        self.monitor.on_session_created()
        logger.info("state_created", session_id=session_id, user_id=user_id)
        return state

    def get(self, session_id: str) -> Optional[AgentState]:
        return self._states.get(session_id)

    def update(self, session_id: str, **fields: Any) -> bool:
        """Patch one or more top-level fields on an existing state."""
        state = self._states.get(session_id)
        if state is None:
            return False
        for k, v in fields.items():
            if hasattr(state, k):
                setattr(state, k, v)
            else:
                logger.warning("state_unknown_field", field=k)
        state.last_active = time.time()
        self.monitor.on_update()
        return True

    def end(self, session_id: str) -> None:
        """Remove state from active registry and clean up Redis checkpoint."""
        self._states.pop(session_id, None)
        self._checkpoints.pop(session_id, None)
        self.monitor.on_session_ended()
        logger.info("state_ended", session_id=session_id)

    async def end_async(self, session_id: str) -> None:
        """Remove state from active registry and clean up Redis checkpoint (async)."""
        self._states.pop(session_id, None)
        self._checkpoints.pop(session_id, None)
        self.monitor.on_session_ended()
        # Clean up Redis checkpoint
        if self._redis is not None:
            key = f"{_CP_KEY_PREFIX}:{session_id}"
            try:
                await self._redis.delete(key)
                logger.debug("state_redis_checkpoint_cleaned", session_id=session_id)
            except Exception as exc:
                logger.warning("state_redis_checkpoint_cleanup_failed", session_id=session_id, error=str(exc))
        logger.info("state_ended", session_id=session_id)

    # ── Checkpointing ─────────────────────────────────────────────────────────

    def checkpoint(self, session_id: str) -> Optional[str]:
        """Save an in-memory snapshot of the current state. Returns checkpoint_id."""
        state = self._states.get(session_id)
        if state is None:
            return None

        cp_id = str(uuid.uuid4())[:8]
        snapshot = copy.deepcopy(state.to_dict())
        cp = Checkpoint(
            checkpoint_id=cp_id,
            session_id=session_id,
            step=state.current_step,
            state_snapshot=snapshot,
        )

        cps = self._checkpoints.setdefault(session_id, [])
        cps.append(cp)
        # Trim oldest if over limit
        if len(cps) > self._CHECKPOINT_LIMIT:
            cps.pop(0)

        state.checkpoints.append(cp_id)
        self.monitor.on_checkpoint(session_id, state.current_step)
        logger.debug("state_checkpointed", session_id=session_id, cp_id=cp_id)
        return cp_id

    async def checkpoint_async(self, session_id: str) -> Optional[str]:
        """Checkpoint in-memory and also persist to Redis (TTL 30 min) if available."""
        cp_id = self.checkpoint(session_id)
        if cp_id and self._redis is not None:
            cps = self._checkpoints.get(session_id, [])
            if cps:
                key = f"{_CP_KEY_PREFIX}:{session_id}"
                try:
                    await self._redis.set(
                        key,
                        json.dumps(cps[-1].state_snapshot, ensure_ascii=False, default=str),
                        ex=_CP_TTL_SECONDS,
                    )
                except Exception as exc:
                    logger.warning("state_redis_checkpoint_failed", session_id=session_id, error=str(exc))
        return cp_id

    def restore(
        self, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[AgentState]:
        """Restore state from an in-memory checkpoint (latest if checkpoint_id is None)."""
        cps = self._checkpoints.get(session_id, [])
        if not cps:
            return None

        if checkpoint_id:
            cp = next((c for c in cps if c.checkpoint_id == checkpoint_id), None)
        else:
            cp = cps[-1]  # latest

        if cp is None:
            return None

        restored = self._restore_from_snapshot(cp.state_snapshot)
        self._states[session_id] = restored
        self.monitor.on_recovery(session_id)
        logger.info("state_restored", session_id=session_id, cp_id=cp.checkpoint_id)
        return restored

    async def restore_from_redis(self, session_id: str) -> Optional[AgentState]:
        """Restore the latest checkpoint from Redis (cross-process recovery)."""
        if self._redis is None:
            return None
        key = f"{_CP_KEY_PREFIX}:{session_id}"
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            snapshot = json.loads(raw)
            restored = self._restore_from_snapshot(snapshot)
            self._states[session_id] = restored
            self.monitor.on_recovery(session_id)
            logger.info("state_restored_from_redis", session_id=session_id)
            return restored
        except Exception as exc:
            logger.warning("state_redis_restore_failed", session_id=session_id, error=str(exc))
            return None

    def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        return [
            {
                "checkpoint_id": c.checkpoint_id,
                "step": c.step,
                "created_at": c.created_at,
            }
            for c in self._checkpoints.get(session_id, [])
        ]

    # ── Export / import ───────────────────────────────────────────────────────

    def export_state(self, session_id: str) -> Optional[str]:
        """Serialise current state to a JSON string."""
        state = self._states.get(session_id)
        if state is None:
            return None
        return json.dumps(state.to_dict(), ensure_ascii=False, default=str)

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _restore_from_snapshot(snapshot: Dict[str, Any]) -> AgentState:
        state = AgentState(
            session_id=snapshot["session_id"],
            user_id=snapshot["user_id"],
        )
        # Restore scalar fields
        for key in (
            "turn_count", "current_task", "current_step",
            "user_tier", "skill_name", "system_prompt",
            "input_valid", "safety_passed", "retry_count",
            "created_at", "last_active", "checkpoints",
            "tool_results", "plan_id", "child_workers",
        ):
            if key in snapshot:
                setattr(state, key, snapshot[key])
        # Restore messages
        state.messages = [
            Message(**m) for m in snapshot.get("messages", [])
        ]
        # Restore plan steps
        state.plan = [
            PlanStep(**s) for s in snapshot.get("plan", [])
        ]
        return state

    # ── Metrics ───────────────────────────────────────────────────────────────

    def metrics(self) -> Dict[str, Any]:
        stats = self.monitor.get_stats()
        stats["tracked_sessions"] = len(self._states)
        stats["total_checkpoint_entries"] = sum(
            len(v) for v in self._checkpoints.values()
        )
        return stats


# ── Module-level singleton ────────────────────────────────────────────────────
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
