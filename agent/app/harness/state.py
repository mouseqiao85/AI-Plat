"""State subsystem for agent-platform."""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlanStep:
    step: int
    action: str
    description: str = ""
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None


@dataclass
class AgentState:
    session_id: str
    user_id: int
    messages: List[Dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    current_task: str = ""
    plan: List[PlanStep] = field(default_factory=list)
    current_step: int = 0
    tool_results: Dict[str, Any] = field(default_factory=dict)
    user_tier: str = "free"
    skill_name: Optional[str] = None
    system_prompt: str = ""
    input_valid: bool = True
    safety_passed: bool = True
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    checkpoints: List[str] = field(default_factory=list)

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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Checkpoint:
    checkpoint_id: str
    session_id: str
    step: int
    state_snapshot: Dict[str, Any]
    created_at: float = field(default_factory=time.time)


class StateManager:
    _CHECKPOINT_LIMIT = 20

    def __init__(self) -> None:
        self._states: Dict[str, AgentState] = {}
        self._checkpoints: Dict[str, List[Checkpoint]] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str, user_id: int, user_tier: str = "free", skill_name: Optional[str] = None) -> AgentState:
        async with self._lock:
            state = AgentState(session_id=session_id, user_id=user_id, user_tier=user_tier, skill_name=skill_name)
            self._states[session_id] = state
            self._checkpoints[session_id] = []
            return state

    async def get(self, session_id: str) -> Optional[AgentState]:
        async with self._lock:
            return self._states.get(session_id)

    async def update(self, session_id: str, **fields: Any) -> bool:
        async with self._lock:
            state = self._states.get(session_id)
            if state is None:
                return False
            for k, v in fields.items():
                if hasattr(state, k):
                    setattr(state, k, v)
            state.last_active = time.time()
            return True

    async def end(self, session_id: str) -> None:
        async with self._lock:
            self._states.pop(session_id, None)

    async def checkpoint(self, session_id: str) -> Optional[str]:
        async with self._lock:
            state = self._states.get(session_id)
            if state is None:
                return None
            cp_id = str(uuid.uuid4())[:8]
            snapshot = copy.deepcopy(state.to_dict())
            cp = Checkpoint(checkpoint_id=cp_id, session_id=session_id, step=state.current_step, state_snapshot=snapshot)
            cps = self._checkpoints.setdefault(session_id, [])
            cps.append(cp)
            if len(cps) > self._CHECKPOINT_LIMIT:
                cps.pop(0)
            state.checkpoints.append(cp_id)
            return cp_id

    async def restore(self, session_id: str, checkpoint_id: Optional[str] = None) -> Optional[AgentState]:
        async with self._lock:
            cps = self._checkpoints.get(session_id, [])
            if not cps:
                return None
            cp = next((c for c in cps if c.checkpoint_id == checkpoint_id), None) if checkpoint_id else cps[-1]
            if cp is None:
                return None
            restored = self._restore_from_snapshot(cp.state_snapshot)
            self._states[session_id] = restored
            return restored

    @staticmethod
    def _restore_from_snapshot(snapshot: Dict[str, Any]) -> AgentState:
        state = AgentState(session_id=snapshot["session_id"], user_id=snapshot["user_id"])
        for key in ("turn_count", "current_task", "current_step", "user_tier", "skill_name",
                     "system_prompt", "input_valid", "safety_passed", "retry_count",
                     "created_at", "last_active", "checkpoints", "tool_results"):
            if key in snapshot:
                setattr(state, key, snapshot[key])
        state.messages = snapshot.get("messages", [])
        state.plan = [PlanStep(**s) for s in snapshot.get("plan", [])]
        return state


_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
