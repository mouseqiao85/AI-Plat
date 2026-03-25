"""
AI-Plat Platform Main Application
Updated with enhanced API routes and authentication system
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.routes import router as api_router
from api.mlops_routes import router as mlops_router
from api.workflow_routes import router as workflow_router
from api.skill_routes import router as skill_router
from auth.routes import router as auth_router
from auth.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NexusMind OS - AI-Plat Platform",
    description="下一代AI平台，实现从数据连接到认知连接的跃迁",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix="/api")
app.include_router(mlops_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")
app.include_router(skill_router, prefix="/api")
app.include_router(auth_router)


@app.get("/")
async def root():
    return {
        "name": "NexusMind OS",
        "version": "1.0.0",
        "message": "欢迎使用AI-Plat开发平台",
        "modules": [
            "ontology",
            "agents",
            "vibecoding",
            "mcp",
            "assets",
            "workflows"
        ],
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI-Plat Platform", "version": "1.0.0"}


def start_server(host: str = "0.0.0.0", port: int = 8000):
    logger.info(f"Starting NexusMind OS on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
