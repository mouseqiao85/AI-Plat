"""Short-term memory manager for conversation history with compression.

Enhanced with mid-session auto-compact (Phase 2):
- Token-based threshold checking before each executor call
- LLM summarization of old messages when threshold exceeded
"""
import logging
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MAX_MESSAGES = 50
DEFAULT_COMPACT_THRESHOLD = 24000
DEFAULT_COMPACT_KEEP = 6
SUMMARY_ROLE = "summary"


class MemoryManager:
    """Manages short-term conversation memory with compression."""

    def __init__(
        self,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        compact_threshold: int = DEFAULT_COMPACT_THRESHOLD,
        compact_keep: int = DEFAULT_COMPACT_KEEP,
    ):
        self.max_messages = max_messages
        self.compact_threshold = compact_threshold
        self.compact_keep = compact_keep

    async def load_history(
        self, db: AsyncSession, conversation_id: int, limit: int = 50
    ) -> list[dict]:
        """Load conversation history as API-format messages."""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()

        api_messages = []
        for msg in messages:
            if msg.role == SUMMARY_ROLE:
                if msg.content:
                    api_messages.insert(0, {"role": "system", "content": f"[对话摘要]\n{msg.content}"})
                continue
            api_messages.append({
                "role": msg.role,
                "content": msg.content or "",
            })

        return api_messages

    async def save_message(
        self,
        db: AsyncSession,
        conversation_id: int,
        role: str,
        content: str,
        token_count: int = 0,
    ) -> Message:
        """Save a message to the database."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count or self._estimate_tokens(content),
        )
        db.add(msg)
        await db.commit()
        return msg

    async def count_messages(self, db: AsyncSession, conversation_id: int) -> int:
        """Count messages in a conversation."""
        result = await db.execute(
            select(func.count()).where(
                Message.conversation_id == conversation_id,
                Message.role != SUMMARY_ROLE,
            )
        )
        return result.scalar() or 0

    async def compress_if_needed(
        self,
        db: AsyncSession,
        conversation_id: int,
        llm_client,
        model: str,
    ) -> bool:
        """Compress old messages into a summary if needed."""
        count = await self.count_messages(db, conversation_id)
        if count <= self.max_messages:
            return False

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != SUMMARY_ROLE)
            .order_by(Message.created_at.asc())
            .limit(count - self.compact_keep)
        )
        old_messages = result.scalars().all()

        if not old_messages:
            return False

        conversation_text = "\n".join(
            f"{m.role}: {m.content}" for m in old_messages if m.content
        )

        try:
            resp = await llm_client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": f"请将以下对话压缩成简短摘要(中文):\n\n{conversation_text}",
                }],
                max_tokens=500,
                temperature=0.3,
            )
            summary = resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"compress failed: {e}")
            return False

        summary_msg = Message(
            conversation_id=conversation_id,
            role=SUMMARY_ROLE,
            content=summary,
        )
        db.add(summary_msg)
        await db.commit()
        return True

    async def mid_session_compact(
        self,
        messages: list[dict],
        llm_client,
        model: str,
        writer=None,
    ) -> list[dict]:
        """Mid-session auto-compact: compress messages in-memory when token count exceeds threshold.

        This is called before each executor iteration to keep context manageable.
        Returns the (possibly compressed) message list.
        """
        total_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in messages)

        if total_tokens < self.compact_threshold:
            return messages

        logger.info("mid_session_compact: %d tokens exceeds threshold %d", total_tokens, self.compact_threshold)

        if writer:
            writer({"type": "compact_start", "token_count": total_tokens})

        # Keep recent messages, compress older ones
        keep_count = self.compact_keep
        if len(messages) <= keep_count:
            return messages

        old_messages = messages[:-keep_count]
        recent_messages = messages[-keep_count:]

        conversation_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in old_messages if m.get("content")
        )

        try:
            resp = await llm_client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": f"请将以下对话压缩成简短摘要，保留关键信息:\n\n{conversation_text}",
                }],
                max_tokens=500,
                temperature=0.3,
            )
            summary = resp.choices[0].message.content or ""

            if writer:
                writer({"type": "compact_done", "summary_tokens": self._estimate_tokens(summary)})

            # Replace old messages with summary
            return [{"role": "system", "content": f"[对话摘要]\n{summary}"}] + recent_messages

        except Exception as e:
            logger.warning("mid_session_compact failed: %s", e)
            if writer:
                writer({"type": "compact_done", "error": str(e)})
            return messages

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count for a text string."""
        if not text:
            return 0
        cjk_count = sum(1 for c in text if "一" <= c <= "鿿")
        other_count = len(text) - cjk_count
        return int(cjk_count * 1.5 + other_count * 0.3)
