"""
AI-Plat 开发平台主入口
实现从"数据连接"到"认知连接"的跃迁
集成千帆平台设计理念的增强功能
"""

import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional
from pydantic import BaseModel

# 导入增强功能
from ai_plat_platform import AIPlatPlatform
from core_enhancements import EnhancedAIPlatPlatform

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="AI-Plat 开发平台",
    description="下一代AI平台，实现从数据连接到认知连接的跃迁，集成千帆平台设计理念",
    version="1.0.0"
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 示例请求模型
class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None


@app.get("/")
async def root():
    """
    平台根路径
    """
    return {
        "message": "欢迎使用AI-Plat开发平台",
        "version": "1.0.0",
        "modules": [
            "ontology",
            "agents", 
            "vibecoding",
            "mcp",
            "asset_management",
            "model_training",
            "model_inference"
        ]
    }


@app.post("/query")
async def handle_query(request: QueryRequest):
    """
    处理查询请求
    """
    logger.info(f"Received query: {request.query}")
    
    # 这里将集成本体推理、智能体、Vibecoding和增强功能
    response = {
        "query": request.query,
        "context": request.context,
        "result": "查询已接收，正在处理...",
        "module_used": "enhanced_ai_plat"
    }
    
    return response


@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {"status": "healthy", "service": "AI-Plat Platform", "version": "1.0.0"}


# 本体模块API
@app.get("/ontology/status")
async def ontology_status():
    """本体模块状态"""
    return {"status": "active", "module": "ontology"}


@app.get("/agents/status")
async def agents_status():
    """智能体模块状态"""
    return {"status": "active", "module": "agents"}


@app.get("/vibecoding/status")
async def vibecoding_status():
    """Vibecoding模块状态"""
    return {"status": "active", "module": "vibecoding"}


@app.get("/mcp/status")
async def mcp_status():
    """MCP模块状态"""
    return {"status": "active", "module": "mcp"}


# 资产管理API
@app.get("/assets/models")
async def get_model_assets():
    """获取模型资产列表"""
    # 这里应该连接到实际的资产管理系统
    return {"models": [], "count": 0}


@app.get("/assets/data")
async def get_data_assets():
    """获取数据资产列表"""
    # 这里应该连接到实际的资产管理系统
    return {"datasets": [], "count": 0}


@app.get("/training/status")
async def training_status():
    """模型训练状态"""
    return {"status": "active", "module": "model_training"}


@app.get("/inference/status")
async def inference_status():
    """模型推理状态"""
    return {"status": "active", "module": "model_inference"}


# 启动函数
def start_server(host: str = "0.0.0.0", port: int = 8000):
    """
    启动服务器
    """
    logger.info(f"Starting AI-Plat platform on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


# 用于直接运行演示的函数
async def run_demo():
    """运行平台演示"""
    print("启动 AI-Plat 开发平台演示...")
    
    # 创建增强版平台实例
    from core_enhancements_fixed import EnhancedAIPlatPlatform
    
    platform = EnhancedAIPlatPlatform()
    
    try:
        # 初始化增强版平台
        await platform.initialize_enhanced_modules()
        
        # 显示平台状态
        status = platform.get_platform_status()
        print(f"\n平台状态:")
        print(f"   ID: {status['platform_id']}")
        print(f"   版本: {status['version']}")
        print(f"   模块状态: {status['modules_initialized']}")
        
        # 运行演示场景
        print("\n运行演示场景...")
        demo_results = await platform.run_demo_scenario()
        print(f"\n演示结果: {demo_results}")
        
        # 运行模块集成示例
        print("\n运行模块集成示例...")
        integration_results = platform.integrate_modules_example()
        print(f"\n集成结果: {integration_results}")
        
        # 运行基于千帆设计的增强演示
        print("\n运行基于千帆设计的增强演示...")
        enhanced_results = await platform.run_qianfan_demo()
        print(f"\n增强版结果: {enhanced_results}")
        
    except Exception as e:
        print(f"平台运行错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n平台演示完成")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        # 运行演示而不是启动服务器
        asyncio.run(run_demo())
    else:
        # 默认启动服务器
        start_server()