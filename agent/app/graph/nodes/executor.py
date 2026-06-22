"""Tool execution node with dual-dispatch: local skill tools + Go gateway tools."""
import json
import logging
import httpx
from langgraph.config import get_stream_writer
from app.core.config import settings
from app.graph.state import AgentState
from app.tools.registry import get_tool_registry

logger = logging.getLogger(__name__)

MAX_RETRY = 3
MAX_ITERATIONS = 80
REPEAT_FAIL_THRESHOLD = 3
REPEAT_SUCCESS_THRESHOLD = 8


async def executor_node(state: AgentState) -> dict:
    """Execute the current step in the plan.

    Dual-dispatch logic:
    - If tool is registered in Python ToolRegistry → execute locally
    - Otherwise → POST to Go gateway /api/v1/tools/execute

    Enhanced with:
    - Iteration counting and max_iterations enforcement
    - Duplicate detection and repeat prevention
    - Per-tool retry (3 attempts)
    - Empty response protection
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    retry_count = state.get("retry_count", 0)
    iteration_count = state.get("iteration_count", 0) + 1
    tool_call_log = list(state.get("tool_call_log") or [])

    if not plan or current_step >= len(plan):
        logger.info("executor_node skipping: plan_len=%d step=%d", len(plan), current_step)
        return {"tool_results": [], "current_step": current_step, "iteration_count": iteration_count}

    # Max iterations enforcement (Phase 2)
    if iteration_count > MAX_ITERATIONS:
        logger.warning("max iterations reached (%d), forcing respond", iteration_count)
        return {
            "tool_results": state.get("tool_results") or [],
            "current_step": len(plan),  # Force to end
            "iteration_count": iteration_count,
        }

    # Mid-session auto-compact check (Phase 2)
    messages = state.get("messages", [])
    if messages and iteration_count % 5 == 0:  # Check every 5 iterations
        try:
            from app.memory.manager import MemoryManager
            from app.llm.client import build_llm_client
            mm = MemoryManager()
            msg_dicts = [
                {"role": getattr(m, "type", "user") if not isinstance(m, dict) else m.get("role", "user"),
                 "content": getattr(m, "content", "") if not isinstance(m, dict) else m.get("content", "")}
                for m in messages
            ]
            writer_tmp = get_stream_writer()
            client = build_llm_client(
                provider_id=state.get("provider_id", ""),
                model=state.get("model", ""),
            )
            compacted = await mm.mid_session_compact(
                msg_dicts, client, state.get("model") or settings.LLM_MODEL, writer_tmp,
            )
            # Note: we don't update messages in state here as LangGraph
            # manages message state; this is for logging/notification only
        except Exception as e:
            logger.debug("mid_session_compact skipped: %s", e)

    step = plan[current_step]
    tool_name = step.get("tool", "")
    args = step.get("args", {})
    logger.info("executor_node executing: step=%d/%d tool=%s iter=%d",
                current_step, len(plan), tool_name, iteration_count)

    # Duplicate detection (Phase 2)
    consecutive_fails = _count_consecutive(tool_call_log, tool_name, success=False)
    consecutive_successes = _count_consecutive(tool_call_log, tool_name, success=True)

    if consecutive_fails >= REPEAT_FAIL_THRESHOLD:
        logger.warning("tool %s failed %d consecutive times, stopping", tool_name, consecutive_fails)
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({
            "tool": tool_name, "args": args,
            "result": {"error": f"Stopped: {tool_name} failed {consecutive_fails} consecutive times"},
            "success": False,
        })
        return {
            "tool_results": tool_results,
            "current_step": current_step + 1,
            "retry_count": 0,
            "iteration_count": iteration_count,
            "tool_call_log": tool_call_log,
        }

    if consecutive_successes >= REPEAT_SUCCESS_THRESHOLD:
        logger.warning("tool %s succeeded %d consecutive times, synthesizing", tool_name, consecutive_successes)
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({
            "tool": tool_name, "args": args,
            "result": {"notice": "Results synthesized from repeated successful calls"},
            "success": True,
        })
        return {
            "tool_results": tool_results,
            "current_step": current_step + 1,
            "retry_count": 0,
            "iteration_count": iteration_count,
            "tool_call_log": tool_call_log,
        }

    # Service degradation: retries exhausted, skip this step
    if retry_count >= MAX_RETRY:
        logger.warning("degraded_step session=%s step=%d tool=%s retries=%d",
                       state.get("session_id"), current_step, tool_name, retry_count)
        degraded = list(state.get("degraded_steps") or [])
        degraded.append({
            "step": current_step, "tool": tool_name, "args": args,
            "reason": f"exhausted {MAX_RETRY} retries",
        })
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({
            "tool": tool_name, "args": args,
            "result": {"error": f"skipped after {MAX_RETRY} retries"},
            "success": False,
        })
        tool_call_log.append({"tool": tool_name, "success": False})
        return {
            "tool_results": tool_results,
            "current_step": current_step + 1,
            "retry_count": 0,
            "degraded_steps": degraded,
            "iteration_count": iteration_count,
            "tool_call_log": tool_call_log,
        }

    writer = get_stream_writer()
    plan_len = len(plan)

    # Check if tool is a local Python tool (skill or built-in)
    registry = get_tool_registry()
    local_tool = registry.get(tool_name)

    if local_tool:
        return await _execute_local(
            local_tool, tool_name, args, state, writer,
            current_step, plan_len, iteration_count, tool_call_log,
        )
    else:
        return await _execute_remote(
            tool_name, args, state, writer,
            current_step, plan_len, retry_count, iteration_count, tool_call_log,
        )


async def _execute_local(
    tool, tool_name, args, state, writer,
    current_step, plan_len, iteration_count, tool_call_log,
):
    """Execute a locally registered Python tool."""
    writer({
        "type": "tool_progress",
        "tool_name": tool_name,
        "current_step": current_step + 1,
        "total_steps": plan_len,
        "status": "running",
    })

    try:
        result = await tool.execute(args)
        success = result.get("success", True)
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({
            "tool": tool_name, "args": args,
            "result": result, "success": success,
        })
        tool_call_log.append({"tool": tool_name, "success": success})

        # Empty response protection
        if not result.get("result"):
            result["result"] = "(empty response)"

        writer({
            "type": "tool_progress",
            "tool_name": tool_name,
            "current_step": current_step + 1,
            "total_steps": plan_len,
            "status": "completed" if success else "failed",
        })
        return {
            "tool_results": tool_results,
            "current_step": current_step + 1,
            "retry_count": 0,
            "iteration_count": iteration_count,
            "tool_call_log": tool_call_log,
        }
    except Exception as e:
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({
            "tool": tool_name, "args": args,
            "result": {"error": str(e)}, "success": False,
        })
        tool_call_log.append({"tool": tool_name, "success": False})
        writer({
            "type": "tool_progress",
            "tool_name": tool_name,
            "current_step": current_step + 1,
            "total_steps": plan_len,
            "status": "failed",
        })
        return {
            "tool_results": tool_results,
            "current_step": current_step,
            "retry_count": state.get("retry_count", 0) + 1,
            "iteration_count": iteration_count,
            "tool_call_log": tool_call_log,
            "error": str(e),
        }


async def _execute_remote(
    tool_name, args, state, writer,
    current_step, plan_len, retry_count, iteration_count, tool_call_log,
):
    """Execute a tool via Go gateway HTTP callback."""
    try:
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
            "current_step": current_step + 1,
            "total_steps": plan_len,
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
                # Empty response protection
                if not result.get("result"):
                    result["result"] = "(empty response from tool)"

                tool_results = list(state.get("tool_results") or [])
                tool_results.append({
                    "tool": tool_name, "args": args,
                    "result": result, "success": result.get("success", True),
                })
                tool_call_log.append({"tool": tool_name, "success": result.get("success", True)})
                writer({
                    "type": "tool_progress",
                    "tool_name": tool_name,
                    "current_step": current_step + 1,
                    "total_steps": plan_len,
                    "status": "completed",
                })
                return {
                    "tool_results": tool_results,
                    "current_step": current_step + 1,
                    "retry_count": 0,
                    "iteration_count": iteration_count,
                    "tool_call_log": tool_call_log,
                }
            else:
                error_text = resp.text
                tool_results = list(state.get("tool_results") or [])
                tool_results.append({
                    "tool": tool_name, "args": args,
                    "result": {"error": error_text}, "success": False,
                })
                tool_call_log.append({"tool": tool_name, "success": False})
                writer({
                    "type": "tool_progress",
                    "tool_name": tool_name,
                    "current_step": current_step + 1,
                    "total_steps": plan_len,
                    "status": "failed" if retry_count + 1 >= MAX_RETRY else "retrying",
                })
                return {
                    "tool_results": tool_results,
                    "current_step": current_step,
                    "retry_count": retry_count + 1,
                    "error": f"tool execution failed: {error_text}",
                    "iteration_count": iteration_count,
                    "tool_call_log": tool_call_log,
                }
    except Exception as e:
        tool_results = list(state.get("tool_results") or [])
        tool_results.append({
            "tool": tool_name, "args": args,
            "result": {"error": str(e)}, "success": False,
        })
        tool_call_log.append({"tool": tool_name, "success": False})
        writer({
            "type": "tool_progress",
            "tool_name": tool_name,
            "current_step": current_step + 1,
            "total_steps": plan_len,
            "status": "failed" if retry_count + 1 >= MAX_RETRY else "retrying",
        })
        return {
            "tool_results": tool_results,
            "current_step": current_step,
            "retry_count": retry_count + 1,
            "error": str(e),
            "iteration_count": iteration_count,
            "tool_call_log": tool_call_log,
        }


def _count_consecutive(tool_call_log: list, tool_name: str, success: bool) -> int:
    """Count consecutive calls of same tool with same success status from end of log."""
    count = 0
    for entry in reversed(tool_call_log):
        if entry.get("tool") == tool_name and entry.get("success") == success:
            count += 1
        else:
            break
    return count
