"""Scope check node for the LangGraph pipeline."""
from app.graph.state import AgentState
from app.harness.scope import get_scope_manager


async def scope_check_node(state: AgentState) -> dict:
    """Check tool permissions before execution."""
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    user_tier = state.get("context", {}).get("user_tier", "free") if state.get("context") else "free"

    if not plan or current_step >= len(plan):
        return {"approved": True}

    step = plan[current_step]
    tool_name = step.get("tool", "")

    scope = get_scope_manager()
    allowed, reason = scope.check_tool(tool_name, user_tier)

    if not allowed:
        return {
            "approved": False,
            "error": reason,
            "response": f"操作被阻止：{reason}",
        }

    return {"approved": True}
