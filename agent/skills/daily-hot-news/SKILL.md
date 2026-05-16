---
name: "daily-hot-news"
version: "1.0.0"
description: "获取今日热点新闻摘要"
author: "agent-platform"
tools: [{'name': 'fetch_hot_news', 'description': '获取今日热点新闻', 'input_schema': {'type': 'object', 'properties': {'category': {'type': 'string', 'description': '新闻类别(tech/finance/general)', 'default': 'general'}, 'count': {'type': 'integer', 'description': '返回新闻条数', 'default': 5}}}}]
config: {'requires': []}
category: "数据采集"
---



# 今日热点新闻 Skill

获取当日热点新闻摘要，支持分类筛选。

## 使用方法

启用此 Skill 后，可以通过以下方式触发:
- "今日热点新闻"
- "今天有什么新闻"
- "最新科技新闻"

## 参数

- `category`: 新闻类别，支持 tech/finance/general
- `count`: 返回新闻条数，默认5条
