"""
MCP Server Implementation for AI-Plat
Allows ML/DL models to be exposed as tools that can be called by other models
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import threading
from enum import Enum


class MCPTransportType(str, Enum):
    """MCP Transport Types"""
    WEBSOCKET = "websocket"
    HTTP = "http"
    STDIO = "stdio"


class MCPModelCall(BaseModel):
    """Model for calling ML/DL models via MCP"""
    model_name: str = Field(..., description="Name of the model to call")
    operation: str = Field(..., description="Operation to perform (e.g., predict, classify, generate)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the model")
    input_data: Any = Field(..., description="Input data for the model")


class MCPResult(BaseModel):
    """Result from MCP model call"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    model_name: str
    operation: str


class ModelRegistry:
    """Registry for ML/DL models that can be exposed via MCP"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_descriptions: Dict[str, str] = {}
    
    def register_model(self, name: str, model_callable: Any, description: str = ""):
        """Register a model that can be called via MCP"""
        self.models[name] = model_callable
        self.model_descriptions[name] = description
    
    def get_model(self, name: str) -> Optional[Any]:
        """Get a registered model"""
        return self.models.get(name)
    
    def list_models(self) -> List[Dict[str, str]]:
        """List all registered models"""
        return [
            {"name": name, "description": desc} 
            for name, desc in self.model_descriptions.items()
        ]


class MCPServer:
    """MCP Server that exposes ML/DL models as callable tools"""
    
    def __init__(self, host: str = "localhost", port: int = 8000, transport: MCPTransportType = MCPTransportType.HTTP):
        self.host = host
        self.port = port
        self.transport = transport
        self.app = FastAPI(title="AI-Plat MCP Server", version="1.0.0")
        self.model_registry = ModelRegistry()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup MCP server routes"""
        
        @self.app.post("/call", response_model=MCPResult)
        async def call_model(call: MCPModelCall):
            """Call a registered model"""
            try:
                model = self.model_registry.get_model(call.model_name)
                if not model:
                    raise HTTPException(status_code=404, detail=f"Model '{call.model_name}' not found")
                
                # Execute the model call
                result = await self._execute_model_call(model, call.operation, call.input_data, call.parameters)
                
                return MCPResult(
                    success=True,
                    result=result,
                    model_name=call.model_name,
                    operation=call.operation
                )
            except Exception as e:
                self.logger.error(f"Error calling model {call.model_name}: {str(e)}")
                return MCPResult(
                    success=False,
                    error=str(e),
                    model_name=call.model_name,
                    operation=call.operation
                )
        
        @self.app.get("/models")
        async def list_registered_models():
            """List all registered models"""
            return self.model_registry.list_models()
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "models_registered": len(self.model_registry.models)}
    
    async def _execute_model_call(self, model, operation: str, input_data: Any, parameters: Dict[str, Any]):
        """Execute a model call with the given parameters"""
        # If the model is an async function, await it
        if asyncio.iscoroutinefunction(model):
            if parameters:
                return await model(input_data, **parameters)
            else:
                return await model(input_data)
        else:
            # If it's a regular function, run in thread pool
            loop = asyncio.get_event_loop()
            if parameters:
                return await loop.run_in_executor(None, lambda: model(input_data, **parameters))
            else:
                return await loop.run_in_executor(None, lambda: model(input_data))
    
    def register_model(self, name: str, model_callable: Any, description: str = ""):
        """Register a model with the MCP server"""
        self.model_registry.register_model(name, model_callable, description)
        self.logger.info(f"Registered model: {name} - {description}")
    
    def start_server(self, background: bool = True):
        """Start the MCP server"""
        if background:
            # Run server in a separate thread
            server_thread = threading.Thread(
                target=uvicorn.run,
                args=(self.app,),
                kwargs={"host": self.host, "port": self.port, "log_level": "info"},
                daemon=True
            )
            server_thread.start()
            self.logger.info(f"MCP Server started on {self.host}:{self.port}")
            return server_thread
        else:
            # Run server in foreground
            uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


# Example model implementations that can be registered with MCP
class ExampleModels:
    """Example ML/DL models that can be registered with MCP Server"""
    
    @staticmethod
    async def image_classifier(input_data: Any, **params):
        """Example image classification model"""
        # Simulate image classification
        # In real implementation, this would call an actual model
        import random
        classes = ["cat", "dog", "bird", "car", "person"]
        confidence = round(random.uniform(0.7, 0.99), 2)
        
        return {
            "class": random.choice(classes),
            "confidence": confidence,
            "model": "example_image_classifier",
            "input_shape": "simulated"
        }
    
    @staticmethod
    async def sentiment_analyzer(input_data: str, **params):
        """Example sentiment analysis model"""
        # Simulate sentiment analysis
        import random
        sentiments = ["positive", "negative", "neutral"]
        
        return {
            "sentiment": random.choice(sentiments),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "text_length": len(input_data),
            "model": "example_sentiment_analyzer"
        }
    
    @staticmethod
    async def text_summarizer(input_data: str, **params):
        """Example text summarization model"""
        # Simulate text summarization
        max_length = params.get("max_length", 50)
        return {
            "summary": f"This is a simulated summary of the input text (truncated to {max_length} chars)",
            "original_length": len(input_data),
            "summary_length": max_length,
            "model": "example_text_summarizer"
        }


def create_example_mcp_server():
    """Create an example MCP server with pre-registered models"""
    server = MCPServer(host="localhost", port=8001)
    
    # Register example models
    server.register_model(
        "image_classifier", 
        ExampleModels.image_classifier,
        "An example image classification model that identifies objects in images"
    )
    
    server.register_model(
        "sentiment_analyzer", 
        ExampleModels.sentiment_analyzer,
        "An example sentiment analysis model that determines sentiment from text"
    )
    
    server.register_model(
        "text_summarizer", 
        ExampleModels.text_summarizer,
        "An example text summarization model that summarizes input text"
    )
    
    return server


if __name__ == "__main__":
    # Example usage
    server = create_example_mcp_server()
    print("Starting MCP Server with example models...")
    print("Available endpoints:")
    print("  - POST /call: Call a registered model")
    print("  - GET  /models: List all registered models")
    print("  - GET  /health: Health check")
    print("\nExample model calls:")
    print('  curl -X POST http://localhost:8001/call -H "Content-Type: application/json" -d \'{"model_name": "image_classifier", "operation": "classify", "input_data": "sample_image_data"}\'')
    
    # Start server in foreground
    server.start_server(background=False)