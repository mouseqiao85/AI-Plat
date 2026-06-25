from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.redis import get_redis, redis_pool


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_redis_client() -> Optional[object]:
    """Return the Redis client, or None if Redis is unavailable."""
    try:
        return get_redis()
    except RuntimeError:
        return None
