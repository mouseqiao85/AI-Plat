---
name: deepresearch
version: "1.0.0"
description: 深度研究技能。触发词:深度研究/深度分析/深入研究/deep research/竞争分析/行业研究/市场分析/研究报告。对指定主题进行多轮搜索、信息整合，输出结构化研究报告。
config:
  optional:
    - BCE_API_KEY
---

# DeepResearch 深度研究技能

对指定主题进行多轮网络搜索、信息整合与分析，输出结构化 Markdown 研究报告。

## 功能

- 自动分解研究主题为多个子问题
- 多轮 Brave Search 搜索（每个子问题 3-5 条结果）
- 使用 BCE API（百度千帆）或 OpenAI 兼容接口做分析综合
- 输出包含：背景、现状、竞争格局、趋势展望、结论的完整报告

## 使用方式

Agent 收到"深度研究/deep research/研究报告"类请求时，调用 `run_skill_script`，执行：

```python
from scripts.deepresearch import run_deepresearch
result = run_deepresearch(topic="你的研究主题")
print(result)
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| topic | str | 必填 | 研究主题 |
| bce_api_key | str | 从环境变量 BCE_API_KEY 读取 | 百度千帆 API Key |
| max_rounds | int | 4 | 搜索轮次 |
| results_per_query | int | 5 | 每次搜索结果数 |

## 输出格式

返回完整 Markdown 研究报告字符串，包含：
1. 执行摘要
2. 背景与现状
3. 核心发现（按子主题分节）
4. 竞争/行业格局
5. 趋势与展望
6. 结论与建议
