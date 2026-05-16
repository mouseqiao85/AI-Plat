"""Router node: classifies intent and loads user profile for context."""
import logging
from app.graph.state import AgentState
from app.memory.long_term import UserMemoryManager

logger = logging.getLogger(__name__)

# Lazy Redis client singleton
_redis_client = None


async def _get_redis():
    """Get or create Redis client (lazy init, fail-safe)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from app.core.config import settings
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis_client.ping()
        return _redis_client
    except Exception:
        return None


async def router_node(state: AgentState) -> dict:
    """Route by intent and load user profile for downstream nodes.

    Loads the user's long-term profile from Redis and formats it
    for injection into the responder's system prompt.
    """
    intent = state.get("intent", "chat")
    user_id = state.get("user_id", 0)

    # Load user profile for context injection (Phase 4)
    user_profile_str = ""
    if user_id:
        try:
            redis = await _get_redis()
            memory_mgr = UserMemoryManager(redis_client=redis)
            profile = await memory_mgr.load_profile(user_id)
            user_profile_str = memory_mgr.format_for_prompt(profile)
        except Exception as e:
            logger.debug("profile load skipped: %s", e)

    return {
        "intent": intent,
        "user_profile_str": user_profile_str,
    }
