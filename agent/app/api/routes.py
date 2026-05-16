import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.graph.graph import build_agent_graph
from app.graph.state import AgentState
from app.llm.client import is_deepseek_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent")

graph = build_agent_graph()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    user_id: int = 0
    conversation_id: int = 0
    provider_id: str = ""
    model: str = ""
    messages: Optional[list] = None
    tools: Optional[list] = None
    skill_name: Optional[str] = None  # Phase 1: activate a specific skill


class ChatResponse(BaseModel):
    response: str
    session_id: str = ""
    tool_results: Optional[list] = None


@router.get("/health")
async def health():
    return {"status": "ok", "service": "agent-service", "version": "1.0.0"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    try:
        input_state = _build_input_state(request)
        result = await graph.ainvoke(input_state)
        return ChatResponse(
            response=result.get("response", ""),
            session_id=request.session_id,
            tool_results=result.get("tool_results"),
        )
    except Exception as e:
        logger.exception("chat error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming SSE chat endpoint."""
    classified_intent = _classify_intent(request.message)
    logger.warning("CHAT_STREAM intent=%s len=%d", classified_intent, len(request.message))
    input_state = _build_input_state(request, intent_override=classified_intent)

    async def generate():
        final_response = ""
        try:
            async for mode, chunk in graph.astream(input_state, stream_mode=["custom", "values"]):
                if mode == "custom":
                    if isinstance(chunk, dict):
                        t = chunk.get("type", "")
                        if t == "text":
                            c = chunk.get("content", "")
                            final_response += c
                            yield f"data: {json.dumps({'type': 'text', 'content': c}, ensure_ascii=False)}\n\n"
                        elif t == "thinking":
                            # Suppress thinking events from reaching the client
                            pass
                        elif t in ("tool_progress", "tool_call", "plan_created",
                                   "plan_step_update", "worker_started",
                                   "worker_progress", "worker_done",
                                   "compact_start", "compact_done",
                                   "file_download", "notice", "card"):
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

                elif mode == "values":
                    if isinstance(chunk, dict):
                        if chunk.get("error"):
                            yield f"data: {json.dumps({'type': 'error', 'error': chunk['error']}, ensure_ascii=False)}\n\n"
                        final_response = chunk.get("response") or final_response

            yield f"data: {json.dumps({'type': 'done', 'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("stream error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _build_input_state(request: ChatRequest, intent_override: str = "") -> dict:
    """Build the initial graph state from a chat request."""
    intent = intent_override or _classify_intent(request.message)

    # Merge Go gateway tools with Python-side tools
    from app.tools.registry import get_tool_registry
    python_tools = get_tool_registry().get_openai_tools()
    all_tools = (request.tools or []) + python_tools
    # Deduplicate by tool name
    seen = set()
    merged_tools = []
    for t in all_tools:
        name = t.get("function", {}).get("name", "")
        if name and name not in seen:
            seen.add(name)
            merged_tools.append(t)

    return {
        "messages": _build_messages(request),
        "session_id": request.session_id,
        "user_id": request.user_id,
        "conversation_id": request.conversation_id,
        "intent": intent,
        "plan": None,
        "current_step": 0,
        "tool_results": None,
        "retrieved_docs": None,
        "context": None,
        "feedback": None,
        "safety_passed": True,
        "approved": True,
        "retry_count": 0,
        "degraded_steps": None,
        "error": None,
        "response": None,
        "provider_id": request.provider_id,
        "model": request.model,
        "available_tools": merged_tools,
        "reasoning_content": None,
        "is_deepseek": _detect_deepseek(request.provider_id, request.model),
        # Phase 1
        "skill_tools": None,
        "active_skill": request.skill_name,
        "tool_call_history": None,
        # Phase 2
        "iteration_count": 0,
        "tool_call_log": None,
        # Phase 3
        "needs_workers": False,
        "worker_results": None,
        "plan_steps": None,
        # Phase 4
        "user_profile_str": None,
    }


def _detect_deepseek(provider_id: str, model: str) -> bool:
    return is_deepseek_provider(provider_id, model)


def _classify_intent(message: str) -> str:
    """Simple intent classification. Supports Chinese and English keywords."""
    cn_keywords = [
        "分析", "执行", "搜索", "计算", "查询", "规划", "生成报告",
        "找一下", "查一下", "对比", "总结", "推荐", "生成",
        "并行", "多智能体", "编排", "多步骤", "处理",
        "自动化", "抓取", "提取", "汇总", "收集",
        "调研", "调查", "研究", "挖掘", "追踪",
    ]
    en_keywords = ["search", "calculate", "compute", "analyze", "plan", "report"]
    all_keywords = cn_keywords + en_keywords
    msg_lower = message.lower()
    for kw in all_keywords:
        if kw in message or kw in msg_lower:
            return "task"
    return "chat"


def _build_messages(request: ChatRequest) -> list:
    """Build messages list from request."""
    msgs = []
    if request.messages:
        for m in request.messages:
            if isinstance(m, dict):
                msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})
    msgs.append({"role": "user", "content": request.message})
    return msgs
