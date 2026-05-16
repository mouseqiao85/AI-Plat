"""Task planning node with LLM-based planning + keyword fallback.

Merges Go gateway tools with Python-side skill tools for a unified tool list.
"""
import json
import logging
from langgraph.config import get_stream_writer
from openai import AsyncOpenAI
from app.core.config import settings
from app.graph.state import AgentState
from app.llm.client import build_llm_client
from app.tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


async def planner_node(state: AgentState) -> dict:
    """Plan task execution steps based on user input and available tools.

    Merges Go gateway tools (from state.available_tools) with Python-side
    skill tools (from ToolRegistry) into a unified tool list for planning.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"error": "no messages", "plan": []}

    user_msg = ""
    for m in reversed(messages):
        content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
        if content and content.strip():
            user_msg = content
            break

    logger.info("planner_node called, intent=%s", state.get("intent", "?"))

    # Merge Go tools + Python skill tools
    go_tools = state.get("available_tools") or []
    registry = get_tool_registry()
    skill_tools_openai = registry.get_openai_tools()

    all_tools = go_tools + skill_tools_openai
    tool_names = [_get_tool_name(t) for t in all_tools]
    tool_descriptions = "\n".join(
        f"- {_get_tool_name(t)}: {_get_tool_description(t)}"
        for t in all_tools
    ) if all_tools else "无可用工具"

    # Try LLM-based planning
    steps = []
    needs_workers = False
    try:
        client = build_llm_client(
            provider_id=state.get("provider_id", ""),
            model=state.get("model", ""),
        )
        effective_model = state.get("model") or settings.LLM_MODEL

        planning_prompt = f"""你是一个任务规划助手。根据用户输入和可用工具，生成执行计划。

可用工具:
{tool_descriptions}

用户输入: {user_msg}

请返回JSON格式的执行计划:
{{"steps": [{{"tool": "tool_name", "args": {{...}}, "description": "步骤说明"}}], "needs_workers": false}}

- 如果多个步骤可以并行执行（互不依赖），设置 "needs_workers": true
- 如果不需要工具，返回: {{"steps": [], "needs_workers": false}}
"""
        resp = await client.chat.completions.create(
            model=effective_model,
            messages=[{"role": "user", "content": planning_prompt}],
            temperature=0.3,
            max_tokens=1000,
        )
        content = resp.choices[0].message.content or "{}"
        # Strip DeepSeek/thinking-style reasoning prefix before the first '{'
        brace_idx = content.find("{")
        if brace_idx > 0:
            content = content[brace_idx:]
        logger.debug("planner llm response: %s", content[:200])
        cleaned = content.strip().removeprefix("```json").removesuffix("```")
        plan_data = json.loads(cleaned)
        steps = plan_data.get("steps", [])
        needs_workers = plan_data.get("needs_workers", False)
    except Exception as e:
        logger.warning("planner llm failed, using keyword fallback: %s", e)

    # Keyword fallback when LLM plan is empty or failed
    if not steps and tool_names:
        steps = _keyword_plan(user_msg, tool_names)
        if steps:
            logger.info("planner keyword fallback: %d steps", len(steps))

    if steps:
        writer = get_stream_writer()
        writer({
            "type": "plan_created",
            "steps": len(steps),
            "needs_workers": needs_workers,
            "plan": [{"tool": s.get("tool", "?"), "desc": s.get("description", "")} for s in steps[:5]],
        })

    return {
        "plan": steps,
        "current_step": 0,
        "needs_workers": needs_workers,
        "plan_steps": steps,
        "skill_tools": skill_tools_openai,
    }


def _keyword_plan(user_msg: str, tool_names: list) -> list:
    """Generate a simple plan based on keyword matching."""
    steps = []
    msg_lower = user_msg.lower()

    if "calculator" in tool_names and ("计算" in user_msg or "calculator" in msg_lower or "算" in user_msg or any(op in user_msg for op in "+-*/")):
        expr = user_msg
        for prefix in ["计算", "算", "calculate", "compute"]:
            expr = expr.replace(prefix, "").strip()
        steps.append({
            "tool": "calculator",
            "args": {"expression": expr},
            "description": f"计算: {expr}",
        })

    if "web_search" in tool_names and ("搜索" in user_msg or "search" in msg_lower or "新闻" in user_msg or "news" in msg_lower or "查询" in user_msg):
        query = user_msg
        for prefix in ["搜索", "search", "查询"]:
            query = query.replace(prefix, "").strip()
        steps.append({
            "tool": "web_search",
            "args": {"query": query},
            "description": f"搜索: {query}",
        })

    # Skill tool keyword matching
    registry = get_tool_registry()
    for tool in registry.list_tools():
        # Match skill tools by checking if their description keywords appear in user message
        if tool.name.startswith("skill_") and tool.name.endswith("_run"):
            skill_name = tool.name.replace("skill_", "").replace("_run", "")
            if skill_name.replace("-", "") in msg_lower.replace("-", "") or \
               any(kw in user_msg for kw in ["热点", "新闻", "hot", "news"]) and "news" in skill_name:
                steps.append({
                    "tool": tool.name,
                    "args": {"input": user_msg, "params": {}},
                    "description": tool.description,
                })

    return steps


def _get_tool_name(t: dict) -> str:
    """Extract tool name from OpenAI format or plain dict format."""
    if isinstance(t, dict):
        fn = t.get("function", {})
        if isinstance(fn, dict) and fn.get("name"):
            return fn["name"]
        return t.get("name", "unknown")
    return "unknown"


def _get_tool_description(t: dict) -> str:
    """Extract tool description from OpenAI format or plain dict format."""
    if isinstance(t, dict):
        fn = t.get("function", {})
        if isinstance(fn, dict) and fn.get("description"):
            return fn["description"]
        return t.get("description", "")
    return ""
