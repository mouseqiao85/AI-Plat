"""
文心蒸汽机API配置脚本
用于安全设置API密钥环境变量
"""

import os
import sys
from pathlib import Path

def setup_api_key():
    """设置API密钥环境变量"""
    api_key = "bce-v3/ALTAK-nIMprNDvrn57vPHwiHTJP/333cd1e75646ed043529e4245c89d5d776182aa4"
    
    # 设置环境变量（仅在当前进程中）
    os.environ['WENXIN_API_KEY'] = api_key
    
    # 尝试在系统中永久设置环境变量（Windows）
    try:
        import subprocess
        # 为当前用户设置环境变量
        subprocess.run([
            'setx', 'WENXIN_API_KEY', api_key
        ], check=True, capture_output=True)
        print("[SUCCESS] API key has been set as system environment variable (requires reopening terminal to take effect)")
    except Exception as e:
        print(f"[WARNING] Unable to set system environment variable: {e}")
        print("  You can temporarily set it in command line: set WENXIN_API_KEY=bce-v3/ALTAK-nIMprNDvrn57vPHwiHTJP/333cd1e75646ed043529e4245c89d5d776182aa4")
    
    print("\n[INFO] API key has been set in current process")
    print("[INFO] You can now run the image generation script to test functionality")

def test_api_connection():
    """测试API连接"""
    try:
        # Temporarily add the current directory to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from wenxin_steamer_image_generator import WenXinSteamerImageGenerator
        
        # Create generator instance
        generator = WenXinSteamerImageGenerator()
        
        # Test generating a simple image
        print("\n[TEST] Testing API connection...")
        result = generator.generate_image(
            prompt="A simple geometric pattern, minimalistic design",
            size="512x512",
            save_path="./output/test_image.png"
        )
        
        if result["success"]:
            print("[SUCCESS] API connection test successful!")
            print(f"   Generated image URL: {result['url']}")
            print(f"   Saved path: {result['save_path']}")
        else:
            print(f"[ERROR] API connection test failed: {result['error']}")
            
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("[INFO] Please ensure wenxin_steamer_image_generator.py file is in the correct location")
    except Exception as e:
        print(f"[ERROR] Error during testing: {e}")

if __name__ == "__main__":
    print("WenXin Steam Image Generator API Configuration Tool")
    print("="*55)
    
    setup_api_key()
    
    # Ask if user wants to perform connection test
    try:
        response = input("\nDo you want to perform API connection test? (y/n): ").lower().strip()
        if response in ['y', 'yes', 'Y', 'YES']:
            test_api_connection()
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
    
    print("\n[INFO] Usage Instructions:")
    print("- Script saved at: C:\\Users\\qiaoshuowen\\clawd\\skills\\AI-Plat\\scripts\\wenxin_steamer_image_generator.py")
    print("- You can use the script to generate images, for example:")
    print("  generator = WenXinSteamerImageGenerator()")
    print('  result = generator.generate_image(prompt="your prompt")')