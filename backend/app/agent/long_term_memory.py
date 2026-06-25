"""长期记忆模块

跨会话持久化用户偏好和关键事实，存储于 Redis（KV，TTL 90天）。
每次会话结束后通过 LLM 提取新信息并合并到用户档案中。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Redis TTL: 90 days
_TTL_SECONDS = 90 * 24 * 3600
_KEY_PREFIX = "user_memory"
# Re-compress profile_summary every N updates
_COMPRESS_INTERVAL = 10


def _utcnow() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _empty_profile(user_id: int) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "preferences": {
            "language_style": "",
            "verbosity": "normal",
            "preferred_formats": [],
            "response_language": "zh",
        },
        "key_facts": {
            "profession": "",
            "interests": [],
            "domain_knowledge": [],
            "mentioned_projects": [],
        },
        "interaction_stats": {
            "total_sessions": 0,
            "total_messages": 0,
            "avg_session_length": 0.0,
            "last_active": "",
            "tools_used": [],
        },
        "profile_summary": "",
        "version": 0,
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }


class UserMemoryManager:
    """Manages persistent user profile stored in Redis.

    Workflow:
        profile = await mgr.load_profile(user_id)
        # inject into system prompt via format_for_prompt(profile)
        # ... conversation ...
        await mgr.update_profile(user_id, api_messages, tools_used)
    """

    def __init__(self, redis_client: Any, openai_client: Any, model: str) -> None:
        self.redis = redis_client
        self.client = openai_client
        self.model = model

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def load_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Load user profile from Redis. Returns None if not found or Redis unavailable."""
        if self.redis is None:
            return None
        try:
            raw = await self.redis.get(self._key(user_id))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("user_memory_load_failed", user_id=user_id, error=str(exc))
            return None

    async def save_profile(self, user_id: int, profile: Dict[str, Any]) -> None:
        """Persist profile to Redis and refresh TTL."""
        if self.redis is None:
            return
        try:
            profile["updated_at"] = _utcnow()
            await self.redis.set(
                self._key(user_id),
                json.dumps(profile, ensure_ascii=False),
                ex=_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("user_memory_save_failed", user_id=user_id, error=str(exc))

    async def _acquire_lock(self, user_id: int) -> bool:
        """Try to acquire a Redis lock for profile updates. Returns True if acquired."""
        if self.redis is None:
            return False
        lock_key = f"{_KEY_PREFIX}:lock:{user_id}"
        try:
            return await self.redis.set(lock_key, "1", nx=True, ex=30)
        except Exception:
            return False

    async def _release_lock(self, user_id: int) -> None:
        """Release the profile update lock."""
        if self.redis is None:
            return
        lock_key = f"{_KEY_PREFIX}:lock:{user_id}"
        try:
            await self.redis.delete(lock_key)
        except Exception:
            pass

    async def update_profile(
        self,
        user_id: int,
        conversation_messages: List[Dict[str, Any]],
        tools_used: List[str],
    ) -> None:
        """Extract new facts from a completed conversation and merge into profile.

        Called as a fire-and-forget background task at session end.
        Uses a Redis lock to prevent concurrent profile updates from overwriting each other.
        """
        if not await self._acquire_lock(user_id):
            logger.warning("user_memory_lock_failed", user_id=user_id)
            return
        try:
            await self._update_profile_inner(user_id, conversation_messages, tools_used)
        finally:
            await self._release_lock(user_id)

    async def _update_profile_inner(
        self,
        user_id: int,
        conversation_messages: List[Dict[str, Any]],
        tools_used: List[str],
    ) -> None:
        try:
            # Re-read profile after acquiring lock to get latest version
            existing = await self.load_profile(user_id)
            profile = existing if existing else _empty_profile(user_id)

            # Build conversation text (user + assistant turns only, skip system)
            lines: List[str] = []
            for msg in conversation_messages:
                role = msg.get("role", "")
                content = msg.get("content") or ""
                if role == "system":
                    continue
                if isinstance(content, list):
                    # Extract text blocks from content block lists
                    text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                    content = " ".join(text_parts)
                if content and role in ("user", "assistant"):
                    label = "用户" if role == "user" else "助手"
                    lines.append(f"{label}：{content}")

            if not lines:
                return

            conversation_text = "\n".join(lines[-40:])  # cap at 40 lines to limit LLM cost

            # LLM extraction
            existing_summary = profile.get("profile_summary", "")
            extracted = await self._extract_facts(conversation_text, existing_summary)

            # Merge into profile
            profile = self._merge_profile(profile, extracted, tools_used)

            # Increment version and optionally compress profile_summary
            profile["version"] = profile.get("version", 0) + 1
            if profile["version"] % _COMPRESS_INTERVAL == 0:
                profile = await self._compress_profile(profile)

            await self.save_profile(user_id, profile)
            logger.info("user_memory_updated", user_id=user_id, version=profile["version"])

        except Exception as exc:
            logger.warning("user_memory_update_failed", user_id=user_id, error=str(exc))

    def format_for_prompt(self, profile: Optional[Dict[str, Any]]) -> str:
        """Convert profile to a compact string for system prompt injection.

        Returns empty string if profile is None or empty.
        """
        if not profile:
            return ""

        prefs = profile.get("preferences", {})
        facts = profile.get("key_facts", {})
        summary = profile.get("profile_summary", "")

        parts: List[str] = []

        lang_style = prefs.get("language_style", "")
        verbosity = prefs.get("verbosity", "")
        if lang_style or verbosity:
            pref_str = "、".join(filter(None, [lang_style, verbosity]))
            parts.append(f"偏好：{pref_str}")

        profession = facts.get("profession", "")
        interests = facts.get("interests", [])
        domain = facts.get("domain_knowledge", [])
        domain_str = "、".join((interests + domain)[:3])
        if profession or domain_str:
            field_parts = [profession, f"关注{domain_str}" if domain_str else ""]
            parts.append("领域：" + "，".join(filter(None, field_parts)))

        if summary:
            parts.append(f"摘要：{summary}")

        if not parts:
            return ""

        return "[用户档案] " + " | ".join(parts)

    async def delete_profile(self, user_id: int) -> None:
        """Hard delete profile (for user-initiated data removal)."""
        if self.redis is None:
            return
        try:
            await self.redis.delete(self._key(user_id))
        except Exception as exc:
            logger.warning("user_memory_delete_failed", user_id=user_id, error=str(exc))

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _key(self, user_id: int) -> str:
        return f"{_KEY_PREFIX}:{user_id}"

    async def _extract_facts(
        self,
        conversation_text: str,
        existing_summary: str,
    ) -> Dict[str, Any]:
        """Call LLM to extract preferences and key facts from conversation."""
        summary_hint = f"现有档案摘要（供参考）：{existing_summary}\n\n" if existing_summary else ""
        prompt = (
            f"{summary_hint}"
            "根据以下对话内容，提取用户的偏好和关键信息，以JSON格式返回（仅含变化或新增的字段）。\n"
            '格式：{"preferences": {"language_style": "...", "verbosity": "...", "preferred_formats": [...], "response_language": "..."}, '
            '"key_facts": {"profession": "...", "interests": [...], "domain_knowledge": [...], "mentioned_projects": [...]}}\n'
            "若某字段无新信息则省略。只返回JSON，不含任何解释。\n\n"
            f"对话内容：\n{conversation_text}"
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as exc:
            logger.debug("user_memory_extract_failed", error=str(exc))
            return {}

    def _merge_profile(
        self,
        existing: Dict[str, Any],
        extracted: Dict[str, Any],
        tools_used: List[str],
    ) -> Dict[str, Any]:
        """Merge extracted facts into existing profile (pure Python, no LLM)."""
        profile = dict(existing)

        # Merge preferences
        if "preferences" in extracted:
            prefs = dict(profile.get("preferences", {}))
            for k, v in extracted["preferences"].items():
                if v:  # only overwrite with non-empty values
                    if isinstance(v, list):
                        existing_list = prefs.get(k, [])
                        prefs[k] = list(dict.fromkeys(existing_list + v))  # dedup, preserve order
                    else:
                        prefs[k] = v
            profile["preferences"] = prefs

        # Merge key_facts
        if "key_facts" in extracted:
            facts = dict(profile.get("key_facts", {}))
            for k, v in extracted["key_facts"].items():
                if v:
                    if isinstance(v, list):
                        existing_list = facts.get(k, [])
                        merged = list(dict.fromkeys(existing_list + v))
                        facts[k] = merged[:20]  # cap list size
                    else:
                        facts[k] = v
            profile["key_facts"] = facts

        # Update interaction stats
        stats = dict(profile.get("interaction_stats", {}))
        stats["total_sessions"] = stats.get("total_sessions", 0) + 1
        stats["last_active"] = _utcnow()
        if tools_used:
            existing_tools = stats.get("tools_used", [])
            stats["tools_used"] = list(dict.fromkeys(existing_tools + tools_used))[:10]
        profile["interaction_stats"] = stats

        return profile

    async def _compress_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Re-summarise profile_summary via LLM when profile grows large."""
        facts = profile.get("key_facts", {})
        prefs = profile.get("preferences", {})

        profile_text = json.dumps(
            {"preferences": prefs, "key_facts": facts},
            ensure_ascii=False,
            indent=2,
        )
        prompt = (
            "请将以下用户档案信息压缩成一段不超过100字的中文摘要，突出最重要的偏好和背景信息。\n"
            f"档案：\n{profile_text}\n\n"
            "直接输出摘要，不含前缀。"
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            summary = (resp.choices[0].message.content or "").strip()
            if summary:
                profile["profile_summary"] = summary
        except Exception as exc:
            logger.debug("user_memory_compress_failed", error=str(exc))

        return profile
