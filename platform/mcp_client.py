"""
MCP Client Implementation for AI-Plat
Allows AI-Plat agents to call remote models via MCP protocol
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging


class MCPClientConfig(BaseModel):
    """Configuration for MCP client"""
    server_url: str = Field(..., description="URL of the MCP server")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")


class MCPClient:
    """Client to interact with MCP servers"""
    
    def __init__(self, config: MCPClientConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def call_model(self, model_name: str, operation: str, input_data: Any, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a model on the MCP server"""
        if not self.session:
            raise RuntimeError("MCPClient not initialized. Use as async context manager or call initialize().")
        
        url = f"{self.config.server_url.rstrip('/')}/call"
        
        payload = {
            "model_name": model_name,
            "operation": operation,
            "input_data": input_data,
            "parameters": parameters or {}
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"MCP call failed with status {response.status}: {error_text}")
        except asyncio.TimeoutError:
            raise Exception(f"MCP call to {model_name} timed out after {self.config.timeout} seconds")
        except Exception as e:
            self.logger.error(f"Error calling MCP model {model_name}: {str(e)}")
            raise
    
    async def list_models(self) -> list:
        """List all models available on the MCP server"""
        if not self.session:
            raise RuntimeError("MCPClient not initialized. Use as async context manager or call initialize().")
        
        url = f"{self.config.server_url.rstrip('/')}/models"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to list models: {response.status} - {error_text}")
        except Exception as e:
            self.logger.error(f"Error listing MCP models: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the MCP server"""
        if not self.session:
            raise RuntimeError("MCPClient not initialized. Use as async context manager or call initialize().")
        
        url = f"{self.config.server_url.rstrip('/')}/health"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Health check failed: {response.status} - {error_text}")
        except Exception as e:
            self.logger.error(f"Error checking MCP server health: {str(e)}")
            raise


class MCPToolAdapter:
    """Adapter to expose MCP calls as AI-Plat skills"""
    
    def __init__(self, mcp_client: MCPClient):
        self.client = mcp_client
    
    async def create_model_tool(self, model_name: str, description: str = ""):
        """Create a skill function for a specific model"""
        async def model_tool(input_data: Any, parameters: Dict[str, Any] = None, operation: str = "predict"):
            """
            Generic function to call a remote model via MCP
            
            Args:
                input_data: Input data for the model
                parameters: Additional parameters for the model
                operation: Operation to perform (default: 'predict')
            """
            result = await self.client.call_model(
                model_name=model_name,
                operation=operation,
                input_data=input_data,
                parameters=parameters
            )
            return result
        
        # Set the function name and description
        model_tool.__name__ = f"call_{model_name.replace('-', '_').replace(' ', '_')}"
        model_tool.__doc__ = f"Call the {model_name} model via MCP. {description}"
        
        return model_tool


async def example_usage():
    """Example of how to use the MCP client with AI-Plat"""
    
    # Configuration for the MCP server
    config = MCPClientConfig(
        server_url="http://localhost:8001",
        timeout=30
    )
    
    # Use the client
    async with MCPClient(config) as client:
        # List available models
        print("Available models:")
        models = await client.list_models()
        for model in models:
            print(f"  - {model['name']}: {model['description']}")
        
        # Call a model
        print("\nCalling image classifier:")
        result = await client.call_model(
            model_name="image_classifier",
            operation="classify",
            input_data="sample_image_data"
        )
        print(f"Result: {result}")
        
        # Create a tool adapter
        adapter = MCPToolAdapter(client)
        image_classifier_tool = await adapter.create_model_tool(
            "image_classifier", 
            "Identify objects in images"
        )
        
        # Use the tool
        tool_result = await image_classifier_tool(
            input_data="another_sample_image",
            operation="classify"
        )
        print(f"Tool result: {tool_result}")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())