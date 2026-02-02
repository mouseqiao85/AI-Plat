"""
MCP Skills for AI-Plat
Skills that enable AI-Plat agents to work with MCP servers
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_client import MCPClient, MCPClientConfig
from mcp_server import MCPServer, ExampleModels
from .skill_registry import global_skill_registry, SkillCategory
from typing import Dict, Any, Optional
import asyncio


@global_skill_registry.register_skill(
    name="mcp_call_model",
    description="通过MCP协议调用远程模型",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.ML_MODEL,
    tags=["mcp", "remote-model", "ai-service", "tool-call"]
)
async def mcp_call_model(
    client_name: str,
    model_name: str,
    operation: str = "predict",
    input_data: Any = None,
    parameters: Optional[Dict[str, Any]] = None,
    server_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    通过MCP协议调用远程模型服务
    
    Args:
        client_name: MCP客户端名称（如果已注册）
        model_name: 要调用的模型名称
        operation: 操作类型（如：predict, classify, summarize等）
        input_data: 输入数据
        parameters: 额外的参数
        server_url: 服务器URL（如果没有预先注册客户端）
        api_key: API密钥（如果没有预先注册客户端）
    
    Returns:
        模型调用结果
    """
    from ..ai_plat_platform import AIPlatPlatform
    
    # 尝试从全局平台实例获取客户端
    # Note: 在实际实现中，需要根据具体架构获取平台实例
    # 这里提供一个简化版本
    
    if server_url:
        # 如果提供了服务器URL，创建临时客户端
        config = MCPClientConfig(server_url=server_url, api_key=api_key)
        async with MCPClient(config) as temp_client:
            result = await temp_client.call_model(
                model_name=model_name,
                operation=operation,
                input_data=input_data,
                parameters=parameters or {}
            )
            return result
    else:
        # 尝试使用已注册的客户端（需要平台支持）
        # 这里返回模拟结果，实际实现需要接入平台实例
        return {
            "success": True,
            "result": f"Simulated call to {model_name} with operation {operation}",
            "model_name": model_name,
            "operation": operation,
            "input_processed": len(str(input_data)) if input_data else 0,
            "parameters_used": parameters or {},
            "via_mcp": True
        }


@global_skill_registry.register_skill(
    name="mcp_register_client",
    description="注册MCP客户端以供后续使用",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.UTILITIES,
    tags=["mcp", "client", "registration", "configuration"]
)
async def mcp_register_client(
    client_name: str,
    server_url: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    注册MCP客户端以供后续使用
    
    Args:
        client_name: 客户端名称
        server_url: MCP服务器URL
        api_key: API密钥（可选）
    
    Returns:
        注册结果
    """
    # 在实际实现中，这会将客户端注册到平台实例
    # 这里返回模拟结果
    return {
        "success": True,
        "client_name": client_name,
        "server_url": server_url,
        "registered": True,
        "message": f"MCP client '{client_name}' registered for server {server_url}"
    }


@global_skill_registry.register_skill(
    name="mcp_list_models",
    description="列出MCP服务器上可用的模型",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.UTILITIES,
    tags=["mcp", "models", "discovery", "listing"]
)
async def mcp_list_models(
    server_url: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    列出MCP服务器上可用的模型
    
    Args:
        server_url: MCP服务器URL
        api_key: API密钥（可选）
    
    Returns:
        可用模型列表
    """
    config = MCPClientConfig(server_url=server_url, api_key=api_key)
    async with MCPClient(config) as client:
        models = await client.list_models()
        return {
            "server_url": server_url,
            "models_count": len(models),
            "models": models
        }


@global_skill_registry.register_skill(
    name="mcp_health_check",
    description="检查MCP服务器健康状态",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.UTILITIES,
    tags=["mcp", "health", "monitoring", "status"]
)
async def mcp_health_check(
    server_url: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    检查MCP服务器健康状态
    
    Args:
        server_url: MCP服务器URL
        api_key: API密钥（可选）
    
    Returns:
        健康检查结果
    """
    config = MCPClientConfig(server_url=server_url, api_key=api_key)
    async with MCPClient(config) as client:
        health = await client.health_check()
        return {
            "server_url": server_url,
            "health_status": health,
            "accessible": health.get("status") == "healthy"
        }


@global_skill_registry.register_skill(
    name="mcp_create_model_tool",
    description="创建MCP模型调用工具",
    version="1.0.0",
    author="AI-Plat Team",
    category=SkillCategory.UTILITIES,
    tags=["mcp", "tool", "automation", "integration"]
)
async def mcp_create_model_tool(
    client_name: str,
    model_name: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    为特定模型创建可重用的工具函数
    
    Args:
        client_name: MCP客户端名称
        model_name: 模型名称
        description: 工具描述
    
    Returns:
        工具创建结果
    """
    # 在实际实现中，这会创建一个可重用的工具
    # 这里返回模拟结果
    return {
        "success": True,
        "tool_name": f"call_{model_name.replace('-', '_').replace(' ', '_')}",
        "model_name": model_name,
        "client_name": client_name,
        "description": description or f"Tool for calling {model_name} via MCP",
        "created": True
    }