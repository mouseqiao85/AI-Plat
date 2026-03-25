"""
FastAPI依赖项
用于认证和授权
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import User
from .service import AuthService, AuthenticationError

# HTTP承载令牌方案
security = HTTPBearer()


async def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    return AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """获取当前用户（依赖注入）"""
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    try:
        # 验证令牌
        token_data = auth_service.verify_token(token)
        
        if token_data.user_id is None:
            return None
        
        # 获取用户信息
        user = auth_service.get_user_by_id(token_data.user_id)
        
        if user is None:
            return None
        
        return user
        
    except AuthenticationError:
        return None
    except Exception:
        return None


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """获取当前活跃用户（依赖注入）"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证或认证无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已停用"
        )
    
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """要求管理员权限（依赖注入）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    return current_user


async def require_developer(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """要求开发者权限（依赖注入）"""
    if current_user.role not in ["admin", "developer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要开发者权限"
        )
    
    return current_user


async def require_analyst(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """要求分析师权限（依赖注入）"""
    if current_user.role not in ["admin", "developer", "analyst"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要分析师权限"
        )
    
    return current_user


async def check_permission(
    resource: str,
    action: str,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """检查特定权限（依赖注入）"""
    has_permission = auth_service.check_permission(
        str(current_user.id),
        resource,
        action
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少权限: {action} on {resource}"
        )
    
    return current_user


class PermissionChecker:
    """权限检查器类"""
    
    def __init__(self, required_permissions: list):
        self.required_permissions = required_permissions
    
    def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        """检查多个权限"""
        user_permissions = auth_service.get_user_permissions(str(current_user.id))
        
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"缺少权限: {permission}"
                )
        
        return current_user


def create_permission_dependency(resource: str, action: str):
    """创建权限依赖项工厂函数"""
    
    async def permission_dependency(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        has_permission = auth_service.check_permission(
            str(current_user.id),
            resource,
            action
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {action} on {resource}"
            )
        
        return current_user
    
    return permission_dependency


# 常用权限依赖项
require_ontology_read = create_permission_dependency("ontology", "read")
require_ontology_write = create_permission_dependency("ontology", "write")
require_agents_manage = create_permission_dependency("agents", "manage")
require_models_deploy = create_permission_dependency("models", "deploy")
require_system_admin = create_permission_dependency("system", "admin")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """获取可选的当前用户（依赖注入）"""
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    try:
        # 验证令牌
        token_data = auth_service.verify_token(token)
        
        if token_data.user_id is None:
            return None
        
        # 获取用户信息
        user = auth_service.get_user_by_id(token_data.user_id)
        
        return user
        
    except AuthenticationError:
        return None
    except Exception:
        return None