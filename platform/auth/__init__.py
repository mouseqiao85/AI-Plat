"""
认证系统模块
AI-Plat平台用户认证和授权
支持JWT、OAuth2、RBAC权限管理、审计日志
"""

__version__ = "1.0.0"

from .models import (
    User, UserCreate, UserUpdate, Token, TokenData,
    UserRole, LoginRequest, RegisterRequest,
    PasswordResetRequest, PasswordChangeRequest,
    Permission, Role
)
from .service import (
    AuthService, AuthenticationError, AuthorizationError, UserNotFoundError
)
from .oauth_service import (
    OAuthService, OAuthProvider, GoogleOAuth, GitHubOAuth
)
from .permission_service import PermissionService
from .audit_service import AuditService
from .dependencies import (
    get_current_user, get_current_active_user,
    require_admin, require_developer, require_analyst,
    check_permission, PermissionChecker
)
from .config import settings, get_auth_settings
from .database import db_manager, get_db_session, setup_database

__all__ = [
    "User", "UserCreate", "UserUpdate", "Token", "TokenData",
    "UserRole", "LoginRequest", "RegisterRequest",
    "PasswordResetRequest", "PasswordChangeRequest",
    "Permission", "Role",
    "AuthService", "AuthenticationError", "AuthorizationError", "UserNotFoundError",
    "OAuthService", "OAuthProvider", "GoogleOAuth", "GitHubOAuth",
    "PermissionService", "AuditService",
    "get_current_user", "get_current_active_user",
    "require_admin", "require_developer", "require_analyst",
    "check_permission", "PermissionChecker",
    "settings", "get_auth_settings",
    "db_manager", "get_db_session", "setup_database"
]
