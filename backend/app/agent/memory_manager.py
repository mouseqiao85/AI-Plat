import re
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401

from app.models import Message

logger = structlog.get_logger(__name__)


# Maximum number of conversation turns to keep in the token budget.
# One turn = one user message + one assistant message => 50 messages.
MAX_TURNS = 25
MAX_MESSAGES = MAX_TURNS * 2

# After compression, keep the most recent N messages verbatim
RECENT_MESSAGES_KEEP = 10

# Role marker for LLM-generated summary rows
SUMMARY_ROLE = "summary"


class MemoryManager:
    """Manages conversation history with DB persistence and token budget control.

    Short-term compression: when history exceeds MAX_MESSAGES, older turns are
    summarised via LLM into a single SUMMARY_ROLE row. Subsequent load_history()
    calls prepend the summary so the model retains long-range context.
    """

    def __init__(self, db_session: AsyncSession, conversation_id: int) -> None:
        self.db = db_session
        self.conversation_id = conversation_id

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def load_history(self) -> List[Dict[str, Any]]:
        """Load conversation history from DB and format for the Claude API.

        If a summary row exists it is prepended as a framing user/assistant pair.
        The remaining (non-summary) messages are window-truncated to MAX_MESSAGES.
        Uses optimized SQL: fetches summary separately, then only the most recent N messages.
        """
        from sqlalchemy import select, func

        try:
            # 1. Fetch the summary row (if any — always the earliest row with role='summary')
            summary_stmt = (
                select(Message)
                .where(Message.conversation_id == self.conversation_id, Message.role == SUMMARY_ROLE)
                .order_by(Message.id.asc())
                .limit(1)
            )
            summary_result = await self.db.execute(summary_stmt)
            summary_msg = summary_result.scalar_one_or_none()

            # 2. Fetch the most recent MAX_MESSAGES non-summary messages (descending, then reverse)
            recent_stmt = (
                select(Message)
                .where(
                    Message.conversation_id == self.conversation_id,
                    Message.role != SUMMARY_ROLE,
                )
                .order_by(Message.id.desc())
                .limit(MAX_MESSAGES)
            )
            recent_result = await self.db.execute(recent_stmt)
            regular_msgs = list(reversed(recent_result.scalars().all()))
        except Exception as exc:
            logger.error("load_history_db_error", conversation_id=self.conversation_id, error=str(exc))
            return []

        formatted = self._format_for_claude(regular_msgs)
        formatted = self._sanitize_history(formatted)

        # Inject summary as a framing user/assistant pair at the head
        if summary_msg:
            formatted.insert(0, {
                "role": "assistant",
                "content": "好的，我已了解之前的对话背景。",
            })
            formatted.insert(0, {
                "role": "user",
                "content": f"[历史对话摘要]\n{summary_msg.content}",
            })

        return formatted

    async def compress_if_needed(
        self,
        openai_client: Any,
        model: str,
    ) -> Optional[str]:
        """Compress conversation history via LLM if it exceeds MAX_MESSAGES.

        Returns the summary text if compression occurred, None otherwise.
        """
        from sqlalchemy import select, delete, update as sa_update

        stmt = (
            select(Message)
            .where(Message.conversation_id == self.conversation_id)
            .order_by(Message.id.asc())
        )
        result = await self.db.execute(stmt)
        all_msgs = list(result.scalars().all())

        # Check whether compression is needed
        non_summary = [m for m in all_msgs if m.role != SUMMARY_ROLE]
        if len(non_summary) <= MAX_MESSAGES:
            return None

        # Split into the portion to compress and the portion to keep verbatim
        to_compress_msgs = non_summary[:-RECENT_MESSAGES_KEEP]
        # Check if we already have a summary row
        existing_summary = all_msgs[0] if all_msgs and all_msgs[0].role == SUMMARY_ROLE else None

        prior_summary = existing_summary.content if existing_summary else None

        # Build conversation text for LLM
        conv_lines: List[str] = []
        for msg in to_compress_msgs:
            role_label = {"user": "用户", "assistant": "助手", "tool": "工具结果"}.get(msg.role, msg.role)
            conv_lines.append(f"{role_label}：{msg.content or ''}")
        conversation_text = "\n".join(conv_lines)

        # Build LLM prompt
        prior_section = f"\n已有摘要（请在此基础上扩充）：\n{prior_summary}\n" if prior_summary else ""
        prompt = (
            "你是一个对话历史压缩助手。请将以下对话历史压缩成一段简洁的中文摘要（不超过300字）。\n"
            "摘要必须保留：用户的主要问题、使用的工具及结果、得出的重要结论。\n"
            f"{prior_section}\n"
            f"对话历史：\n{conversation_text}\n\n"
            "请直接输出摘要，不要包含任何前缀或解释。"
        )

        try:
            resp = await openai_client.chat.completions.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            summary_text = resp.choices[0].message.content or ""
        except Exception as exc:
            # LLM call failed — do NOT delete messages; keep them intact for next attempt
            logger.warning(
                "compression_failed_preserving_messages",
                conversation_id=self.conversation_id,
                error=str(exc),
            )
            return None

        if not summary_text.strip():
            return None

        # Persist: update existing summary row, or insert a new one
        if existing_summary:
            await self.db.execute(
                sa_update(Message)
                .where(Message.id == existing_summary.id)
                .values(content=summary_text)
            )
        else:
            new_summary = Message(
                conversation_id=self.conversation_id,
                role=SUMMARY_ROLE,
                content=summary_text,
                token_count=0,
            )
            self.db.add(new_summary)
            await self.db.flush()

        # Delete the compressed messages (keep summary + recent verbatim)
        ids_to_delete = [m.id for m in to_compress_msgs]
        if ids_to_delete:
            await self.db.execute(
                delete(Message).where(Message.id.in_(ids_to_delete))
            )

        await self.db.flush()
        return summary_text

    async def save_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        card_data: Optional[Dict[str, Any]] = None,
        reasoning_content: Optional[str] = None,
        file_downloads: Optional[List[Dict[str, Any]]] = None,
        token_count: int = 0,
    ) -> Message:
        """Persist a message to the database."""
        import json

        msg = Message(
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            tool_call_id=tool_call_id,
            card_data=json.dumps(card_data, ensure_ascii=False) if card_data else None,
            reasoning_content=reasoning_content,
            file_downloads=json.dumps(file_downloads, ensure_ascii=False) if file_downloads else None,
            token_count=token_count,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _sanitize_history(formatted: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove orphan tool messages and tool_calls that would cause API errors.

        DeepSeek/OpenAI require every assistant message with tool_calls to be followed
        by matching tool messages. Orphan tool_calls cause HTTP 400:
        "An assistant message with 'tool_calls' must be followed by tool messages..."
        """
        # Build a map: for each tool_call_id, check if a matching tool message exists
        # somewhere AFTER the assistant that declared it.
        tool_response_ids: set = set()
        for msg in formatted:
            if msg.get("role") == "tool":
                tc_id = msg.get("tool_call_id", "")
                if tc_id:
                    tool_response_ids.add(tc_id)

        clean: List[Dict[str, Any]] = []
        for msg in formatted:
            if msg.get("role") == "tool":
                tc_id = msg.get("tool_call_id", "")
                if tc_id not in tool_response_ids:
                    continue  # drop orphan tool without matching assistant
                clean.append(msg)
            elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Verify ALL tool_call_ids have matching tool responses
                tc_ids = [tc.get("id", "") for tc in msg["tool_calls"]]
                missing = [tid for tid in tc_ids if tid and tid not in tool_response_ids]
                if missing:
                    logger.warning(
                        "stripping_orphan_tool_calls",
                        tool_call_ids=tc_ids,
                        missing_ids=missing,
                    )
                    msg = dict(msg)
                    del msg["tool_calls"]
                    if "reasoning_content" in msg:
                        del msg["reasoning_content"]
                clean.append(msg)
            else:
                clean.append(msg)

        return clean

    @staticmethod
    def _format_for_claude(messages_orm: List[Message]) -> List[Dict[str, Any]]:
        """Convert ORM message objects into OpenAI-compatible API format."""
        import json

        formatted: List[Dict[str, Any]] = []

        for msg in messages_orm:
            # Summary rows are handled by load_history() — skip here
            if msg.role == SUMMARY_ROLE:
                continue

            if msg.role == "tool":
                # Tool result: OpenAI format uses role=tool with tool_call_id
                formatted.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.content or "",
                })
            elif msg.role == "assistant" and msg.tool_calls:
                # Assistant message with tool calls — OpenAI format
                try:
                    tool_calls_list = json.loads(msg.tool_calls) if isinstance(msg.tool_calls, str) else (msg.tool_calls or [])
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning(
                        "malformed_tool_calls_skipped",
                        conversation_id=msg.conversation_id,
                        message_id=msg.id,
                        error=str(exc),
                    )
                    # Fall back to plain assistant message
                    formatted.append({"role": "assistant", "content": msg.content or ""})
                    continue
                openai_tool_calls = []
                for tc in tool_calls_list:
                    args = tc.get("arguments", "")
                    # arguments may be stored as dict; serialize if needed
                    if not isinstance(args, str):
                        args = json.dumps(args, ensure_ascii=False)
                    openai_tool_calls.append({
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": args,
                        },
                    })
                entry: Dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": openai_tool_calls,
                }
                # DeepSeek: reasoning_content MUST be present when tool_calls exist
                if msg.tool_calls and msg.reasoning_content is not None:
                    entry["reasoning_content"] = msg.reasoning_content
                elif msg.reasoning_content:
                    entry["reasoning_content"] = msg.reasoning_content
                formatted.append(entry)
            else:
                # Plain user or assistant text message
                entry: Dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
                if msg.role == "assistant" and msg.reasoning_content is not None:
                    entry["reasoning_content"] = msg.reasoning_content
                formatted.append(entry)

        return formatted

    # ------------------------------------------------------------------ #
    # Mid-session auto-compact (in-memory, no DB writes)
    # ------------------------------------------------------------------ #

    @staticmethod
    def estimate_token_count(api_messages: List[Dict[str, Any]]) -> int:
        """Estimate the token count of a message list using CJK/ASCII heuristics.

        CJK characters ≈ 1.5 chars/token, ASCII ≈ 4 chars/token.
        Tool call entries add ~50 tokens each, role metadata adds ~20 tokens per message.
        No external tokenizer dependency required.
        """
        total = 0
        for msg in api_messages:
            # Role metadata overhead
            total += 20
            # Content
            content = msg.get("content") or ""
            cjk_count = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', content))
            ascii_count = len(content) - cjk_count
            total += int(cjk_count / 1.5) + int(ascii_count / 4)
            # Tool calls
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                total += len(tool_calls) * 50
                for tc in tool_calls:
                    args = tc.get("function", {}).get("arguments", "")
                    if args:
                        cjk = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', args))
                        asc = len(args) - cjk
                        total += int(cjk / 1.5) + int(asc / 4)
        return total

    async def compact_if_exceeds_tokens(
        self,
        api_messages: List[Dict[str, Any]],
        openai_client: Any,
        model: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check token budget and compress in-memory api_messages if threshold exceeded.

        This is a mid-session compression that operates on the in-flight message list
        (NOT on the DB). DB-level compression is handled by ``compress_if_needed`` at
        session start/end.

        Returns (compact_happened, summary_text).
        """
        from app.core.config import settings

        token_count = self.estimate_token_count(api_messages)
        if token_count < settings.COMPACT_TOKEN_THRESHOLD:
            return (False, None)

        # Determine how many recent messages to keep
        # COMPACT_RECENT_KEEP * 2 = number of individual messages (user+assistant pairs)
        keep_count = settings.COMPACT_RECENT_KEEP * 2
        if len(api_messages) <= keep_count + 1:
            # Not enough messages to compress beyond system + recent
            return (False, None)

        # System prompt is always index 0; keep it
        system_msg = api_messages[0]
        old_messages = api_messages[1:-keep_count]
        recent_messages = api_messages[-keep_count:]

        if not old_messages:
            return (False, None)

        # Build conversation text for the LLM summarizer
        conv_lines: List[str] = []
        for msg in old_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content") or ""
            role_label = {"user": "用户", "assistant": "助手", "tool": "工具结果"}.get(role, role)
            conv_lines.append(f"{role_label}：{content[:500]}")  # truncate each for budget
        conversation_text = "\n".join(conv_lines)

        prompt = (
            "你是一个对话历史压缩助手。请将以下对话历史压缩成一段简洁的中文摘要（不超过400字）。\n"
            "摘要必须保留：\n"
            "1. 用户的任务目标和核心问题\n"
            "2. 使用的关键工具及结果\n"
            "3. 已得出的重要结论和决策\n"
            "4. 当前进度\n\n"
            f"对话历史：\n{conversation_text}\n\n"
            "请直接输出摘要，不要包含任何前缀或解释。"
        )

        try:
            resp = await openai_client.chat.completions.create(
                model=model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            summary_text = resp.choices[0].message.content or ""
        except Exception as exc:
            logger.warning(
                "mid_session_compact_llm_failed",
                conversation_id=self.conversation_id,
                error=str(exc),
            )
            return (False, None)

        if not summary_text.strip():
            return (False, None)

        # Replace api_messages in-place: [system, summary framing pair, ...recent]
        api_messages.clear()
        api_messages.append(system_msg)
        api_messages.append({
            "role": "user",
            "content": f"[历史对话摘要]\n{summary_text}",
        })
        api_messages.append({
            "role": "assistant",
            "content": "好的，我已了解之前的对话背景，继续为您服务。",
        })
        api_messages.extend(recent_messages)

        logger.info(
            "mid_session_compact_done",
            conversation_id=self.conversation_id,
            old_tokens=token_count,
            new_tokens=self.estimate_token_count(api_messages),
        )
        return (True, summary_text)
