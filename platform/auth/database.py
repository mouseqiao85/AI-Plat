"""
数据库连接和会话管理
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

from .config import DATABASE_URL

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类
Base = declarative_base()


def init_db():
    """初始化数据库，创建所有表"""
    from .schemas import Base
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Session:
    """获取数据库会话"""
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.Base = Base
    
    def create_all_tables(self):
        """创建所有表"""
        self.Base.metadata.create_all(bind=self.engine)
    
    def drop_all_tables(self):
        """删除所有表（慎用）"""
        self.Base.metadata.drop_all(bind=self.engine)
    
    def reset_database(self):
        """重置数据库（删除并重新创建所有表）"""
        self.drop_all_tables()
        self.create_all_tables()
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """关闭数据库会话"""
        session.close()
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"数据库连接测试失败: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()


def create_default_roles_and_permissions():
    """创建默认的角色和权限"""
    # TODO: 实现默认角色和权限的创建逻辑
    pass


def setup_database():
    """设置数据库，创建表并初始化数据"""
    print("正在初始化数据库...")
    
    # 创建所有表
    db_manager.create_all_tables()
    print("✓ 数据库表创建完成")
    
    # 创建默认角色和权限
    create_default_roles_and_permissions()
    print("✓ 默认角色和权限创建完成")
    
    print("数据库初始化完成")


if __name__ == "__main__":
    # 测试数据库连接和初始化
    if db_manager.test_connection():
        print("数据库连接成功")
        setup_database()
    else:
        print("数据库连接失败")