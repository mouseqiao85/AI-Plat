# 维克多·斯波朗迪123法则和2B法则使用指南

## 概述

本指南介绍了如何使用集成到股票分析系统中的维克多·斯波朗迪123法则和2B法则策略，以增强趋势反转识别能力。

## 策略介绍

### 123法则
123法则用于识别趋势反转，包含三个条件：
1. 趋势线被突破
2. 上升趋势不再创新高，或下降趋势不再创新低
3. 价格突破前期关键高低点（上升趋势中跌破前期低点，下降趋势中突破前期高点）

### 2B法则
2B法则用于识别假突破现象：
- 看跌2B：价格创新高后回落，未能持续上涨
- 看涨2B：价格创新低后回升，未能持续下跌

## 集成方式

维克多·斯波朗迪策略已无缝集成到现有的股票分析工具中：

1. **自动分析**：在执行 `analyze_stock()` 方法时会自动运行维克多·斯波朗迪策略分析
2. **信号检测**：自动检测123法则和2B法则信号
3. **置信度评估**：为每个信号分配置信度分数
4. **结果整合**：将策略结果整合到整体分析报告中

## 使用方法

### 基本使用
```python
from stock_analysis_tool import StockAnalyzer

# 创建分析器实例
analyzer = StockAnalyzer('your_tushare_token')

# 分析股票（自动包含维克多·斯波朗迪策略分析）
result = analyzer.analyze_stock('002438', n_days=5)

# 打印报告（包含维克多·斯波朗迪策略结果）
analyzer.print_analysis_report(result)
```

### 访问策略分析结果
```python
# 获取维克多·斯波朗迪策略分析结果
vs_analysis = result['vic_sperandeo_analysis']

# 获取信号统计
signal_counts = vs_analysis['signal_counts']
print(f"看涨信号: {signal_counts['bullish_signals']}")
print(f"看跌信号: {signal_counts['bearish_signals']}")

# 获取最新信号
latest_bullish = vs_analysis['latest_signals']['bullish']
latest_bearish = vs_analysis['latest_signals']['bearish']
```

## 信号解释

### 123法则信号
- `123_bullish_reversal`: 看涨反转信号（下降趋势结束）
- `123_bearish_reversal`: 看跌反转信号（上升趋势结束）

### 2B法则信号
- `2b_bullish`: 看涨2B信号（假突破底部）
- `2b_bearish`: 看跌2B信号（假突破顶部）

## 置信度说明

每个信号都有对应的置信度分数（0-1），反映信号的可靠性：
- 高置信度 (>0.7)：信号较为可靠
- 中置信度 (0.4-0.7)：信号有一定参考价值
- 低置信度 (<0.4)：信号需谨慎对待

## 注意事项

1. 策略结果仅供参考，不构成投资建议
2. 结合其他分析方法使用效果更佳
3. 市场环境变化可能影响策略有效性
4. 建议设置适当的止损措施