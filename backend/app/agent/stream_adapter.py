import json
from enum import Enum
from typing import Any


class SSEEventType(str, Enum):
    """SSE event types for the client-facing stream."""
    THINKING = "thinking"
    TEXT = "text"
    TOOL_CALL = "tool_call"
    CARD = "card"
    DONE = "done"
    ERROR = "error"
    PING = "ping"
    NOTICE = "notice"          # skill 依赖/账号提示
    CONVERSATION_ID = "conversation_id"  # 告知前端当前对话 ID
    CONVERSATION_TITLE = "conversation_title"  # 告知前端对话标题已更新
    FILE_DOWNLOAD = "file_download"  # 超长报告/HTML 生成文件下载
    COMPACT_START = "compact_start"  # 开始压缩对话历史
    COMPACT_DONE = "compact_done"   # 压缩完成
    PLAN_CREATED = "plan_created"    # 执行计划已创建
    PLAN_STEP_UPDATE = "plan_step_update"  # 计划步骤状态变更
    WORKER_STARTED = "worker_started"   # 子任务启动
    WORKER_PROGRESS = "worker_progress" # 子任务进展
    WORKER_DONE = "worker_done"        # 子任务完成


def format_sse_event(event_type: SSEEventType, data: Any) -> str:
    """Format an SSE event string.

    Returns a string in the format:
        event: {type}\\n data: {json}\\n\\n
    """
    payload = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return f"event: {event_type.value}\ndata: {payload}\n\n"
