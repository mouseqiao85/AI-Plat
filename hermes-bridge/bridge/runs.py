"""Bookkeeping for ``flow_runs`` — one row per orchestrator execution.

Phase 2 only persists the lifecycle (pending → running → succeeded/failed)
and final outputs. The streaming layer in Phase 3 writes intermediate
deltas straight to SSE; only the resolved per-role chunks land here.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import subprocess
import shutil
import zipfile
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import db
from .collaboration import CollaborationMessage

AGENT_WORK_DIR = os.getenv("AGENT_WORK_DIR", "/home/admin/.agent-platform/runs")
RUN_ARTIFACT_ZIP_MAX_BYTES = int(os.getenv("RUN_ARTIFACT_ZIP_MAX_BYTES", str(100 * 1024 * 1024)))
RUN_ARTIFACT_ZIP_MAX_FILES = int(os.getenv("RUN_ARTIFACT_ZIP_MAX_FILES", "2000"))
RUN_INPUT_MAX_CHARS = int(os.getenv("RUN_INPUT_MAX_CHARS", "60000"))


@dataclass
class RoleOutput:
    role_id: str
    content: str
    latency_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "content": self.content,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class FlowRun:
    id: int
    flow_id: int
    input_text: str
    status: str
    error: str
    outputs: List[Dict]
    started_at: str
    finished_at: Optional[str]
    project_dir: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "flow_id": self.flow_id,
            "input_text": self.input_text,
            "status": self.status,
            "error": self.error,
            "outputs": self.outputs,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "project_dir": self.project_dir,
        }


@dataclass
class FlowRunEvent:
    id: int
    run_id: int
    seq: int
    event_type: str
    payload: Dict[str, Any]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "seq": self.seq,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        }


def _row_to_run(row) -> FlowRun:
    return FlowRun(
        id=row["id"],
        flow_id=row["flow_id"],
        input_text=row["input_text"],
        status=row["status"],
        error=row["error"] or "",
        outputs=json.loads(row["outputs"] or "[]"),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        project_dir=row["project_dir"] or "",
    )


def _row_to_event(row) -> FlowRunEvent:
    return FlowRunEvent(
        id=row["id"],
        run_id=row["run_id"],
        seq=row["seq"],
        event_type=row["event_type"],
        payload=json.loads(row["payload"] or "{}"),
        created_at=row["created_at"],
    )


def _row_to_collaboration_message(row) -> CollaborationMessage:
    return CollaborationMessage(
        id=row["id"],
        run_id=row["run_id"],
        seq=row["seq"],
        from_agent=row["from_agent"],
        to_agent=row["to_agent"],
        type=row["type"],
        payload=json.loads(row["payload"] or "{}"),
        priority=row["priority"],
        timeout_ms=row["timeout_ms"],
        status=row["status"],
        role_id=row["role_id"],
        output_index=row["output_index"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _event_payload(event: Any) -> Dict[str, Any]:
    if hasattr(event, "to_payload"):
        payload = event.to_payload()
    elif is_dataclass(event):
        payload = asdict(event)
    elif isinstance(event, dict):
        payload = dict(event)
    else:
        raise TypeError("event must be a dict or dataclass")
    return {k: v for k, v in payload.items() if v is not None}


def sanitize_input_text(input_text: str) -> str:
    """Remove binary attachment bodies from run input while preserving labels."""
    text = input_text or ""

    def _binary_notice(match: re.Match) -> str:
        return f"{match.group(1)}\n\n[二进制附件内容已移除：请将文件转为文本/Markdown，或先导入知识库。]"

    def _replace_binary_attachment(match: re.Match) -> str:
        header = match.group(1)
        body = match.group(2) or ""
        if body.startswith("PK\x03\x04") or body.startswith("PK\u0003\u0004") or body.startswith("PK"):
            return f"{header}\n\n[二进制附件内容已移除：请将文件转为文本/Markdown，或先导入知识库。]"
        return match.group(0)

    text = re.sub(
        r"(\n---\n\*\*附件:\s*[^*]+\*\*\n\n)(.*?)(?=\n---\n\*\*附件:|\Z)",
        _replace_binary_attachment,
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"(\*\*[^*\n]+\.(?:docx|xlsx|pptx|doc|pdf)[^*\n]*\*\*\s*)PK[\s\S]*?(?=\n---\n|\Z)",
        _binary_notice,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    if len(text) > RUN_INPUT_MAX_CHARS:
        text = text[:RUN_INPUT_MAX_CHARS] + f"\n\n[输入已截断：超过 {RUN_INPUT_MAX_CHARS} 字符]"
    return text


def create(flow_id: int, input_text: str) -> FlowRun:
    input_text = sanitize_input_text(input_text)
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO flow_runs (flow_id, input_text, status, outputs)
               VALUES (?, ?, 'pending', '[]')""",
            (flow_id, input_text),
        )
        run_id = cur.lastrowid
        # Historical deployments relied on FK cascade inconsistently. If SQLite
        # reuses or migrates ids, clear any stale child rows before this run can
        # append legitimate events/messages.
        cur.execute("DELETE FROM collaboration_messages WHERE run_id = ?", (run_id,))
        cur.execute("DELETE FROM flow_run_events WHERE run_id = ?", (run_id,))
    return get(run_id)


def get(run_id: int) -> FlowRun:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM flow_runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"run not found: {run_id}")
    return _row_to_run(row)


def list_for_flow(flow_id: int, limit: int = 50) -> List[FlowRun]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM flow_runs WHERE flow_id = ? ORDER BY started_at DESC LIMIT ?",
            (flow_id, limit),
        )
        rows = cur.fetchall()
    return [_row_to_run(r) for r in rows]


def set_project_dir(run_id: int, project_dir: str) -> None:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE flow_runs SET project_dir = ? WHERE id = ?",
            (project_dir, run_id),
        )


def mark_running(run_id: int) -> None:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE flow_runs SET status = 'running' WHERE id = ?", (run_id,),
        )


def append_output(run_id: int, output: RoleOutput) -> int:
    """Append one role's resolved output. Atomic via the in-process lock.

    Returns the zero-based index of the persisted output for cross-linking
    collaboration messages to legacy role outputs.
    """
    with db.cursor() as cur:
        cur.execute("SELECT outputs FROM flow_runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(f"run not found: {run_id}")
        outputs = json.loads(row["outputs"] or "[]")
        output_index = len(outputs)
        outputs.append(output.to_dict())
        cur.execute(
            "UPDATE flow_runs SET outputs = ? WHERE id = ?",
            (json.dumps(outputs, ensure_ascii=False), run_id),
        )
    return output_index


def append_event(run_id: int, event: Any) -> Dict[str, Any]:
    payload = _event_payload(event)
    payload["run_id"] = payload.get("run_id", run_id)
    event_type = str(payload.get("type") or "message")
    with db.cursor() as cur:
        cur.execute("SELECT 1 FROM flow_runs WHERE id = ?", (run_id,))
        if cur.fetchone() is None:
            raise KeyError(f"run not found: {run_id}")
        cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM flow_run_events WHERE run_id = ?", (run_id,))
        seq = int(cur.fetchone()["next_seq"])
        payload["seq"] = seq
        cur.execute(
            """INSERT INTO flow_run_events (run_id, seq, event_type, payload)
               VALUES (?, ?, ?, ?)""",
            (run_id, seq, event_type, json.dumps(payload, ensure_ascii=False)),
        )
    return payload


def list_events(run_id: int, after_seq: int = 0, limit: int = 500) -> List[FlowRunEvent]:
    safe_limit = max(1, min(limit, 1000))
    with db.cursor() as cur:
        cur.execute(
            """SELECT * FROM flow_run_events
               WHERE run_id = ? AND seq > ?
               ORDER BY seq ASC
               LIMIT ?""",
            (run_id, after_seq, safe_limit),
        )
        rows = cur.fetchall()
    return [_row_to_event(r) for r in rows]


def append_collaboration_message(message: CollaborationMessage) -> CollaborationMessage:
    with db.cursor() as cur:
        cur.execute("SELECT 1 FROM flow_runs WHERE id = ?", (message.run_id,))
        if cur.fetchone() is None:
            raise KeyError(f"run not found: {message.run_id}")
        cur.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM collaboration_messages WHERE run_id = ?", (message.run_id,))
        seq = int(cur.fetchone()["next_seq"])
        cur.execute(
            """INSERT INTO collaboration_messages
               (run_id, seq, from_agent, to_agent, type, payload, priority,
                timeout_ms, status, role_id, output_index)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message.run_id,
                seq,
                message.from_agent,
                message.to_agent,
                message.type,
                json.dumps(message.payload, ensure_ascii=False),
                message.priority,
                message.timeout_ms,
                message.status,
                message.role_id,
                message.output_index,
            ),
        )
        message_id = cur.lastrowid
        cur.execute("SELECT * FROM collaboration_messages WHERE id = ?", (message_id,))
        row = cur.fetchone()
    return _row_to_collaboration_message(row)


def list_collaboration_messages(run_id: int, after_seq: int = 0, limit: int = 500) -> List[CollaborationMessage]:
    safe_limit = max(1, min(limit, 1000))
    with db.cursor() as cur:
        cur.execute(
            """SELECT * FROM collaboration_messages
               WHERE run_id = ? AND seq > ?
               ORDER BY seq ASC
               LIMIT ?""",
            (run_id, after_seq, safe_limit),
        )
        rows = cur.fetchall()
    return [_row_to_collaboration_message(r) for r in rows]


def update_collaboration_message_status(message_id: int, status: str) -> CollaborationMessage:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM collaboration_messages WHERE id = ?", (message_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(f"collaboration message not found: {message_id}")
        message = _row_to_collaboration_message(row)
        message.transition(status)
        cur.execute(
            """UPDATE collaboration_messages
               SET status = ?, updated_at = ?
               WHERE id = ?""",
            (message.status, message.updated_at, message_id),
        )
        cur.execute("SELECT * FROM collaboration_messages WHERE id = ?", (message_id,))
        row = cur.fetchone()
    return _row_to_collaboration_message(row)


def finalize(run_id: int, status: str, error: str = "") -> None:
    if status not in {"succeeded", "failed", "cancelled"}:
        raise ValueError(f"invalid terminal status: {status}")
    with db.cursor() as cur:
        cur.execute(
            "UPDATE flow_runs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
            (status, error, datetime.utcnow().isoformat(sep=" ", timespec="seconds"), run_id),
        )


def delete(run_id: int) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM collaboration_messages WHERE run_id = ?", (run_id,))
        cur.execute("DELETE FROM flow_run_events WHERE run_id = ?", (run_id,))
        cur.execute("DELETE FROM flow_runs WHERE id = ?", (run_id,))


def work_root() -> Path:
    return Path(AGENT_WORK_DIR).resolve()


def resolve_project_dir(run: FlowRun) -> Path:
    root = work_root()
    expected = (root / f"flow-{run.flow_id}" / f"run-{run.id}").resolve()
    candidate = Path(run.project_dir) if run.project_dir else expected
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != expected:
        raise ValueError("run work directory does not match run id")
    if resolved == root or root not in resolved.parents:
        raise ValueError("unsafe run work directory")
    return resolved


def remove_project_dir(run: FlowRun) -> tuple[bool, str]:
    project_dir = resolve_project_dir(run)
    if not project_dir.exists():
        return False, str(project_dir)
    if not project_dir.is_dir():
        raise ValueError("run work path is not a directory")
    shutil.rmtree(project_dir)
    return True, str(project_dir)


def _run_output_markdown(run: FlowRun) -> str:
    lines = [
        "# 多智能体流程运行结果",
        "",
        f"- Flow ID: {run.flow_id}",
        f"- Run ID: {run.id}",
        f"- 状态: {run.status}",
        f"- 开始时间: {run.started_at}",
        f"- 结束时间: {run.finished_at or ''}",
    ]
    if run.error:
        lines.append(f"- 错误: {run.error}")
    lines.extend(["", "## 输入", "", run.input_text or ""])

    for output in run.outputs:
        role_id = output.get("role_id") or "unknown"
        lines.extend(["", "---", "", f"## {role_id}", ""])
        if output.get("latency_ms") is not None:
            lines.append(f"- 耗时: {output.get('latency_ms')}ms")
        if output.get("error"):
            lines.append(f"- 错误: {output.get('error')}")
        content = output.get("content") or ""
        # If content is a file reference marker, read the actual content from disk
        if content == "(see file)" and run.project_dir:
            role_file = Path(run.project_dir) / f"role_output_{role_id.replace('/', '--')}.md"
            if role_file.exists():
                content = role_file.read_text(encoding="utf-8")
        lines.extend(["", content])
    return "\n".join(lines).strip() + "\n"


def _run_output_text(run: FlowRun) -> str:
    return _run_output_markdown(run).replace("# ", "").replace("## ", "")


def _run_output_html(run: FlowRun) -> str:
    body = html.escape(_run_output_markdown(run))
    return (
        "<!doctype html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head><meta charset=\"utf-8\"><title>多智能体流程运行结果</title></head>\n"
        "<body><pre style=\"white-space: pre-wrap; font-family: system-ui, sans-serif;\">"
        f"{body}</pre></body>\n</html>\n"
    )


def write_run_output_files(run: FlowRun) -> tuple[int, int]:
    project_dir = resolve_project_dir(run)
    project_dir.mkdir(parents=True, exist_ok=True)
    documents = {
        "run-output.md": _run_output_markdown(run).encode("utf-8"),
        "run-output.txt": _run_output_text(run).encode("utf-8"),
        "run-output.html": _run_output_html(run).encode("utf-8"),
    }
    total_bytes = 0
    for filename, content in documents.items():
        total_bytes += len(content)
        (project_dir / filename).write_bytes(content)

    if shutil.which("pandoc"):
        docx_path = project_dir / "run-output.docx"
        try:
            subprocess.run(
                ["pandoc", str(project_dir / "run-output.md"), "-o", str(docx_path)],
                check=True,
                capture_output=True,
                timeout=60,
            )
            total_bytes += docx_path.stat().st_size
        except (OSError, subprocess.SubprocessError):
            docx_path.unlink(missing_ok=True)

    file_count = len([path for path in project_dir.iterdir() if path.is_file() and path.name.startswith("run-output.")])
    return file_count, total_bytes


def build_artifact_zip(run: FlowRun) -> tuple[bytes, str, int, int]:
    project_dir = resolve_project_dir(run)
    write_run_output_files(run)

    total_bytes = 0
    file_count = 0
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if project_dir.exists() and project_dir.is_dir():
            for path in project_dir.rglob("*"):
                if path.is_symlink() or not path.is_file():
                    continue
                resolved = path.resolve()
                if resolved == project_dir or project_dir not in resolved.parents:
                    continue
                size = resolved.stat().st_size
                total_bytes += size
                file_count += 1
                if total_bytes > RUN_ARTIFACT_ZIP_MAX_BYTES:
                    raise OverflowError("run artifacts exceed max zip size")
                if file_count > RUN_ARTIFACT_ZIP_MAX_FILES:
                    raise OverflowError("run artifacts exceed max file count")
                zf.write(resolved, resolved.relative_to(project_dir).as_posix())

    if file_count == 0:
        raise FileNotFoundError("run artifacts not found")
    filename = f"flow-{run.flow_id}-run-{run.id}-materials.zip"
    return buf.getvalue(), filename, file_count, total_bytes
