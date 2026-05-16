"""Output validation node for the LangGraph pipeline.

Enhanced (Phase 4): triggers async user profile update after validation.
"""
import asyncio
import logging
from app.graph.state import AgentState
from app.harness.validator import get_validator

logger = logging.getLogger(__name__)


async def output_validator_node(state: AgentState) -> dict:
    """Validate agent output before sending to user."""
    response = state.get("response", "")
    logger.info("output_validator: response_len=%d", len(response or ""))

    if not response:
        return {"safety_passed": True}

    validator = get_validator()
    result = validator.validate_output(response, auto_rewrite=True)

    if not result.passed:
        return {
            "safety_passed": False,
            "error": "; ".join(result.issues),
        }

    # Phase 4: Trigger async profile update (non-blocking)
    user_id = state.get("user_id", 0)
    if user_id:
        asyncio.create_task(_update_user_profile(state))

    if result.rewritten:
        return {
            "safety_passed": True,
            "response": result.rewritten,
        }

    return {"safety_passed": True}


async def _update_user_profile(state: dict) -> None:
    """Background task to update user profile from conversation."""
    try:
        from app.graph.nodes.router import _get_redis
        from app.memory.long_term import UserMemoryManager
        from app.llm.client import build_llm_client
        from app.core.config import settings

        user_id = state.get("user_id", 0)
        if not user_id:
            return

        redis = await _get_redis()
        memory_mgr = UserMemoryManager(redis_client=redis)

        messages = state.get("messages", [])
        msg_dicts = []
        for m in messages[-10:]:  # Only last 10 messages
            if isinstance(m, dict):
                msg_dicts.append(m)
            elif hasattr(m, "content"):
                msg_dicts.append({"role": getattr(m, "type", "user"), "content": m.content or ""})

        tool_results = state.get("tool_results") or []
        tools_used = [r.get("tool", "") for r in tool_results if r.get("success")]

        client = build_llm_client(
            provider_id=state.get("provider_id", ""),
            model=state.get("model", ""),
        )

        await memory_mgr.update_profile(
            user_id=user_id,
            messages=msg_dicts,
            tools_used=tools_used,
            llm_client=client,
            model=state.get("model") or settings.LLM_MODEL,
        )
    except Exception as e:
        logger.debug("profile update background task failed: %s", e)
