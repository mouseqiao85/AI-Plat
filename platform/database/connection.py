"""
数据库连接管理
支持PostgreSQL连接池和异步操作
"""

import os
from typing import Generator, Optional, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime
import logging

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.ext.declarative import declarative_base as sync_declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ai_plat"
)

ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_plat"
)

Base = declarative_base()

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """设置数据库连接参数"""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET timezone TO 'UTC'")
    cursor.close()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """获取数据库会话"""
    return SessionLocal()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(
            self.database_url,
            pool_size=20,
            max_overflow=30,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        self.Base = Base
    
    def create_all_tables(self):
        """创建所有表"""
        self.Base.metadata.create_all(bind=self.engine)
        logger.info("所有数据库表创建完成")
    
    def drop_all_tables(self):
        """删除所有表"""
        self.Base.metadata.drop_all(bind=self.engine)
        logger.warning("所有数据库表已删除")
    
    def reset_database(self):
        """重置数据库"""
        self.drop_all_tables()
        self.create_all_tables()
        logger.info("数据库已重置")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """会话上下文管理器"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def get_table_names(self) -> list:
        """获取所有表名"""
        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        return table_name in self.get_table_names()


db_manager = DatabaseManager()


def init_database():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    if not db_manager.test_connection():
        raise ConnectionError("数据库连接失败，请检查配置")
    
    db_manager.create_all_tables()
    
    logger.info("数据库初始化完成")


def get_database_info() -> dict:
    """获取数据库信息"""
    return {
        "database_url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
        "tables": db_manager.get_table_names(),
        "pool_size": engine.pool.size(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "connection_valid": db_manager.test_connection()
    }
