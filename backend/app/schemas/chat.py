from typing import Optional, List, Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    skill_name: Optional[str] = None
    provider_id: Optional[str] = None
    model: Optional[str] = None


class ToolCallInfo(BaseModel):
    id: str
    name: str
    input: dict


class SSEEvent(BaseModel):
    """SSE event sent to frontend."""
    event: str  # thinking, text, tool_call, card, done, error
    data: Any = None
