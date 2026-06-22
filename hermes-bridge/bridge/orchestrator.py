"""Multi-subagent orchestrator.

Walks the role list of a saved ``DialogFlow`` and dispatches each role
using direct LLM execution (DeepSeek API with tool-calling). Streams
one event per role (start / chunk / complete / fail) and persists the
final outputs through ``runs.py``.

Supported flow shapes include sequential, parallel, hierarchical,
competitive, pipeline, and peer-to-peer. A per-role failure is isolated for
parallel/competitive/peer flows as long as at least one role produces output;
pipeline fails fast when a stage fails. Full DAG/canvas flows are deferred.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

from . import flows as flows_mod
from . import hermes_cli, runs as runs_mod
from .collaboration import CollaborationMessage
from .sandbox_policy import DEFAULT_SANDBOX_POLICY

logger = logging.getLogger(__name__)

# Per-role wall-clock cap.
ROLE_TIMEOUT_SECONDS = int(os.getenv("ORCH_ROLE_TIMEOUT", "7200"))
GRAPHRAG_TIMEOUT_SECONDS = int(os.getenv("ORCH_GRAPHRAG_TIMEOUT", "60"))
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8001").rstrip("/")
GRAPHRAG_QUERY_MAX_CHARS = int(os.getenv("ORCH_GRAPHRAG_QUERY_MAX_CHARS", "1500"))
DAG_UPSTREAM_CONTENT_MAX_CHARS = int(os.getenv("ORCH_DAG_UPSTREAM_CONTENT_MAX_CHARS", "12000"))
PEER_MESSAGE_MAX_CHARS = int(os.getenv("ORCH_PEER_MESSAGE_MAX_CHARS", "6000"))
RESOLVER_CONTEXT_MAX_CHARS = int(os.getenv("ORCH_RESOLVER_CONTEXT_MAX_CHARS", "8000"))

STANCE_PRESETS = [
    {
        "stance_name": "evidence-first skeptic",
        "objective": "stress-test claims, assumptions, data quality, and failure modes before accepting an answer",
        "must_defend": "high evidence standards and explicit uncertainty",
        "must_challenge": "unsupported optimism, vague recommendations, and missing risks",
        "evidence_standard": "cite concrete facts from the task or clearly label assumptions",
        "risk_bias": "conservative; prefer robust answers over impressive but fragile answers",
        "forbidden_overlap": "do not simply restate other roles' likely solution; expose hidden weaknesses",
    },
    {
        "stance_name": "builder-operator",
        "objective": "turn the task into an executable, practical plan with sequencing and ownership",
        "must_defend": "feasibility, operational clarity, and implementation details",
        "must_challenge": "abstract strategy without a path to execution",
        "evidence_standard": "tie recommendations to observable constraints and implementation steps",
        "risk_bias": "pragmatic; accept manageable risk when execution value is clear",
        "forbidden_overlap": "do not focus only on critique; produce a concrete path forward",
    },
    {
        "stance_name": "user-value advocate",
        "objective": "optimize for user outcome, clarity, adoption, and real-world usefulness",
        "must_defend": "the user's job-to-be-done and decision quality",
        "must_challenge": "solutions that are technically neat but user-hostile or hard to understand",
        "evidence_standard": "explain how each recommendation improves the user's outcome",
        "risk_bias": "balanced; prefer useful clarity over excessive sophistication",
        "forbidden_overlap": "do not duplicate implementation analysis unless it changes user value",
    },
    {
        "stance_name": "strategic upside maximizer",
        "objective": "identify the highest-leverage, ambitious option and its upside case",
        "must_defend": "long-term leverage, differentiation, and compounding value",
        "must_challenge": "overly local optimization and timid defaults",
        "evidence_standard": "separate upside thesis from facts and assumptions",
        "risk_bias": "ambitious but explicit about downside and prerequisites",
        "forbidden_overlap": "do not hide risks; make the upside case falsifiable",
    },
]

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

    def to_payload(self) -> Dict:
        payload = {"type": self.type, "run_id": self.run_id}
        for key in ("role_id", "content", "error", "latency_ms", "index", "total"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        if self.extra:
            payload.update(self.extra)
        return payload

    def to_sse(self) -> str:
        return f"data: {json.dumps(self.to_payload(), ensure_ascii=False)}\n\n"


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
    return template.replace("{input}", user_input).replace("{prior}", prior)


# ── File-backed role output streaming ──────────────────────────────────────

def _role_output_path(project_dir: str, role_id: str) -> str:
    """Path to a role's streaming output file within the project directory."""
    safe = role_id.replace("/", "--").replace("\\", "--")
    return os.path.join(project_dir, f"role_output_{safe}.md")


def _role_workspace(project_dir: str, role_id: str) -> str:
    """Per-role tool workspace, isolated from sibling agents in the same run."""
    if not project_dir:
        return ""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "--", role_id).strip(".-") or "role"
    path = os.path.join(project_dir, "work", safe)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return project_dir
    return path


def _append_role_chunk_to_file(project_dir: str, role_id: str, content: str) -> None:
    """Append a streaming chunk to the per-role output file."""
    path = _role_output_path(project_dir, role_id)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
    except OSError:
        pass  # best-effort file writing

def _write_role_output_file(project_dir: str, role_id: str, content: str, latency_ms: int, error: str | None) -> None:
    """Write the complete, final role output as a markdown file."""
    path = _role_output_path(project_dir, role_id)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        header = f"# {role_id}\n\n- latency: {latency_ms}ms\n"
        if error:
            header += f"- error: {error}\n"
        header += "\n---\n\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + content)
    except OSError:
        pass


# ── Single-role execution ───────────────────────────────────────────────────

async def _execute_role(
    role_id: str, task: str, session_id: str = "", model: str = "", project_dir: str = "",
    sandbox_policy: Optional[Dict] = None,
) -> Dict:
    """Run one skill via direct LLM. Returns dict with content/latency_ms/error/session_id."""
    started = time.monotonic()
    loop = asyncio.get_event_loop()
    def _call_direct():
        if sandbox_policy is None or sandbox_policy == DEFAULT_SANDBOX_POLICY:
            return hermes_cli.execute_skill_direct(
                role_id, task, ROLE_TIMEOUT_SECONDS, session_id, model, project_dir,
            )
        try:
            return hermes_cli.execute_skill_direct(
                role_id, task, ROLE_TIMEOUT_SECONDS, session_id, model, project_dir,
                sandbox_policy=sandbox_policy,
            )
        except TypeError as exc:
            if "sandbox_policy" not in str(exc):
                raise
            return hermes_cli.execute_skill_direct(
                role_id, task, ROLE_TIMEOUT_SECONDS, session_id, model, project_dir,
            )

    try:
        content, sid = await asyncio.wait_for(
            loop.run_in_executor(None, _call_direct),
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
    sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[dict]:
    """Run one skill with streaming. Yields {type, content, ...} dicts
    as LLM output arrives, ending with a terminal dict containing the full result."""
    started = time.monotonic()
    loop = asyncio.get_event_loop()

    # Streaming path: spawn the blocking generator in a thread, feed chunks back
    result_holder = {"content": "", "sid": session_id, "error": None, "done": False}

    def _run_stream():
        try:
            stream_kwargs = {
                "timeout": ROLE_TIMEOUT_SECONDS,
                "session_id": session_id,
                "model": model,
                "project_dir": project_dir,
            }
            if sandbox_policy is not None and sandbox_policy != DEFAULT_SANDBOX_POLICY:
                stream_kwargs["sandbox_policy"] = sandbox_policy
            try:
                stream = hermes_cli.execute_skill_direct_stream(role_id, task, **stream_kwargs)
            except TypeError as exc:
                if "sandbox_policy" not in str(exc):
                    raise
                stream_kwargs.pop("sandbox_policy", None)
                stream = hermes_cli.execute_skill_direct_stream(role_id, task, **stream_kwargs)
            for chunk, sid, is_done in stream:
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

def _preview(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "…"


def _compact_text(value: str, limit: int) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    marker = f"\n...[truncated {len(text)} chars]...\n"
    if len(marker) >= limit:
        return text[:limit]
    side = max(1, (limit - len(marker)) // 2)
    head = text[:side].rstrip()
    tail = text[-(limit - len(marker) - len(head)):].lstrip()
    return f"{head}{marker}{tail}"[:limit]


def _dag_upstream_content(content: str) -> str:
    return _compact_text(content or "", DAG_UPSTREAM_CONTENT_MAX_CHARS)


def _graphrag_query_text(query: str) -> tuple[str, bool]:
    compact = _compact_text(query or "", GRAPHRAG_QUERY_MAX_CHARS)
    return compact, compact != (query or "").strip()


def _role_contract(role_id: str, role_order: List[str], flow_spec: Optional[Dict] = None) -> Dict:
    spec = flow_spec if isinstance(flow_spec, dict) else {}
    contracts = spec.get("role_contracts") or spec.get("roles") or {}
    raw: Dict = {}
    if isinstance(contracts, dict):
        item = contracts.get(role_id)
        if isinstance(item, dict):
            raw = dict(item)
    elif isinstance(contracts, list):
        for item in contracts:
            if isinstance(item, dict) and str(item.get("role_id") or item.get("id") or "") == role_id:
                raw = dict(item)
                break

    try:
        idx = role_order.index(role_id)
    except ValueError:
        idx = 0
    preset = STANCE_PRESETS[idx % len(STANCE_PRESETS)]
    contract = {**preset, **raw}
    contract["role_id"] = role_id
    required_schema = [
        "Position",
        "Assumptions",
        "Evidence",
        "Challenges to other likely positions",
        "Recommendation",
        "Self-critique",
    ]
    custom_schema = contract.get("output_schema")
    if isinstance(custom_schema, list):
        merged_schema = [str(item) for item in custom_schema if str(item).strip()]
        for item in required_schema:
            if item not in merged_schema:
                merged_schema.append(item)
        contract["output_schema"] = merged_schema
    else:
        contract["output_schema"] = required_schema
    return contract


def _contract_block(contract: Dict) -> str:
    schema = contract.get("output_schema")
    if isinstance(schema, list):
        schema_text = ", ".join(str(item) for item in schema if str(item).strip())
    else:
        schema_text = str(schema or "")
    return (
        "ROLE CONTRACT (binding for this run):\n"
        f"- role_id: {contract.get('role_id', '')}\n"
        f"- stance_name: {contract.get('stance_name', '')}\n"
        f"- objective: {contract.get('objective', '')}\n"
        f"- must_defend: {contract.get('must_defend', '')}\n"
        f"- must_challenge: {contract.get('must_challenge', '')}\n"
        f"- evidence_standard: {contract.get('evidence_standard', '')}\n"
        f"- risk_bias: {contract.get('risk_bias', '')}\n"
        f"- forbidden_overlap: {contract.get('forbidden_overlap', '')}\n"
        f"- required_output_sections: {schema_text}\n"
    )


def _adjudication_contract(flow_spec: Optional[Dict] = None) -> Dict:
    spec = flow_spec if isinstance(flow_spec, dict) else {}
    raw = spec.get("adjudication") or spec.get("judge") or {}
    if not isinstance(raw, dict):
        raw = {}
    contract = {
        "decision_rule": "select the answer with the best evidence, reasoning, user utility, and risk handling; preserve useful minority views",
        "rubric": [
            "Task fit and completeness",
            "Evidence quality and traceability",
            "Reasoning quality",
            "Risk and uncertainty handling",
            "Actionability for the user",
            "Original contribution versus duplication",
        ],
        "required_output_sections": [
            "Decision",
            "Score matrix",
            "Disagreement map",
            "Winning synthesis",
            "Minority report",
            "Failure notes",
        ],
    }
    for key, value in raw.items():
        if value:
            contract[key] = value
    return contract


def _adjudication_block(contract: Dict) -> str:
    rubric = contract.get("rubric")
    if isinstance(rubric, list):
        rubric_text = "\n".join(f"- {item}" for item in rubric)
    else:
        rubric_text = f"- {rubric}"
    sections = contract.get("required_output_sections")
    if isinstance(sections, list):
        sections_text = ", ".join(str(item) for item in sections)
    else:
        sections_text = str(sections or "")
    return (
        "ADJUDICATION CONTRACT (binding):\n"
        f"- decision_rule: {contract.get('decision_rule', '')}\n"
        "- rubric:\n"
        f"{rubric_text}\n"
        f"- required_output_sections: {sections_text}\n"
        "- The final answer must cite candidate/peer role_ids when using or rejecting their arguments.\n"
        "- Do not choose an answer because it is longer; choose by rubric quality.\n"
        "- Preserve a minority report when a losing answer contains a materially useful warning or insight.\n"
    )


def _peer_message_payload(item: Dict, *, include_content: bool = True) -> Dict:
    content = item.get("content") or ""
    payload = {
        "role_id": item.get("role_id") or "",
        "latency_ms": item.get("latency_ms"),
        "error": item.get("error"),
    }
    if include_content:
        payload["content"] = _compact_text(content, PEER_MESSAGE_MAX_CHARS)
    else:
        payload["content_preview"] = _preview(content)
    return payload


def _role_contract_task(
    task: str,
    *,
    role_id: str,
    role_order: List[str],
    flow_type: str,
    flow_spec: Optional[Dict] = None,
    phase: str = "",
) -> str:
    contract = _role_contract(role_id, role_order, flow_spec)
    phase_line = f"- phase: {phase}\n" if phase else ""
    return (
        f"You are executing one role in a {flow_type} multi-agent flow. The "
        "role contract below is binding for this run and overrides generic "
        "skill behavior when they conflict.\n\n"
        f"{_contract_block(contract)}"
        "FLOW DISCIPLINE:\n"
        f"- flow_type: {flow_type}\n"
        f"{phase_line}"
        "- Defend your assigned stance and do not collapse into generic agreement.\n"
        "- Challenge assumptions relevant to your stance, even if the upstream input is confident.\n"
        "- Keep the output useful for the next role or final user, not just internally consistent.\n"
        "- Include concise evidence/reasoning for important claims and state uncertainty.\n"
        "- Include a short self-critique or residual risk note.\n"
        "- Do not ask the user follow-up questions.\n\n"
        f"ROLE TASK:\n\n{task}"
    )


def _append_message(
    *,
    run_id: int,
    from_agent: str,
    to_agent: str,
    message_type: str,
    status: str,
    role_id: str,
    payload: Optional[Dict] = None,
    output_index: Optional[int] = None,
) -> None:
    runs_mod.append_collaboration_message(CollaborationMessage(
        run_id=run_id,
        from_agent=from_agent,
        to_agent=to_agent,
        type=message_type,
        payload=payload or {},
        status=status,
        role_id=role_id,
        output_index=output_index,
    ))


async def _run_sequential(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    flow_spec: Optional[Dict] = None,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    prior = ""
    session_id = ""
    total = len(role_ids)
    for idx, role_id in enumerate(role_ids):
        task = render_prompt(template, user_input=user_input, prior=prior)
        task = _role_contract_task(
            task,
            role_id=role_id,
            role_order=role_ids,
            flow_type="sequential",
            flow_spec=flow_spec,
            phase=f"step {idx + 1}/{total}",
        )
        _append_message(
            run_id=run_id,
            from_agent="orchestrator",
            to_agent=role_id,
            message_type="role_task",
            status="sent",
            role_id=role_id,
            payload={"flow_type": "sequential", "index": idx, "total": total, "task_preview": _preview(task)},
        )
        yield Event(type="role_started", run_id=run_id, role_id=role_id,
                    index=idx, total=total)

        full_content = ""
        latency = 0
        role_failed = False
        async for chunk in _execute_role_stream(
            role_id, task, session_id, model=model, project_dir=project_dir,
            sandbox_policy=sandbox_policy,
        ):
            if chunk["type"] == "text":
                full_content += chunk["content"]
                yield Event(type="role_output", run_id=run_id, role_id=role_id,
                            content=chunk["content"], index=idx, total=total)
                # Stream output directly to disk — no DB content bloat
                if project_dir:
                    _append_role_chunk_to_file(project_dir, role_id, chunk["content"])
            elif chunk["type"] == "done":
                full_content = chunk.get("content", full_content)
                latency = chunk.get("latency_ms", 0)
                if chunk.get("session_id"):
                    session_id = chunk["session_id"]
                # Write the complete role output to disk as a role file
                if project_dir:
                    _write_role_output_file(project_dir, role_id, full_content, latency, None)
            elif chunk["type"] == "error":
                if project_dir:
                    _write_role_output_file(project_dir, role_id, full_content, latency, chunk["error"])
                output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
                    role_id=role_id, content="(see file)", latency_ms=latency,
                    error=chunk["error"],
                ))
                _append_message(
                    run_id=run_id,
                    from_agent=role_id,
                    to_agent="orchestrator",
                    message_type="role_result",
                    status="failed",
                    role_id=role_id,
                    output_index=output_index,
                    payload={"flow_type": "sequential", "index": idx, "total": total, "error": chunk["error"]},
                )
                yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                            error=chunk["error"], index=idx, total=total)
                role_failed = True
                break
        if role_failed:
            continue
        if project_dir:
            _write_role_output_file(project_dir, role_id, full_content, latency, None)
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id, content="(see file)", latency_ms=latency,
            error=None,
        ))
        _append_message(
            run_id=run_id,
            from_agent=role_id,
            to_agent="orchestrator",
            message_type="role_result",
            status="received",
            role_id=role_id,
            output_index=output_index,
            payload={
                "flow_type": "sequential",
                "index": idx,
                "total": total,
                "latency_ms": latency,
                "content_preview": _preview(full_content),
            },
        )
        yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                    content=full_content, latency_ms=latency,
                    index=idx, total=total)
        prior = full_content


def _pipeline_stage_task(*, user_input: str, queued_input: str, stage_id: str, stage_index: int, total: int) -> str:
    if stage_index == 0:
        return (
            "You are stage 1 in a pipeline multi-agent flow. Process the original "
            "user input and produce a clear queue item for the next stage.\n\n"
            f"Stage role: {stage_id}\n"
            f"Pipeline position: {stage_index + 1}/{total}\n\n"
            f"Original user input:\n\n{user_input}"
        )
    return (
        "You are a downstream stage in a pipeline multi-agent flow. Consume the "
        "queued output from the previous stage and transform it for the next stage "
        "or final answer.\n\n"
        f"Stage role: {stage_id}\n"
        f"Pipeline position: {stage_index + 1}/{total}\n\n"
        f"Original user input:\n\n{user_input}\n\n---\n\n"
        f"Queued item from previous stage:\n\n{queued_input}"
    )


async def _run_pipeline(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    flow_spec: Optional[Dict] = None,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    queued_input = ""
    session_id = ""
    total = len(role_ids)
    for idx, role_id in enumerate(role_ids):
        base_task = _pipeline_stage_task(
            user_input=user_input,
            queued_input=queued_input,
            stage_id=role_id,
            stage_index=idx,
            total=total,
        )
        if template:
            task = render_prompt(template, user_input=base_task, prior=queued_input)
        else:
            task = base_task
        task = _role_contract_task(
            task,
            role_id=role_id,
            role_order=role_ids,
            flow_type="pipeline",
            flow_spec=flow_spec,
            phase=f"stage {idx + 1}/{total}",
        )
        _append_message(
            run_id=run_id,
            from_agent="pipeline/router",
            to_agent=role_id,
            message_type="pipeline_stage_task",
            status="sent",
            role_id=role_id,
            payload={
                "flow_type": "pipeline",
                "phase": "stage",
                "stage": idx,
                "total": total,
                "queue": f"stage-{idx}",
                "task_preview": _preview(task),
            },
        )
        yield Event(type="role_started", run_id=run_id, role_id=role_id, index=idx, total=total)

        full_content = ""
        latency = 0
        stage_failed = False
        async for chunk in _execute_role_stream(
            role_id, task, session_id, model=model, project_dir=project_dir,
            sandbox_policy=sandbox_policy,
        ):
            if chunk["type"] == "text":
                full_content += chunk["content"]
                yield Event(type="role_output", run_id=run_id, role_id=role_id,
                            content=chunk["content"], index=idx, total=total)
                if project_dir:
                    _append_role_chunk_to_file(project_dir, role_id, chunk["content"])
            elif chunk["type"] == "done":
                full_content = chunk.get("content", full_content)
                latency = chunk.get("latency_ms", 0)
                if chunk.get("session_id"):
                    session_id = chunk["session_id"]
                if project_dir:
                    _write_role_output_file(project_dir, role_id, full_content, latency, None)
            elif chunk["type"] == "error":
                latency = chunk.get("latency_ms", latency)
                if project_dir:
                    _write_role_output_file(project_dir, role_id, full_content, latency, chunk["error"])
                output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
                    role_id=role_id, content="(see file)", latency_ms=latency,
                    error=chunk["error"],
                ))
                _append_message(
                    run_id=run_id,
                    from_agent=role_id,
                    to_agent="pipeline/router",
                    message_type="pipeline_stage_result",
                    status="failed",
                    role_id=role_id,
                    output_index=output_index,
                    payload={
                        "flow_type": "pipeline",
                        "phase": "stage",
                        "stage": idx,
                        "total": total,
                        "queue": f"stage-{idx + 1}",
                        "error": chunk["error"],
                    },
                )
                yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                            error=chunk["error"], latency_ms=latency, index=idx, total=total,
                            extra={"fatal": True, "stage": idx})
                stage_failed = True
                break
        if stage_failed:
            return

        if project_dir:
            _write_role_output_file(project_dir, role_id, full_content, latency, None)
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id, content="(see file)", latency_ms=latency, error=None,
        ))
        _append_message(
            run_id=run_id,
            from_agent=role_id,
            to_agent="pipeline/router",
            message_type="pipeline_stage_result",
            status="received",
            role_id=role_id,
            output_index=output_index,
            payload={
                "flow_type": "pipeline",
                "phase": "stage",
                "stage": idx,
                "total": total,
                "latency_ms": latency,
                "queue": f"stage-{idx + 1}",
                "content_preview": _preview(full_content),
            },
        )
        if idx < total - 1:
            next_role = role_ids[idx + 1]
            _append_message(
                run_id=run_id,
                from_agent=role_id,
                to_agent=next_role,
                message_type="pipeline_queue_item",
                status="sent",
                role_id=next_role,
                output_index=output_index,
                payload={
                    "flow_type": "pipeline",
                    "phase": "queue",
                    "from_stage": idx,
                    "to_stage": idx + 1,
                    "queue": f"stage-{idx + 1}",
                    "content_preview": _preview(full_content),
                },
            )
        yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                    content=full_content, latency_ms=latency, index=idx, total=total)
        queued_input = full_content


async def _run_parallel(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    flow_spec: Optional[Dict] = None,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    total = len(role_ids)

    # Emit role_started events upfront so the UI can render N panels.
    for idx, role_id in enumerate(role_ids):
        yield Event(type="role_started", run_id=run_id, role_id=role_id,
                    index=idx, total=total)

    async def _wrapped(idx: int, role_id: str) -> Dict:
        task = render_prompt(template, user_input=user_input, prior="")
        task = _role_contract_task(
            task,
            role_id=role_id,
            role_order=role_ids,
            flow_type="parallel",
            flow_spec=flow_spec,
            phase=f"parallel branch {idx + 1}/{total}",
        )
        _append_message(
            run_id=run_id,
            from_agent="orchestrator",
            to_agent=role_id,
            message_type="role_task",
            status="sent",
            role_id=role_id,
            payload={"flow_type": "parallel", "index": idx, "total": total, "task_preview": _preview(task)},
        )
        result = await _execute_role(role_id, task, project_dir=_role_workspace(project_dir, role_id), sandbox_policy=sandbox_policy)
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
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id,
            content=result["content"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        ))
        _append_message(
            run_id=run_id,
            from_agent=role_id,
            to_agent="orchestrator",
            message_type="role_result",
            status="failed" if result["error"] else "received",
            role_id=role_id,
            output_index=output_index,
            payload={
                "flow_type": "parallel",
                "index": idx,
                "total": total,
                "latency_ms": result["latency_ms"],
                "error": result["error"],
                "content_preview": _preview(result["content"] or ""),
            },
        )
        if result["error"]:
            yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                        error=result["error"], latency_ms=result["latency_ms"],
                        index=idx, total=total)
        else:
            yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                        content=result["content"], latency_ms=result["latency_ms"],
                        index=idx, total=total)


def _hierarchical_master_task(template: str, *, user_input: str) -> str:
    base = render_prompt(template, user_input=user_input, prior="")
    return (
        "You are the master agent in a hierarchical multi-agent flow. "
        "Break the user request into clear worker instructions.\n\n"
        f"User input:\n\n{base}"
    )


def _hierarchical_worker_task(*, user_input: str, master_plan: str, worker_id: str) -> str:
    return (
        "You are a worker agent in a hierarchical multi-agent flow. "
        "Follow the master plan for your role and return your best result.\n\n"
        f"Worker role: {worker_id}\n\n"
        f"Master plan:\n\n{master_plan}\n\n---\n\nUser input:\n\n{user_input}"
    )


def _hierarchical_summary_task(*, user_input: str, master_plan: str, worker_results: List[Dict]) -> str:
    return (
        "You are the master agent in a hierarchical multi-agent flow. "
        "Synthesize the worker results into the final answer. Include useful "
        "worker findings and account for failed workers without exposing stack traces.\n\n"
        f"User input:\n\n{user_input}\n\n---\n\n"
        f"Master plan:\n\n{master_plan}\n\n---\n\n"
        f"Worker results JSON:\n\n{json.dumps(worker_results, ensure_ascii=False, indent=2)}"
    )


async def _stream_hierarchical_master(
    *,
    role_id: str,
    task: str,
    run_id: int,
    index: int,
    total: int,
    model: str,
    project_dir: str,
    sandbox_policy: Optional[Dict],
    message_type: str,
    message_payload: Dict,
) -> AsyncIterator[Event | Dict]:
    _append_message(
        run_id=run_id,
        from_agent="orchestrator",
        to_agent=role_id,
        message_type=message_type,
        status="sent",
        role_id=role_id,
        payload={**message_payload, "task_preview": _preview(task)},
    )
    yield Event(type="role_started", run_id=run_id, role_id=role_id, index=index, total=total)

    full_content = ""
    latency = 0
    async for chunk in _execute_role_stream(
        role_id, task, model=model, project_dir=project_dir,
        sandbox_policy=sandbox_policy,
    ):
        if chunk["type"] == "text":
            full_content += chunk["content"]
            yield Event(type="role_output", run_id=run_id, role_id=role_id,
                        content=chunk["content"], index=index, total=total)
            if project_dir:
                _append_role_chunk_to_file(project_dir, role_id, chunk["content"])
        elif chunk["type"] == "done":
            full_content = chunk.get("content", full_content)
            latency = chunk.get("latency_ms", 0)
            if project_dir:
                _write_role_output_file(project_dir, role_id, full_content, latency, None)
        elif chunk["type"] == "error":
            latency = chunk.get("latency_ms", latency)
            if project_dir:
                _write_role_output_file(project_dir, role_id, full_content, latency, chunk["error"])
            output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
                role_id=role_id, content="(see file)", latency_ms=latency, error=chunk["error"],
            ))
            _append_message(
                run_id=run_id,
                from_agent=role_id,
                to_agent="orchestrator",
                message_type=message_type.replace("task", "result"),
                status="failed",
                role_id=role_id,
                output_index=output_index,
                payload={**message_payload, "error": chunk["error"]},
            )
            yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                        error=chunk["error"], latency_ms=latency, index=index, total=total,
                        extra={"fatal": True})
            yield {"error": chunk["error"], "content": "", "latency_ms": latency}
            return

    if project_dir:
        _write_role_output_file(project_dir, role_id, full_content, latency, None)
    output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
        role_id=role_id, content="(see file)", latency_ms=latency, error=None,
    ))
    _append_message(
        run_id=run_id,
        from_agent=role_id,
        to_agent="orchestrator",
        message_type=message_type.replace("task", "result"),
        status="received",
        role_id=role_id,
        output_index=output_index,
        payload={**message_payload, "latency_ms": latency, "content_preview": _preview(full_content)},
    )
    yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                content=full_content, latency_ms=latency, index=index, total=total)
    yield {"content": full_content, "latency_ms": latency, "error": None}


async def _run_hierarchical(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    flow_spec: Optional[Dict] = None,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    master_id = role_ids[0]
    worker_ids = role_ids[1:]
    total = len(role_ids)

    master_result: Dict = {}
    async for item in _stream_hierarchical_master(
        role_id=master_id,
        task=_role_contract_task(
            _hierarchical_master_task(template, user_input=user_input),
            role_id=master_id,
            role_order=role_ids,
            flow_type="hierarchical",
            flow_spec=flow_spec,
            phase="master plan",
        ),
        run_id=run_id,
        index=0,
        total=total,
        model=model,
        project_dir=project_dir,
        sandbox_policy=sandbox_policy,
        message_type="master_plan_task",
        message_payload={"flow_type": "hierarchical", "phase": "plan", "index": 0, "total": total},
    ):
        if isinstance(item, Event):
            yield item
        else:
            master_result = item
    if master_result.get("error"):
        return

    master_plan = master_result.get("content") or ""
    for idx, worker_id in enumerate(worker_ids, start=1):
        yield Event(type="role_started", run_id=run_id, role_id=worker_id, index=idx, total=total)

    async def _worker(idx: int, worker_id: str) -> Dict:
        task = _role_contract_task(
            _hierarchical_worker_task(user_input=user_input, master_plan=master_plan, worker_id=worker_id),
            role_id=worker_id,
            role_order=role_ids,
            flow_type="hierarchical",
            flow_spec=flow_spec,
            phase=f"worker {idx}/{total - 1}",
        )
        _append_message(
            run_id=run_id,
            from_agent=master_id,
            to_agent=worker_id,
            message_type="worker_task",
            status="sent",
            role_id=worker_id,
            payload={"flow_type": "hierarchical", "phase": "worker", "index": idx, "total": total, "task_preview": _preview(task)},
        )
        result = await _execute_role(
            worker_id,
            task,
            model=model,
            project_dir=_role_workspace(project_dir, worker_id),
            sandbox_policy=sandbox_policy,
        )
        result["__index"] = idx
        result["__role_id"] = worker_id
        return result

    worker_results: List[Dict] = []
    tasks = [asyncio.create_task(_worker(idx, worker_id)) for idx, worker_id in enumerate(worker_ids, start=1)]
    for completed in asyncio.as_completed(tasks):
        result = await completed
        idx = result["__index"]
        worker_id = result["__role_id"]
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=worker_id,
            content=result["content"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        ))
        worker_record = {
            "role_id": worker_id,
            "content": result["content"],
            "latency_ms": result["latency_ms"],
            "error": result["error"],
        }
        worker_results.append(worker_record)
        _append_message(
            run_id=run_id,
            from_agent=worker_id,
            to_agent=master_id,
            message_type="worker_result",
            status="failed" if result["error"] else "received",
            role_id=worker_id,
            output_index=output_index,
            payload={
                "flow_type": "hierarchical",
                "phase": "worker",
                "index": idx,
                "total": total,
                "latency_ms": result["latency_ms"],
                "error": result["error"],
                "content_preview": _preview(result["content"] or ""),
            },
        )
        if result["error"]:
            yield Event(type="role_failed", run_id=run_id, role_id=worker_id,
                        error=result["error"], latency_ms=result["latency_ms"], index=idx, total=total)
        else:
            yield Event(type="role_completed", run_id=run_id, role_id=worker_id,
                        content=result["content"], latency_ms=result["latency_ms"], index=idx, total=total)

    worker_results.sort(key=lambda item: worker_ids.index(item["role_id"]))
    async for item in _stream_hierarchical_master(
        role_id=master_id,
        task=_role_contract_task(
            _hierarchical_summary_task(user_input=user_input, master_plan=master_plan, worker_results=worker_results),
            role_id=master_id,
            role_order=role_ids,
            flow_type="hierarchical",
            flow_spec=flow_spec,
            phase="master synthesis",
        ),
        run_id=run_id,
        index=0,
        total=total,
        model=model,
        project_dir=project_dir,
        sandbox_policy=sandbox_policy,
        message_type="master_summary_task",
        message_payload={"flow_type": "hierarchical", "phase": "summary", "index": 0, "total": total},
    ):
        if isinstance(item, Event):
            yield item


def _competitive_candidate_task(
    template: str,
    *,
    user_input: str,
    candidate_id: str,
    role_order: List[str],
    flow_spec: Optional[Dict] = None,
) -> str:
    base = render_prompt(template, user_input=user_input, prior="")
    contract = _role_contract(candidate_id, role_order, flow_spec)
    return (
        "You are a candidate agent in a competitive multi-agent flow. Your job "
        "is not to be agreeable; your job is to defend a distinct stance under "
        "the binding role contract below. Produce an independent answer that "
        "the judge can compare against other candidates.\n\n"
        f"Candidate role: {candidate_id}\n\n"
        f"{_contract_block(contract)}\n"
        "RESPONSE RULES:\n"
        "- Make your assumptions explicit.\n"
        "- Challenge at least one plausible alternative stance.\n"
        "- Include evidence or reasoning trace for important claims.\n"
        "- Include a short self-critique naming where your answer could be wrong.\n"
        "- Do not ask the user follow-up questions.\n\n"
        f"User input:\n\n{base}"
    )


def _competitive_consensus_task(
    *,
    user_input: str,
    candidate_results: List[Dict],
    flow_spec: Optional[Dict] = None,
) -> str:
    adjudication = _adjudication_contract(flow_spec)
    return (
        "You are the consensus judge in a competitive multi-agent flow. "
        "Do not merely summarize. Adjudicate the disagreement using the binding "
        "contract below, then produce a final answer that uses the strongest "
        "parts of the candidate work. Account for failed candidates without "
        "exposing stack traces.\n\n"
        f"{_adjudication_block(adjudication)}\n"
        "JUDGE OUTPUT RULES:\n"
        "- Include a score matrix with one row per candidate role_id.\n"
        "- Include a disagreement map naming the key conflicts between candidates.\n"
        "- Select a winner or synthesized winner, with a concrete rationale.\n"
        "- Include a minority report for any useful losing argument.\n"
        "- Do not reward verbosity; penalize unsupported or duplicated claims.\n\n"
        f"User input:\n\n{user_input}\n\n---\n\n"
        f"Candidate results JSON:\n\n{json.dumps(candidate_results, ensure_ascii=False, indent=2)}"
    )


async def _run_competitive(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    flow_spec: Optional[Dict] = None,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    consensus_id = role_ids[0]
    candidate_ids = role_ids[1:]
    total = len(role_ids)

    for idx, candidate_id in enumerate(candidate_ids, start=1):
        yield Event(type="role_started", run_id=run_id, role_id=candidate_id, index=idx, total=total)

    async def _candidate(idx: int, candidate_id: str) -> Dict:
        task = _competitive_candidate_task(
            template,
            user_input=user_input,
            candidate_id=candidate_id,
            role_order=candidate_ids,
            flow_spec=flow_spec,
        )
        _append_message(
            run_id=run_id,
            from_agent="orchestrator",
            to_agent=candidate_id,
            message_type="candidate_task",
            status="sent",
            role_id=candidate_id,
            payload={"flow_type": "competitive", "phase": "candidate", "index": idx, "total": total, "task_preview": _preview(task)},
        )
        result = await _execute_role(
            candidate_id,
            task,
            model=model,
            project_dir=_role_workspace(project_dir, candidate_id),
            sandbox_policy=sandbox_policy,
        )
        result["__index"] = idx
        result["__role_id"] = candidate_id
        return result

    candidate_results: List[Dict] = []
    tasks = [asyncio.create_task(_candidate(idx, candidate_id)) for idx, candidate_id in enumerate(candidate_ids, start=1)]
    for completed in asyncio.as_completed(tasks):
        result = await completed
        idx = result["__index"]
        candidate_id = result["__role_id"]
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=candidate_id,
            content=result["content"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        ))
        candidate_record = {
            "role_id": candidate_id,
            "content": result["content"],
            "latency_ms": result["latency_ms"],
            "error": result["error"],
        }
        candidate_results.append(candidate_record)
        _append_message(
            run_id=run_id,
            from_agent=candidate_id,
            to_agent=consensus_id,
            message_type="candidate_result",
            status="failed" if result["error"] else "received",
            role_id=candidate_id,
            output_index=output_index,
            payload={
                "flow_type": "competitive",
                "phase": "candidate",
                "index": idx,
                "total": total,
                "latency_ms": result["latency_ms"],
                "error": result["error"],
                "content_preview": _preview(result["content"] or ""),
            },
        )
        if result["error"]:
            yield Event(type="role_failed", run_id=run_id, role_id=candidate_id,
                        error=result["error"], latency_ms=result["latency_ms"], index=idx, total=total)
        else:
            yield Event(type="role_completed", run_id=run_id, role_id=candidate_id,
                        content=result["content"], latency_ms=result["latency_ms"], index=idx, total=total)

    candidate_results.sort(key=lambda item: candidate_ids.index(item["role_id"]))
    async for item in _stream_hierarchical_master(
        role_id=consensus_id,
        task=_competitive_consensus_task(
            user_input=user_input,
            candidate_results=candidate_results,
            flow_spec=flow_spec,
        ),
        run_id=run_id,
        index=0,
        total=total,
        model=model,
        project_dir=project_dir,
        sandbox_policy=sandbox_policy,
        message_type="consensus_task",
        message_payload={"flow_type": "competitive", "phase": "consensus", "index": 0, "total": total},
    ):
        if isinstance(item, Event):
            yield item


def _peer_initial_task(
    template: str,
    *,
    user_input: str,
    peer_id: str,
    role_order: List[str],
    flow_spec: Optional[Dict] = None,
) -> str:
    base = render_prompt(template, user_input=user_input, prior="")
    contract = _role_contract(peer_id, role_order, flow_spec)
    return (
        "You are a peer agent in a peer-to-peer multi-agent collaboration. "
        "Produce an independent initial answer from the binding stance below. "
        "Do not optimize for consensus yet; optimize for a clear, defensible "
        "position that can survive review.\n\n"
        f"Peer role: {peer_id}\n\n"
        f"{_contract_block(contract)}\n"
        "INITIAL RESPONSE RULES:\n"
        "- State your position and assumptions.\n"
        "- Name what you would challenge in a competing answer.\n"
        "- Include evidence or reasoning trace for important claims.\n"
        "- Include a short self-critique.\n\n"
        f"User input:\n\n{base}"
    )


def _peer_review_task(
    *,
    user_input: str,
    peer_id: str,
    initial_answer: str,
    peer_messages: List[Dict],
    role_order: List[str],
    flow_spec: Optional[Dict] = None,
) -> str:
    contract = _role_contract(peer_id, role_order, flow_spec)
    adjudication = _adjudication_contract(flow_spec)
    return (
        "You are participating in a peer-to-peer multi-agent collaboration. "
        "Review the other peers' full messages, identify concrete agreements "
        "and disagreements, revise your answer if warranted, and cast a vote. "
        "You must preserve your role's stance unless another peer clearly beats "
        "it under the adjudication rubric.\n\n"
        f"Peer role: {peer_id}\n\n"
        f"{_contract_block(contract)}\n"
        f"{_adjudication_block(adjudication)}\n"
        "REVIEW RESPONSE RULES:\n"
        "- Include a peer-by-peer critique, naming each peer role_id you reviewed.\n"
        "- Explain what you changed from your initial answer, if anything.\n"
        "- Vote by rubric quality, not by similarity to your own stance.\n"
        "- End with exactly one final vote line: VOTE: <role_id>\n"
        "- The vote must target one of the provided peer role_ids, including your own role_id if your answer remains strongest.\n\n"
        f"Original user input:\n\n{user_input}\n\n---\n\n"
        f"Your initial answer:\n\n{initial_answer}\n\n---\n\n"
        f"Peer messages JSON:\n\n{json.dumps(peer_messages, ensure_ascii=False, indent=2)}"
    )


def _dag_node_task(
    template: str,
    *,
    user_input: str,
    node: Dict,
    upstream_results: List[Dict],
    role_order: Optional[List[str]] = None,
    flow_spec: Optional[Dict] = None,
) -> str:
    upstream = ""
    if upstream_results:
        upstream = json.dumps(upstream_results, ensure_ascii=False, indent=2)
    node_template = node.get("prompt_template") or template
    base = render_prompt(node_template, user_input=user_input, prior=upstream)
    if upstream:
        task = (
            "You are executing one node in a DAG multi-agent flow. Use the upstream "
            "node outputs as dependencies, produce this node's deliverable, and do "
            "not repeat unrelated upstream text.\n\n"
            f"Node id: {node['id']}\n"
            f"Role id: {node['role_id']}\n"
            f"Node label: {node.get('label') or node['id']}\n\n"
            f"Original user input:\n\n{user_input}\n\n---\n\n"
            f"Upstream results JSON:\n\n{upstream}\n\n---\n\n"
            f"Node prompt:\n\n{base}"
        )
    else:
        task = (
        "You are executing a root node in a DAG multi-agent flow. Produce this "
        "node's deliverable for the original user input.\n\n"
        f"Node id: {node['id']}\n"
        f"Role id: {node['role_id']}\n"
        f"Node label: {node.get('label') or node['id']}\n\n"
        f"Node prompt:\n\n{base}"
        )
    return _role_contract_task(
        task,
        role_id=node["role_id"],
        role_order=role_order or [node["role_id"]],
        flow_type="dag",
        flow_spec=flow_spec,
        phase=f"node {node['id']}",
    )


def _dag_node_actor_id(node: Dict) -> str:
    if node.get("type") == "graphrag":
        return f"graphrag:{node['id']}"
    return node["role_id"]


def _format_graphrag_content(query: str, contexts: List[Dict]) -> str:
    if not contexts:
        return f"GraphRAG query: {query}\n\nNo matching knowledge graph context was found."
    return (
        "GraphRAG knowledge context\n\n"
        f"Query: {query}\n\n"
        "Contexts JSON:\n\n"
        f"{json.dumps(contexts, ensure_ascii=False, indent=2)}"
    )


async def _execute_graphrag_node(node: Dict, *, user_input: str, upstream_results: List[Dict]) -> Dict:
    started = time.monotonic()
    upstream = json.dumps(upstream_results, ensure_ascii=False, indent=2) if upstream_results else ""
    query_template = str(node.get("query_template") or "{input}")
    try:
        query = render_prompt(query_template, user_input=user_input, prior=upstream).strip()
    except Exception as exc:  # noqa: BLE001
        return {
            "content": "",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": f"render GraphRAG query failed: {exc}",
            "metadata": {"query_template": query_template},
        }
    if not query:
        query = user_input.strip()
    query, query_truncated = _graphrag_query_text(query)

    try:
        import httpx

        max_hits = int(node.get("max_hits") or 3)
        async with httpx.AsyncClient(timeout=httpx.Timeout(GRAPHRAG_TIMEOUT_SECONDS)) as client:
            resp = await client.get(
                f"{AGENT_SERVICE_URL}/api/v1/knowledge-graph/graphrag",
                params={"q": query, "limit": max(1, min(max_hits, 10))},
            )
            resp.raise_for_status()
            payload = resp.json()
        contexts = payload.get("contexts") if isinstance(payload, dict) else []
        if not isinstance(contexts, list):
            contexts = []
        return {
            "content": _format_graphrag_content(query, contexts),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": None,
            "metadata": {
                "query": query,
                "query_truncated": query_truncated,
                "hit_count": len(contexts),
                "max_hits": max_hits,
                "response_query": payload.get("query") if isinstance(payload, dict) else None,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("GraphRAG DAG node %s failed", node.get("id"))
        return {
            "content": "",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "error": str(exc),
            "metadata": {
                "query": query,
                "query_truncated": query_truncated,
                "max_hits": int(node.get("max_hits") or 3),
            },
        }


async def _run_dag(
    role_ids: List[str], user_input: str, template: str, run_id: int, flow_spec: Dict,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    spec = flows_mod.normalize_dag_spec(role_ids, flow_spec)
    nodes = spec["nodes"]
    edges = spec["edges"]
    node_by_id = {node["id"]: node for node in nodes}
    node_order = [node["id"] for node in nodes]
    total = len(nodes)

    incoming: Dict[str, List[str]] = {node_id: [] for node_id in node_order}
    outgoing: Dict[str, List[str]] = {node_id: [] for node_id in node_order}
    remaining_deps: Dict[str, int] = {node_id: 0 for node_id in node_order}
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        incoming[edge["to"]].append(edge["from"])
        remaining_deps[edge["to"]] += 1

    for idx, node_id in enumerate(node_order):
        node = node_by_id[node_id]
        actor_id = _dag_node_actor_id(node)
        yield Event(
            type="role_started",
            run_id=run_id,
            role_id=actor_id,
            index=idx,
            total=total,
            extra={"node_id": node_id, "phase": "queued"},
        )

    completed: Dict[str, Dict] = {}
    failed: Dict[str, Dict] = {}
    ready = [node_id for node_id in node_order if remaining_deps[node_id] == 0]

    async def _run_node(node_id: str) -> Dict:
        node = node_by_id[node_id]
        idx = node_order.index(node_id)
        upstream_results = [
            {
                "node_id": parent_id,
                "role_id": completed[parent_id]["role_id"],
                "content": _dag_upstream_content(completed[parent_id]["content"]),
                "error": completed[parent_id].get("error"),
            }
            for parent_id in incoming[node_id]
            if parent_id in completed
        ]
        actor_id = _dag_node_actor_id(node)
        if node.get("type") == "graphrag":
            upstream = json.dumps(upstream_results, ensure_ascii=False, indent=2) if upstream_results else ""
            task = render_prompt(str(node.get("query_template") or "{input}"), user_input=user_input, prior=upstream)
        else:
            task = _dag_node_task(
                template,
                user_input=user_input,
                node=node,
                upstream_results=upstream_results,
                role_order=role_ids,
                flow_spec=flow_spec,
            )
        _append_message(
            run_id=run_id,
            from_agent="dag/router",
            to_agent=actor_id,
            message_type="dag_node_task",
            status="sent",
            role_id=actor_id,
            payload={
                "flow_type": "dag",
                "node_id": node_id,
                "node_label": node.get("label") or node_id,
                "node_type": node.get("type") or "role",
                "index": idx,
                "total": total,
                "upstream": incoming[node_id],
                "task_preview": _preview(task),
            },
        )
        if node.get("type") == "graphrag":
            result = await _execute_graphrag_node(node, user_input=user_input, upstream_results=upstream_results)
        else:
            result = await _execute_role(
                node["role_id"],
                task,
                model=model,
                project_dir=_role_workspace(project_dir, actor_id),
                sandbox_policy=sandbox_policy,
            )
        result["__node_id"] = node_id
        result["__role_id"] = actor_id
        result["__index"] = idx
        return result

    while ready:
        level = ready
        ready = []
        tasks = [asyncio.create_task(_run_node(node_id)) for node_id in level]
        for completed_task in asyncio.as_completed(tasks):
            result = await completed_task
            node_id = result["__node_id"]
            role_id = result["__role_id"]
            idx = result["__index"]
            output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
                role_id=role_id,
                content=result["content"],
                latency_ms=result["latency_ms"],
                error=result["error"],
            ))
            record = {
                "node_id": node_id,
                "role_id": role_id,
                "content": result["content"],
                "latency_ms": result["latency_ms"],
                "error": result["error"],
                "metadata": result.get("metadata") or {},
                "output_index": output_index,
            }
            completed[node_id] = record
            if result["error"]:
                failed[node_id] = record
            _append_message(
                run_id=run_id,
                from_agent=role_id,
                to_agent="dag/router",
                message_type="dag_node_result",
                status="failed" if result["error"] else "received",
                role_id=role_id,
                output_index=output_index,
                payload={
                    "flow_type": "dag",
                    "node_id": node_id,
                    "node_type": node_by_id[node_id].get("type") or "role",
                    "index": idx,
                    "total": total,
                    "latency_ms": result["latency_ms"],
                    "error": result["error"],
                    "metadata": result.get("metadata") or {},
                    "content_preview": _preview(result["content"] or ""),
                },
            )
            if result["error"]:
                yield Event(
                    type="role_failed",
                    run_id=run_id,
                    role_id=role_id,
                    error=result["error"],
                    latency_ms=result["latency_ms"],
                    index=idx,
                    total=total,
                    extra={"node_id": node_id},
                )
            else:
                yield Event(
                    type="role_completed",
                    run_id=run_id,
                    role_id=role_id,
                    content=result["content"],
                    latency_ms=result["latency_ms"],
                    index=idx,
                    total=total,
                    extra={"node_id": node_id},
                )

            for child_id in outgoing[node_id]:
                child_role = _dag_node_actor_id(node_by_id[child_id])
                _append_message(
                    run_id=run_id,
                    from_agent=role_id,
                    to_agent=child_role,
                    message_type="dag_edge_handoff",
                    status="failed" if result["error"] else "sent",
                    role_id=child_role,
                    output_index=output_index,
                    payload={
                        "flow_type": "dag",
                        "from_node": node_id,
                        "to_node": child_id,
                        "metadata": result.get("metadata") or {},
                        "content_preview": _preview(result["content"] or result["error"] or ""),
                    },
                )
                remaining_deps[child_id] -= 1
                if remaining_deps[child_id] == 0:
                    ready.append(child_id)

    if len(completed) != len(nodes):
        missing = [node_id for node_id in node_order if node_id not in completed]
        logger.warning("dag run %s did not complete nodes: %s", run_id, ", ".join(missing))


def _extract_vote(content: str, valid_role_ids: List[str]) -> str:
    match = re.search(r"^\s*VOTE\s*:\s*([^\s,;]+)", content or "", flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    vote = match.group(1).strip()
    return vote if vote in valid_role_ids else ""


def _resolve_peer_conflict(peer_results: List[Dict], role_order: List[str]) -> Dict:
    successful = [item for item in peer_results if not item.get("error") and (item.get("content") or "").strip()]
    if not successful:
        return {"content": "", "winner": "", "strategy": "none", "votes": {}}
    if len(successful) == 1:
        winner = successful[0]["role_id"]
        return {
            "content": successful[0]["content"],
            "winner": winner,
            "strategy": "single_success",
            "votes": {winner: 1},
        }

    votes: Dict[str, int] = {}
    for item in successful:
        vote = _extract_vote(item.get("content") or "", role_order)
        if vote:
            votes[vote] = votes.get(vote, 0) + 1
    if votes:
        max_votes = max(votes.values())
        winners = [role_id for role_id, count in votes.items() if count == max_votes]
        if len(winners) == 1:
            winner = winners[0]
            selected = next((item for item in successful if item["role_id"] == winner), successful[0])
            return {"content": selected["content"], "winner": winner, "strategy": "majority_vote", "votes": votes}

    return {
        "content": "",
        "winner": "",
        "strategy": "requires_resolver",
        "votes": votes,
    }


def _peer_resolver_task(
    *,
    user_input: str,
    peer_results: List[Dict],
    role_order: List[str],
    votes: Dict[str, int],
    flow_spec: Optional[Dict] = None,
) -> str:
    adjudication = _adjudication_contract(flow_spec)
    role_contracts = [_role_contract(role_id, role_order, flow_spec) for role_id in role_order]
    compact_results = []
    for item in peer_results:
        compact_results.append({
            "role_id": item.get("role_id"),
            "latency_ms": item.get("latency_ms"),
            "error": item.get("error"),
            "content": _compact_text(item.get("content") or "", RESOLVER_CONTEXT_MAX_CHARS),
        })
    return (
        "You are an independent resolver for a peer-to-peer multi-agent flow. "
        "The peers did not produce a clean majority or the vote needs adjudication. "
        "Resolve the disagreement by rubric quality, not by answer length or role popularity.\n\n"
        f"{_adjudication_block(adjudication)}\n"
        "RESOLVER OUTPUT RULES:\n"
        "- Include a score matrix with one row per successful peer role_id.\n"
        "- Include a disagreement map naming the concrete conflicts.\n"
        "- Select a winner or synthesize a final answer if synthesis is stronger than any single peer.\n"
        "- Include a minority report for useful losing warnings.\n"
        "- End with a line `WINNER: <role_id>` when one peer wins, or `WINNER: synthesis` when you synthesize.\n\n"
        f"Original user input:\n\n{user_input}\n\n---\n\n"
        f"Role contracts JSON:\n\n{json.dumps(role_contracts, ensure_ascii=False, indent=2)}\n\n---\n\n"
        f"Votes JSON:\n\n{json.dumps(votes, ensure_ascii=False, indent=2)}\n\n---\n\n"
        f"Peer results JSON:\n\n{json.dumps(compact_results, ensure_ascii=False, indent=2)}"
    )


def _extract_winner(content: str, valid_role_ids: List[str]) -> str:
    match = re.search(r"^\s*WINNER\s*:\s*([^\s,;]+)", content or "", flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    winner = match.group(1).strip()
    if winner.lower() == "synthesis":
        return "synthesis"
    return winner if winner in valid_role_ids else ""


def _resolver_failure_report(error: str, votes: Dict[str, int], peer_results: List[Dict]) -> str:
    compact_results = [
        {
            "role_id": item.get("role_id"),
            "error": item.get("error"),
            "content_preview": _preview(item.get("content") or "", 300),
        }
        for item in peer_results
    ]
    return (
        "Conflict resolution did not produce a safe winner.\n\n"
        "Reason:\n"
        f"{error or 'resolver returned empty output'}\n\n"
        "Votes observed:\n"
        f"{json.dumps(votes, ensure_ascii=False, indent=2)}\n\n"
        "Peer output previews:\n"
        f"{json.dumps(compact_results, ensure_ascii=False, indent=2)}\n\n"
        "No winner was selected because the resolver failed and the orchestrator "
        "does not use answer length as a fallback decision rule."
    )


async def _run_peer_to_peer(
    role_ids: List[str], user_input: str, template: str, run_id: int,
    flow_spec: Optional[Dict] = None,
    model: str = "", project_dir: str = "", sandbox_policy: Optional[Dict] = None,
) -> AsyncIterator[Event]:
    total = len(role_ids)
    for idx, role_id in enumerate(role_ids):
        yield Event(type="role_started", run_id=run_id, role_id=role_id, index=idx, total=total)

    async def _initial(idx: int, role_id: str) -> Dict:
        task = _peer_initial_task(
            template,
            user_input=user_input,
            peer_id=role_id,
            role_order=role_ids,
            flow_spec=flow_spec,
        )
        _append_message(
            run_id=run_id,
            from_agent="peer/router",
            to_agent=role_id,
            message_type="peer_initial_task",
            status="sent",
            role_id=role_id,
            payload={"flow_type": "peer_to_peer", "phase": "initial", "round": 0, "index": idx, "total": total, "task_preview": _preview(task)},
        )
        result = await _execute_role(
            role_id,
            task,
            model=model,
            project_dir=_role_workspace(project_dir, role_id),
            sandbox_policy=sandbox_policy,
        )
        result["__index"] = idx
        result["__role_id"] = role_id
        return result

    initial_results: List[Dict] = []
    tasks = [asyncio.create_task(_initial(idx, role_id)) for idx, role_id in enumerate(role_ids)]
    for completed in asyncio.as_completed(tasks):
        result = await completed
        idx = result["__index"]
        role_id = result["__role_id"]
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id,
            content=result["content"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        ))
        record = {"role_id": role_id, "content": result["content"], "latency_ms": result["latency_ms"], "error": result["error"], "output_index": output_index}
        initial_results.append(record)
        _append_message(
            run_id=run_id,
            from_agent=role_id,
            to_agent="peer/router",
            message_type="peer_initial_result",
            status="failed" if result["error"] else "received",
            role_id=role_id,
            output_index=output_index,
            payload={
                "flow_type": "peer_to_peer",
                "phase": "initial",
                "round": 0,
                "index": idx,
                "total": total,
                "latency_ms": result["latency_ms"],
                "error": result["error"],
                "content_preview": _preview(result["content"] or ""),
            },
        )
        if result["error"]:
            yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                        error=result["error"], latency_ms=result["latency_ms"], index=idx, total=total)
        else:
            yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                        content=result["content"], latency_ms=result["latency_ms"], index=idx, total=total)

    initial_results.sort(key=lambda item: role_ids.index(item["role_id"]))
    successful_initials = [item for item in initial_results if not item.get("error")]
    if not successful_initials:
        return

    for source in successful_initials:
        for target in successful_initials:
            if source["role_id"] == target["role_id"]:
                continue
            _append_message(
                run_id=run_id,
                from_agent=source["role_id"],
                to_agent=target["role_id"],
                message_type="peer_broadcast",
                status="sent",
                role_id=target["role_id"],
                output_index=source.get("output_index"),
                payload={
                    "flow_type": "peer_to_peer",
                    "phase": "broadcast",
                    "round": 1,
                    "source_output_index": source.get("output_index"),
                    "content_preview": _preview(source.get("content") or ""),
                },
            )

    review_results: List[Dict] = []

    async def _review(idx: int, role_id: str, initial_answer: str, peer_messages: List[Dict]) -> Dict:
        task = _peer_review_task(
            user_input=user_input,
            peer_id=role_id,
            initial_answer=initial_answer,
            peer_messages=peer_messages,
            role_order=role_ids,
            flow_spec=flow_spec,
        )
        _append_message(
            run_id=run_id,
            from_agent="peer/router",
            to_agent=role_id,
            message_type="peer_review_task",
            status="sent",
            role_id=role_id,
            payload={"flow_type": "peer_to_peer", "phase": "review", "round": 1, "index": idx, "total": total, "task_preview": _preview(task)},
        )
        result = await _execute_role(
            role_id,
            task,
            model=model,
            project_dir=_role_workspace(project_dir, role_id),
            sandbox_policy=sandbox_policy,
        )
        result["__index"] = idx
        result["__role_id"] = role_id
        return result

    review_tasks = []
    for source in successful_initials:
        idx = role_ids.index(source["role_id"])
        peers = [
            _peer_message_payload(item, include_content=True)
            for item in successful_initials
            if item["role_id"] != source["role_id"]
        ]
        review_tasks.append(asyncio.create_task(_review(idx, source["role_id"], source.get("content") or "", peers)))

    for completed in asyncio.as_completed(review_tasks):
        result = await completed
        idx = result["__index"]
        role_id = result["__role_id"]
        output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
            role_id=role_id,
            content=result["content"],
            latency_ms=result["latency_ms"],
            error=result["error"],
        ))
        record = {"role_id": role_id, "content": result["content"], "latency_ms": result["latency_ms"], "error": result["error"], "output_index": output_index}
        review_results.append(record)
        _append_message(
            run_id=run_id,
            from_agent=role_id,
            to_agent="peer/router",
            message_type="peer_review_result",
            status="failed" if result["error"] else "received",
            role_id=role_id,
            output_index=output_index,
            payload={
                "flow_type": "peer_to_peer",
                "phase": "review",
                "round": 1,
                "index": idx,
                "total": total,
                "latency_ms": result["latency_ms"],
                "error": result["error"],
                "content_preview": _preview(result["content"] or ""),
            },
        )
        if result["error"]:
            yield Event(type="role_failed", run_id=run_id, role_id=role_id,
                        error=result["error"], latency_ms=result["latency_ms"], index=idx, total=total)
        else:
            yield Event(type="role_completed", run_id=run_id, role_id=role_id,
                        content=result["content"], latency_ms=result["latency_ms"], index=idx, total=total)

    review_results.sort(key=lambda item: role_ids.index(item["role_id"]))
    resolution = _resolve_peer_conflict(review_results or initial_results, role_ids)
    if resolution.get("strategy") == "requires_resolver":
        resolver_source = review_results or initial_results
        task = _peer_resolver_task(
            user_input=user_input,
            peer_results=resolver_source,
            role_order=role_ids,
            votes=resolution.get("votes", {}),
            flow_spec=flow_spec,
        )
        _append_message(
            run_id=run_id,
            from_agent="peer/router",
            to_agent="orchestrator/resolver",
            message_type="conflict_resolution_task",
            status="sent",
            role_id="orchestrator/resolver",
            payload={
                "flow_type": "peer_to_peer",
                "phase": "resolution",
                "strategy": "llm_resolver",
                "votes": resolution.get("votes", {}),
                "task_preview": _preview(task),
            },
        )
        result = await _execute_role(
            "orchestrator/resolver",
            task,
            model=model,
            project_dir=_role_workspace(project_dir, "orchestrator-resolver"),
            sandbox_policy=sandbox_policy,
        )
        winner = _extract_winner(result.get("content") or "", role_ids)
        resolver_content = result.get("content") or ""
        if result.get("error") or not resolver_content.strip():
            resolver_content = _resolver_failure_report(
                result.get("error") or "",
                resolution.get("votes", {}),
                resolver_source,
            )
        resolution = {
            "content": resolver_content,
            "winner": winner,
            "strategy": "llm_resolver_failed" if result.get("error") else "llm_resolver",
            "votes": resolution.get("votes", {}),
            "latency_ms": result.get("latency_ms", 0),
            "error": result.get("error"),
        }
    if not resolution.get("content"):
        return
    output_index = runs_mod.append_output(run_id, runs_mod.RoleOutput(
        role_id="orchestrator/resolver",
        content=resolution["content"],
        latency_ms=resolution.get("latency_ms", 0),
        error=resolution.get("error"),
    ))
    _append_message(
        run_id=run_id,
        from_agent="orchestrator/resolver",
        to_agent="orchestrator",
        message_type="conflict_resolution_result",
        status="received",
        role_id="orchestrator/resolver",
        output_index=output_index,
        payload={
            "flow_type": "peer_to_peer",
            "phase": "resolution",
            "strategy": resolution.get("strategy"),
            "winner": resolution.get("winner"),
            "votes": resolution.get("votes", {}),
            "error": resolution.get("error"),
            "content_preview": _preview(resolution.get("content") or ""),
        },
    )
    yield Event(
        type="conflict_resolved",
        run_id=run_id,
        role_id="orchestrator/resolver",
        content=resolution["content"],
        latency_ms=resolution.get("latency_ms", 0),
        index=total,
        total=total + 1,
        extra={
            "strategy": resolution.get("strategy"),
            "winner": resolution.get("winner"),
            "votes": resolution.get("votes", {}),
        },
    )
    yield Event(type="role_completed", run_id=run_id, role_id="orchestrator/resolver",
                content=resolution["content"], latency_ms=resolution.get("latency_ms", 0),
                index=total, total=total + 1)


async def _flow_events(run_id: int, flow_id: int, user_input: str, project_dir: str = "") -> AsyncIterator[Event]:
    flow = flows_mod.get(flow_id)
    runs_mod.mark_running(run_id)

    if not project_dir:
        project_dir = str(Path(AGENT_WORK_DIR) / f"flow-{flow.id}" / f"run-{run_id}")
        try:
            Path(project_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("could not create work dir %s: %s — falling back to tmp sandbox",
                           project_dir, exc)
            project_dir = ""
    runs_mod.set_project_dir(run_id, project_dir)

    run_total = len(flow.role_ids)
    run_extra = {
        "flow_id": flow.id,
        "flow_type": flow.flow_type,
        "role_ids": flow.role_ids,
        "project_dir": project_dir,
    }
    if flow.flow_type == "dag":
        try:
            dag_spec = flows_mod.normalize_dag_spec(flow.role_ids, flow.flow_spec)
            run_total = len(dag_spec.get("nodes") or flow.role_ids)
            run_extra["dag_nodes"] = dag_spec.get("nodes") or []
        except Exception:
            run_total = len(flow.role_ids)

    yield Event(
        type="run_started", run_id=run_id, total=run_total,
        extra=run_extra,
    )

    sandbox_policy = flow.sandbox_policy

    if flow.flow_type == "sequential":
        generator = _run_sequential(flow.role_ids, user_input,
                                    flow.prompt_template, run_id,
                                    flow_spec=flow.flow_spec,
                                    model=flow.model, project_dir=project_dir,
                                    sandbox_policy=sandbox_policy)
    elif flow.flow_type == "parallel":
        generator = _run_parallel(flow.role_ids, user_input,
                                  flow.prompt_template, run_id,
                                  flow_spec=flow.flow_spec,
                                  model=flow.model, project_dir=project_dir,
                                  sandbox_policy=sandbox_policy)
    elif flow.flow_type == "pipeline":
        generator = _run_pipeline(flow.role_ids, user_input,
                                  flow.prompt_template, run_id,
                                  flow_spec=flow.flow_spec,
                                  model=flow.model, project_dir=project_dir,
                                  sandbox_policy=sandbox_policy)
    elif flow.flow_type == "hierarchical":
        generator = _run_hierarchical(flow.role_ids, user_input,
                                      flow.prompt_template, run_id,
                                      flow_spec=flow.flow_spec,
                                      model=flow.model, project_dir=project_dir,
                                      sandbox_policy=sandbox_policy)
    elif flow.flow_type == "competitive":
        generator = _run_competitive(flow.role_ids, user_input,
                                     flow.prompt_template, run_id,
                                     flow_spec=flow.flow_spec,
                                     model=flow.model, project_dir=project_dir,
                                     sandbox_policy=sandbox_policy)
    elif flow.flow_type == "peer_to_peer":
        generator = _run_peer_to_peer(flow.role_ids, user_input,
                                      flow.prompt_template, run_id,
                                      flow_spec=flow.flow_spec,
                                      model=flow.model, project_dir=project_dir,
                                      sandbox_policy=sandbox_policy)
    elif flow.flow_type == "dag":
        generator = _run_dag(flow.role_ids, user_input,
                             flow.prompt_template, run_id,
                             flow.flow_spec,
                             model=flow.model, project_dir=project_dir,
                             sandbox_policy=sandbox_policy)
    else:
        raise ValueError(f"unsupported flow_type: {flow.flow_type}")

    any_failure = False
    any_success = False
    async for event in generator:
        if event.type == "role_failed":
            any_failure = True
            if event.extra and event.extra.get("fatal"):
                any_success = False
        elif event.type == "role_completed":
            any_success = True
        yield event

    if not any_success:
        yield Event(type="run_failed", run_id=run_id, error="no role produced output")
        runs_mod.finalize(run_id, "failed", "no role produced output")
        runs_mod.write_run_output_files(runs_mod.get(run_id))
    else:
        yield Event(type="run_completed", run_id=run_id)
        runs_mod.finalize(run_id, "succeeded", "with partial failures" if any_failure else "")
        runs_mod.write_run_output_files(runs_mod.get(run_id))


async def execute_flow_run(run_id: int, flow_id: int, user_input: str, project_dir: str = "") -> None:
    try:
        async for event in _flow_events(run_id, flow_id, user_input, project_dir):
            runs_mod.append_event(run_id, event)
    except asyncio.CancelledError:
        runs_mod.append_event(run_id, Event(type="run_cancelled", run_id=run_id, error="cancelled by user"))
        runs_mod.finalize(run_id, "cancelled", "cancelled by user")
        raise
    except Exception as exc:                                 # noqa: BLE001
        logger.exception("flow %s run %s blew up", flow_id, run_id)
        runs_mod.append_event(run_id, Event(type="run_failed", run_id=run_id, error=str(exc)))
        runs_mod.finalize(run_id, "failed", str(exc))


async def run_flow(flow_id: int, user_input: str, project_dir: str = "") -> AsyncIterator[Event]:
    """Compatibility streaming wrapper; new clients should start a run then tail events."""
    run = runs_mod.create(flow_id, user_input)
    async for event in _flow_events(run.id, flow_id, user_input, project_dir):
        runs_mod.append_event(run.id, event)
        yield event
