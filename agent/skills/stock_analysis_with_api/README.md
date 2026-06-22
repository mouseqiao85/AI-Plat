# 股票分析技能与文心5.0整合系统

## 系统概述
本系统结合了股票分析技能和百度文心5.0模型，可以生成专业的股票分析报告，并由AI模型提供专业的操盘手级判断。系统严格使用真实股票数据进行分析，不采用任何模拟数据。**新增增强版波浪理论分析、优化的文心操盘手解读模块和多源数据验证机制**。

## 快速开始

### 1. 设置API密钥
```bash
# Windows
set WENXIN_API_KEY=bce-v3/your-api-key-here
set TUSHARE_TOKEN=your-tushare-token-here

# Linux/Mac
export WENXIN_API_KEY=bce-v3/your-api-key-here
export TUSHARE_TOKEN=your-tushare-token-here
```

### 2. 安装依赖
```bash
pip install openai tushare pandas numpy scikit-learn matplotlib akshare yfinance textblob jieba snownlp
```

### 3. 运行分析
```bash
# 方法1: 使用全新的集成分析系统（推荐）
python integrated_stock_analysis_system.py 002536.SZ  # 飞龙股份

# 方法2: 原有完整流程（兼容）
python full_stock_analysis_workflow.py 002536.SZ  # 飞龙股份

# 方法3: 使用真实数据专用流程
python real_data_stock_analysis.py 002438.SZ  # 江苏神通

# 方法4: 通过入口脚本
python __init__.py 002536.SZ
```

## 功能特点

1. **真实数据驱动**：严格使用真实股票数据进行分析，不采用任何模拟数据
2. **多维度分析**：整合基本面、技术面、波浪理论等多维度分析
3. **专业判断**：利用文心5.0模型提供专业操盘手级判断
4. **智能预测**：基于真实历史数据训练的机器学习模型进行价格预测
5. **风险控制**：提供详细的风险管理和操作建议
6. **格式化输出**：按指定格式输出专业分析报告
7. **增强波浪理论**：新增精确的波浪计数、模式识别和斐波那契分析
8. **优化文心解读**：改进提示词工程，提供更专业的操盘手术语
9. **多源数据验证**：整合tushare、akshare等多个数据源，提高准确性
10. **维克多·斯波朗迪策略**：集成123法则和2B法则，增强趋势反转识别能力

## 输出文件
- `Integrated_Stock_Analysis_[股票代码]_[时间戳].md` - 集成分析报告（新）
- `Full_Stock_Analysis_[股票代码]_[时间戳].md` - 完整分析报告（原有）

## 核心模块

### 新增增强模块
- `integrated_stock_analysis_system.py` - 集成股票分析主系统（新增）
- `enhanced_wave_analysis_tool.py` - 增强版波浪理论分析工具（新增）
- `enhanced_wenxin_skill.py` - 优化版文心操盘手解读模块（新增）
- `enhanced_data_fetcher.py` - 增强版数据获取模块（新增）

### 原有核心模块
- `full_stock_analysis_workflow.py` - 完整流程主程序
- `real_data_stock_analysis.py` - 真实数据专用分析流程
- `enhanced_stock_analysis_tool.py` - 增强版股票分析工具（确保使用真实数据）
- `wave_analysis_tool.py` - 原版波浪理论分析工具
- `sentiment_analysis_tool.py` - 情绪分析工具
- `__init__.py` - 统一入口文件

## 增强功能详解

### 1. 增强波浪理论分析
- **波浪计数**：实现精确的波浪计数算法
- **模式识别**：识别头肩顶/底、双顶/底、三角形整理等经典模式
- **斐波那契分析**：增强的回撤和扩展位分析
- **多周期一致性**：评估不同时间框架的对齐程度

### 2. 优化文心操盘手解读
- **改进提示词**：更专业的操盘手术语和策略
- **结构化输出**：按5大维度输出专业分析
- **市场洞察**：结合A股市场特点提供针对性建议

### 3. 多源数据验证
- **tushare集成**：官方权威数据源
- **akshare补充**：开源数据验证
- **新浪财经实时**：实时价格验证
- **数据清洗**：异常值检测和清理

## 数据验证机制
- 所有价格数据来自实时API或官方历史数据
- 价格范围验证（确保在合理区间内）
- 多源数据交叉验证
- 自动回退机制（当实时数据不可用时使用最新历史数据）
- 异常值检测和清理机制

## 注意事项
1. API调用可能需要一定时间，请耐心等待
2. 确保API密钥有效且有足够的调用额度
3. 股票投资有风险，分析结果仅供参考
4. 所有分析均基于真实股票数据，不包含任何模拟数据
5. 推荐使用新的集成分析系统以获得最佳效果