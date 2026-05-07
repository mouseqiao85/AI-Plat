import sys
import io
import os
import logging
import structlog
import asyncio
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Fix Windows GBK console encoding — allow emoji/CJK in log output
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def _patch_stream_handlers() -> None:
    """Redirect all logging StreamHandlers that point to a non-UTF-8 console.

    Strategy A – replace stale stream references (works for handlers already
    created before this module ran, e.g. uvicorn's root handler).

    Strategy B – monkey-patch StreamHandler.emit so that any handler whose
    stream still raises UnicodeEncodeError falls back to errors='replace'.
    This is the safety net for handlers that SQLAlchemy/uvicorn create lazily
    after this function first runs (Strategy B is idempotent; calling the
    function twice is safe).
    """
    # Strategy A: walk every known logger and re-point stale stream refs
    loggers = [logging.root] + list(logging.Logger.manager.loggerDict.values())
    for _log in loggers:
        if not isinstance(_log, logging.Logger):
            continue
        for _h in _log.handlers:
            if not isinstance(_h, logging.StreamHandler) or isinstance(
                _h, logging.FileHandler
            ):
                continue
            _stream = getattr(_h, "stream", None)
            if _stream is None:
                continue
            _enc = (getattr(_stream, "encoding", None) or "utf-8").lower().replace("-", "")
            if _enc in ("utf8", "utf8"):
                continue
            try:
                _fd = _stream.fileno()
                if _fd == 1:
                    _h.stream = sys.stdout
                elif _fd == 2:
                    _h.stream = sys.stderr
            except Exception:
                pass

    # Strategy C: Ensure SQLAlchemy loggers use UTF-8-safe handlers.
    for _sa_name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine"):
        _sa_logger = logging.getLogger(_sa_name)
        _sa_logger.handlers = [
            h for h in _sa_logger.handlers
            if isinstance(h, logging.FileHandler)
            or (
                isinstance(h, logging.StreamHandler)
                and (getattr(getattr(h, "stream", None), "encoding", "") or "").lower().replace("-", "") == "utf8"
            )
        ]
        if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in _sa_logger.handlers):
            _sa_h = logging.StreamHandler(sys.stderr)
            _sa_h.setFormatter(logging.Formatter("%(message)s"))
            _sa_logger.addHandler(_sa_h)
        _sa_logger.propagate = False

    # Strategy B: monkey-patch StreamHandler.emit as a universal safety net
    _orig_emit = getattr(logging.StreamHandler, "_orig_emit", None)
    if _orig_emit is None:
        _orig_emit = logging.StreamHandler.emit
        logging.StreamHandler._orig_emit = _orig_emit  # type: ignore[attr-defined]

        def _safe_emit(self: logging.StreamHandler, record: logging.LogRecord) -> None:  # type: ignore[override]
            try:
                _orig_emit(self, record)
            except UnicodeEncodeError:
                try:
                    msg = self.format(record)
                    stream = self.stream
                    buf = getattr(stream, "buffer", None)
                    if buf is not None:
                        buf.write((msg + self.terminator).encode(
                            getattr(stream, "encoding", "utf-8") or "utf-8",
                            errors="replace",
                        ))
                        buf.flush()
                    else:
                        stream.write(
                            (msg + self.terminator)
                            .encode("utf-8", errors="replace")
                            .decode("utf-8", errors="replace")
                        )
                        self.flush()
                except Exception:
                    self.handleError(record)

        logging.StreamHandler.emit = _safe_emit  # type: ignore[method-assign]


_patch_stream_handlers()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.redis import init_redis, close_redis, check_redis_health, redis_pool
from app.core.database import engine, Base, close_db, _is_sqlite

logger = structlog.get_logger(__name__)


def _migrate_add_reasoning_content(connection) -> None:
    """Add reasoning_content column to messages table if it doesn't exist (SQLite)."""
    from sqlalchemy import inspect as sa_inspect, text as sa_text
    inspector = sa_inspect(connection)
    columns = [c["name"] for c in inspector.get_columns("messages")]
    if "reasoning_content" not in columns:
        connection.execute(sa_text("ALTER TABLE messages ADD COLUMN reasoning_content TEXT"))
        logger.info("migration_added_reasoning_content_column")


# Track DB readiness
db_ready = True

# Track background tasks for graceful shutdown
_background_tasks: set = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_ready

    # Startup — gracefully handle missing infrastructure
    try:
        await init_redis()
        logger.info("redis_connected")
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Migration: add reasoning_content column for existing SQLite databases
            if _is_sqlite:
                await conn.run_sync(_migrate_add_reasoning_content)
        logger.info("database_ready")
        db_ready = True
    except Exception as exc:
        logger.warning("database_unavailable", error=str(exc))
        db_ready = False

    # Seed admin account if DB is available
    if db_ready:
        try:
            from app.core.database import async_session_factory
            from app.models import User as UserModel
            from app.core.security import hash_password
            from sqlalchemy import select

            async with async_session_factory() as db:
                result = await db.execute(select(UserModel).where(UserModel.username == "admin"))
                if result.scalar_one_or_none() is None:
                    admin_password = os.environ.get("ADMIN_PASSWORD", "")
                    if not admin_password:
                        logger.warning("ADMIN_PASSWORD not set, skipping admin account creation")
                    if admin_password:
                        admin = UserModel(
                            username="admin",
                            password_hash=hash_password(admin_password),
                            nickname="管理员",
                            role="admin",
                            membership_tier="enterprise",
                        )
                    db.add(admin)
                    await db.commit()
                    logger.info("admin_account_seeded")
        except Exception as exc:
            logger.warning("admin_seed_failed", error=str(exc))

    # Ensure generated files directory exists + start cleanup coroutine
    os.makedirs(settings.FILE_DOWNLOAD_DIR, exist_ok=True)
    # Ensure sandbox base directory exists
    sandbox_base = settings.SANDBOX_BASE_DIR or os.path.join(os.path.expanduser("~"), ".joeyagent")
    os.makedirs(sandbox_base, exist_ok=True)
    logger.info("sandbox_base_ready", path=sandbox_base)

    from app.services.file_storage import cleanup_loop
    cleanup_task = asyncio.create_task(cleanup_loop())

    yield

    # Shutdown — graceful
    cleanup_task.cancel()
    try:
        await asyncio.wait_for(cleanup_task, timeout=2.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    # Await tracked background tasks with a timeout
    if _background_tasks:
        done, pending = await asyncio.wait(_background_tasks, timeout=5.0)
        for task in pending:
            task.cancel()

    if redis_pool is not None:
        await close_redis()
    await close_db()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    detail = {"detail": "Internal server error"}
    if settings.DEBUG:
        detail["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=500, content=detail)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.audit import AuditMiddleware

app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    from app.core.redis import get_redis
    from app.core.database import async_session_factory
    from sqlalchemy import text

    checks = {
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "time": datetime.now(timezone.utc).isoformat(),
    }

    # Redis check
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"down: {exc}"

    # DB check
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"down: {exc}"

    is_ok = checks.get("redis") == "ok" and checks.get("db") == "ok"
    return JSONResponse(content=checks, status_code=200 if is_ok else 503)


# Register routers
from app.api import auth, chat, skill, conversations, files, admin

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(skill.router, prefix="/api/v1/skills", tags=["skill"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# Re-patch after all imports
_patch_stream_handlers()
