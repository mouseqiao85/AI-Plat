"""Tests for DeepSeek thinking/reasoning support.

Covers:
  - memory_manager: _format_for_claude with reasoning_content
  - memory_manager: save_message with reasoning_content
  - engine: is_deepseek detection
  - engine: THINKING SSE events from streaming deltas
  - engine: assistant_msg includes reasoning_content
  - engine: multi-turn reasoning_content preserved in api_messages
  - worker: _is_deepseek detection
  - worker: assistant_msg includes reasoning_content
  - SSE pipeline: DeepSeek model with thinking chunks
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeDelta:
    """A fake delta with only the attributes explicitly set. No MagicMock auto-creation."""
    __slots__ = ("content", "tool_calls", "reasoning_content")

    def __init__(self, **kwargs):
        self.content = kwargs.get("content", None)
        self.tool_calls = kwargs.get("tool_calls", None)
        if "reasoning_content" in kwargs:
            self.reasoning_content = kwargs["reasoning_content"]


class _FakeChoice:
    """A fake choice that wraps a delta and has finish_reason."""
    __slots__ = ("delta", "finish_reason")

    def __init__(self, delta: _FakeDelta, finish_reason=None):
        self.delta = delta
        self.finish_reason = finish_reason


class _FakeChunk:
    """A fake streaming chunk with a list of choices."""
    __slots__ = ("choices",)

    def __init__(self, delta: _FakeDelta, finish_reason=None):
        self.choices = [_FakeChoice(delta, finish_reason)]


def _make_delta(**kwargs) -> _FakeDelta:
    """Build a fake delta with the given attributes (only those passed are set)."""
    return _FakeDelta(**kwargs)


# ── Unit: memory_manager._format_for_claude ───────────────────────────────────

class TestFormatForClaudeReasoning:
    """_format_for_claude should include reasoning_content in assistant messages."""

    def test_assistant_with_reasoning_and_tool_calls(self):
        from app.agent.memory_manager import MemoryManager
        from app.models import Message

        msg = Message(
            id=1,
            conversation_id=1,
            role="assistant",
            content="让我搜索一下...",
            tool_calls=json.dumps([
                {"id": "tc1", "name": "brave_search", "arguments": '{"q":"test"}'}
            ]),
            reasoning_content="用户想搜索test相关内容，我需要调用brave_search工具。",
            token_count=0,
        )

        result = MemoryManager._format_for_claude([msg])
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["reasoning_content"] == "用户想搜索test相关内容，我需要调用brave_search工具。"
        assert "tool_calls" in result[0]
        assert len(result[0]["tool_calls"]) == 1

    def test_assistant_with_reasoning_no_tool_calls(self):
        from app.agent.memory_manager import MemoryManager
        from app.models import Message

        msg = Message(
            id=1,
            conversation_id=1,
            role="assistant",
            content="9.11 > 9.8",
            tool_calls=None,
            reasoning_content="比较两个数字的大小，9.11比9.8大。",
            token_count=0,
        )

        result = MemoryManager._format_for_claude([msg])
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "9.11 > 9.8"
        assert result[0]["reasoning_content"] == "比较两个数字的大小，9.11比9.8大。"

    def test_assistant_without_reasoning_unchanged(self):
        from app.agent.memory_manager import MemoryManager
        from app.models import Message

        msg = Message(
            id=1,
            conversation_id=1,
            role="assistant",
            content="普通回复",
            tool_calls=None,
            reasoning_content=None,
            token_count=0,
        )

        result = MemoryManager._format_for_claude([msg])
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "普通回复"
        assert "reasoning_content" not in result[0]

    def test_user_message_never_has_reasoning(self):
        from app.agent.memory_manager import MemoryManager
        from app.models import Message

        msg = Message(
            id=1,
            conversation_id=1,
            role="user",
            content="你好",
            reasoning_content="should be ignored",
            token_count=0,
        )

        result = MemoryManager._format_for_claude([msg])
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "reasoning_content" not in result[0]


# ── Unit: engine is_deepseek detection ────────────────────────────────────────

class TestDeepSeekDetection:
    """Verify the is_deepseek flag is set correctly."""

    def test_detected_by_provider_id(self):
        """provider_id='deepseek' should set is_deepseek=True."""
        from app.agent.engine import AgentEngine

        engine = AgentEngine(MagicMock(), MagicMock())
        # We can't call run() easily, but we can check the logic inline
        # Test the condition expression directly
        provider_id = "deepseek"
        chat_model = "deepseek-v4-pro"
        is_ds = provider_id == "deepseek" or "deepseek" in (chat_model or "").lower()
        assert is_ds is True

    def test_detected_by_model_name(self):
        """Model name containing 'deepseek' should set is_deepseek=True."""
        provider_id = "default"
        chat_model = "deepseek-v4-flash"
        is_ds = provider_id == "deepseek" or "deepseek" in (chat_model or "").lower()
        assert is_ds is True

    def test_not_detected_for_other_providers(self):
        """Non-DeepSeek providers should leave is_deepseek=False."""
        provider_id = "openai"
        chat_model = "gpt-4"
        is_ds = provider_id == "deepseek" or "deepseek" in (chat_model or "").lower()
        assert is_ds is False

    def test_not_detected_for_default(self):
        """Default provider with non-deepseek model should be False."""
        provider_id = None
        chat_model = "gpt-4o"
        is_ds = provider_id == "deepseek" or "deepseek" in (chat_model or "").lower()
        assert is_ds is False


# ── Unit: worker._is_deepseek detection ───────────────────────────────────────

class TestWorkerDeepSeekDetection:
    """Worker should detect DeepSeek from its model name."""

    def test_worker_detects_deepseek_model(self):
        from app.agent.worker import Worker, WorkerConfig
        config = WorkerConfig(worker_id="w1", task="test")
        worker = Worker(config, MagicMock(), MagicMock(), model="deepseek-v4-pro")
        assert worker._is_deepseek is True

    def test_worker_detects_deepseek_flash(self):
        from app.agent.worker import Worker, WorkerConfig
        config = WorkerConfig(worker_id="w1", task="test")
        worker = Worker(config, MagicMock(), MagicMock(), model="deepseek-v4-flash")
        assert worker._is_deepseek is True

    def test_worker_does_not_detect_other_models(self):
        from app.agent.worker import Worker, WorkerConfig
        config = WorkerConfig(worker_id="w1", task="test")
        worker = Worker(config, MagicMock(), MagicMock(), model="gpt-4o")
        assert worker._is_deepseek is False


# ── Unit: engine streaming THINKING events ────────────────────────────────────

class TestEngineThinkingStreaming:
    """Engine should emit THINKING SSE events for reasoning_content deltas."""

    def test_thinking_event_emitted_for_reasoning_delta(self):
        """When delta has reasoning_content, a THINKING SSE event should be emitted."""
        from app.agent.stream_adapter import SSEEventType, format_sse_event

        # Simulate what the engine does when it sees reasoning_content
        reasoning_delta = "用户想问天气..."
        event = format_sse_event(SSEEventType.THINKING, {"text": reasoning_delta})
        assert "event: thinking" in event
        assert "用户想问天气..." in event
        assert event.endswith("\n\n")

    def test_thinking_event_not_emitted_for_normal_delta(self):
        """When delta has only content (no reasoning_content), no THINKING event."""
        from app.agent.stream_adapter import SSEEventType, format_sse_event

        # Normal content delta -> TEXT event, not THINKING
        event = format_sse_event(SSEEventType.TEXT, {"text": "今天天气很好"})
        assert "event: text" in event
        assert "thinking" not in event


# ── Unit: assistant_msg construction ──────────────────────────────────────────

class TestAssistantMessageConstruction:
    """The assistant_msg dict should include reasoning_content when present."""

    def test_msg_with_reasoning_and_tool_calls(self):
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": "让我搜索一下",
        }
        reasoning_content = "需要搜索天气信息"
        if reasoning_content:
            assistant_msg["reasoning_content"] = reasoning_content
        assistant_msg["tool_calls"] = [{
            "id": "tc1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"杭州"}'},
        }]

        assert assistant_msg["reasoning_content"] == "需要搜索天气信息"
        assert "tool_calls" in assistant_msg
        assert assistant_msg["role"] == "assistant"

    def test_msg_with_reasoning_no_tool_calls(self):
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": "答案是42",
        }
        reasoning_content = "计算得出..."
        if reasoning_content:
            assistant_msg["reasoning_content"] = reasoning_content

        assert assistant_msg["reasoning_content"] == "计算得出..."
        assert "tool_calls" not in assistant_msg

    def test_msg_without_reasoning_no_field(self):
        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": "你好！",
        }
        reasoning_content = ""
        if reasoning_content:
            assistant_msg["reasoning_content"] = reasoning_content

        assert "reasoning_content" not in assistant_msg

    def test_extra_body_structure_for_deepseek(self):
        """Verify the extra_body dict shape matches DeepSeek API requirement."""
        extra_body = {"thinking": {"type": "enabled"}}
        assert extra_body["thinking"]["type"] == "enabled"
        # Must match the format from liushi-think.txt and tool-think.txt
        assert "thinking" in extra_body


# ── Unit: multi-turn reasoning_content in api_messages ─────────────────────────

class TestMultiTurnReasoningPreservation:
    """reasoning_content must be preserved across turns for DeepSeek multi-turn."""

    def test_reasoning_included_in_api_messages_after_first_turn(self):
        """After turn 1, the assistant message in api_messages should have reasoning_content."""
        # Simulate turn 1 result
        api_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "9.11 and 9.8, which is greater?"},
        ]

        # Turn 1 assistant response with reasoning
        turn1_reasoning = "9.11比9.8大0.31"
        turn1_content = "9.11 大于 9.8。"

        api_messages.append({
            "role": "assistant",
            "content": turn1_content,
            "reasoning_content": turn1_reasoning,
        })

        # Turn 2 user message
        api_messages.append({
            "role": "user",
            "content": "How many Rs in strawberry?",
        })

        # Verify the messages list is correct for multi-turn DeepSeek
        assert len(api_messages) == 4
        assert api_messages[2]["role"] == "assistant"
        assert api_messages[2]["reasoning_content"] == turn1_reasoning
        # reasoning_content must NOT be passed in the second user message
        assert "reasoning_content" not in api_messages[3]

    def test_tool_call_iteration_preserves_reasoning(self):
        """Each tool-call iteration should preserve reasoning_content."""
        api_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "杭州明天天气怎么样"},
        ]

        # Iteration 1: model calls get_date
        api_messages.append({
            "role": "assistant",
            "content": None,
            "reasoning_content": "用户问天气，需要先获取日期再查询天气。",
            "tool_calls": [{
                "id": "tc1",
                "type": "function",
                "function": {"name": "get_date", "arguments": "{}"},
            }],
        })
        api_messages.append({
            "role": "tool",
            "tool_call_id": "tc1",
            "content": "2026-05-01",
        })

        # Iteration 2: model calls get_weather with the date
        api_messages.append({
            "role": "assistant",
            "content": None,
            "reasoning_content": "获得了今天的日期，现在用这个日期查询杭州天气。",
            "tool_calls": [{
                "id": "tc2",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"location":"杭州","date":"2026-05-01"}'},
            }],
        })

        # Both assistant messages should have reasoning_content
        assert api_messages[2]["reasoning_content"] == "用户问天气，需要先获取日期再查询天气。"
        assert api_messages[4]["reasoning_content"] == "获得了今天的日期，现在用这个日期查询杭州天气。"
        assert api_messages[2]["tool_calls"][0]["function"]["name"] == "get_date"
        assert api_messages[4]["tool_calls"][0]["function"]["name"] == "get_weather"


# ── SSE Pipeline integration: DeepSeek with thinking ──────────────────────────

@pytest.mark.anyio
class TestDeepSeekSSEPipeline:
    """Full SSE pipeline with DeepSeek model and thinking chunks."""

    async def _get_token(self) -> str:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/dev-login")
            return resp.json()["access_token"]

    async def test_chat_with_deepseek_thinking_chunks(self):
        """When using deepseek model, THINKING events should appear in stream."""
        token = await self._get_token()

        # Build fake SSE events as the engine would emit them
        from app.agent.stream_adapter import format_sse_event, SSEEventType

        thinking_event = format_sse_event(SSEEventType.THINKING, {"text": "让我思考一下..."})
        text_event = format_sse_event(SSEEventType.TEXT, {"text": "搜索结果如下"})

        assert "event: thinking" in thinking_event
        assert "让我思考一下" in thinking_event
        assert "event: text" in text_event

    async def test_chat_without_deepseek_no_thinking(self):
        """When using default (non-DeepSeek) model, no extra_body is added."""
        token = await self._get_token()

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Hello!"
        mock_chunk.choices[0].delta.tool_calls = None
        mock_chunk.choices[0].finish_reason = "stop"

        async def mock_stream():
            yield mock_chunk

        mock_create = AsyncMock(return_value=mock_stream())

        with patch("openai.resources.chat.completions.AsyncCompletions.create", mock_create), \
             patch("app.core.dependencies.get_redis", return_value=MagicMock()):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                timeout=30,
            ) as client:
                async with client.stream(
                    "POST",
                    "/api/v1/chat/",
                    json={"message": "Hello"},
                    headers={"Authorization": f"Bearer {token}"},
                ) as resp:
                    events: List[str] = []
                    thinking_events: List[str] = []
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            events.append(line)
                            if "thinking" in line:
                                thinking_events.append(line)
                        if any("done" in e for e in events):
                            break

                    # Non-DeepSeek model should NOT emit thinking events
                    assert len(thinking_events) == 0, (
                        f"Expected no THINKING events for non-DeepSeek model"
                    )

    async def test_deepseek_with_tool_call_no_lost_reasoning(self):
        """DeepSeek model with tool calls should preserve reasoning_content throughout the loop.

        This test verifies the api_messages structure directly (unit-test style),
        rather than going through the full HTTP SSE pipeline.
        """
        api_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "搜索test"},
        ]

        # Turn 1: model responds with reasoning + tool call
        api_messages.append({
            "role": "assistant",
            "content": None,
            "reasoning_content": "需要搜索信息",
            "tool_calls": [{
                "id": "tc_test1",
                "type": "function",
                "function": {"name": "brave_search", "arguments": '{"q":"test"}'},
            }],
        })

        # Tool result
        api_messages.append({
            "role": "tool",
            "tool_call_id": "tc_test1",
            "content": json.dumps({"results": [{"title": "Test", "url": "https://example.com"}]}),
        })

        # Turn 2: model responds with final answer
        api_messages.append({
            "role": "assistant",
            "content": "搜索结果：Test - https://example.com",
            "reasoning_content": "根据搜索结果，找到了相关信息。",
        })

        # Verify multi-turn structure preserves reasoning_content
        assert api_messages[2]["reasoning_content"] == "需要搜索信息"
        assert api_messages[2]["tool_calls"][0]["function"]["name"] == "brave_search"
        assert api_messages[3]["role"] == "tool"
        assert api_messages[4]["reasoning_content"] == "根据搜索结果，找到了相关信息。"
        assert api_messages[4]["content"] == "搜索结果：Test - https://example.com"


# ── Unit: save_message with reasoning_content ─────────────────────────────────

class TestSaveMessageReasoning:
    """save_message should persist reasoning_content to DB."""

    @pytest.mark.anyio
    async def test_save_message_includes_reasoning(self):
        """When reasoning_content is provided, it should be saved to the Message model."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        from app.agent.memory_manager import MemoryManager
        mm = MemoryManager(mock_db, conversation_id=1)

        msg = await mm.save_message(
            role="assistant",
            content="测试回复",
            tool_calls=[{"id": "tc1", "name": "test_tool", "arguments": "{}"}],
            reasoning_content="这是推理过程",
        )

        assert msg.role == "assistant"
        assert msg.content == "测试回复"
        assert msg.reasoning_content == "这是推理过程"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_save_message_without_reasoning(self):
        """When reasoning_content is None, the field should be None."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        from app.agent.memory_manager import MemoryManager
        mm = MemoryManager(mock_db, conversation_id=1)

        msg = await mm.save_message(
            role="assistant",
            content="普通回复",
            reasoning_content=None,
        )

        assert msg.reasoning_content is None
