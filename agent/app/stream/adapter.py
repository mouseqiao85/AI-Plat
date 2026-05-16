"""SSE event type definitions and formatting utilities."""
import json
from enum import Enum
from typing import Any


class SSEEventType(str, Enum):
    # Existing
    THINKING = "thinking"
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"
    PING = "ping"
    NOTICE = "notice"
    CONVERSATION_ID = "conversation_id"
    CONVERSATION_TITLE = "conversation_title"
    PLAN_CREATED = "plan_created"
    PLAN_STEP_UPDATE = "plan_step_update"
    # Phase 2: Tool loop
    COMPACT_START = "compact_start"
    COMPACT_DONE = "compact_done"
    # Phase 3: Workers
    WORKER_STARTED = "worker_started"
    WORKER_PROGRESS = "worker_progress"
    WORKER_DONE = "worker_done"
    # Phase 5: File generation
    FILE_DOWNLOAD = "file_download"
    # Structured data
    CARD = "card"


def format_sse_event(event_type: SSEEventType, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return f"event: {event_type.value}\ndata: {payload}\n\n"
