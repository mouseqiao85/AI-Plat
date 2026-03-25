"""
数据库模块
AI-Plat平台数据持久化层
"""

__version__ = "1.0.0"

from .connection import DatabaseManager, get_db, get_db_session, engine, SessionLocal
from .models import Base, User, Ontology, Agent, Workflow, MCPServer, Dataset, Model, AuditLog
from .cache import CacheService, get_cache
from .repository import (
    UserRepository, OntologyRepository, AgentRepository,
    WorkflowRepository, MCPServerRepository, DatasetRepository, ModelRepository
)

__all__ = [
    "DatabaseManager", "get_db", "get_db_session", "engine", "SessionLocal",
    "Base", "User", "Ontology", "Agent", "Workflow", "MCPServer", "Dataset", "Model", "AuditLog",
    "CacheService", "get_cache",
    "UserRepository", "OntologyRepository", "AgentRepository",
    "WorkflowRepository", "MCPServerRepository", "DatasetRepository", "ModelRepository"
]
