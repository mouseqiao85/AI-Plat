"""Long-term user memory manager with Redis persistence.

Enhanced (Phase 4) with:
- Structured profile schema
- LLM-based fact extraction with merge/compress
- Redis distributed lock for concurrent updates
- Profile versioning
"""
import json
import logging
import time
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

PROFILE_VERSION = 2
LOCK_TIMEOUT = 10  # seconds


class UserMemoryManager:
    """Manages cross-session user profile memory stored in Redis."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.ttl = getattr(settings, "MEMORY_TTL_DAYS", 90) * 86400

    def _key(self, user_id: int) -> str:
        return f"user_memory:{user_id}"

    def _lock_key(self, user_id: int) -> str:
        return f"user_memory_lock:{user_id}"

    async def _acquire_lock(self, user_id: int) -> bool:
        """Acquire a distributed lock for profile updates."""
        if not self.redis:
            return True
        try:
            return await self.redis.set(
                self._lock_key(user_id), "1",
                nx=True, ex=LOCK_TIMEOUT,
            )
        except Exception:
            return True  # Proceed without lock on failure

    async def _release_lock(self, user_id: int) -> None:
        """Release the distributed lock."""
        if not self.redis:
            return
        try:
            await self.redis.delete(self._lock_key(user_id))
        except Exception:
            pass

    async def load_profile(self, user_id: int) -> dict:
        """Load user profile from Redis."""
        try:
            if self.redis is None:
                return self._empty_profile(user_id)
            data = await self.redis.get(self._key(user_id))
            if data:
                profile = json.loads(data)
                # Migrate old profiles
                if profile.get("version", 1) < PROFILE_VERSION:
                    profile = self._migrate_profile(profile, user_id)
                return profile
        except Exception as e:
            logger.warning(f"load profile failed: {e}")
        return self._empty_profile(user_id)

    async def save_profile(self, user_id: int, profile: dict):
        """Save user profile to Redis with TTL."""
        try:
            if self.redis is None:
                return
            profile["version"] = PROFILE_VERSION
            await self.redis.set(
                self._key(user_id),
                json.dumps(profile, ensure_ascii=False),
                ex=self.ttl,
            )
        except Exception as e:
            logger.warning(f"save profile failed: {e}")

    async def delete_profile(self, user_id: int):
        """Delete user profile."""
        try:
            if self.redis is not None:
                await self.redis.delete(self._key(user_id))
        except Exception:
            pass

    async def update_profile(
        self,
        user_id: int,
        messages: list,
        tools_used: list,
        llm_client=None,
        model: str = "",
    ):
        """Update profile based on conversation data with lock protection."""
        if not await self._acquire_lock(user_id):
            logger.warning("could not acquire lock for user %d, skipping update", user_id)
            return

        try:
            profile = await self.load_profile(user_id)

            # Update interaction stats
            stats = profile["interaction_stats"]
            stats["total_messages"] = stats.get("total_messages", 0) + len(messages)
            stats["total_sessions"] = stats.get("total_sessions", 0) + 1
            for tool in tools_used:
                if tool not in stats["tools_used"]:
                    stats["tools_used"].append(tool)

            # LLM-based fact extraction
            if llm_client and len(messages) > 2:
                await self._extract_facts(profile, messages, llm_client, model)

            # Compress if profile is too large
            self._compress_profile(profile)

            await self.save_profile(user_id, profile)
        finally:
            await self._release_lock(user_id)

    async def _extract_facts(self, profile: dict, messages: list, llm_client, model: str):
        """Use LLM to extract user facts from conversation."""
        try:
            conversation_text = "\n".join(
                m.get("content", "") for m in messages[-10:] if m.get("content")
            )

            existing_facts = json.dumps({
                "preferences": profile["preferences"],
                "key_facts": profile["key_facts"],
            }, ensure_ascii=False)

            resp = await llm_client.chat.completions.create(
                model=model or settings.LLM_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        "从以下对话中提取用户信息，与现有信息合并（去重、更新矛盾信息）。\n\n"
                        f"现有信息:\n{existing_facts}\n\n"
                        f"新对话:\n{conversation_text}\n\n"
                        "返回JSON格式:\n"
                        '{"preferences": {"language_style": "", "verbosity": "normal|concise|detailed", '
                        '"response_language": "zh|en"}, '
                        '"key_facts": {"profession": "", "interests": [], "domain_knowledge": []}, '
                        '"profile_summary": "一句话描述用户"}'
                    ),
                }],
                max_tokens=500,
                temperature=0.3,
            )
            content = resp.choices[0].message.content or "{}"
            facts = json.loads(content.strip().removeprefix("```json").removesuffix("```"))

            # Merge preferences
            if "preferences" in facts and isinstance(facts["preferences"], dict):
                for k, v in facts["preferences"].items():
                    if v:  # Only update non-empty values
                        profile["preferences"][k] = v

            # Merge key_facts
            if "key_facts" in facts and isinstance(facts["key_facts"], dict):
                kf = profile["key_facts"]
                if facts["key_facts"].get("profession"):
                    kf["profession"] = facts["key_facts"]["profession"]
                for interest in facts["key_facts"].get("interests", []):
                    if interest and interest not in kf["interests"]:
                        kf["interests"].append(interest)
                for domain in facts["key_facts"].get("domain_knowledge", []):
                    if domain and domain not in kf["domain_knowledge"]:
                        kf["domain_knowledge"].append(domain)

            # Update summary
            if facts.get("profile_summary"):
                profile["profile_summary"] = facts["profile_summary"]

        except Exception as e:
            logger.warning(f"fact extraction failed: {e}")

    def _compress_profile(self, profile: dict):
        """Compress profile if lists are too long."""
        kf = profile.get("key_facts", {})
        if len(kf.get("interests", [])) > 20:
            kf["interests"] = kf["interests"][-15:]
        if len(kf.get("domain_knowledge", [])) > 20:
            kf["domain_knowledge"] = kf["domain_knowledge"][-15:]
        if len(profile.get("interaction_stats", {}).get("tools_used", [])) > 50:
            profile["interaction_stats"]["tools_used"] = profile["interaction_stats"]["tools_used"][-30:]

    def format_for_prompt(self, profile: dict) -> str:
        """Format profile for injection into system prompt."""
        if not profile:
            return ""

        parts = []

        # Preferences
        prefs = profile.get("preferences", {})
        if prefs.get("language_style"):
            parts.append(f"风格偏好: {prefs['language_style']}")
        if prefs.get("verbosity") and prefs["verbosity"] != "normal":
            parts.append(f"详细度: {prefs['verbosity']}")

        # Key facts
        kf = profile.get("key_facts", {})
        if kf.get("profession"):
            parts.append(f"职业: {kf['profession']}")
        if kf.get("interests"):
            parts.append(f"兴趣: {', '.join(kf['interests'][:5])}")
        if kf.get("domain_knowledge"):
            parts.append(f"专业领域: {', '.join(kf['domain_knowledge'][:5])}")

        # Summary
        if profile.get("profile_summary"):
            parts.append(f"概述: {profile['profile_summary']}")

        # Stats
        stats = profile.get("interaction_stats", {})
        if stats.get("total_sessions", 0) > 0:
            parts.append(f"互动: {stats.get('total_messages', 0)}条消息, {stats['total_sessions']}次会话")

        return "[用户档案]\n" + "\n".join(parts) if parts else ""

    def _migrate_profile(self, old_profile: dict, user_id: int) -> dict:
        """Migrate old profile format to new structured schema."""
        new_profile = self._empty_profile(user_id)

        # Migrate old list-based preferences
        old_prefs = old_profile.get("preferences", [])
        if isinstance(old_prefs, list):
            for p in old_prefs[:5]:
                new_profile["preferences"]["language_style"] = str(p)
                break
        elif isinstance(old_prefs, dict):
            new_profile["preferences"] = {**new_profile["preferences"], **old_prefs}

        # Migrate key_facts
        old_facts = old_profile.get("key_facts", [])
        if isinstance(old_facts, list):
            new_profile["key_facts"]["domain_knowledge"] = old_facts[:10]
        elif isinstance(old_facts, dict):
            new_profile["key_facts"] = {**new_profile["key_facts"], **old_facts}

        # Migrate interests
        old_interests = old_profile.get("interests", [])
        if isinstance(old_interests, list):
            new_profile["key_facts"]["interests"] = old_interests[:10]

        # Migrate stats
        old_stats = old_profile.get("interaction_stats", {})
        if old_stats:
            new_profile["interaction_stats"]["total_messages"] = old_stats.get("messages", 0)
            new_profile["interaction_stats"]["total_sessions"] = old_stats.get("sessions", 0)

        return new_profile

    @staticmethod
    def _empty_profile(user_id: int) -> dict:
        return {
            "user_id": user_id,
            "preferences": {
                "language_style": "",
                "verbosity": "normal",
                "response_language": "zh",
            },
            "key_facts": {
                "profession": "",
                "interests": [],
                "domain_knowledge": [],
            },
            "interaction_stats": {
                "total_sessions": 0,
                "total_messages": 0,
                "tools_used": [],
            },
            "profile_summary": "",
            "version": PROFILE_VERSION,
        }
