"""
认证API路由
FastAPI路由定义
支持OAuth2、审计日志、权限管理
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import secrets

from .models import (
    User, UserCreate, Token, LoginRequest, RegisterRequest,
    PasswordChangeRequest, PasswordResetRequest, UserUpdate, Permission, Role
)
from .service import AuthService, AuthenticationError, AuthorizationError, UserNotFoundError
from .dependencies import get_current_user, get_current_active_user, require_admin
from .oauth_service import OAuthService
from .permission_service import PermissionService
from .audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2密码承载令牌方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    auth_service: AuthService = Depends()
):
    """用户注册"""
    try:
        user = auth_service.register_user(user_create)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    login_request: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends()
):
    """用户登录"""
    try:
        user = auth_service.authenticate_user(
            login_request.username, 
            login_request.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户账户已停用"
            )
        
        # 创建访问令牌和刷新令牌
        access_token = auth_service.create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role
            }
        )
        
        refresh_token = auth_service.create_refresh_token(str(user.id))
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30分钟
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends()
):
    """OAuth2兼容登录（表单）"""
    try:
        user = auth_service.authenticate_user(
            form_data.username,
            form_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户账户已停用"
            )
        
        # 创建访问令牌
        access_token = auth_service.create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role
            }
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends()
):
    """刷新访问令牌"""
    try:
        access_token = auth_service.refresh_access_token(refresh_token)
        
        return Token(
            access_token=access_token,
            token_type="bearer"
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新令牌失败: {str(e)}"
        )


@router.post("/logout")
async def logout(
    refresh_token: str,
    auth_service: AuthService = Depends()
):
    """用户登出"""
    success = auth_service.logout(refresh_token)
    
    if success:
        return {"message": "登出成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="登出失败，刷新令牌无效"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return current_user


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends()
):
    """更新当前用户信息"""
    try:
        updated_user = auth_service.update_user(
            str(current_user.id),
            user_update.dict(exclude_unset=True)
        )
        
        if not updated_user:
            raise UserNotFoundError("用户未找到")
        
        return updated_user
        
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户信息失败: {str(e)}"
        )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends()
):
    """修改当前用户密码"""
    success = auth_service.change_password(
        str(current_user.id),
        password_change.current_password,
        password_change.new_password
    )
    
    if success:
        return {"message": "密码修改成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误或用户不存在"
        )


@router.post("/password-reset/request")
async def request_password_reset(
    password_reset: PasswordResetRequest,
    auth_service: AuthService = Depends()
):
    """请求密码重置（发送重置邮件）"""
    # TODO: 实现密码重置邮件发送逻辑
    return {
        "message": "密码重置请求已受理",
        "email": password_reset.email,
        "note": "密码重置功能正在开发中"
    }


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    token: str,
    new_password: str,
    auth_service: AuthService = Depends()
):
    """确认密码重置"""
    # TODO: 实现密码重置确认逻辑
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="密码重置功能正在开发中"
    )


@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends()
):
    """获取用户列表（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    users = auth_service.list_users()
    
    return {
        "users": users,
        "count": len(users)
    }


@router.get("/users/{user_id}", response_model=User)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends()
):
    """根据ID获取用户信息（需要管理员权限）"""
    # 检查权限
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    user = auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )
    
    return user


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends()
):
    """激活用户（需要管理员权限）"""
    # 检查权限
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    success = auth_service.activate_user(user_id)
    
    if success:
        return {"message": "用户激活成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends()
):
    """停用用户（需要管理员权限）"""
    # 检查权限
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    success = auth_service.deactivate_user(user_id)
    
    if success:
        return {"message": "用户停用成功"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )


@router.get("/validate-token")
async def validate_token(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends()
):
    """验证令牌有效性"""
    try:
        token_data = auth_service.verify_token(token)
        return {
            "valid": True,
            "user_id": token_data.user_id,
            "username": token_data.username,
            "role": token_data.role
        }
    except AuthenticationError as e:
        return {
            "valid": False,
            "error": str(e)
        }


@router.get("/health")
async def auth_health_check():
    """认证系统健康检查"""
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }


# ==================== OAuth2 路由 ====================

oauth_states = {}


@router.get("/oauth/providers")
async def get_oauth_providers():
    """获取可用的OAuth提供者"""
    oauth_service = OAuthService()
    providers = oauth_service.get_available_providers()
    return {
        "providers": providers,
        "count": len(providers)
    }


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(provider: str, redirect_uri: Optional[str] = None):
    """获取OAuth授权URL"""
    oauth_service = OAuthService()
    
    if provider not in oauth_service.get_available_providers():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的OAuth提供者: {provider}"
        )
    
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri
    }
    
    auth_url = oauth_service.get_authorization_url(provider, state)
    
    return {
        "authorization_url": auth_url,
        "state": state
    }


@router.get("/oauth/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...)
):
    """处理OAuth回调"""
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的state参数"
        )
    
    stored_state = oauth_states.pop(state)
    if stored_state["provider"] != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider不匹配"
        )
    
    try:
        oauth_service = OAuthService()
        result = await oauth_service.handle_callback(provider, code)
        
        audit_service = AuditService()
        audit_service.log(
            action="oauth.login",
            resource_type="user",
            user_id=result["user"]["id"],
            details={"provider": provider}
        )
        
        return Token(
            access_token=result["access_token"],
            token_type=result["token_type"],
            refresh_token=result.get("refresh_token")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OAuth认证失败: {str(e)}"
        )


# ==================== 权限管理路由 ====================

@router.get("/permissions", response_model=List[Permission])
async def list_permissions(
    current_user: User = Depends(require_admin)
):
    """获取所有权限列表（管理员）"""
    permission_service = PermissionService()
    return permission_service.get_all_permissions()


@router.get("/roles", response_model=List[Role])
async def list_roles(
    current_user: User = Depends(require_admin)
):
    """获取所有角色列表（管理员）"""
    permission_service = PermissionService()
    return permission_service.get_all_roles()


@router.post("/roles")
async def create_role(
    name: str,
    description: str = "",
    permissions: List[str] = None,
    current_user: User = Depends(require_admin)
):
    """创建角色（管理员）"""
    permission_service = PermissionService()
    role = permission_service.create_role(name, description, permissions)
    
    audit_service = AuditService()
    audit_service.log_user_action(
        user_id=str(current_user.id),
        action="role.assign",
        resource_type="role",
        resource_id=name,
        details={"permissions": permissions}
    )
    
    return {"message": "角色创建成功", "role": role.dict()}


@router.post("/users/{user_id}/role")
async def assign_user_role(
    user_id: str,
    role_name: str,
    current_user: User = Depends(require_admin)
):
    """为用户分配角色（管理员）"""
    permission_service = PermissionService()
    success = permission_service.assign_role_to_user(user_id, role_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色分配失败"
        )
    
    audit_service = AuditService()
    audit_service.log_user_action(
        user_id=str(current_user.id),
        action="role.assign",
        resource_type="user",
        resource_id=user_id,
        details={"role": role_name}
    )
    
    return {"message": "角色分配成功"}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取用户权限列表"""
    if str(current_user.id) != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    
    permission_service = PermissionService()
    permissions = permission_service.get_user_permissions(user_id)
    
    return {
        "user_id": user_id,
        "permissions": permissions,
        "count": len(permissions)
    }


# ==================== 审计日志路由 ====================

@router.get("/audit/logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin)
):
    """获取审计日志（管理员）"""
    from datetime import datetime, timedelta
    
    audit_service = AuditService()
    start_time = datetime.utcnow() - timedelta(days=days)
    
    logs = audit_service.get_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_time=start_time,
        limit=limit,
        offset=offset
    )
    
    return {
        "logs": logs,
        "count": len(logs)
    }


@router.get("/audit/statistics")
async def get_audit_statistics(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(require_admin)
):
    """获取审计统计（管理员）"""
    from datetime import datetime, timedelta
    
    audit_service = AuditService()
    start_time = datetime.utcnow() - timedelta(days=days)
    
    stats = audit_service.get_statistics(start_time=start_time)
    
    return stats


@router.get("/audit/my-activity")
async def get_my_activity(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户活动记录"""
    audit_service = AuditService()
    logs = audit_service.get_user_activity(
        user_id=str(current_user.id),
        days=days,
        limit=limit
    )
    
    return {
        "user_id": str(current_user.id),
        "logs": logs,
        "count": len(logs)
    }