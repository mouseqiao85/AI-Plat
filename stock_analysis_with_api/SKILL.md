---
name: stock_analysis_with_api
version: 1.1.0
description: 股票综合分析技能 — 技术面、波浪理论、维克多·斯波朗迪策略、情绪面、机器学习预测
author: Clawdbot
license: MIT
enabled: true
config:
  requires:
    - TUSHARE_TOKEN
  optional:
    - WENXIN_API_KEY
tools:
  - name: stock_technical_analysis
    description: K线形态、技术指标、RandomForest预测、交易建议
  - name: stock_wave_analysis
    description: 艾略特波浪分析、斐波那契回撤、维克多·斯波朗迪1-2-3/2B策略
  - name: stock_sentiment_analysis
    description: 新闻舆情、社交媒体、政策影响、市场情绪综合评分
dependencies:
  - tushare>=1.4.7
  - scikit-learn>=1.3.0
  - snownlp>=0.12.3
  - jieba>=0.42.1
  - scipy>=1.11.0
keywords:
  - stock-analysis
  - technical-analysis
  - elliott-wave
  - vic-sperandeo
  - sentiment-analysis
  - ml-prediction
---

# 股票综合分析技能

## 概述

基于实时API与历史数据的全方位股票量化分析技能，涵盖技术面、波浪理论、策略信号、情绪面及机器学习预测。

## 分析能力

### 1. 技术面分析 (`stock_technical_analysis`)

- K线形态识别（长阳线、锤子线、十字星、倒锤子线等）
- 技术指标计算（MA5/10/20/60、RSI、MACD、布林带、成交量比率）
- RandomForest回归预测模型（N日价格预测）
- 综合评分交易建议（强烈买入→强烈卖出，5档）
- 短期/中期/长期投资策略与目标价位

**输入**: `stock_code` (必填), `n_days` (预测天数, 默认5)
**输出**: 技术指标、K线形态、预测价格、交易建议、投资策略

### 2. 波浪与策略分析 (`stock_wave_analysis`)

- 艾略特波浪阶段识别（推动浪1-5、调整浪A-B-C）
- 波浪计数与有效性评分
- 斐波那契回撤位与扩展位
- 趋势强度量化评分
- 模式识别（头肩顶/底、双顶/底、三角形整理）
- 多时间框架一致性评估
- 维克多·斯波朗迪 123法则趋势反转信号
- 维克多·斯波朗迪 2B法则假突破信号

**输入**: `stock_code` (必填)
**输出**: 波浪阶段、趋势强度、斐波那契位、反转信号、交易信号

### 3. 情绪面分析 (`stock_sentiment_analysis`)

- 新闻情感分析（SnowNLP中文情感打分）
- 社交媒体舆情分析
- 政策影响评估（利好/利空政策梳理）
- 市场情绪指标（波动率、成交量趋势、价格动量）
- 加权综合情绪评分

**输入**: `stock_code` (必填), `company_name` (可选), `industry` (可选)
**输出**: 各维度情绪得分、综合评分、情绪解读

## 数据源

| 数据类型 | 来源 |
|---------|------|
| 实时行情 | 东方财富 → 新浪 → AkShare (多源回退) |
| 历史K线 | tushare pro API |
| 财务数据 | tushare (EPS/PE/PB/ROE/现金流) |
| 舆情数据 | SnowNLP情感分析 + tushare量价指标 |

## 配置要求

- **TUSHARE_TOKEN** (必填): tushare pro API密钥，在 `.env` 中配置
- **WENXIN_API_KEY** (可选): 百度文心大模型API密钥，用于AI专业操盘手分析

## 注意事项

- 预测模型基于历史数据，仅供参考，不构成投资建议
- 中国市场惯例：红涨绿跌（与西方市场相反）
- 技术分析工具在盘后数据更新前可能存在延迟
