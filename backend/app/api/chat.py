import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import ChatRequest
from app.core.config import settings, get_llm_providers
from app.core.dependencies import get_db, get_redis_client
from app.api.auth import get_current_user
from app.models import User
from app.agent.engine import AgentEngine
from app.agent.stream_adapter import SSEEventType, format_sse_event

router = APIRouter(tags=["chat"])

# Heartbeat interval (seconds) — keeps SSE connection alive during silent periods
SSE_HEARTBEAT_INTERVAL = 15


@router.get("/providers")
async def list_providers():
    """Return available LLM providers (API keys masked)."""
    providers = get_llm_providers()
    # Mask API keys for security
    for p in providers:
        key = p.get("api_key", "")
        if key and len(key) > 8:
            p["api_key"] = key[:4] + "..." + key[-4:]
        elif key:
            p["api_key"] = "****"
    return {"providers": providers}


@router.post("/")
async def chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """SSE streaming chat endpoint. Yields SSE events from the agent engine."""
    engine = AgentEngine(db_session=db, redis_client=redis, skill_name=req.skill_name)

    async def event_generator():
        # Create a queue for events; run the engine in a background task
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def produce():
            try:
                async for event_str in engine.run(
                    user=current_user,
                    message=req.message,
                    conversation_id=req.conversation_id,
                    provider_id=req.provider_id,
                    model=req.model,
                ):
                    await queue.put(event_str)
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                err = format_sse_event(SSEEventType.ERROR, {"message": f"Internal error: {exc}"})
                await queue.put(err)
            finally:
                await queue.put(None)  # sentinel

        producer_task = asyncio.create_task(produce())
        deadline = time.monotonic() + settings.REQUEST_TIMEOUT

        try:
            while True:
                # Check overall request timeout
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    yield format_sse_event(SSEEventType.ERROR, {
                        "message": f"请求超时（{settings.REQUEST_TIMEOUT}秒限制），请简化问题或稍后重试"
                    })
                    yield format_sse_event(SSEEventType.DONE, {"stop_reason": "timeout"})
                    break

                try:
                    wait_time = min(remaining, SSE_HEARTBEAT_INTERVAL)
                    event_str = await asyncio.wait_for(queue.get(), timeout=wait_time)
                except asyncio.TimeoutError:
                    # No event arrived within the interval — send a ping
                    yield format_sse_event(SSEEventType.PING, {"ts": time.time()})
                    continue

                if event_str is None:
                    break
                yield event_str
        finally:
            producer_task.cancel()
            try:
                await producer_task
            except (asyncio.CancelledError, Exception):
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
