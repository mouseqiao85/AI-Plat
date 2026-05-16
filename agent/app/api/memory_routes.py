"""Memory API routes: user profile CRUD for the Go gateway to proxy."""
import logging
from fastapi import APIRouter, HTTPException
from app.memory.long_term import UserMemoryManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])

_memory_mgr: UserMemoryManager = None


def get_memory_manager() -> UserMemoryManager:
    global _memory_mgr
    if _memory_mgr is None:
        _memory_mgr = UserMemoryManager(redis_client=None)
    return _memory_mgr


@router.get("/profile/{user_id}")
async def get_profile(user_id: int):
    """Get user profile from memory."""
    mgr = get_memory_manager()
    try:
        profile = await mgr.load_profile(user_id)
        return profile
    except Exception as e:
        logger.error("failed to load profile for user %d: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profile/{user_id}")
async def delete_profile(user_id: int):
    """Delete user profile from memory."""
    mgr = get_memory_manager()
    try:
        await mgr.delete_profile(user_id)
        return {"status": "deleted", "user_id": user_id}
    except Exception as e:
        logger.error("failed to delete profile for user %d: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{user_id}")
async def get_memory_stats(user_id: int):
    """Get memory statistics for a user."""
    mgr = get_memory_manager()
    try:
        profile = await mgr.load_profile(user_id)
        stats = profile.get("interaction_stats", {})
        return {
            "user_id": user_id,
            "total_sessions": stats.get("total_sessions", 0),
            "total_messages": stats.get("total_messages", 0),
            "tools_used": stats.get("tools_used", []),
            "profile_summary": profile.get("profile_summary", ""),
            "has_preferences": bool(profile.get("preferences", {}).get("language_style")),
            "has_facts": bool(profile.get("key_facts", {}).get("profession") or
                            profile.get("key_facts", {}).get("interests")),
        }
    except Exception as e:
        logger.error("failed to get stats for user %d: %s", user_id, e)
        raise HTTPException(status_code=500, detail=str(e))
