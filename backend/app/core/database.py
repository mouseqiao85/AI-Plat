from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    **({} if _is_sqlite else {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def close_db():
    """Dispose the SQLAlchemy engine. Called during app shutdown."""
    await engine.dispose()
