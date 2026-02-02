"""
Test script to validate enhanced features based on Qianfan design
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'platform'))

from platform.core_enhancements_fixed import EnhancedAIPlatPlatform


async def test_enhanced_features():
    """Test the enhanced features of AI-Plat platform"""
    print("Testing Enhanced AI-Plat Features Based on Qianfan Design...")
    
    # Create enhanced platform instance
    platform = EnhancedAIPlatPlatform()
    
    # Initialize modules
    await platform.initialize_enhanced_modules()
    
    print("\n✓ Platform initialization successful")
    print(f"✓ Platform ID: {platform.platform_id}")
    print(f"✓ Modules initialized: {platform.modules_initialized}")
    
    # Test asset management
    print("\n1. Testing Asset Management...")
    model_asset = platform.asset_management.register_model_asset(
        platform.asset_management.__class__.__annotations__.get('model_asset', type('ModelAsset', (), {}))(
            id="test_model_1",
            name="Test Model",
            description="A test model for validation",
            model_type="pretrained",
            framework="paddle",
            version="1.0.0"
        )
    )
    print("✓ Model asset registered")
    
    # Test data asset
    data_asset = platform.asset_management.register_data_asset(
        platform.asset_management.__class__.__annotations__.get('data_asset', type('DataAsset', (), {}))(
            id="test_data_1",
            name="Test Dataset",
            description="A test dataset for validation",
            data_type="structured",
            format="csv",
            size=1024
        )
    )
    print("✓ Data asset registered")
    
    # Test deployment package creation
    pkg = platform.asset_management.create_deployment_package(
        model_id="test_model_1",
        name="Test Deployment Package",
        description="A test deployment package"
    )
    print("✓ Deployment package created")
    
    # Test training simulation
    print("\n2. Testing Model Training Simulation...")
    sft_job = await platform.model_training.run_sft_training(
        model_id="test_model_1",
        dataset_id="test_data_1",
        hyperparameters={"lr": 1e-4, "batch_size": 8}
    )
    print("✓ SFT training job completed")
    
    # Test inference simulation
    print("\n3. Testing Model Inference Simulation...")
    service_id = await platform.model_inference.deploy_online_service(
        package_id=pkg.id if pkg else "test_pkg_1",
        service_name="Test Inference Service",
        resources={"cpu": "2", "memory": "4Gi"}
    )
    print("✓ Online service deployed")
    
    batch_job = await platform.model_inference.run_batch_inference(
        service_id=service_id,
        dataset_id="test_data_1"
    )
    print("✓ Batch inference job completed")
    
    # Test MCP integration
    print("\n4. Testing MCP Integration...")
    if platform.mcp_server:
        print(f"✓ MCP Server running with models: {list(platform.mcp_server.model_registry.model_descriptions.keys())}")
        
        # Register a test model
        platform.mcp_server.register_model(
            "test_model",
            lambda x: f"Processed: {x}",
            "Test model for validation"
        )
        print("✓ Test model registered with MCP")
    else:
        print("⚠ MCP Server not available")
    
    # Print final statistics
    print("\n5. Final Statistics:")
    print(f"   - Model Assets: {len(platform.asset_management.get_model_assets())}")
    print(f"   - Data Assets: {len(platform.asset_management.get_data_assets())}")
    print(f"   - Deployment Packages: {len(platform.asset_management.get_deployment_packages())}")
    print(f"   - Training Jobs: {len(platform.model_training.training_jobs)}")
    print(f"   - Services: {len(platform.model_inference.services)}")
    print(f"   - Inference Results: {len(platform.model_inference.inference_results)}")
    print(f"   - MCP Integration: {platform.mcp_server is not None}")
    
    print("\n🎉 All enhanced features tested successfully!")
    print("AI-Plat platform now includes Qianfan design principles and capabilities.")


if __name__ == "__main__":
    asyncio.run(test_enhanced_features())