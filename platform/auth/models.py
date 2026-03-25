"""
认证系统数据模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    GUEST = "guest"


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=8, description="密码")


class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """用户响应模型"""
    id: str = Field(..., description="用户ID")
    role: UserRole = Field(default=UserRole.GUEST, description="用户角色")
    is_active: bool = Field(default=True, description="是否激活")
    is_verified: bool = Field(default=False, description="是否已验证邮箱")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    expires_in: int = Field(default=3600, description="过期时间（秒）")


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    scopes: List[str] = []


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")


class PasswordResetRequest(BaseModel):
    """密码重置请求模型"""
    email: EmailStr = Field(..., description="邮箱地址")


class PasswordChangeRequest(BaseModel):
    """密码更改请求模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, description="新密码")


class Permission(BaseModel):
    """权限模型"""
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    resource: str = Field(..., description="资源类型")
    action: str = Field(..., description="操作类型")


class Role(BaseModel):
    """角色模型"""
    name: UserRole = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    permissions: List[Permission] = Field(default_factory=list, description="权限列表")