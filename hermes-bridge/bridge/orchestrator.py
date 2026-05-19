"""Multi-subagent orchestrator.

Walks the role list of a saved ``DialogFlow`` and dispatches each role
using direct LLM execution (DeepSeek API with tool-calling). Streams
one event per role (start / chunk / complete / fail) and persists the
final outputs through ``runs.py``.

Two flow shapes are supported today:

* ``sequential`` — pipe role₁'s output into role₂'s prompt. The default
  prompt template is ``{input}`` so both shapes work without authoring a
  template; if a flow defines ``prompt_template`` we render it with the
  ``{input}`` and ``{prior}`` variables.
* ``parallel`` — fan out the same input to every role concurrently. A
  per-role failure is isolated (status=failed for that role; the run still
  reports ``succeeded`` overall as long as at least one role produced
  output). In ``sequential``, the first failure aborts the chain.

DAG flows are deferred — see Phase 5+.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from . import flows as flows_mod
from . import hermes_cli, runs as runs_mod

logger = logging.getLogger(__name__)

# Per-role wall-clock cap.
ROLE_TIMEOUT_SECONDS = int(os.getenv("ORCH_ROLE_TIMEOUT", "600"))

# Persisted Write-tool artifacts root. Per-run subdir is created under this.
# Override via AGENT_WORK_DIR env var.
AGENT_WORK_DIR = os.getenv(
    "AGENT_WORK_DIR",
    "/home/admin/.agent-platform/runs",
)


# ── Event model ──────────────────────────────────────────────────────────────

@dataclass
class Event:
    """Server-Sent Event payload. ``content`` is role output text when
    present; ``error`` is set on failure events."""
    type: str
    run_id: int
    role_id: Optional[str] = None
    content: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None
    index: Optional[int] = None
    total: Optional[int] = None
    extra: Optional[Dict] = None

    def to_sse(self) -> str:
        payload = {"type": self.type, "run_id": self.run_id}
        for key in ("role_id", "content", "error", "latency_ms", "index", "total"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        if self.extra:
            payload.update(self.extra)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── Prompt rendering ─────────────────────────────────────────────────────────

def render_prompt(template: str, *, user_input: str, prior: str = "") -> str:
    """Render the per-role task. Two variables: ``{input}`` and ``{prior}``.

    ``{input}`` is the original user input; ``{prior}`` is the previous
    role's output in sequential mode (empty in parallel mode and for the
    first role). An empty template defaults to passing the input straight
    through, prepending the prior output as quoted context if any.
    """
    if not template:
        if prior:
            return f"Prior reviewer output:\n\n{prior}\n\n---\n\nUser input:\n\n{user_input}"
        return user_input
    return template.format(input=user_input, prior=prior)


# ── Single-role execution ───────────────────────────────────────────────────

async def _execute_role(role_id: str, task: str, session_id: str = "", model: str = "", project_dir: str = "") -> Dict:
    """Run one skill via direct LLM. Returns dict with content/latency_ms/error/session_id."""
    started = time.monotonic()
    loop = asyncio.get_event_loop()
    try:
        content, sid = await asyncio.wait_for(
            loop.run_in_executor(
                None, hermes_cli.execute_skill_direct,
                role_id, task, ROLE_TIMEOUT_SECONDS, session_id, model, project_dir,
            ),
            timeout=ROLE_TIMEOUT_SECONDS + 5,
        )
        return {
            "content": content,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": None,
            "session_id": sid,
        }
    except asyncio.TimeoutError:
        return {
            "content": "",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": f"role timed out after {ROLE_TIMEOUT_SECONDS}s",
            "session_id": session_id,
        }
    except Exception as exc:                                 # noqa: BLE001
        logger.exception("role %s failed", role_id)
        return {
            "content": "",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": str(exc),
            "session_id": session_id,
        }


async def _execute_role_stream(
    role_id: str, task: str, session_id: str = "", model: str = "", project_dir: str = "",
) -> AsyncIterator[dict]:
    """Run one skill with streaming. Yields {type, content, ...} dicts
    as LLM output arrives, ending with a terminal dict containing the full result."""
    started = time.monotonic()
    loop = asyncio.get_event_loop()

    # Streaming path: spawn the blocking generator in a thread, feed chunks back
    result_holder = {"content": "", "sid": session_id, "error": None, "done": False}

    def _run_stream():
        try:
            for chunk, sid, is_done in hermes_cli.execute_skill_direct_stream(
                role_id, task, ROLE_TIMEOUT_SECONDS, session_id, model=model,
                project_dir=project_dir,
            ):
                if is_done:
                    result_holder["content"] = chunk
                    result_holder["sid"] = sid
                    result_holder["done"] = True
                else:
                    result_holder["_chunks"].append(chunk)
        except Exception as e:
            result_holder["error"] = str(e)
            result_holder["done"] = True

    result_holder["_chunks"] = []
    thread = loop.run_in_executor(None, _run_stream)

    # Poll for chunks from the thread. We key on an explicit `done` flag rather
    # than truthiness of content — the model can legitimately emit an empty
    # final string and the polling loop must still terminate.
    last_idx = 0
    try:
        while True:
            await asyncio.sleep(0.1)
            current = result_holder["_chunks"]
            while last_idx < len(current):
                yield {
                    "type": "text", "role_id": role_id,
                    "content": current[last_idx], "session_id": result_holder["sid"],
                }
                last_idx += 1
            if result_holder["error"]:
                yield {
                    "type": "error", "role_id": role_id,
                    "error": result_holder["error"],
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "session_id": result_holder["sid"],
                }
                return
            if result_holder["done"]:
                latency = int((time.monotonic() - started) * 1000)
                yield {
                    "type": "done", "role_id": role_id,
                    "content": result_holder["content"],
                    "latency_ms": latency,
                    "session_id": result_holder["sid"],
                }
                return
    except asyncio.TimeoutError:
        yield {
            "type": "error", "role_id": role_id,
            "error": f"role timed out after {ROLE_TIMEOUT_SECONDS}s",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "session_id": result_holder["sid"],
        }


# ── Orchestration ───────────────────────────────────────────────────────────

async def _run_sequential(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    model: str = "", project_dir: str = "",
) -> AsyncIterator[Event]:
    prior = ""
    session_id = ""
    total = len(role_ids)
    for idx, role_id in enumerate(role_ids):
        task = render_prompt(template, user_input=user_input, prior=prior)
        yield Event(type="role_started", run_id=run_id, role_id=role_id,
                    index=idx, total=total)

        full_content = ""
        latency = 0
        role_failed = False
        async for chunk in _execute_role_stream(role_id, task, session_id, model=model, project_dir=project_dir):
            if chunk["type"] == "text":
                full_content += chunk["content"]
                yield Event(type="role_output", run_id=run_id, role_id=role_id,
                            content=chunk["content"], index=idx, total=total)
            elif chunk["type"] == "done":
                full_content = chunk.get("content", full_content)
                latency = chunk.get("latency_ms", 0)
                if chunk.get("session_id"):
                    session_id = chunk["session_id"]
            elif chunk["type"] == "error":
                runs_mod.append_output(run_id, runs_mod.RoleOutput(
                    role_id=role_id, content=full_content, latency_ms=latency,
                    error=chunk["error"],
                ))
                yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                            error=chunk["error"], index=idx, total=total)
                role_failed = True
                break
        if role_failed:
            continue
        runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id, content=full_content, latency_ms=latency,
            error=None,
        ))
        yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                    content=full_content, latency_ms=latency,
                    index=idx, total=total)
        prior = full_content


async def _run_parallel(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    model: str = "", project_dir: str = "",
) -> AsyncIterator[Event]:
    total = len(role_ids)

    # Emit role_started events upfront so the UI can render N panels.
    for idx, role_id in enumerate(role_ids):
        yield Event(type="role_started", run_id=run_id, role_id=role_id,
                    index=idx, total=total)

    async def _wrapped(idx: int, role_id: str) -> Dict:
        task = render_prompt(template, user_input=user_input, prior="")
        result = await _execute_role(role_id, task, project_dir=project_dir)
        result["__index"] = idx
        result["__role_id"] = role_id
        return result

    tasks = [
        asyncio.create_task(_wrapped(idx, role_id))
        for idx, role_id in enumerate(role_ids)
    ]
    for completed in asyncio.as_completed(tasks):
        result = await completed
        idx = result["__index"]
        role_id = result["__role_id"]
        runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id,
            content=result["content"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        ))
        if result["error"]:
            yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                        error=result["error"], latency_ms=result["latency_ms"],
                        index=idx, total=total)
        else:
            yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                        content=result["content"], latency_ms=result["latency_ms"],
                        index=idx, total=total)


async def run_flow(flow_id: int, user_input: str, project_dir: str = "") -> AsyncIterator[Event]:
    """Top-level orchestrator. Yields SSE-shaped events end-to-end."""
    flow = flows_mod.get(flow_id)
    run = runs_mod.create(flow_id, user_input)
    runs_mod.mark_running(run.id)
    finalized = False

    # Persist Write-tool artifacts to a stable per-run dir instead of /tmp sandbox.
    # Caller-provided project_dir wins; otherwise derive under AGENT_WORK_DIR.
    if not project_dir:
        project_dir = str(Path(AGENT_WORK_DIR) / f"flow-{flow.id}" / f"run-{run.id}")
        try:
            Path(project_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("could not create work dir %s: %s — falling back to tmp sandbox",
                           project_dir, exc)
            project_dir = ""
    runs_mod.set_project_dir(run.id, project_dir)

    yield Event(
        type="run_started", run_id=run.id, total=len(flow.role_ids),
        extra={"flow_id": flow.id, "flow_type": flow.flow_type,
               "role_ids": flow.role_ids,
               "project_dir": project_dir},
    )

    try:
        if flow.flow_type == "sequential":
            generator = _run_sequential(flow.role_ids, user_input,
                                        flow.prompt_template, run.id,
                                        model=flow.model, project_dir=project_dir)
        elif flow.flow_type == "parallel":
            generator = _run_parallel(flow.role_ids, user_input,
                                      flow.prompt_template, run.id,
                                      model=flow.model, project_dir=project_dir)
        else:
            raise ValueError(f"unsupported flow_type: {flow.flow_type}")

        any_failure = False
        any_success = False
        async for event in generator:
            if event.type == "role_failed":
                any_failure = True
            elif event.type == "role_completed":
                any_success = True
            yield event

        # Sequential is now best-effort (a role failure no longer aborts the
        # chain). Run is failed only if NO role produced output; otherwise
        # succeeded — partial failures are recorded per-role in outputs.
        if not any_success:
            runs_mod.finalize(run.id, "failed", "no role produced output")
            finalized = True
            yield Event(type="run_failed", run_id=run.id,
                        error="no role produced output")
        else:
            runs_mod.finalize(run.id, "succeeded",
                              "with partial failures" if any_failure else "")
            finalized = True
            yield Event(type="run_completed", run_id=run.id)

    except Exception as exc:                                 # noqa: BLE001
        logger.exception("flow %s run %s blew up", flow_id, run.id)
        if not finalized:
            runs_mod.finalize(run.id, "failed", str(exc))
            finalized = True
        yield Event(type="run_failed", run_id=run.id, error=str(exc))
    finally:
        # If we exit before finalize — typically because the SSE client
        # disconnected and the async generator is being closed via GeneratorExit
        # — mark the run as cancelled so it doesn't sit in 'running' forever.
        if not finalized:
            try:
                runs_mod.finalize(run.id, "cancelled", "client disconnected")
            except Exception:                                # noqa: BLE001
                logger.exception("failed to finalize cancelled run %s", run.id)
