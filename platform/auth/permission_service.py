"""
权限管理服务
实现基于角色的访问控制 (RBAC)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

from .schemas import PermissionDB, RoleDB, RolePermissionDB, UserRoleDB
from .models import Permission, Role, UserRole
from .database import get_db_session


class PermissionService:
    """权限服务"""
    
    DEFAULT_PERMISSIONS = [
        {"name": "ontology:read", "resource": "ontology", "action": "read", "description": "查看本体"},
        {"name": "ontology:write", "resource": "ontology", "action": "write", "description": "编辑本体"},
        {"name": "ontology:delete", "resource": "ontology", "action": "delete", "description": "删除本体"},
        {"name": "agents:read", "resource": "agents", "action": "read", "description": "查看代理"},
        {"name": "agents:manage", "resource": "agents", "action": "manage", "description": "管理代理"},
        {"name": "models:read", "resource": "models", "action": "read", "description": "查看模型"},
        {"name": "models:deploy", "resource": "models", "action": "deploy", "description": "部署模型"},
        {"name": "datasets:read", "resource": "datasets", "action": "read", "description": "查看数据集"},
        {"name": "datasets:write", "resource": "datasets", "action": "write", "description": "编辑数据集"},
        {"name": "workflows:read", "resource": "workflows", "action": "read", "description": "查看工作流"},
        {"name": "workflows:execute", "resource": "workflows", "action": "execute", "description": "执行工作流"},
        {"name": "vibecoding:use", "resource": "vibecoding", "action": "use", "description": "使用Vibecoding"},
        {"name": "mcp:read", "resource": "mcp", "action": "read", "description": "查看MCP连接"},
        {"name": "mcp:manage", "resource": "mcp", "action": "manage", "description": "管理MCP连接"},
        {"name": "system:admin", "resource": "system", "action": "admin", "description": "系统管理"},
        {"name": "users:read", "resource": "users", "action": "read", "description": "查看用户"},
        {"name": "users:manage", "resource": "users", "action": "manage", "description": "管理用户"},
        {"name": "audit:read", "resource": "audit", "action": "read", "description": "查看审计日志"},
    ]
    
    DEFAULT_ROLES = {
        "admin": {
            "description": "系统管理员，拥有所有权限",
            "permissions": ["*"]
        },
        "developer": {
            "description": "开发人员，可以管理本体、代理和模型",
            "permissions": [
                "ontology:read", "ontology:write",
                "agents:read", "agents:manage",
                "models:read", "models:deploy",
                "datasets:read", "datasets:write",
                "workflows:read", "workflows:execute",
                "vibecoding:use",
                "mcp:read", "mcp:manage"
            ]
        },
        "analyst": {
            "description": "业务分析师，可以查看和使用平台资源",
            "permissions": [
                "ontology:read",
                "agents:read",
                "models:read",
                "datasets:read",
                "workflows:read", "workflows:execute",
                "vibecoding:use",
                "mcp:read"
            ]
        },
        "guest": {
            "description": "访客，只能查看公开资源",
            "permissions": [
                "ontology:read",
                "agents:read",
                "models:read"
            ]
        }
    }
    
    def __init__(self, db_session: Session = None):
        self.db_session = db_session or get_db_session()
    
    def initialize_permissions(self) -> None:
        """初始化默认权限"""
        for perm_data in self.DEFAULT_PERMISSIONS:
            existing = self.db_session.query(PermissionDB).filter(
                PermissionDB.name == perm_data["name"]
            ).first()
            
            if not existing:
                permission = PermissionDB(
                    id=uuid.uuid4(),
                    name=perm_data["name"],
                    resource=perm_data["resource"],
                    action=perm_data["action"],
                    description=perm_data.get("description", "")
                )
                self.db_session.add(permission)
        
        self.db_session.commit()
    
    def initialize_roles(self) -> None:
        """初始化默认角色"""
        for role_name, role_data in self.DEFAULT_ROLES.items():
            existing = self.db_session.query(RoleDB).filter(
                RoleDB.name == role_name
            ).first()
            
            if not existing:
                role = RoleDB(
                    id=uuid.uuid4(),
                    name=role_name,
                    description=role_data.get("description", "")
                )
                self.db_session.add(role)
                self.db_session.flush()
                
                for perm_name in role_data.get("permissions", []):
                    if perm_name == "*":
                        permissions = self.db_session.query(PermissionDB).all()
                        for perm in permissions:
                            rp = RolePermissionDB(
                                id=uuid.uuid4(),
                                role_id=role.id,
                                permission_id=perm.id
                            )
                            self.db_session.add(rp)
                    else:
                        perm = self.db_session.query(PermissionDB).filter(
                            PermissionDB.name == perm_name
                        ).first()
                        if perm:
                            rp = RolePermissionDB(
                                id=uuid.uuid4(),
                                role_id=role.id,
                                permission_id=perm.id
                            )
                            self.db_session.add(rp)
        
        self.db_session.commit()
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户的所有权限"""
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        
        user_role = self.db_session.query(UserRoleDB).filter(
            UserRoleDB.user_id == user_uuid
        ).first()
        
        if not user_role:
            user = self.get_user_by_id(user_id)
            if user:
                role_name = user.role if isinstance(user.role, str) else user.role.value
                role = self.db_session.query(RoleDB).filter(
                    RoleDB.name == role_name
                ).first()
                if role:
                    user_role = UserRoleDB(
                        id=uuid.uuid4(),
                        user_id=user_uuid,
                        role_id=role.id
                    )
                    self.db_session.add(user_role)
                    self.db_session.commit()
        
        if not user_role:
            return []
        
        role_permissions = self.db_session.query(RolePermissionDB).filter(
            RolePermissionDB.role_id == user_role.role_id
        ).all()
        
        permissions = []
        for rp in role_permissions:
            perm = self.db_session.query(PermissionDB).filter(
                PermissionDB.id == rp.permission_id
            ).first()
            if perm:
                permissions.append(perm.name)
        
        return permissions
    
    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户是否有指定权限"""
        permissions = self.get_user_permissions(user_id)
        
        if "*" in permissions:
            return True
        
        required_permission = f"{resource}:{action}"
        wildcard_permission = f"{resource}:*"
        
        return required_permission in permissions or wildcard_permission in permissions
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """为用户分配角色"""
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        
        role = self.db_session.query(RoleDB).filter(
            RoleDB.name == role_name
        ).first()
        
        if not role:
            return False
        
        existing = self.db_session.query(UserRoleDB).filter(
            UserRoleDB.user_id == user_uuid
        ).first()
        
        if existing:
            existing.role_id = role.id
        else:
            user_role = UserRoleDB(
                id=uuid.uuid4(),
                user_id=user_uuid,
                role_id=role.id
            )
            self.db_session.add(user_role)
        
        self.db_session.commit()
        return True
    
    def create_permission(self, name: str, resource: str, action: str, description: str = "") -> Permission:
        """创建新权限"""
        existing = self.db_session.query(PermissionDB).filter(
            PermissionDB.name == name
        ).first()
        
        if existing:
            return Permission(**{
                "name": existing.name,
                "resource": existing.resource,
                "action": existing.action,
                "description": existing.description
            })
        
        permission = PermissionDB(
            id=uuid.uuid4(),
            name=name,
            resource=resource,
            action=action,
            description=description
        )
        self.db_session.add(permission)
        self.db_session.commit()
        
        return Permission(name=name, resource=resource, action=action, description=description)
    
    def create_role(self, name: str, description: str = "", permissions: List[str] = None) -> Role:
        """创建新角色"""
        existing = self.db_session.query(RoleDB).filter(
            RoleDB.name == name
        ).first()
        
        if existing:
            return Role(name=name, description=existing.description, permissions=[])
        
        role = RoleDB(
            id=uuid.uuid4(),
            name=name,
            description=description
        )
        self.db_session.add(role)
        self.db_session.flush()
        
        if permissions:
            for perm_name in permissions:
                perm = self.db_session.query(PermissionDB).filter(
                    PermissionDB.name == perm_name
                ).first()
                if perm:
                    rp = RolePermissionDB(
                        id=uuid.uuid4(),
                        role_id=role.id,
                        permission_id=perm.id
                    )
                    self.db_session.add(rp)
        
        self.db_session.commit()
        
        return Role(name=name, description=description, permissions=[])
    
    def get_all_permissions(self) -> List[Permission]:
        """获取所有权限"""
        permissions = self.db_session.query(PermissionDB).all()
        return [
            Permission(
                name=p.name,
                resource=p.resource,
                action=p.action,
                description=p.description
            )
            for p in permissions
        ]
    
    def get_all_roles(self) -> List[Role]:
        """获取所有角色"""
        roles = self.db_session.query(RoleDB).all()
        result = []
        for r in roles:
            role_perms = self.db_session.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == r.id
            ).all()
            
            perms = []
            for rp in role_perms:
                perm = self.db_session.query(PermissionDB).filter(
                    PermissionDB.id == rp.permission_id
                ).first()
                if perm:
                    perms.append(Permission(
                        name=perm.name,
                        resource=perm.resource,
                        action=perm.action,
                        description=perm.description
                    ))
            
            result.append(Role(name=r.name, description=r.description, permissions=perms))
        
        return result
    
    def get_user_by_id(self, user_id: str):
        """获取用户"""
        from .schemas import UserDB
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        return self.db_session.query(UserDB).filter(UserDB.id == user_uuid).first()
