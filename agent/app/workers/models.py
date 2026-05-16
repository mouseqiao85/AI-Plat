"""Worker and orchestrator result models."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WorkerConfig:
    """Configuration for a worker instance."""
    task_description: str
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    max_iterations: int = 3
    worker_id: int = 0


@dataclass
class WorkerResult:
    """Result from a worker execution."""
    worker_id: int
    task_description: str
    success: bool = False
    result: Any = None
    error: Optional[str] = None
    iterations_used: int = 0
    tool_calls: list = field(default_factory=list)
