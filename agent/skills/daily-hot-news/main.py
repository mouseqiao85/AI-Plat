"""Daily hot news skill script.

This script fetches trending news. In a real implementation,
it would call a news API. For demo purposes, it returns mock data.
"""
import json
from datetime import datetime

# input_data and params are injected by the sandbox
category = params.get("category", "general") if params else "general"
count = params.get("count", 5) if params else 5

# Mock news data (in production, this would call a news API)
mock_news = {
    "general": [
        {"title": "AI技术突破：新一代大模型发布", "source": "科技日报"},
        {"title": "全球气候峰会达成新协议", "source": "新华社"},
        {"title": "量子计算实现新里程碑", "source": "自然杂志"},
        {"title": "新能源汽车销量创历史新高", "source": "经济观察"},
        {"title": "太空探索：火星样本返回计划更新", "source": "航天新闻"},
    ],
    "tech": [
        {"title": "GPT-5发布：多模态能力大幅提升", "source": "TechCrunch"},
        {"title": "芯片制造工艺突破2nm节点", "source": "半导体行业"},
        {"title": "开源大模型性能超越商业模型", "source": "GitHub Blog"},
        {"title": "自动驾驶L4级别获批商用", "source": "36氪"},
        {"title": "Web4.0标准草案发布", "source": "W3C"},
    ],
    "finance": [
        {"title": "央行宣布新货币政策调整", "source": "财经网"},
        {"title": "科技股领涨全球市场", "source": "华尔街日报"},
        {"title": "数字人民币跨境支付试点扩大", "source": "金融时报"},
        {"title": "新兴市场投资机遇分析", "source": "经济学人"},
        {"title": "加密货币监管框架更新", "source": "路透社"},
    ],
}

news_list = mock_news.get(category, mock_news["general"])[:count]
today = datetime.now().strftime("%Y-%m-%d")

result = json.dumps({
    "date": today,
    "category": category,
    "news": news_list,
    "count": len(news_list),
}, ensure_ascii=False)
