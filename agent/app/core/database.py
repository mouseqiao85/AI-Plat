from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

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


async def run_lightweight_migrations():
    """Apply additive SQLite migrations not covered by create_all."""
    if not _is_sqlite:
        return
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(knowledge_nodes)"))
        columns = {row[1] for row in result.fetchall()}
        if columns and "content" not in columns:
            await conn.execute(text("ALTER TABLE knowledge_nodes ADD COLUMN content TEXT"))
        await conn.execute(text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts
            USING fts5(content, title, path, heading, content='knowledge_chunks', content_rowid='id')
            """
        ))
        await conn.execute(text(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_chunks_ai AFTER INSERT ON knowledge_chunks BEGIN
              INSERT INTO knowledge_chunks_fts(rowid, content, title, path, heading)
              SELECT new.id, new.content, knowledge_nodes.title, new.path, new.heading
              FROM knowledge_nodes WHERE knowledge_nodes.id = new.node_id;
            END
            """
        ))
        await conn.execute(text(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_chunks_ad AFTER DELETE ON knowledge_chunks BEGIN
              INSERT INTO knowledge_chunks_fts(knowledge_chunks_fts, rowid, content, title, path, heading)
              VALUES('delete', old.id, old.content, '', old.path, old.heading);
            END
            """
        ))
        await conn.execute(text(
            """
            CREATE TRIGGER IF NOT EXISTS knowledge_chunks_au AFTER UPDATE ON knowledge_chunks BEGIN
              INSERT INTO knowledge_chunks_fts(knowledge_chunks_fts, rowid, content, title, path, heading)
              VALUES('delete', old.id, old.content, '', old.path, old.heading);
              INSERT INTO knowledge_chunks_fts(rowid, content, title, path, heading)
              SELECT new.id, new.content, knowledge_nodes.title, new.path, new.heading
              FROM knowledge_nodes WHERE knowledge_nodes.id = new.node_id;
            END
            """
        ))


async def close_db():
    await engine.dispose()
