"""
OAuth2集成服务
支持Google和GitHub第三方登录
"""

import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from .models import User, UserCreate, UserRole
from .service import AuthService
from .config import settings
from .schemas import UserDB
from .database import get_db_session


class OAuthProvider:
    """OAuth提供者基类"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(self, state: str) -> str:
        """获取授权URL"""
        raise NotImplementedError
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """交换授权码获取令牌"""
        raise NotImplementedError
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        raise NotImplementedError


class GoogleOAuth(OAuthProvider):
    """Google OAuth提供者"""
    
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            return response.json()


class GitHubOAuth(OAuthProvider):
    """GitHub OAuth提供者"""
    
    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_INFO_URL = "https://api.github.com/user"
    USER_EMAIL_URL = "https://api.github.com/user/emails"
    
    SCOPES = ["user:email"]
    
    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
            "state": state
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri
                },
                headers={"Accept": "application/json"}
            )
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_INFO_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
            )
            user_data = response.json()
            
            if user_data.get("email") is None:
                emails = await client.get(
                    self.USER_EMAIL_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    }
                )
                email_list = emails.json()
                primary_email = next(
                    (e for e in email_list if e.get("primary")),
                    email_list[0] if email_list else {}
                )
                user_data["email"] = primary_email.get("email")
            
            return user_data


class OAuthService:
    """OAuth服务"""
    
    def __init__(self):
        self.db_session = get_db_session()
        self.auth_service = AuthService()
        
        self.providers: Dict[str, OAuthProvider] = {}
        
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.providers["google"] = GoogleOAuth(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                redirect_uri=f"{settings.APP_URL}/auth/oauth/callback/google"
            )
        
        if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
            self.providers["github"] = GitHubOAuth(
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                redirect_uri=f"{settings.APP_URL}/auth/oauth/callback/github"
            )
    
    def get_available_providers(self) -> list:
        """获取可用的OAuth提供者"""
        return list(self.providers.keys())
    
    def get_authorization_url(self, provider: str, state: str) -> Optional[str]:
        """获取OAuth授权URL"""
        oauth_provider = self.providers.get(provider)
        if not oauth_provider:
            return None
        return oauth_provider.get_authorization_url(state)
    
    async def handle_callback(self, provider: str, code: str) -> Dict[str, Any]:
        """处理OAuth回调"""
        oauth_provider = self.providers.get(provider)
        if not oauth_provider:
            raise ValueError(f"不支持的OAuth提供者: {provider}")
        
        token_data = await oauth_provider.exchange_code(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ValueError("获取访问令牌失败")
        
        user_info = await oauth_provider.get_user_info(access_token)
        
        user = await self._create_or_update_user(provider, user_info)
        
        jwt_token = self.auth_service.create_access_token({
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        })
        
        refresh_token = self.auth_service.create_refresh_token(str(user.id))
        
        return {
            "access_token": jwt_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.dict()
        }
    
    async def _create_or_update_user(self, provider: str, user_info: Dict[str, Any]) -> User:
        """创建或更新用户"""
        if provider == "google":
            email = user_info.get("email")
            username = user_info.get("email", "").split("@")[0]
            full_name = user_info.get("name", "")
            avatar_url = user_info.get("picture", "")
            provider_id = user_info.get("id")
        elif provider == "github":
            email = user_info.get("email")
            username = user_info.get("login", "")
            full_name = user_info.get("name", "") or username
            avatar_url = user_info.get("avatar_url", "")
            provider_id = str(user_info.get("id", ""))
        else:
            raise ValueError(f"不支持的OAuth提供者: {provider}")
        
        if not email:
            raise ValueError("无法获取用户邮箱")
        
        existing_user = self.db_session.query(UserDB).filter(
            UserDB.email == email
        ).first()
        
        if existing_user:
            if avatar_url and existing_user.avatar_url != avatar_url:
                existing_user.avatar_url = avatar_url
                existing_user.updated_at = datetime.utcnow()
                self.db_session.commit()
            return User(**existing_user.to_dict())
        
        base_username = username
        counter = 1
        while self.db_session.query(UserDB).filter(
            UserDB.username == username
        ).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        new_user = UserDB(
            id=uuid.uuid4(),
            username=username,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            hashed_password="",
            role=UserRole.GUEST.value,
            is_active=True,
            is_verified=True
        )
        
        self.db_session.add(new_user)
        self.db_session.commit()
        
        return User(**new_user.to_dict())
