"""Integration tests: default provider + DeepSeek with mocked API.

Verifies the full request/response pipeline for both providers
without requiring real API keys.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

# ── Shared test helpers ────────────────────────────────────────────

class _Delta:
    def __init__(self, content=None, reasoning_content=None, tool_calls=None):
        self.content = content
        self.reasoning_content = reasoning_content
        self.tool_calls = tool_calls

class _Choice:
    def __init__(self, delta=None, finish_reason=None, index=0):
        self.delta = delta or _Delta()
        self.finish_reason = finish_reason
        self.index = index

def _make_async_stream(chunks: list):
    """Create an async-iterable stream that yields chunk wrappers."""
    class _Stream:
        def __init__(self, items):
            self._items = items
        def __aiter__(self):
            self._iter = iter(self._items)
            return self
        async def __anext__(self):
            try:
                c = next(self._iter)
            except StopIteration:
                raise StopAsyncIteration
            return MagicMock(choices=[c])
    return _Stream(chunks)

_DEFAULT_CHUNKS = [
    _Choice(_Delta(content="Hello")),
    _Choice(_Delta(content=", world")),
    _Choice(_Delta(content="!")),
    _Choice(_Delta(), finish_reason="stop"),
]

_DEEPSEEK_CHUNKS = [
    _Choice(_Delta(reasoning_content="Let me think about this...")),
    _Choice(_Delta(reasoning_content="I need to consider carefully.")),
    _Choice(_Delta(content="The")),
    _Choice(_Delta(content=" answer is 42")),
    _Choice(_Delta(content=".")),
    _Choice(_Delta(), finish_reason="stop"),
]

# Tool call simulation
class _FuncDelta:
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments

class _ToolCallDelta:
    def __init__(self, index=0, id=None, type=None, function=None):
        self.index = index
        self.id = id
        self.type = type
        self.function = function

_DEEPSEEK_TOOL_CHUNKS = [
    _Choice(_Delta(tool_calls=[
        _ToolCallDelta(index=0, id="call_001", type="function",
                       function=_FuncDelta(name="web_search"))
    ])),
    _Choice(_Delta(tool_calls=[
        _ToolCallDelta(index=0, function=_FuncDelta(arguments='{"query"'))
    ])),
    _Choice(_Delta(tool_calls=[
        _ToolCallDelta(index=0, function=_FuncDelta(arguments=': "test"}'))
    ])),
    _Choice(_Delta(), finish_reason="tool_calls"),
]


# ── Provider Detection ────────────────────────────────────────────

class TestProviderDetection:
    def test_is_deepseek_by_provider_id(self):
        from app.llm.client import is_deepseek_provider
        assert is_deepseek_provider("deepseek", "") is True

    def test_is_deepseek_by_model(self):
        from app.llm.client import is_deepseek_provider
        for m in ("deepseek-v4-pro", "deepseek-v4-flash", "deepseek-reasoner"):
            assert is_deepseek_provider("", m) is True, f"failed for {m}"

    def test_not_deepseek(self):
        from app.llm.client import is_deepseek_provider
        assert is_deepseek_provider("openai", "gpt-4o") is False
        assert is_deepseek_provider("", "glm-5") is False

    def test_deepseek_substring_in_model(self):
        from app.llm.client import is_deepseek_provider
        assert is_deepseek_provider("any", "my-deepseek-wrapper") is True


# ── Build Client ──────────────────────────────────────────────────

class TestBuildClient:
    def test_deepseek_uses_official_base(self):
        from app.llm.client import build_llm_client
        client = build_llm_client(provider_id="deepseek", model="deepseek-v4-pro")
        assert "api.deepseek.com" in str(client.base_url)

    def test_custom_base_overrides_deepseek_default(self):
        from app.llm.client import build_llm_client
        client = build_llm_client(provider_id="deepseek", base_url="https://proxy/v1")
        assert "proxy" in str(client.base_url)

    def test_default_uses_configured_base(self):
        from app.llm.client import build_llm_client
        client = build_llm_client(base_url="https://custom.api/v1")
        assert "custom.api" in str(client.base_url)


# ── Streaming Tests: Default Provider ─────────────────────────────

class TestDefaultProviderStreaming:
    @pytest.mark.asyncio
    async def test_standard_streaming(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEFAULT_CHUNKS))

        events = []
        async for event in chat_completion_stream(
            mock_client, model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            provider_id="",
        ):
            events.append(event)

        full = "".join(e["content"] for e in events if e["type"] == "text")
        assert full == "Hello, world!"
        assert not any(e["type"] == "thinking" for e in events)

        done = events[-1]
        assert done["type"] == "done"
        assert done["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_no_extra_body_for_default(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEFAULT_CHUNKS))

        async for _ in chat_completion_stream(
            mock_client, model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hi"}],
            provider_id="openai",
        ):
            pass

        kwargs = mock_client.chat.completions.create.call_args[1]
        assert "extra_body" not in kwargs


# ── Streaming Tests: DeepSeek Provider ────────────────────────────

class TestDeepSeekProviderStreaming:
    @pytest.mark.asyncio
    async def test_thinking_mode_enabled_without_tools(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEEPSEEK_CHUNKS))

        events = []
        async for event in chat_completion_stream(
            mock_client, model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "What is the answer?"}],
            provider_id="deepseek",
        ):
            events.append(event)

        thinking = [e for e in events if e["type"] == "thinking"]
        assert len(thinking) >= 2, f"Expected >=2 thinking events, got {len(thinking)}"
        assert "Let me think" in thinking[0]["text"]

        text_events = [e for e in events if e["type"] == "text"]
        full = "".join(e["content"] for e in text_events)
        assert "42" in full

        kwargs = mock_client.chat.completions.create.call_args[1]
        assert kwargs.get("extra_body") == {"thinking": {"type": "enabled"}}

    @pytest.mark.asyncio
    async def test_thinking_disabled_with_tools(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEEPSEEK_TOOL_CHUNKS))

        tools = [{"type": "function", "function": {"name": "web_search", "parameters": {}}}]
        events = []
        async for event in chat_completion_stream(
            mock_client, model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "search test"}],
            provider_id="deepseek", tools=tools,
        ):
            events.append(event)

        thinking = [e for e in events if e["type"] == "thinking"]
        assert len(thinking) == 0, "Must NOT emit thinking with tools"

        kwargs = mock_client.chat.completions.create.call_args[1]
        assert "extra_body" not in kwargs

    @pytest.mark.asyncio
    async def test_tool_call_streaming(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEEPSEEK_TOOL_CHUNKS))

        events = []
        async for event in chat_completion_stream(
            mock_client, model="deepseek-v4-pro",
            messages=[{"role": "user", "content": "search"}],
            provider_id="deepseek",
            tools=[{"type": "function", "function": {"name": "web_search", "parameters": {}}}],
        ):
            events.append(event)

        done = events[-1]
        assert done["type"] == "done"
        assert done["finish_reason"] == "tool_calls"
        assert done["tool_calls"] is not None
        tc = done["tool_calls"][0]
        assert tc["id"] == "call_001"
        assert tc["function"]["name"] == "web_search"
        assert "test" in tc["function"]["arguments"]


# ── Multi-round Messages ──────────────────────────────────────────

class TestMultiRoundMessages:
    @pytest.mark.asyncio
    async def test_history_preserved_in_messages(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEFAULT_CHUNKS))

        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
        ]

        async for _ in chat_completion_stream(
            mock_client, model="gpt-4o-mini",
            messages=messages, provider_id="",
        ):
            pass

        sent = mock_client.chat.completions.create.call_args[1]["messages"]
        assert len(sent) == 3, f"Expected 3 messages, got {len(sent)}"
        assert sent[2]["content"] == "Q2"

    @pytest.mark.asyncio
    async def test_deepseek_multi_round_thinking(self):
        from app.llm.client import chat_completion_stream

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEEPSEEK_CHUNKS))

        # Round 1
        msgs = [{"role": "user", "content": "What is 2+2?"}]
        events1 = []
        async for event in chat_completion_stream(
            mock_client, model="deepseek-v4-pro",
            messages=msgs, provider_id="deepseek",
        ):
            events1.append(event)

        r1_text = "".join(e["content"] for e in events1 if e["type"] == "text")
        r1_thinking = [e for e in events1 if e["type"] == "thinking"]

        # Round 2
        msgs.append({"role": "assistant", "content": r1_text})
        msgs.append({"role": "user", "content": "And 3+3?"})

        mock_client2 = AsyncMock()
        mock_client2.chat.completions.create = AsyncMock(
            return_value=_make_async_stream(_DEEPSEEK_CHUNKS))

        events2 = []
        async for event in chat_completion_stream(
            mock_client2, model="deepseek-v4-pro",
            messages=msgs, provider_id="deepseek",
        ):
            events2.append(event)

        r2_thinking = [e for e in events2 if e["type"] == "thinking"]

        assert len(r1_thinking) > 0, "Round 1 must have thinking"
        assert len(r2_thinking) > 0, "Round 2 must have thinking"

        r2_sent = mock_client2.chat.completions.create.call_args[1]["messages"]
        assert len(r2_sent) == 3, f"Round 2 should have 3 msgs, got {len(r2_sent)}"


# ── Responder Node ────────────────────────────────────────────────

class TestResponderNode:
    def _make_state(self, **overrides):
        base = {
            "messages": [{"role": "user", "content": "Hello"}],
            "provider_id": "openai",
            "model": "gpt-4o-mini",
            "tool_results": None,
            "available_tools": None,
            "session_id": "t1", "user_id": 1, "conversation_id": 0,
            "intent": "chat", "plan": None, "current_step": 0,
            "retrieved_docs": None, "context": None, "feedback": None,
            "safety_passed": True, "approved": True, "retry_count": 0,
            "error": None, "response": None,
            "reasoning_content": None, "is_deepseek": False,
        }
        base.update(overrides)
        return base

    def test_default_provider_state(self):
        state = self._make_state()
        assert state["is_deepseek"] is False

    def test_deepseek_provider_state(self):
        state = self._make_state(provider_id="deepseek", model="deepseek-v4-pro", is_deepseek=True)
        assert state["is_deepseek"] is True

    def test_normalize_messages_basic(self):
        from app.graph.nodes.responder import _normalize_messages

        normalized = _normalize_messages([
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ])
        assert len(normalized) == 2
        assert all("role" in m and "content" in m for m in normalized)

    def test_normalize_messages_with_tool_calls(self):
        from app.graph.nodes.responder import _normalize_messages

        normalized = _normalize_messages([
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "test", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "result"},
        ])
        assert len(normalized) == 2
        assert "tool_calls" in normalized[0]
        assert normalized[1]["role"] == "tool"
