"""
数据仓库层
封装数据库CRUD操作
"""

from typing import Optional, List, Dict, Any, Type, TypeVar, Generic
from datetime import datetime
import uuid
import logging

from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import SQLAlchemyError

from .connection import get_db_session
from .models import (
    Base, User, Ontology, Agent, Workflow,
    MCPServer, Dataset, Model, AuditLog
)
from .cache import get_cache, CacheService

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """基础仓库"""
    
    model: Type[T] = None
    cache_namespace: str = None
    
    def __init__(self, db: Session = None, cache: CacheService = None):
        self.db = db or get_db_session()
        self.cache = cache or get_cache()
    
    def get_by_id(self, id: str) -> Optional[T]:
        """根据ID获取"""
        cache_key = f"id:{id}"
        cached = self.cache.get(cache_key, self.cache_namespace)
        if cached:
            return self.model(**cached)
        
        try:
            obj = self.db.query(self.model).filter(
                self.model.id == uuid.UUID(id)
            ).first()
            
            if obj:
                self.cache.set(
                    cache_key,
                    obj.to_dict(),
                    ttl=300,
                    namespace=self.cache_namespace
                )
            return obj
        except SQLAlchemyError as e:
            logger.error(f"获取{self.model.__name__}失败: {e}")
            return None
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] = None
    ) -> List[T]:
        """获取所有"""
        query = self.db.query(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, obj_in: Dict[str, Any]) -> T:
        """创建"""
        try:
            if "id" not in obj_in:
                obj_in["id"] = uuid.uuid4()
            elif isinstance(obj_in["id"], str):
                obj_in["id"] = uuid.UUID(obj_in["id"])
            
            obj = self.model(**obj_in)
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            
            cache_key = f"id:{obj.id}"
            self.cache.set(
                cache_key,
                obj.to_dict(),
                ttl=300,
                namespace=self.cache_namespace
            )
            
            return obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"创建{self.model.__name__}失败: {e}")
            raise
    
    def update(self, id: str, obj_in: Dict[str, Any]) -> Optional[T]:
        """更新"""
        try:
            obj = self.get_by_id(id)
            if not obj:
                return None
            
            for key, value in obj_in.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            
            setattr(obj, "updated_at", datetime.utcnow())
            self.db.commit()
            self.db.refresh(obj)
            
            cache_key = f"id:{id}"
            self.cache.set(
                cache_key,
                obj.to_dict(),
                ttl=300,
                namespace=self.cache_namespace
            )
            
            return obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"更新{self.model.__name__}失败: {e}")
            raise
    
    def delete(self, id: str) -> bool:
        """删除"""
        try:
            obj = self.get_by_id(id)
            if not obj:
                return False
            
            self.db.delete(obj)
            self.db.commit()
            
            cache_key = f"id:{id}"
            self.cache.delete(cache_key, namespace=self.cache_namespace)
            
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"删除{self.model.__name__}失败: {e}")
            raise
    
    def count(self, filters: Dict[str, Any] = None) -> int:
        """计数"""
        query = self.db.query(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.count()


class UserRepository(BaseRepository[User]):
    """用户仓库"""
    
    model = User
    cache_namespace = "users"
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取"""
        cache_key = f"username:{username}"
        cached = self.cache.get(cache_key, self.cache_namespace)
        if cached:
            return User(**cached)
        
        user = self.db.query(User).filter(User.username == username).first()
        if user:
            self.cache.set(cache_key, user.to_dict(), ttl=300, namespace=self.cache_namespace)
        return user
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取"""
        cache_key = f"email:{email}"
        cached = self.cache.get(cache_key, self.cache_namespace)
        if cached:
            return User(**cached)
        
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            self.cache.set(cache_key, user.to_dict(), ttl=300, namespace=self.cache_namespace)
        return user
    
    def get_active_users(self) -> List[User]:
        """获取活跃用户"""
        return self.db.query(User).filter(User.is_active == True).all()
    
    def get_by_role(self, role: str) -> List[User]:
        """根据角色获取用户"""
        return self.db.query(User).filter(User.role == role).all()


class OntologyRepository(BaseRepository[Ontology]):
    """本体仓库"""
    
    model = Ontology
    cache_namespace = "ontologies"
    
    def get_by_name(self, name: str, owner_id: str = None) -> Optional[Ontology]:
        """根据名称获取"""
        query = self.db.query(Ontology).filter(Ontology.name == name)
        if owner_id:
            query = query.filter(Ontology.owner_id == uuid.UUID(owner_id))
        return query.first()
    
    def get_by_domain(self, domain: str) -> List[Ontology]:
        """根据领域获取"""
        return self.db.query(Ontology).filter(Ontology.domain == domain).all()
    
    def get_public(self) -> List[Ontology]:
        """获取公开本体"""
        return self.db.query(Ontology).filter(Ontology.is_public == True).all()
    
    def search(self, keyword: str, limit: int = 20) -> List[Ontology]:
        """搜索本体"""
        return self.db.query(Ontology).filter(
            Ontology.name.ilike(f"%{keyword}%") |
            Ontology.description.ilike(f"%{keyword}%")
        ).limit(limit).all()


class AgentRepository(BaseRepository[Agent]):
    """代理仓库"""
    
    model = Agent
    cache_namespace = "agents"
    
    def get_by_status(self, status: str) -> List[Agent]:
        """根据状态获取"""
        return self.db.query(Agent).filter(Agent.status == status).all()
    
    def get_running(self) -> List[Agent]:
        """获取运行中的代理"""
        return self.db.query(Agent).filter(Agent.status == "running").all()
    
    def get_by_skill(self, skill_id: str) -> List[Agent]:
        """根据技能获取代理"""
        return self.db.query(Agent).filter(
            Agent.skills.contains([skill_id])
        ).all()


class WorkflowRepository(BaseRepository[Workflow]):
    """工作流仓库"""
    
    model = Workflow
    cache_namespace = "workflows"
    
    def get_active(self) -> List[Workflow]:
        """获取活跃工作流"""
        return self.db.query(Workflow).filter(Workflow.status == "active").all()
    
    def get_by_status(self, status: str) -> List[Workflow]:
        """根据状态获取"""
        return self.db.query(Workflow).filter(Workflow.status == status).all()


class MCPServerRepository(BaseRepository[MCPServer]):
    """MCP服务器仓库"""
    
    model = MCPServer
    cache_namespace = "mcp_servers"
    
    def get_healthy(self) -> List[MCPServer]:
        """获取健康的服务器"""
        return self.db.query(MCPServer).filter(
            MCPServer.status == "healthy"
        ).all()
    
    def get_by_type(self, server_type: str) -> List[MCPServer]:
        """根据类型获取"""
        return self.db.query(MCPServer).filter(
            MCPServer.server_type == server_type
        ).all()


class DatasetRepository(BaseRepository[Dataset]):
    """数据集仓库"""
    
    model = Dataset
    cache_namespace = "datasets"
    
    def get_by_type(self, data_type: str) -> List[Dataset]:
        """根据类型获取"""
        return self.db.query(Dataset).filter(Dataset.data_type == data_type).all()
    
    def get_ready(self) -> List[Dataset]:
        """获取就绪的数据集"""
        return self.db.query(Dataset).filter(Dataset.status == "ready").all()


class ModelRepository(BaseRepository[Model]):
    """模型仓库"""
    
    model = Model
    cache_namespace = "models"
    
    def get_deployed(self) -> List[Model]:
        """获取已部署的模型"""
        return self.db.query(Model).filter(Model.status == "deployed").all()
    
    def get_by_framework(self, framework: str) -> List[Model]:
        """根据框架获取"""
        return self.db.query(Model).filter(Model.framework == framework).all()
    
    def get_by_type(self, model_type: str) -> List[Model]:
        """根据类型获取"""
        return self.db.query(Model).filter(Model.model_type == model_type).all()


class AuditLogRepository(BaseRepository[AuditLog]):
    """审计日志仓库"""
    
    model = AuditLog
    cache_namespace = "audit_logs"
    
    def get_by_user(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """获取用户日志"""
        return self.db.query(AuditLog).filter(
            AuditLog.user_id == uuid.UUID(user_id)
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def get_by_action(self, action: str, limit: int = 100) -> List[AuditLog]:
        """根据操作获取日志"""
        return self.db.query(AuditLog).filter(
            AuditLog.action == action
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def get_recent(self, hours: int = 24, limit: int = 100) -> List[AuditLog]:
        """获取最近日志"""
        from datetime import timedelta
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(AuditLog).filter(
            AuditLog.created_at >= start_time
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    def create_log(
        self,
        action: str,
        resource_type: str,
        user_id: str = None,
        resource_id: str = None,
        details: dict = None,
        ip_address: str = None
    ) -> AuditLog:
        """创建审计日志"""
        return self.create({
            "user_id": uuid.UUID(user_id) if user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "ip_address": ip_address
        })
