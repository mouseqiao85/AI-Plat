"""Worker: independent LLM session with tool access for parallel subtask execution."""
import json
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.llm.client import build_llm_client
from app.tools.registry import get_tool_registry
from app.workers.models import WorkerConfig, WorkerResult

logger = logging.getLogger(__name__)


class Worker:
    """Executes a subtask with its own LLM session, up to max_iterations tool calls."""

    def __init__(self, config: WorkerConfig, provider_id: str = "", model: str = ""):
        self.config = config
        self.provider_id = provider_id
        self.model = model

    async def run(self) -> WorkerResult:
        """Execute the worker's task."""
        result = WorkerResult(
            worker_id=self.config.worker_id,
            task_description=self.config.task_description,
        )

        # If a specific tool is given, execute it directly
        if self.config.tool_name:
            tool_result = await self._execute_tool(
                self.config.tool_name, self.config.tool_args
            )
            result.result = tool_result.get("result")
            result.success = tool_result.get("success", False)
            result.iterations_used = 1
            result.tool_calls.append({
                "tool": self.config.tool_name,
                "args": self.config.tool_args,
                "result": tool_result,
            })
            return result

        # Otherwise, use LLM to decide tools iteratively
        try:
            client = build_llm_client(provider_id=self.provider_id, model=self.model)
            effective_model = self.model or settings.LLM_MODEL

            # Build available tools list
            registry = get_tool_registry()
            all_tools = registry.get_openai_tools()

            messages = [{
                "role": "user",
                "content": (
                    f"Complete this subtask: {self.config.task_description}\n"
                    "Use available tools if needed. Be concise."
                ),
            }]

            for iteration in range(self.config.max_iterations):
                create_kwargs = {
                    "model": effective_model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                }
                if all_tools:
                    create_kwargs["tools"] = all_tools

                resp = await client.chat.completions.create(**create_kwargs)
                choice = resp.choices[0]

                if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                    # Execute tool calls
                    for tc in choice.message.tool_calls:
                        tool_name = tc.function.name
                        try:
                            tool_args = json.loads(tc.function.arguments)
                        except (json.JSONDecodeError, TypeError):
                            tool_args = {}

                        tool_result = await self._execute_tool(tool_name, tool_args)
                        result.tool_calls.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": tool_result,
                        })

                        # Add tool result to messages for next iteration
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{"id": tc.id, "type": "function",
                                           "function": {"name": tool_name, "arguments": tc.function.arguments}}],
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        })

                    result.iterations_used = iteration + 1
                else:
                    # LLM produced final answer
                    result.result = choice.message.content or ""
                    result.success = True
                    result.iterations_used = iteration + 1
                    return result

            # Exhausted iterations — get final answer
            messages.append({"role": "user", "content": "请总结你的发现。"})
            resp = await client.chat.completions.create(
                model=effective_model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
            )
            result.result = resp.choices[0].message.content or ""
            result.success = True

        except Exception as e:
            logger.error("worker %d failed: %s", self.config.worker_id, e)
            result.error = str(e)
            result.success = False

        return result

    async def _execute_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a tool - try local first, then Go gateway."""
        registry = get_tool_registry()
        local_tool = registry.get(tool_name)

        if local_tool:
            try:
                return await local_tool.execute(args)
            except Exception as e:
                return {"result": str(e), "success": False}

        # Fall back to Go gateway
        try:
            headers = {}
            if settings.DEBUG and settings.GO_DEV_TOKEN:
                headers["Authorization"] = f"Bearer {settings.GO_DEV_TOKEN}"

            async with httpx.AsyncClient(timeout=settings.TOOL_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.GO_CALLBACK_URL}/api/v1/tools/execute",
                    json={"tool_name": tool_name, "arguments": args, "session_id": ""},
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.json()
                return {"result": f"HTTP {resp.status_code}: {resp.text}", "success": False}
        except Exception as e:
            return {"result": str(e), "success": False}
