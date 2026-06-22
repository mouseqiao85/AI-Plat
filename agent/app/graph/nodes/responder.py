"""Response generation node with streaming support.

Enhanced (Phase 4) with user profile injection into system prompt.
Enhanced (Phase 5) with long output file generation.
Enhanced (Phase 6) with inline tool-call loop — when the LLM returns tool_calls,
the responder executes them, injects results, and re-calls the LLM until
a pure text response is produced.
"""
import json
import logging
import re
from datetime import datetime
from langgraph.config import get_stream_writer
from app.graph.state import AgentState
from app.llm.client import (
    build_llm_client,
    chat_completion_stream,
    is_deepseek_provider,
)
from app.tools.registry import get_tool_registry
from app.core.config import settings

logger = logging.getLogger(__name__)

_HTML_RE = re.compile(r'<[^>]+>')
_ENTITY_RE = re.compile(r'&[#\w]+;')

# Threshold for triggering file generation (chars)
FILE_GEN_THRESHOLD = 3000

# Max rounds of inline tool-call loop to prevent infinite loops
MAX_TOOL_ROUNDS = 8

FILE_OUTPUT_FORMATS = [
    ("pptx", [r"\bpptx?\b", r"幻灯片", r"演示文稿"]),
    ("docx", [r"\bdocx?\b", r"\bword\b", r"文档"]),
    ("xlsx", [r"\bxlsx?\b", r"\bexcel\b", r"表格", r"工作簿"]),
    ("html", [r"\bhtml?\b", r"网页"]),
    ("md", [r"\bmarkdown\b", r"\bmd\b"]),
]


def _latest_user_text(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content") or "")
    return ""


def _requested_file_format(text: str) -> str:
    lower = (text or "").lower()
    wants_output = any(keyword in lower for keyword in [
        "输出", "生成", "导出", "下载", "保存", "文件", "ppt", "html", "markdown", "doc", "word", "excel", "xlsx",
        "create", "generate", "export", "download", "save", "file",
    ])
    if not wants_output:
        return ""
    for fmt, patterns in FILE_OUTPUT_FORMATS:
        if any(re.search(pattern, lower, re.IGNORECASE) for pattern in patterns):
            return fmt
    return ""


def _file_placeholder(filename: str) -> str:
    return f"已生成文件：{filename}"


def _clean_html(text: str) -> str:
    text = _HTML_RE.sub('', text)
    text = _ENTITY_RE.sub('', text)
    return text[:2000]


async def responder_node(state: AgentState) -> dict:
    """Generate response with inline tool-call loop support.

    If the LLM returns tool_calls, this node will:
    1. Execute each tool via the registry (local) or remote (Go gateway)
    2. Inject tool results back into the message context
    3. Re-call the LLM with the updated context
    4. Repeat until a pure text response is produced or MAX_TOOL_ROUNDS is reached
    """
    messages = list(state.get("messages", []))
    provider_id = state.get("provider_id", "")
    model = state.get("model", "")
    tools = state.get("available_tools")
    writer = get_stream_writer()
    deepseek = is_deepseek_provider(provider_id, model)
    file_output_format = _requested_file_format(_latest_user_text(messages))

    # Track tool results across rounds
    all_tool_results = list(state.get("tool_results") or [])
    tool_call_history = list(state.get("tool_call_history") or [])
    iteration_count = state.get("iteration_count", 0)

    # Build initial system context from existing tool results + user profile
    system_context = _build_system_context(state, all_tool_results)
    if system_context:
        # Inject as a system message before the existing messages
        ctx_msg = {"role": "system", "content": system_context}
        messages = [ctx_msg] + _normalize_messages(messages)

    rounds = 0
    last_text_response = ""
    final_reasoning = ""

    while rounds < MAX_TOOL_ROUNDS:
        rounds += 1
        iteration_count += 1

        client = build_llm_client(provider_id=provider_id, model=model)
        api_messages = _normalize_messages(messages)

        # Inject user profile on the first round
        if rounds == 1:
            user_profile_str = state.get("user_profile_str", "")
            if user_profile_str:
                api_messages.insert(0, {"role": "system", "content": user_profile_str})

        if not api_messages:
            return {"response": "抱歉，我无法理解您的请求。请重新描述您的问题。", "error": "empty_messages"}

        full_content = ""
        reasoning = ""
        tool_calls_result = None

        try:
            async for event in chat_completion_stream(
                client=client,
                model=model,
                messages=api_messages,
                tools=tools,
                provider_id=provider_id,
            ):
                if event["type"] == "text":
                    full_content += event["content"]
                    if not file_output_format:
                        writer({"type": "text", "content": event["content"]})
                elif event["type"] == "thinking":
                    reasoning += event.get("text", "")
                elif event["type"] == "done":
                    tc = event.get("tool_calls")
                    if tc and tools:
                        tool_calls_result = tc
                    else:
                        last_text_response = full_content or event.get("content", "")
                        final_reasoning = reasoning
                    break  # Done event always breaks the stream loop

        except Exception as e:
            logger.error("responder round %d failed: %s", rounds, e)
            return {
                "response": f"抱歉，回复生成失败: {str(e)}",
                "error": str(e),
                "is_deepseek": deepseek,
                "iteration_count": iteration_count,
                "tool_call_history": tool_call_history,
                "tool_results": all_tool_results,
            }

        # If no tool_calls, we have the final text response
        if not tool_calls_result:
            # Phase 5: Check long output for file generation
            content_to_check = last_text_response or full_content
            file_info = None
            if file_output_format:
                file_info = await _try_generate_file(content_to_check, state, writer, file_output_format)
                if file_info:
                    placeholder = _file_placeholder(file_info["filename"])
                    writer({"type": "text", "content": placeholder})
                    content_to_check = placeholder
            elif len(content_to_check) > FILE_GEN_THRESHOLD:
                await _try_generate_file(content_to_check, state, writer)

            return {
                "response": content_to_check,
                "reasoning_content": final_reasoning,
                "is_deepseek": deepseek,
                "iteration_count": iteration_count,
                "tool_call_history": tool_call_history,
                "tool_results": all_tool_results,
            }

        # ── Execute tool calls ──
        logger.info("responder tool-call round %d/%d: %d tool calls",
                     rounds, MAX_TOOL_ROUNDS, len(tool_calls_result))

        # Emit tool_call events to frontend
        for tc in tool_calls_result:
            tname = tc.get("function", {}).get("name", "unknown")
            targs = tc.get("function", {}).get("arguments", "{}")
            writer({
                "type": "tool_call",
                "tool_name": tname,
                "tool_args": targs,
                "status": "running",
            })

        round_results = []
        tool_call_log_entries = []

        for tc in tool_calls_result:
            tcid = tc.get("id", "")
            tname = tc.get("function", {}).get("name", "unknown")
            try:
                targs = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                targs = {}

            result = await _execute_tool(tname, targs, state, writer, deepseek)
            success = result.get("success", False)
            result_text = result.get("result", str(result))

            round_results.append({
                "tool_call_id": tcid,
                "tool_name": tname,
                "result": result_text,
                "success": success,
            })
            tool_call_log_entries.append({"tool": tname, "success": success})

        # Accumulate results into the message context
        all_tool_results.extend(round_results)
        tool_call_history.extend(tool_call_log_entries)

        # Inject assistant message with tool_calls + tool results into messages
        assistant_msg = {
            "role": "assistant",
            "tool_calls": tool_calls_result,
        }
        if full_content:
            assistant_msg["content"] = full_content
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        messages.append(assistant_msg)
        for rr in round_results:
            messages.append({
                "role": "tool",
                "tool_call_id": rr["tool_call_id"],
                "content": str(rr["result"])[:2000],
            })

        # Stream a brief notice about the round
        writer({"type": "notice", "content": f"[Round {rounds} completed — {len(round_results)} tool(s) executed]"})

    # MAX_TOOL_ROUNDS reached — return whatever we have
    logger.warning("responder reached max tool rounds (%d)", MAX_TOOL_ROUNDS)
    fallback = last_text_response or "抱歉，生成回复时达到了最大工具调用轮次。请尝试简化您的问题。"
    return {
        "response": fallback,
        "reasoning_content": final_reasoning,
        "is_deepseek": deepseek,
        "iteration_count": iteration_count,
        "tool_call_history": tool_call_history,
        "tool_results": all_tool_results,
    }


async def _execute_tool(tool_name: str, args: dict, state: AgentState,
                        writer, deepseek: bool) -> dict:
    """Execute a single tool — local (Python registry) or remote (Go gateway)."""
    registry = get_tool_registry()
    local_tool = registry.get(tool_name)

    if local_tool:
        # Local execution (skill tools, built-in Python tools)
        try:
            result = await local_tool.execute(args)
            writer({
                "type": "tool_progress",
                "tool_name": tool_name,
                "status": "completed" if result.get("success", True) else "failed",
            })
            return result
        except Exception as e:
            logger.error("local tool %s failed: %s", tool_name, e)
            writer({"type": "tool_progress", "tool_name": tool_name, "status": "failed"})
            return {"result": f"Tool execution error: {str(e)}", "success": False}
    else:
        # Remote execution via Go gateway
        return await _execute_remote_tool(tool_name, args, state, writer)


async def _execute_remote_tool(tool_name: str, args: dict, state: AgentState,
                                writer) -> dict:
    """Execute a tool via Go gateway HTTP callback."""
    try:
        import httpx
        headers = {}
        gateway_dev_token = settings.gateway_dev_token
        gateway_jwt_secret = settings.gateway_jwt_secret
        if settings.DEBUG and gateway_dev_token:
            headers["Authorization"] = f"Bearer {gateway_dev_token}"
        elif gateway_jwt_secret:
            from jose import jwt as _jwt
            try:
                token = _jwt.encode(
                    {"sub": "agent-service", "role": "admin"},
                    gateway_jwt_secret,
                    algorithm=settings.JWT_ALGORITHM,
                )
                headers["Authorization"] = f"Bearer {token}"
            except Exception:
                pass

        writer({
            "type": "tool_progress",
            "tool_name": tool_name,
            "status": "running",
        })

        async with httpx.AsyncClient(timeout=settings.TOOL_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.GO_CALLBACK_URL}/api/v1/tools/execute",
                json={
                    "tool_name": tool_name,
                    "arguments": args,
                    "session_id": state.get("session_id", ""),
                },
                headers=headers,
            )
            if resp.status_code == 200:
                result = resp.json()
                if not result.get("result"):
                    result["result"] = "(empty response from tool)"
                writer({
                    "type": "tool_progress",
                    "tool_name": tool_name,
                    "status": "completed",
                })
                return {"result": result.get("result", ""), "success": result.get("success", True)}
            else:
                error_text = resp.text
                writer({"type": "tool_progress", "tool_name": tool_name, "status": "failed"})
                return {"result": f"Remote tool failed: {error_text}", "success": False}
    except Exception as e:
        logger.error("remote tool %s failed: %s", tool_name, e)
        writer({"type": "tool_progress", "tool_name": tool_name, "status": "failed"})
        return {"result": f"Remote tool error: {str(e)}", "success": False}


async def _try_generate_file(content: str, state: dict, writer, format_hint: str = "") -> dict | None:
    """Try to generate a downloadable file for long outputs."""
    try:
        from app.tools.file_gen import generate_file
        file_info = await generate_file(
            content=content,
            session_id=state.get("session_id", ""),
            user_id=state.get("user_id", 0),
            format_hint=format_hint,
        )
        if file_info:
            writer({
                "type": "file_download",
                "file_id": file_info["file_id"],
                "filename": file_info["filename"],
                "download_url": file_info["download_url"],
                "url": file_info["download_url"],
                "content_type": file_info["content_type"],
                "size": file_info["size"],
            })
            return file_info
    except Exception as e:
        logger.warning("file generation failed: %s", e)
    return None


def _build_system_context(state: AgentState, tool_results: list) -> str:
    """Build system context from current date and existing tool results."""
    today = datetime.now().strftime("%Y-%m-%d")
    available_tool_names = {
        _get_tool_name(t)
        for t in [
            *(state.get("available_tools") or []),
            *(state.get("skill_tools") or []),
            *get_tool_registry().get_openai_tools(),
        ]
    }
    parts = [
        f"当前日期: {today}",
        "涉及最新、当前、今年、今天、实时、新闻、趋势、近期事实或报告时间的问题，不要仅凭模型记忆作答。",
    ]
    if "brave_search" in available_tool_names:
        parts.append("回答上述时效性问题前，应优先调用 brave_search 获取互联网最新信息。")
    elif "web_search" in available_tool_names:
        parts.append("回答上述时效性问题前，应优先调用 web_search 获取互联网最新信息。")

    if tool_results:
        parts.append("已有工具执行结果:")
        for r in tool_results:
            tname = r.get("tool_name", r.get("tool", "unknown"))
            raw = str(r.get("result", r.get("error", "")))
            parts.append(f"[工具 {tname}]: {_clean_html(raw)}")

    return "\n".join(parts)


def _get_tool_name(t: dict) -> str:
    if isinstance(t, dict):
        fn = t.get("function", {})
        if isinstance(fn, dict) and fn.get("name"):
            return fn["name"]
        return t.get("name", "")
    return ""



def _normalize_messages(messages: list) -> list:
    """Normalize message list to OpenAI API format."""
    result = []
    role_map = {"human": "user", "ai": "assistant", "system": "system",
                "developer": "developer", "tool": "tool", "function": "function"}
    for m in messages:
        if isinstance(m, dict):
            role = m.get("role", "")
            content = m.get("content", "")
            if role and (content or m.get("tool_calls") or m.get("tool_call_id")):
                entry = {"role": role}
                if m.get("tool_calls"):
                    entry["tool_calls"] = m["tool_calls"]
                    if content:
                        entry["content"] = content
                else:
                    entry["content"] = content or ""
                if m.get("reasoning_content"):
                    entry["reasoning_content"] = m["reasoning_content"]
                if m.get("tool_call_id"):
                    entry["tool_call_id"] = m["tool_call_id"]
                result.append(entry)
        elif hasattr(m, "type") and hasattr(m, "content"):
            role = role_map.get(m.type, m.type)
            result.append({"role": role, "content": m.content or ""})
        elif hasattr(m, "role") and hasattr(m, "content"):
            result.append({"role": m.role, "content": m.content or ""})
    return result
