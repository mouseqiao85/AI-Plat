"""
文心蒸汽机图像生成模型对接脚本
用于NexusMind OS (AI-Plat V3.0)的图像生成功能
"""

import os
from openai import OpenAI
from typing import Optional
import base64
from pathlib import Path


class WenXinSteamerImageGenerator:
    """
    文心蒸汽机图像生成器
    对接百度千帆平台的musesteamer-air-image模型
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端
        :param api_key: 百度千帆平台API密钥，如未提供则从环境变量获取
        """
        self.api_key = api_key or os.getenv('WENXIN_API_KEY')
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置WENXIN_API_KEY环境变量或传入api_key参数")
        
        self.client = OpenAI(
            base_url='https://qianfan.baidubce.com/v2',
            api_key=self.api_key
        )
        
    def generate_image(self, prompt: str, size: str = "1328x1328", save_path: Optional[str] = None) -> dict:
        """
        生成图像
        :param prompt: 图像生成的提示词
        :param size: 图像尺寸，默认为"1328x1328"
        :param save_path: 可选，保存图像的路径
        :return: 包含图像URL和元数据的字典
        """
        try:
            response = self.client.images.generate(
                model="musesteamer-air-image",
                prompt=prompt,
                size=size,
                n=1,
                extra_body={
                    "prompt_extend": True
                }
            )
            
            # 获取生成的图像数据
            image_data = response.data[0]
            
            # 如果指定了保存路径，则保存图像
            if save_path:
                # 确保目录存在
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                
                # 从URL下载图像并保存
                import requests
                img_response = requests.get(image_data.url)
                with open(save_path, 'wb') as f:
                    f.write(img_response.content)
                    
            return {
                "success": True,
                "url": image_data.url,
                "save_path": save_path,
                "prompt": prompt,
                "size": size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt
            }


def main():
    """示例用法"""
    # 从环境变量获取API密钥
    api_key = os.getenv('WENXIN_API_KEY')
    
    if not api_key:
        print("请先设置环境变量 WENXIN_API_KEY")
        print("获取地址：https://console.bce.baidu.com/qianfan/ais/console/apiKey")
        return
    
    # 创建生成器实例
    generator = WenXinSteamerImageGenerator(api_key)
    
    # 示例：生成一张图像
    prompt = "A futuristic cityscape with flying vehicles and neon lights, digital art"
    result = generator.generate_image(
        prompt=prompt,
        size="1328x1328",
        save_path="./output/example_image.png"
    )
    
    if result["success"]:
        print(f"图像生成成功!")
        print(f"提示词: {result['prompt']}")
        print(f"图像URL: {result['url']}")
        print(f"保存路径: {result['save_path']}")
    else:
        print(f"图像生成失败: {result['error']}")


if __name__ == "__main__":
    main()