"""Provider-aware LLM client with DeepSeek thinking mode support."""
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# DeepSeek provider configuration
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"}


def is_deepseek_provider(provider_id: str = "", model: str = "") -> bool:
    """Detect whether the current provider/model is DeepSeek."""
    if provider_id == "deepseek":
        return True
    if "deepseek" in model.lower():
        return True
    return False


def build_llm_client(
    api_key: str = "",
    base_url: str = "",
    provider_id: str = "",
    model: str = "",
) -> AsyncOpenAI:
    """Build an AsyncOpenAI client for the given provider/model.

    Resolution order:
    1. Explicit api_key/base_url params
    2. Dynamic provider from llm_providers.json (by provider_id)
    3. DeepSeek detection (by provider_id or model name)
    4. Default settings from config
    """
    # Try dynamic provider resolution
    dynamic_provider = None
    if provider_id and not api_key and not base_url:
        try:
            from app.core.providers import get_provider
            dynamic_provider = get_provider(provider_id)
            if dynamic_provider and dynamic_provider.enabled:
                api_key = dynamic_provider.api_key
                base_url = dynamic_provider.base_url
        except Exception:
            pass

    if is_deepseek_provider(provider_id, model):
        effective_base = base_url or DEEPSEEK_BASE_URL
        effective_key = api_key or settings.LLM_DEEPSEEK_API_KEY
        logger.debug("using deepseek client base=%s model=%s", effective_base, model or "deepseek-v4-pro")
    else:
        effective_base = base_url or settings.LLM_BASE_URL
        effective_key = api_key or settings.LLM_API_KEY

    # Build custom headers: prefer dynamic provider's custom_header, then settings
    default_headers = None
    custom_header_str = ""
    if dynamic_provider and dynamic_provider.custom_header:
        custom_header_str = dynamic_provider.custom_header
    elif settings.LLM_CUSTOM_HEADER:
        custom_header_str = settings.LLM_CUSTOM_HEADER

    if custom_header_str:
        try:
            default_headers = json.loads(custom_header_str)
        except (json.JSONDecodeError, TypeError):
            logger.warning("failed to parse custom_header: %s", custom_header_str)

    logger.debug("llm client: base=%s model=%s has_custom_header=%s",
                 effective_base, model or settings.LLM_MODEL, bool(default_headers))

    return AsyncOpenAI(
        api_key=effective_key,
        base_url=effective_base,
        timeout=settings.LLM_TIMEOUT,
        default_headers=default_headers,
    )


@dataclass
class LLMResponse:
    content: str = ""
    reasoning_content: str = ""
    finish_reason: str = "stop"
    tool_calls: list = field(default_factory=list)


async def chat_completion(
    client: AsyncOpenAI,
    model: str,
    messages: list,
    tools: Optional[list] = None,
    stream: bool = False,
    provider_id: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> LLMResponse:
    """Non-streaming chat completion with DeepSeek thinking support."""
    create_kwargs: dict = {
        "model": model or settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    if tools:
        create_kwargs["tools"] = tools

    deepseek = is_deepseek_provider(provider_id, model)
    if deepseek and not tools:
        create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

    resp = await client.chat.completions.create(**create_kwargs)
    choice = resp.choices[0]

    return LLMResponse(
        content=choice.message.content or "",
        reasoning_content=getattr(choice.message, "reasoning_content", "") or "",
        finish_reason=choice.finish_reason or "stop",
        tool_calls=[],
    )


async def chat_completion_stream(
    client: AsyncOpenAI,
    model: str,
    messages: list,
    tools: Optional[list] = None,
    provider_id: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[dict]:
    """Streaming chat completion yielding {type, content, reasoning_content, tool_calls, finish_reason} events.

    Supports DeepSeek thinking mode with automatic tool-call conflict resolution:
    - DeepSeek supports tools OR thinking, not both simultaneously.
    - When tools are provided, thinking is disabled.
    - When no tools, thinking is enabled.
    """
    create_kwargs: dict = {
        "model": model or settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    if tools:
        create_kwargs["tools"] = tools

    deepseek = is_deepseek_provider(provider_id, model)
    if deepseek and not tools:
        create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

    logger.debug("llm_stream model=%s deepseek=%s has_tools=%s", model, deepseek, bool(tools))

    stream = await client.chat.completions.create(**create_kwargs)

    reasoning_content = ""
    content = ""
    tool_call_buf: dict[int, dict] = {}

    async for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        # Reasoning / thinking content (DeepSeek)
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            reasoning_content += delta.reasoning_content
            yield {
                "type": "thinking",
                "text": delta.reasoning_content,
                "reasoning_content": reasoning_content,
            }

        # Regular text content
        if delta.content:
            content += delta.content
            yield {
                "type": "text",
                "content": delta.content,
            }

        # Tool calls (streaming)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in tool_call_buf:
                    tool_call_buf[idx] = {
                        "id": tc.id or "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                if tc.id:
                    tool_call_buf[idx]["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        tool_call_buf[idx]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        tool_call_buf[idx]["function"]["arguments"] += tc.function.arguments

        finish_reason = chunk.choices[0].finish_reason
        if finish_reason:
            tool_calls_list = sorted(tool_call_buf.values(), key=lambda x: list(tool_call_buf.keys())[list(tool_call_buf.values()).index(x)] if x in tool_call_buf.values() else 0)
            yield {
                "type": "done",
                "finish_reason": finish_reason,
                "content": content,
                "reasoning_content": reasoning_content,
                "tool_calls": tool_calls_list if tool_calls_list else None,
            }
