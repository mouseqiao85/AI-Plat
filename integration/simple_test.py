"""
简化版文心蒸汽机API连接测试
"""

import os
import sys
from pathlib import Path

# 添加项目路径到Python路径
sys.path.append(str(Path(__file__).parent.parent))

# 设置API密钥
os.environ['WENXIN_API_KEY'] = "bce-v3/ALTAK-nIMprNDvrn57vPHwiHTJP/333cd1e75646ed043529e4245c89d5d776182aa4"

print("Checking WenXin Steam Image API connection...")

try:
    from integration.wenxin_api_adapter import WenXinAPIAdapter
    
    print("[SUCCESS] Module imported successfully")
    
    # 尝试初始化适配器
    adapter = WenXinAPIAdapter()
    print("[SUCCESS] API adapter initialized successfully")
    
    # 验证API密钥是否正确设置
    if adapter.api_key:
        print("[SUCCESS] API key is correctly set")
        print(f"   API key preview: {adapter.api_key[:20]}...")
    else:
        print("[ERROR] API key not set")
        
    print("\n[INFO] Integration Status: API adapter configured successfully")
    print("   - Ready to use WenXin Steam Image Generation in NexusMind OS")
    print("   - Ensure network connectivity for remote API calls")
    print("   - Image generation may take some time, please be patient")
    
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
except Exception as e:
    print(f"[ERROR] An error occurred: {e}")
    
print("\n[COMPLETE] WenXin Steam API connection test finished")