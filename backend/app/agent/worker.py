"""Worker subsystem — logical sub-processes for Orchestrator-Worker pattern.

Each Worker runs an independent LLM session with its own message history
and tool registry. Workers are same-process coroutines (not OS processes)
that communicate via asyncio and shared result channels.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

from app.agent.tool_registry import ToolRegistry
from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for a single worker."""

    worker_id: str
    task: str
    skill_name: Optional[str] = None


@dataclass
class WorkerResult:
    """Result of a worker's execution."""

    worker_id: str
    status: str          # completed | failed | timeout
    content: str = ""
    tool_calls: int = 0
    error: Optional[str] = None


class Worker:
    """A logical sub-process that executes a single task with its own LLM session.

    The worker has:
    - Its own message history (system + user task)
    - Access to the parent's tool registry
    - A max iteration limit (3) to prevent runaway tool chains
    - Yields progress events as dicts for the parent engine to relay
    """

    MAX_ITERATIONS = 3

    def __init__(
        self,
        config: WorkerConfig,
        client: Any,
        registry: ToolRegistry,
        db: Any = None,
        redis: Any = None,
        model: Optional[str] = None,
    ) -> None:
        self.config = config
        self.client = client
        self.registry = registry
        self.db = db
        self.redis = redis
        self.model = model or settings.LLM_MODEL
        self._is_deepseek = "deepseek" in (self.model or "").lower()
        self._result: Optional[WorkerResult] = None

    @property
    def result(self) -> Optional[WorkerResult]:
        return self._result

    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the worker's task, yielding progress events.

        Yields dicts with keys:
          - type: "text" | "tool_call"
          - content/tool_name/etc.: event-specific payload
        """
        import httpx
        from openai import AsyncOpenAI

        # Build minimal message history
        api_messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    f"你是一个任务执行助手。请独立完成以下任务，尽量使用可用工具。\n"
                    f"任务完成后，直接给出结果摘要。\n"
                    f"你的worker_id是 {self.config.worker_id}。"
                ),
            },
            {"role": "user", "content": self.config.task},
        ]

        for iteration in range(self.MAX_ITERATIONS):
            assistant_text = ""
            reasoning_content = ""
            tool_calls: List[Dict[str, Any]] = []
            finish_reason = None

            try:
                create_kwargs: Dict[str, Any] = dict(
                    model=self.model,
                    max_tokens=2048,
                    messages=api_messages,
                    tools=self.registry.get_schemas(),
                    stream=True,
                )
                if self._is_deepseek:
                    create_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                stream = await self.client.chat.completions.create(**create_kwargs)  # type: ignore[arg-type]

                async for chunk in stream:
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta
                    choice_finish = chunk.choices[0].finish_reason

                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_content += delta.reasoning_content

                    if delta.content:
                        assistant_text += delta.content

                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            while len(tool_calls) <= idx:
                                tool_calls.append({"id": "", "name": "", "arguments": ""})
                            if tc_delta.id:
                                tool_calls[idx]["id"] = tc_delta.id
                            if tc_delta.function and tc_delta.function.name:
                                tool_calls[idx]["name"] = tc_delta.function.name
                            if tc_delta.function and tc_delta.function.arguments:
                                tool_calls[idx]["arguments"] += tc_delta.function.arguments

                    if choice_finish:
                        finish_reason = choice_finish

            except Exception as exc:
                self._result = WorkerResult(
                    worker_id=self.config.worker_id,
                    status="failed",
                    content=assistant_text,
                    tool_calls=0,
                    error=str(exc),
                )
                yield {"type": "error", "error": str(exc)}
                return

            # Build assistant message
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": assistant_text or None}
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls
                ]
            api_messages.append(assistant_msg)

            # Handle tool calls
            if finish_reason == "tool_calls" and tool_calls:
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_id = tc["id"]
                    try:
                        tool_input = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        tool_input = {}

                    yield {"type": "tool_call", "tool_name": tool_name, "tool_id": tool_id}

                    try:
                        result = await asyncio.wait_for(
                            self.registry.execute_tool(tool_name, **tool_input),
                            timeout=settings.TOOL_TIMEOUT,
                        )
                        result_str = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
                    except asyncio.TimeoutError:
                        result_str = f"工具 {tool_name} 执行超时"
                    except Exception as exc:
                        result_str = f"工具 {tool_name} 执行错误: {str(exc)}"

                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result_str,
                    })

                continue  # loop back for another LLM call

            # finish_reason == "stop" — done
            if finish_reason == "stop" or finish_reason is None:
                yield {"type": "text", "content": assistant_text}
                self._result = WorkerResult(
                    worker_id=self.config.worker_id,
                    status="completed",
                    content=assistant_text,
                    tool_calls=len(tool_calls),
                )
                return

        # Max iterations reached
        self._result = WorkerResult(
            worker_id=self.config.worker_id,
            status="completed",
            content=assistant_text,
            tool_calls=len(tool_calls),
        )
