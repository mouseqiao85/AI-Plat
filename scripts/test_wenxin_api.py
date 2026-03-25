"""
测试文心蒸汽机API连接
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置API密钥
os.environ['WENXIN_API_KEY'] = "bce-v3/ALTAK-nIMprNDvrn57vPHwiHTJP/333cd1e75646ed043529e4245c89d5d776182aa4"

try:
    from wenxin_steamer_image_generator import WenXinSteamerImageGenerator
    
    print("正在初始化文心蒸汽机图像生成器...")
    generator = WenXinSteamerImageGenerator()
    
    print("初始化成功！正在测试图像生成...")
    result = generator.generate_image(
        prompt="A beautiful landscape with mountains and lake",
        size="512x512",
        save_path="./output/test_landscape.png"
    )
    
    if result["success"]:
        print("✅ API连接和图像生成测试成功！")
        print(f"图像URL: {result['url']}")
        print(f"保存路径: {result['save_path']}")
    else:
        print(f"❌ 测试失败: {result['error']}")
        
except Exception as e:
    print(f"❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()