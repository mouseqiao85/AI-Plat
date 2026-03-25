"""
AI-Plat Platform Types
TypeScript-style type definitions for Python
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OntologyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class MCPConnectionStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class ModelCategory(str, Enum):
    PRETRAINED = "pretrained"
    FINE_TUNED = "fine_tuned"
    CUSTOM = "custom"


class SkillCategory(str, Enum):
    DATA_PROCESSING = "data_processing"
    ML_MODEL = "ml_model"
    TEXT_GENERATION = "text_generation"
    IMAGE_PROCESSING = "image_processing"
    WORKFLOW = "workflow"
    UTILITY = "utility"


@dataclass
class OntologyEntity:
    id: str
    name: str
    entity_type: str
    label: Optional[str] = None
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    relations: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OntologyInfo:
    id: str
    name: str
    description: Optional[str] = None
    entities: int = 0
    relations: int = 0
    status: OntologyStatus = OntologyStatus.ACTIVE
    created_at: Optional[datetime] = None


@dataclass
class AgentInfo:
    id: str
    name: str
    description: Optional[str] = None
    status: AgentStatus = AgentStatus.STOPPED
    skills: List[str] = field(default_factory=list)
    tasks_completed: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    uptime_seconds: int = 0
    created_at: Optional[datetime] = None


@dataclass
class TaskInfo:
    id: str
    name: str
    description: Optional[str] = None
    agent_id: str
    skill_id: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class MCPConnection:
    id: str
    name: str
    endpoint: str
    status: MCPConnectionStatus = MCPConnectionStatus.UNKNOWN
    response_time_ms: int = 0
    total_calls: int = 0
    availability: float = 0.0
    models: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class ModelAsset:
    id: str
    name: str
    description: Optional[str] = None
    category: ModelCategory = ModelCategory.PRETRAINED
    framework: str = "unknown"
    version: str = "1.0.0"
    rating: float = 0.0
    total_calls: str = "0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class DatasetAsset:
    id: str
    name: str
    description: Optional[str] = None
    data_type: str = "unknown"
    format: str = "unknown"
    size: str = "0B"
    records: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class SkillInfo:
    id: str
    name: str
    description: Optional[str] = None
    category: SkillCategory = SkillCategory.UTILITY
    version: str = "1.0.0"
    author: str = "unknown"
    parameters: Dict[str, Any] = field(default_factory=dict)
    return_type: str = "Any"


@dataclass
class WorkflowStep:
    id: str
    name: str
    agent_id: str
    skill_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None


@dataclass
class Workflow:
    id: str
    name: str
    description: Optional[str] = None
    steps: List[WorkflowStep] = field(default_factory=list)
    status: str = "created"
    created_at: Optional[datetime] = None


@dataclass
class DashboardMetrics:
    roi_current: float = 0.0
    roi_change: float = 0.0
    tasks_completed: int = 0
    tasks_pending: int = 0
    tasks_running: int = 0
    success_rate: float = 0.0
    agents_total: int = 0
    agents_running: int = 0
    api_calls_today: int = 0
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0


@dataclass
class PlatformStatus:
    platform_id: str
    version: str
    status: str
    uptime: int
    modules: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]
