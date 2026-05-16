"""Worker Orchestrator node: dispatches parallel workers and collects results."""
import asyncio
import logging
from langgraph.config import get_stream_writer
from app.graph.state import AgentState
from app.workers.worker import Worker
from app.workers.models import WorkerConfig, WorkerResult

logger = logging.getLogger(__name__)

MAX_CONCURRENT_WORKERS = 5


async def worker_orchestrator_node(state: AgentState) -> dict:
    """Orchestrate parallel worker execution for plan steps.

    Dispatches each plan step as an independent Worker, runs them concurrently,
    collects results, and emits SSE progress events.
    """
    plan = state.get("plan", [])
    provider_id = state.get("provider_id", "")
    model = state.get("model", "")
    writer = get_stream_writer()

    if not plan:
        logger.info("worker_orchestrator: empty plan, skipping")
        return {"worker_results": [], "tool_results": []}

    logger.info("worker_orchestrator: dispatching %d workers (concurrency<=%d)",
                len(plan), MAX_CONCURRENT_WORKERS)

    # Create worker configs from plan steps
    configs = []
    for i, step in enumerate(plan):
        configs.append(WorkerConfig(
            task_description=step.get("description", f"Execute {step.get('tool', 'unknown')}"),
            tool_name=step.get("tool", ""),
            tool_args=step.get("args", {}),
            max_iterations=3,
            worker_id=i,
        ))

    # Emit start events
    writer({
        "type": "worker_started",
        "total_workers": len(configs),
        "tasks": [c.task_description for c in configs],
    })

    # Run workers in parallel with concurrency limit
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_WORKERS)
    results: list[WorkerResult] = []

    async def run_worker(config: WorkerConfig) -> WorkerResult:
        async with semaphore:
            worker = Worker(config=config, provider_id=provider_id, model=model)
            result = await worker.run()
            # Emit progress
            writer({
                "type": "worker_progress",
                "worker_id": result.worker_id,
                "task": config.task_description,
                "success": result.success,
                "iterations": result.iterations_used,
            })
            return result

    tasks = [run_worker(cfg) for cfg in configs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    worker_results = []
    tool_results = list(state.get("tool_results") or [])

    for r in results:
        if isinstance(r, Exception):
            worker_results.append({
                "worker_id": -1,
                "success": False,
                "error": str(r),
            })
        else:
            worker_results.append({
                "worker_id": r.worker_id,
                "task": r.task_description,
                "success": r.success,
                "result": r.result,
                "error": r.error,
                "iterations": r.iterations_used,
                "tool_calls": r.tool_calls,
            })
            # Also add to tool_results for responder context
            tool_results.append({
                "tool": f"worker_{r.worker_id}",
                "args": {"task": r.task_description},
                "result": {"result": r.result, "success": r.success},
                "success": r.success,
            })

    # Emit done
    success_count = sum(1 for r in worker_results if r.get("success"))
    logger.info("worker_orchestrator: done total=%d ok=%d fail=%d",
                len(worker_results), success_count, len(worker_results) - success_count)
    writer({
        "type": "worker_done",
        "total": len(worker_results),
        "succeeded": success_count,
        "failed": len(worker_results) - success_count,
    })

    return {
        "worker_results": worker_results,
        "tool_results": tool_results,
        "current_step": len(plan),  # All steps handled by workers
    }
