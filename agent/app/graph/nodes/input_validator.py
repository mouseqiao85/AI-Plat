"""Input validation node for the LangGraph pipeline."""
from app.graph.state import AgentState
from app.harness.validator import get_validator


async def input_validator_node(state: AgentState) -> dict:
    """Validate user input before routing. Returns safety_passed=False on failure."""
    messages = state.get("messages", [])
    if not messages:
        return {"safety_passed": False, "error": "no messages"}

    last_msg = messages[-1].get("content", "") if isinstance(messages[-1], dict) else str(messages[-1])

    validator = get_validator()
    result = validator.validate_input(last_msg)

    if not result.passed:
        return {
            "safety_passed": False,
            "error": "; ".join(result.issues),
            "response": f"抱歉，您的输入未通过安全检查：{'；'.join(result.issues)}",
        }

    return {"safety_passed": True}
