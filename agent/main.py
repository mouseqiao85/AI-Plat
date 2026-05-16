import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine, close_db
from app.api.routes import router as agent_router
from app.api.skill_routes import router as skill_router, register_enabled_skills
from app.api.admin_routes import router as admin_router
from app.api.memory_routes import router as memory_router
from app.api.file_routes import router as file_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Agent Service in {settings.APP_ENV} mode")
    # Ensure data directory exists for SQLite
    import os as _os
    if settings.DATABASE_URL.startswith("sqlite"):
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        db_dir = _os.path.dirname(db_path)
        if db_dir and not _os.path.exists(db_dir):
            _os.makedirs(db_dir, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Initialize Skill Manager and Tool Registry
    from app.skill.manager import init_skill_manager
    from app.tools.registry import get_tool_registry
    from app.tools.plan_tool import CreatePlanTool
    from app.tools.brave_search import BraveSearchTool

    skill_mgr = init_skill_manager(settings.SKILLS_DIR)
    logger.info("SkillManager initialized: %d skills discovered", len(skill_mgr.list_skills()))

    # Register built-in Python tools
    registry = get_tool_registry()
    registry.register(CreatePlanTool())
    if settings.BRAVE_API_KEY:
        registry.register(BraveSearchTool())
        logger.info("brave_search tool enabled")
    else:
        logger.info("brave_search tool disabled (BRAVE_API_KEY not set)")

    # Register tools for enabled skills
    register_enabled_skills()
    logger.info("ToolRegistry initialized: %d tools", len(registry.list_tools()))

    # Ensure generated files directory exists
    _os.makedirs(settings.GENERATED_FILES_DIR, exist_ok=True)

    yield
    await close_db()
    logger.info("Agent Service stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(skill_router)
app.include_router(admin_router)
app.include_router(memory_router)
app.include_router(file_router)


@app.get("/health")
async def root_health():
    return {"status": "ok", "service": "agent-service", "env": settings.APP_ENV}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
