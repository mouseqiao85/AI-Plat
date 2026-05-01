from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import hash_password, verify_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_wechat_openid(self, openid: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.wechat_openid == openid))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        phone: Optional[str] = None,
        password: Optional[str] = None,
        wechat_openid: Optional[str] = None,
        nickname: str = "用户",
    ) -> User:
        user = User(
            phone=phone,
            password_hash=hash_password(password) if password else None,
            wechat_openid=wechat_openid,
            nickname=nickname,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, phone: str, password: str) -> Optional[User]:
        user = await self.get_by_phone(phone)
        if user and user.password_hash and verify_password(password, user.password_hash):
            return user
        return None

    async def check_daily_limit(self, user: User) -> bool:
        """Check if user has exceeded daily chat limit. Returns True if allowed."""
        today = date.today()
        if user.membership_tier != "free":
            return True
        if user.daily_chat_count_date != today:
            user.daily_chat_count = 0
            user.daily_chat_count_date = today
            await self.db.commit()
            return True
        from app.core.config import settings
        return user.daily_chat_count < settings.FREE_DAILY_CHAT_LIMIT

    async def increment_chat_count(self, user: User):
        today = date.today()
        if user.daily_chat_count_date != today:
            user.daily_chat_count = 1
            user.daily_chat_count_date = today
        else:
            user.daily_chat_count += 1
        await self.db.commit()
