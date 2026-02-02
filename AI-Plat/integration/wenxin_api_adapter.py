"""
文心蒸汽机API适配器
用于NexusMind OS (AI-Plat V3.0)的图像生成服务
"""

import os
import asyncio
import aiohttp
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ImageGenerationRequest:
    """图像生成请求数据类"""
    prompt: str
    size: str = "1328x1328"
    n: int = 1
    style: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class ImageGenerationResult:
    """图像生成结果数据类"""
    success: bool
    url: Optional[str] = None
    local_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class WenXinAPIAdapter:
    """文心蒸汽机API适配器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化适配器
        :param api_key: 百度千帆API密钥
        """
        self.api_key = api_key or os.getenv('WENXIN_API_KEY')
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置WENXIN_API_KEY环境变量")
        
        self.base_url = 'https://qianfan.baidubce.com/v2'
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_image(
        self, 
        request: ImageGenerationRequest
    ) -> ImageGenerationResult:
        """
        生成图像
        :param request: 图像生成请求
        :return: 图像生成结果
        """
        if not self.session:
            raise RuntimeError("API适配器未正确初始化，请使用async with语句")
        
        try:
            # 构建请求参数
            payload = {
                "model": "musesteamer-air-image",
                "prompt": request.prompt,
                "size": request.size,
                "n": request.n,
                "extra_body": {
                    "prompt_extend": True
                }
            }
            
            # 添加样式参数（如果提供）
            if request.style:
                payload["extra_body"]["style"] = request.style
            
            logger.info(f"正在调用文心蒸汽机API生成图像，提示词: {request.prompt[:50]}...")
            
            # 发送API请求
            async with self.session.post(
                f"{self.base_url}/images/generations",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # 获取生成的图像URL
                    image_url = result.get('data', [{}])[0].get('url')
                    
                    logger.info("图像生成成功")
                    return ImageGenerationResult(
                        success=True,
                        url=image_url,
                        metadata=result
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"API调用失败: {response.status}, {error_text}")
                    return ImageGenerationResult(
                        success=False,
                        error=f"API调用失败: {response.status} - {error_text}"
                    )
                    
        except Exception as e:
            logger.error(f"生成图像时发生错误: {str(e)}")
            return ImageGenerationResult(
                success=False,
                error=str(e)
            )
    
    async def download_image(self, url: str, save_path: str) -> bool:
        """
        下载生成的图像到本地
        :param url: 图像URL
        :param save_path: 保存路径
        :return: 是否成功
        """
        if not self.session:
            raise RuntimeError("API适配器未正确初始化，请使用async with语句")
        
        try:
            # 确保目录存在
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    with open(save_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    logger.info(f"图像已保存到: {save_path}")
                    return True
                else:
                    logger.error(f"下载图像失败: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"下载图像时发生错误: {str(e)}")
            return False


class ImageGenerationManager:
    """图像生成管理器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.adapter = WenXinAPIAdapter(api_key)
        self.output_dir = Path("./output/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_and_save(
        self, 
        prompt: str, 
        filename: str, 
        size: str = "1328x1328",
        style: Optional[str] = None
    ) -> ImageGenerationResult:
        """
        生成图像并保存到本地
        :param prompt: 图像生成提示词
        :param filename: 保存的文件名
        :param size: 图像尺寸
        :param style: 图像风格
        :return: 生成结果
        """
        # 创建请求对象
        request = ImageGenerationRequest(
            prompt=prompt,
            size=size,
            style=style
        )
        
        # 生成图像
        async with self.adapter as adapter:
            result = await adapter.generate_image(request)
            
            if result.success and result.url:
                # 保存到本地
                local_path = str(self.output_dir / filename)
                download_success = await adapter.download_image(result.url, local_path)
                
                if download_success:
                    result.local_path = local_path
                    logger.info(f"图像已生成并保存: {local_path}")
                else:
                    logger.warning("图像生成成功，但下载到本地失败")
            
            return result


# 示例用法
async def main():
    """示例用法"""
    # 从环境变量获取API密钥
    api_key = os.getenv('WENXIN_API_KEY')
    
    if not api_key:
        print("请先设置环境变量 WENXIN_API_KEY")
        return
    
    # 创建管理器
    manager = ImageGenerationManager(api_key)
    
    # 生成一张图像
    result = await manager.generate_and_save(
        prompt="A futuristic cityscape with flying vehicles and neon lights, digital art",
        filename="future_city.png",
        size="1024x1024"
    )
    
    if result.success:
        print(f"✅ 图像生成成功!")
        print(f"   提示词: {result.metadata.get('prompt', 'N/A') if result.metadata else 'N/A'}")
        print(f"   图像URL: {result.url}")
        print(f"   本地路径: {result.local_path}")
    else:
        print(f"❌ 图像生成失败: {result.error}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())