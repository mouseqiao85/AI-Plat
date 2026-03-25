"""
审计日志服务
记录用户操作和系统事件
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .schemas import AuditLogDB
from .database import get_db_session


class AuditService:
    """审计服务"""
    
    ACTION_TYPES = {
        "user.login": "用户登录",
        "user.logout": "用户登出",
        "user.register": "用户注册",
        "user.update": "用户信息更新",
        "user.password_change": "密码修改",
        "user.activate": "用户激活",
        "user.deactivate": "用户停用",
        "role.assign": "角色分配",
        "permission.check": "权限检查",
        "ontology.create": "本体创建",
        "ontology.update": "本体更新",
        "ontology.delete": "本体删除",
        "ontology.query": "本体查询",
        "agent.create": "代理创建",
        "agent.start": "代理启动",
        "agent.stop": "代理停止",
        "agent.execute": "代理执行",
        "model.deploy": "模型部署",
        "model.train": "模型训练",
        "dataset.create": "数据集创建",
        "dataset.upload": "数据集上传",
        "workflow.create": "工作流创建",
        "workflow.execute": "工作流执行",
        "api.access": "API访问",
        "system.config": "系统配置",
        "oauth.login": "OAuth登录",
    }
    
    def __init__(self, db_session: Session = None):
        self.db_session = db_session or get_db_session()
    
    def log(
        self,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """记录审计日志"""
        log_id = uuid.uuid4()
        
        user_uuid = None
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                pass
        
        audit_log = AuditLogDB(
            id=log_id,
            user_id=user_uuid,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        
        self.db_session.add(audit_log)
        self.db_session.commit()
        
        return str(log_id)
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request=None
    ) -> str:
        """记录用户操作日志"""
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
        
        return self.log(
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_api_access(
        self,
        user_id: Optional[str],
        endpoint: str,
        method: str,
        status_code: int,
        request=None
    ) -> str:
        """记录API访问日志"""
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
        
        return self.log(
            action="api.access",
            resource_type="api",
            user_id=user_id,
            resource_id=endpoint,
            details={
                "method": method,
                "status_code": status_code,
                "endpoint": endpoint
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        query = self.db_session.query(AuditLogDB)
        
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                query = query.filter(AuditLogDB.user_id == user_uuid)
            except ValueError:
                pass
        
        if action:
            query = query.filter(AuditLogDB.action == action)
        
        if resource_type:
            query = query.filter(AuditLogDB.resource_type == resource_type)
        
        if start_time:
            query = query.filter(AuditLogDB.created_at >= start_time)
        
        if end_time:
            query = query.filter(AuditLogDB.created_at <= end_time)
        
        logs = query.order_by(desc(AuditLogDB.created_at)).offset(offset).limit(limit).all()
        
        return [self._log_to_dict(log) for log in logs]
    
    def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户活动记录"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        return self.get_logs(
            user_id=user_id,
            start_time=start_time,
            limit=limit
        )
    
    def get_recent_activity(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近活动"""
        return self.get_logs(limit=limit)
    
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取审计统计"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()
        
        logs = self.db_session.query(AuditLogDB).filter(
            AuditLogDB.created_at >= start_time,
            AuditLogDB.created_at <= end_time
        ).all()
        
        action_counts = {}
        resource_counts = {}
        user_counts = {}
        
        for log in logs:
            action = log.action
            resource = log.resource_type
            user_id = str(log.user_id) if log.user_id else "anonymous"
            
            action_counts[action] = action_counts.get(action, 0) + 1
            resource_counts[resource] = resource_counts.get(resource, 0) + 1
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        return {
            "total_events": len(logs),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "by_action": action_counts,
            "by_resource": resource_counts,
            "by_user": user_counts,
            "unique_users": len(user_counts)
        }
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧日志"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        result = self.db_session.query(AuditLogDB).filter(
            AuditLogDB.created_at < cutoff_time
        ).delete()
        
        self.db_session.commit()
        
        return result
    
    def _log_to_dict(self, log: AuditLogDB) -> Dict[str, Any]:
        """转换日志为字典"""
        return {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "action_description": self.ACTION_TYPES.get(log.action, log.action),
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
    
    def _get_client_ip(self, request) -> str:
        """获取客户端IP"""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"
