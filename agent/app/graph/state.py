from typing import TypedDict, Annotated, List, Optional, Any
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str
    user_id: int
    conversation_id: int
    intent: str
    plan: Optional[List[dict]]
    current_step: int
    tool_results: Optional[List[dict]]
    retrieved_docs: Optional[List[dict]]
    context: Optional[dict]
    feedback: Optional[dict]
    safety_passed: bool
    approved: bool
    retry_count: int
    degraded_steps: Optional[List[dict]]
    error: Optional[str]
    response: Optional[str]
    provider_id: str
    model: str
    available_tools: Optional[List[dict]]
    reasoning_content: Optional[str]
    is_deepseek: bool
    # Phase 1: Skill system
    skill_tools: Optional[List[dict]]
    active_skill: Optional[str]
    tool_call_history: Optional[List[dict]]
    # Phase 2: Tool loop enhancement
    iteration_count: int
    tool_call_log: Optional[List[dict]]
    # Phase 3: Orchestrator-Worker
    needs_workers: bool
    worker_results: Optional[List[dict]]
    plan_steps: Optional[List[dict]]
    # Phase 4: Long-term memory
    user_profile_str: Optional[str]
    # Phase 5: Session lifecycle management (optional, used when session_manager is enabled)
    timeout_at: Optional[float]
    pid: Optional[int]
    child_pids: Optional[List[int]]
