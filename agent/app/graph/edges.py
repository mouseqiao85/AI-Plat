"""Conditional edge functions for the agent graph."""
import logging
from app.graph.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "chat")
    logger.warning("ROUTE_BY_INTENT intent=%s", intent)
    if intent == "task":
        return "planner"
    return "responder"


def route_by_safety(state: AgentState) -> str:
    if state.get("safety_passed", True):
        return "allowed"
    return "fail"


def should_continue(state: AgentState) -> str:
    """Continue executing plan steps until all are done.

    Enhanced with max_iterations check (Phase 2).
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    iteration_count = state.get("iteration_count", 0)
    max_iter = getattr(settings, "MAX_ITERATIONS", 80)

    # Max iterations guard
    if iteration_count >= max_iter:
        logger.warning("max_iterations reached (%d/%d), forcing respond", iteration_count, max_iter)
        return "respond"

    if plan and current_step < len(plan):
        return "continue"
    return "respond"


def route_by_scope(state: AgentState) -> str:
    if state.get("approved", True):
        return "allowed"
    return "blocked"


def route_after_plan(state: AgentState) -> str:
    """Route after planning: to worker_orchestrator if parallel workers needed,
    otherwise to scope_check for sequential execution.
    Empty plan bypasses scope_check->executor directly to responder."""
    plan = state.get("plan", [])

    # Empty plan -> responder directly, skip scope_check -> executor no-op loop
    if not plan:
        logger.info("route_after_plan: empty plan, going to responder")
        return "responder"

    needs_workers = state.get("needs_workers", False)
    if needs_workers and len(plan) > 1:
        logger.info("route_after_plan: dispatching to worker_orchestrator (%d steps)", len(plan))
        return "worker_orchestrator"

    return "scope_check"
