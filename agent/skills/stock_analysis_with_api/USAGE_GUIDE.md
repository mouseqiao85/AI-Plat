# 股票分析技能使用指南

## 概述

本指南介绍了如何使用增强版股票分析技能，特别强调新增的艾略特波浪理论分析功能。

## 安装和配置

### 1. 安装依赖包

```bash
pip install tushare pandas numpy scikit-learn requests textblob jieba snownlp scipy matplotlib
```

### 2. 获取tushare Token

1. 访问 [tushare官网](https://tushare.pro/)
2. 注册账户并获取免费Token
3. 将Token用于初始化分析器

## 基本使用方法

### 1. 增强版波浪理论分析

```python
from enhanced_stock_analysis_tool import EnhancedStockAnalyzer

# 初始化分析器
token = 'your_tushare_token'
analyzer = EnhancedStockAnalyzer(token)

# 使用增强版波浪理论分析
result = analyzer.enhanced_analysis_with_waves('002438', n_days=5)  # 分析江苏神通，预测未来5天
analyzer.print_analysis_report(result)
```

### 2. 波浪理论筛选

```python
from stock_screening_tool import StockScreeningTool

# 初始化选股工具
token = 'your_tushare_token'
screener = StockScreeningTool(token)

# 按波浪理论筛选：处于特定波浪阶段的股票
result = screener.wave_theory_screen(wave_stage='impulse_wave')  # 筛选处于推动浪的股票

# 综合筛选：结合波浪理论和其他条件
result = screener.comprehensive_screen_with_wave(
    price_min=0, 
    price_max=20, 
    wave_stage_preference='impulse_wave',  # 偏好的波浪阶段
    volume_percentile=30,
    rsi_min=30, 
    rsi_max=70
)

screener.print_screening_report(result)
```

## 分析框架详解

### 一、基础信息层
- 股票代码、公司名称、所属行业
- 当前价格、最新交易日、当日涨跌幅
- K线形态识别

### 二、波浪理论分析层
- **浪型划分与趋势结构判断**：识别当前处于第几浪
- **推动浪特征识别**：第1-5浪的特征分析
- **调整浪特征识别**：A-B-C浪的特征分析
- **趋势强度评估**：量化评估趋势强度
- **斐波那契分析**：回撤位和扩展位计算

### 三、技术指标验证层
- RSI、MACD等传统技术指标
- 均线系统分析
- 支撑阻力位识别

### 四、筹码分析层
- 成交量分析
- 筹码分布特征
- 主力动向判断

### 五、舆情分析层
- 市盈率、市净率等基本面指标
- 财务状况评估

### 六、基本面分析层
- 公司业务和行业地位
- 财务状况和业务特点

### 七、综合实战策略
- 基于多维度分析的交易信号
- 短中长期策略建议
- 风险控制措施

### 八、预测分析与模型验证
- 未来价格预测
- 模型准确率评估

### 九、投资策略建议
- 具体操作建议
- 仓位管理指导

### 十、综合评估
- 多维度共振分析
- 风险提示

## 波浪理论分析详解

### 1. 波浪阶段识别
- **推动浪阶段**：第1、3、5浪，通常与主要趋势方向一致
- **调整浪阶段**：第2、4浪，与主要趋势方向相反
- **调整浪类型**：A-B-C浪，复杂的调整模式

### 2. 趋势强度分类
- **强**：趋势明确，波动幅度大
- **中**：趋势清晰，波动适中
- **弱**：趋势模糊，波动较小

### 3. 交易信号生成
- **BUY信号**：处于推动浪，技术指标配合
- **HOLD信号**：处于调整浪，趋势不明朗
- **SELL信号**：处于调整浪末端，技术指标恶化

## 实际应用示例

### 示例1：江苏神通(002438)分析

```python
from enhanced_stock_analysis_tool import EnhancedStockAnalyzer

analyzer = EnhancedStockAnalyzer('your_token')
result = analyzer.enhanced_analysis_with_waves('002438', n_days=5)

# 输出示例：
# 股票代码: 002438
# 当前价格: 17.23元
# 当前波浪阶段: 可能处于推动浪阶段（第1、3、5浪）
# 趋势强度: 弱 (得分: 0)
# 交易信号: BUY (强度: 2/3)
# ...
```

### 示例2：综合筛选

```python
from stock_screening_tool import StockScreeningTool

screener = StockScreeningTool('your_token')
result = screener.comprehensive_screen_with_wave(
    price_min=10,
    price_max=50,
    wave_stage_preference='corrective_wave',  # 寻找处于调整浪的股票
    pb_max=3,
    pe_min=10,
    pe_max=30
)
```

## 风险提示

1. **波浪理论主观性**：不同分析师可能对同一段行情有不同的波浪划分
2. **市场环境变化**：市场结构变化可能影响波浪理论的有效性
3. **多维度验证**：建议结合技术指标、基本面等多个维度进行验证
4. **风险管理**：任何分析都不能保证100%准确，必须设置止损位

## 最佳实践

1. **结合使用**：将波浪理论与其他分析方法结合使用
2. **多时间框架**：在多个时间框架下验证波浪划分
3. **动态调整**：根据市场变化动态调整波浪划分
4. **风险控制**：始终设置合理的止损位
5. **持续学习**：不断学习和完善波浪理论知识

## 常见问题解答

Q: 如何判断波浪划分的准确性？
A: 通过斐波那契比例、交替原则、波浪特征等多个方面进行验证。

Q: 波浪理论适用于哪些市场？
A: 主要适用于有一定趋势性的市场，对于震荡市场效果可能不佳。

Q: 如何处理波浪划分的分歧？
A: 优先考虑主要趋势，设置多个可能的目标位和止损位。