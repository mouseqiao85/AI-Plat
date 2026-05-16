from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    user_id: int = 0
    conversation_id: int = 0
    skill_name: str = ""
    model: str = ""
    provider: str = ""
    project_dir: str = ""


class StreamEvent(BaseModel):
    type: str  # "text", "done", "error", "tool_call", "tool_result"
    content: str = ""
    tool_name: str = ""
    status: str = ""
    error: str = ""
    done: bool = False


class SkillInfo(BaseModel):
    name: str
    description: str
    category: str = ""
    status: str = "enabled"


class AgentWorkflow(BaseModel):
    name: str
    description: str
    stages: list = []
    estimated_duration: str = ""
