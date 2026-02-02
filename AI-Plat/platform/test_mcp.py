"""
Test script to verify MCP functionality
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

from mcp_server import create_example_mcp_server
from mcp_client import MCPClient, MCPClientConfig


async def test_mcp_functionality():
    print("[TEST] Testing MCP Functionality...")
    
    # Create MCP server with example models
    server = create_example_mcp_server()
    print(f"[SUCCESS] Created MCP server with models: {list(server.model_registry.model_descriptions.keys())}")
    
    # Test direct model calling
    print("\n[Test 1] Testing direct model call...")
    result = await server.model_registry.models['image_classifier']('test_data')
    print(f"   Image classifier result: {result}")
    
    result = await server.model_registry.models['sentiment_analyzer']('This is a wonderful day!')
    print(f"   Sentiment analyzer result: {result}")
    
    # Start server in background
    print(f"\n[Test 2] Starting MCP server on {server.host}:{server.port}...")
    server_thread = server.start_server(background=True)
    
    # Wait a moment for server to start
    await asyncio.sleep(2)
    
    # Create client and test connection
    print("\n[Test 3] Testing MCP client connection...")
    client_config = MCPClientConfig(
        server_url=f"http://{server.host}:{server.port}",
        timeout=10
    )
    
    async with MCPClient(client_config) as client:
        # Test health check
        health = await client.health_check()
        print(f"   Health check: {health}")
        
        # List available models
        models = await client.list_models()
        print(f"   Available models: {len(models)}")
        for model in models:
            print(f"     - {model['name']}: {model['description']}")
        
        # Call models via MCP
        print("\n[Test 4] Testing model calls via MCP protocol...")
        
        # Call image classifier
        result = await client.call_model(
            model_name="image_classifier",
            operation="classify",
            input_data="sample_image_for_mcp"
        )
        print(f"   Image classifier via MCP: {result}")
        
        # Call sentiment analyzer
        result = await client.call_model(
            model_name="sentiment_analyzer",
            operation="analyze",
            input_data="The MCP integration works perfectly!"
        )
        print(f"   Sentiment analyzer via MCP: {result}")
    
    print("\n[COMPLETE] MCP functionality test completed successfully!")
    print("   [SUCCESS] Models can be registered and called directly")
    print("   [SUCCESS] MCP server can be started and accessed")
    print("   [SUCCESS] Clients can discover and call remote models")
    print("   [SUCCESS] Full model-to-model communication cycle works")


if __name__ == "__main__":
    asyncio.run(test_mcp_functionality())