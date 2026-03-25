"""
MCP Integration Example for AI-Plat
Demonstrates how to use MCP to connect different models
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_plat_platform import AIPlatPlatform
from mcp_server import create_example_mcp_server
from mcp_client import MCPClient, MCPClientConfig
from agents.skill_registry import global_skill_registry
from agents.skill_agent import SkillAgent


async def mcp_integration_example():
    """
    Example showing how to integrate MCP functionality with AI-Plat
    Demonstrates the ability for one model/service to call another via MCP
    """
    print("="*70)
    print("🔄 MCP Integration Example: Model-to-Model Communication")
    print("="*70)
    
    # 1. Start an MCP server with example models
    print("\n1. 🚀 Starting MCP Server with example models...")
    mcp_server = create_example_mcp_server()
    
    # Start the server in the background
    server_thread = mcp_server.start_server(background=True)
    await asyncio.sleep(2)  # Give server time to start
    
    print(f"   ✓ MCP Server running on {mcp_server.host}:{mcp_server.port}")
    print(f"   ✓ Registered models: {[name for name in mcp_server.model_registry.model_descriptions.keys()]}")
    
    # 2. Create an MCP client to connect to the server
    print("\n2. 📡 Creating MCP Client...")
    client_config = MCPClientConfig(
        server_url=f"http://{mcp_server.host}:{mcp_server.port}",
        timeout=30
    )
    
    async with MCPClient(client_config) as client:
        # 3. List available models
        print("\n3. 📋 Listing available models...")
        models = await client.list_models()
        for model in models:
            print(f"   - {model['name']}: {model['description']}")
        
        # 4. Call models via MCP
        print("\n4. 🤖 Calling models via MCP protocol...")
        
        # Call image classifier
        result1 = await client.call_model(
            model_name="image_classifier",
            operation="classify",
            input_data="sample_image_data"
        )
        print(f"   Image Classification Result: {result1}")
        
        # Call sentiment analyzer
        result2 = await client.call_model(
            model_name="sentiment_analyzer",
            operation="analyze",
            input_data="This is a wonderful day with great opportunities!"
        )
        print(f"   Sentiment Analysis Result: {result2}")
    
    # 5. Integrate with AI-Plat agents
    print("\n5. 🤝 Integrating MCP with AI-Plat Agents...")
    
    # Create an AI-Plat platform instance
    platform = AIPlatPlatform()
    await platform.initialize_modules()
    
    # Register the MCP server with the platform
    platform.register_mcp_server("example_server", mcp_server)
    
    # Register a client with the platform
    platform.register_mcp_client(
        "example_client",
        MCPClientConfig(server_url=f"http://{mcp_server.host}:{mcp_server.port}")
    )
    
    # Create an agent to use MCP skills
    agent = SkillAgent(
        name="MCPIntegrationAgent",
        description="Agent that demonstrates MCP integration",
        skills=["mcp_call_model", "mcp_list_models", "mcp_health_check"]
    )
    await agent.initialize()
    
    print(f"   ✓ Created agent: {agent.name}")
    print(f"   ✓ Agent skills: {agent.skills}")
    
    # 6. Use the agent to call remote models via MCP
    print("\n6. 🧠 Using AI-Plat Agent to call remote models...")
    
    # Add a task to call a remote model
    task_id = await agent.add_task(
        name="Remote Model Call",
        description="Call image classifier via MCP",
        skill_id="mcp_call_model",  # This is one of our MCP skills
        parameters={
            "server_url": f"http://{mcp_server.host}:{mcp_server.port}",
            "model_name": "image_classifier",
            "operation": "classify",
            "input_data": "test_image_data_for_agent"
        }
    )
    
    # Execute the task
    result = await agent.execute_task(task_id)
    print(f"   Agent MCP Call Result: {result}")
    
    # 7. Demonstrate model-to-model communication pattern
    print("\n7. 🔗 Demonstrating Model-to-Model Communication Pattern...")
    print("   This shows how a main model (like GPT-4) can call specialized sub-models")
    print("   by wrapping them as MCP tools:")
    print("")
    print("   Main Model Request:")
    print("   'Please analyze this image and describe the sentiment of any text in it'")
    print("")
    print("   Execution Flow:")
    print("   1. Main model calls 'image_classifier' tool via MCP")
    print("   2. Image classifier identifies text in image")
    print("   3. Main model then calls 'sentiment_analyzer' tool via MCP")
    print("   4. Sentiment analyzer processes the extracted text")
    print("   5. Results combined and returned to user")
    
    # 8. Show how to create reusable tools from MCP services
    print("\n8. 🛠️ Creating Reusable Tools from MCP Services...")
    
    # This would typically create a persistent tool that agents can reuse
    tool_creation_result = await global_skill_registry.execute_skill(
        "mcp_create_model_tool",
        client_name="example_client",
        model_name="image_classifier",
        description="Tool for image classification via MCP"
    )
    print(f"   Created reusable tool: {tool_creation_result}")
    
    # 9. Clean up
    print("\n9. 🧹 Cleanup...")
    print("   Note: In a real scenario, we would properly shut down the server")
    print("   For this example, the server continues running in the background")
    
    print("\n" + "="*70)
    print("✅ MCP Integration Example Completed Successfully!")
    print("   Demonstrated capabilities:")
    print("   - MCP server hosting multiple ML models")
    print("   - MCP client connecting to remote models")
    print("   - Integration with AI-Plat agents")
    print("   - Model-to-model communication pattern")
    print("   - Creation of reusable tools from MCP services")
    print("="*70)
    
    return {
        "server_status": "running",
        "client_calls": 2,  # image_classifier and sentiment_analyzer
        "agent_tasks": 1,    # task executed by agent
        "integration_demo": True
    }


async def run_full_demo():
    """Run the complete MCP integration demo"""
    print("🚀 Starting AI-Plat MCP Integration Demo...")
    
    try:
        results = await mcp_integration_example()
        print(f"\n🎯 Demo completed successfully!")
        print(f"   - Server status: {results['server_status']}")
        print(f"   - Client calls made: {results['client_calls']}")
        print(f"   - Agent tasks executed: {results['agent_tasks']}")
        print(f"   - Integration demo: {results['integration_demo']}")
        
    except Exception as e:
        print(f"❌ Error during demo: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_full_demo())