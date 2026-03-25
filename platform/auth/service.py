"""
认证服务
提供用户认证和授权相关业务逻辑
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
from passlib.context import CryptContext
from jose import JWTError, jwt

from .models import User, UserCreate, TokenData, UserRole, LoginRequest
from .schemas import UserDB, RefreshTokenDB
from .database import get_db_session
from .config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    """认证异常"""
    pass


class AuthorizationError(Exception):
    """授权异常"""
    pass


class UserNotFoundError(Exception):
    """用户未找到异常"""
    pass


class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.db_session = get_db_session()
    
    # 密码相关方法
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希值"""
        return pwd_context.hash(password)
    
    # Token相关方法
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh"
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # 保存刷新令牌到数据库
        refresh_token_db = RefreshTokenDB(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            token=encoded_jwt,
            expires_at=expire
        )
        self.db_session.add(refresh_token_db)
        self.db_session.commit()
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> TokenData:
        """验证令牌"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_type = payload.get("type")
            if token_type != "access":
                raise AuthenticationError("无效的令牌类型")
            
            user_id = payload.get("sub")
            username = payload.get("username")
            role = payload.get("role")
            scopes = payload.get("scopes", [])
            
            if user_id is None:
                raise AuthenticationError("令牌中缺少用户ID")
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=role,
                scopes=scopes
            )
        except JWTError:
            raise AuthenticationError("令牌无效或已过期")
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """使用刷新令牌获取新的访问令牌"""
        try:
            # 验证刷新令牌
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            token_type = payload.get("type")
            if token_type != "refresh":
                raise AuthenticationError("无效的刷新令牌")
            
            user_id = payload.get("sub")
            if user_id is None:
                raise AuthenticationError("刷新令牌中缺少用户ID")
            
            # 检查刷新令牌是否在数据库中且未撤销
            token_db = self.db_session.query(RefreshTokenDB).filter(
                RefreshTokenDB.token == refresh_token,
                RefreshTokenDB.revoked == False,
                RefreshTokenDB.expires_at > datetime.utcnow()
            ).first()
            
            if not token_db:
                raise AuthenticationError("刷新令牌无效或已撤销")
            
            # 获取用户信息
            user_db = self.db_session.query(UserDB).filter(
                UserDB.id == uuid.UUID(user_id)
            ).first()
            
            if not user_db:
                raise UserNotFoundError("用户不存在")
            
            # 创建新的访问令牌
            access_token = self.create_access_token({
                "sub": str(user_db.id),
                "username": user_db.username,
                "role": user_db.role
            })
            
            return access_token
            
        except JWTError:
            raise AuthenticationError("刷新令牌无效或已过期")
    
    # 用户相关方法
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.id == uuid.UUID(user_id)
        ).first()
        
        if not user_db:
            return None
        
        return User(**user_db.to_dict())
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.username == username
        ).first()
        
        if not user_db:
            return None
        
        return User(**user_db.to_dict())
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.email == email
        ).first()
        
        if not user_db:
            return None
        
        return User(**user_db.to_dict())
    
    def list_users(self) -> List[Dict[str, Any]]:
        """获取所有用户列表"""
        users_db = self.db_session.query(UserDB).all()
        return [user.to_dict() for user in users_db]
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        # 尝试通过用户名或邮箱查找用户
        user_db = self.db_session.query(UserDB).filter(
            (UserDB.username == username) | (UserDB.email == username)
        ).first()
        
        if not user_db:
            return None
        
        if not self.verify_password(password, user_db.hashed_password):
            return None
        
        # 更新最后登录时间
        user_db.last_login = datetime.utcnow()
        self.db_session.commit()
        
        return User(**user_db.to_dict())
    
    def register_user(self, user_create: UserCreate) -> User:
        """注册新用户"""
        # 检查用户名是否已存在
        existing_user = self.get_user_by_username(user_create.username)
        if existing_user:
            raise AuthenticationError("用户名已存在")
        
        # 检查邮箱是否已存在
        existing_email = self.get_user_by_email(user_create.email)
        if existing_email:
            raise AuthenticationError("邮箱已存在")
        
        # 创建用户
        user_id = uuid.uuid4()
        hashed_password = self.get_password_hash(user_create.password)
        
        user_db = UserDB(
            id=user_id,
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            role=UserRole.GUEST.value,
            is_active=True,
            is_verified=False
        )
        
        self.db_session.add(user_db)
        self.db_session.commit()
        
        return self.get_user_by_id(str(user_id))
    
    def update_user(self, user_id: str, user_update: dict) -> Optional[User]:
        """更新用户信息"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.id == uuid.UUID(user_id)
        ).first()
        
        if not user_db:
            return None
        
        # 更新字段
        for key, value in user_update.items():
            if value is not None and hasattr(user_db, key):
                setattr(user_db, key, value)
        
        user_db.updated_at = datetime.utcnow()
        self.db_session.commit()
        
        return self.get_user_by_id(user_id)
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """修改密码"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.id == uuid.UUID(user_id)
        ).first()
        
        if not user_db:
            return False
        
        # 验证当前密码
        if not self.verify_password(current_password, user_db.hashed_password):
            return False
        
        # 更新密码
        user_db.hashed_password = self.get_password_hash(new_password)
        user_db.updated_at = datetime.utcnow()
        self.db_session.commit()
        
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """停用用户"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.id == uuid.UUID(user_id)
        ).first()
        
        if not user_db:
            return False
        
        user_db.is_active = False
        user_db.updated_at = datetime.utcnow()
        self.db_session.commit()
        
        return True
    
    def activate_user(self, user_id: str) -> bool:
        """激活用户"""
        user_db = self.db_session.query(UserDB).filter(
            UserDB.id == uuid.UUID(user_id)
        ).first()
        
        if not user_db:
            return False
        
        user_db.is_active = True
        user_db.updated_at = datetime.utcnow()
        self.db_session.commit()
        
        return True
    
    # 权限相关方法
    
    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """检查用户是否有权限"""
        # TODO: 实现权限检查逻辑
        # 现在先返回True，后续完善
        return True
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户权限列表"""
        # TODO: 实现权限查询逻辑
        # 现在返回空列表，后续完善
        return []
    
    def logout(self, refresh_token: str) -> bool:
        """用户登出"""
        # 撤销刷新令牌
        token_db = self.db_session.query(RefreshTokenDB).filter(
            RefreshTokenDB.token == refresh_token
        ).first()
        
        if token_db:
            token_db.revoked = True
            self.db_session.commit()
            return True
        
        return False