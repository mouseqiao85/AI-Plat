"""
核心数据模型
SQLAlchemy ORM模型定义
"""

from datetime import datetime
from typing import Optional, List
import uuid
import json

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Integer, Float,
    JSON, ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .connection import Base


class UserRoleEnum(PyEnum):
    """用户角色枚举"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    GUEST = "guest"


class AgentStatus(PyEnum):
    """代理状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    PENDING = "pending"


class WorkflowStatus(PyEnum):
    """工作流状态枚举"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class MCPServerStatus(PyEnum):
    """MCP服务器状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    OFFLINE = "offline"


class DatasetStatus(PyEnum):
    """数据集状态枚举"""
    DRAFT = "draft"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"


class ModelStatus(PyEnum):
    """模型状态枚举"""
    DRAFT = "draft"
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    ERROR = "error"


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(Text)
    role = Column(String(20), default=UserRoleEnum.GUEST.value, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    ontologies = relationship("Ontology", back_populates="owner", lazy="dynamic")
    agents = relationship("Agent", back_populates="owner", lazy="dynamic")
    workflows = relationship("Workflow", back_populates="owner", lazy="dynamic")
    
    __table_args__ = (
        Index("ix_users_username_email", "username", "email"),
    )
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Ontology(Base):
    """本体表"""
    __tablename__ = "ontologies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    domain = Column(String(100), index=True)
    version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="active")
    entity_count = Column(Integer, default=0)
    relation_count = Column(Integer, default=0)
    schema_definition = Column(JSON, default=dict)
    config = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_public = Column(Boolean, default=False)
    tags = Column(ARRAY(String), default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="ontologies")
    
    __table_args__ = (
        Index("ix_ontologies_name_domain", "name", "domain"),
    )
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "version": self.version,
            "status": self.status,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "is_public": self.is_public,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Agent(Base):
    """代理表"""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    agent_type = Column(String(50), default="skill")
    status = Column(String(20), default=AgentStatus.STOPPED.value)
    skills = Column(ARRAY(String), default=list)
    config = Column(JSON, default=dict)
    capabilities = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_public = Column(Boolean, default=False)
    last_active = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="agents")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status,
            "skills": self.skills,
            "config": self.config,
            "capabilities": self.capabilities,
            "metrics": self.metrics,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "is_public": self.is_public,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Workflow(Base):
    """工作流表"""
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    status = Column(String(20), default=WorkflowStatus.DRAFT.value)
    definition = Column(JSON, default=dict)
    nodes = Column(JSON, default=list)
    edges = Column(JSON, default=list)
    variables = Column(JSON, default=dict)
    schedule = Column(JSON)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_public = Column(Boolean, default=False)
    execution_count = Column(Integer, default=0)
    last_execution = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="workflows")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "nodes": self.nodes,
            "edges": self.edges,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "is_public": self.is_public,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class MCPServer(Base):
    """MCP服务器表"""
    __tablename__ = "mcp_servers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    endpoint = Column(String(500), nullable=False)
    server_type = Column(String(50), default="model")
    status = Column(String(20), default=MCPServerStatus.OFFLINE.value)
    models = Column(ARRAY(String), default=list)
    config = Column(JSON, default=dict)
    credentials = Column(JSON)
    capabilities = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    health_check_interval = Column(Integer, default=60)
    last_health_check = Column(DateTime)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "endpoint": self.endpoint,
            "server_type": self.server_type,
            "status": self.status,
            "models": self.models,
            "capabilities": self.capabilities,
            "metrics": self.metrics,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Dataset(Base):
    """数据集表"""
    __tablename__ = "datasets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    data_type = Column(String(50), index=True)
    format = Column(String(20))
    status = Column(String(20), default=DatasetStatus.DRAFT.value)
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    record_count = Column(BigInteger)
    schema = Column(JSON, default=dict)
    statistics = Column(JSON, default=dict)
    version = Column(String(20), default="1.0.0")
    tags = Column(ARRAY(String), default=list)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "format": self.format,
            "status": self.status,
            "file_size": self.file_size,
            "record_count": self.record_count,
            "version": self.version,
            "tags": self.tags,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Model(Base):
    """模型表"""
    __tablename__ = "models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    model_type = Column(String(50), index=True)
    framework = Column(String(50))
    status = Column(String(20), default=ModelStatus.DRAFT.value)
    version = Column(String(20), default="1.0.0")
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))
    hyperparameters = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    training_config = Column(JSON, default=dict)
    deployment_config = Column(JSON, default=dict)
    endpoint_url = Column(String(500))
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    is_public = Column(Boolean, default=False)
    tags = Column(ARRAY(String), default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "model_type": self.model_type,
            "framework": self.framework,
            "status": self.status,
            "version": self.version,
            "metrics": self.metrics,
            "endpoint_url": self.endpoint_url,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "is_public": self.is_public,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), index=True)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    status = Column(String(20), default="success")
    error_message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


from sqlalchemy import BigInteger
