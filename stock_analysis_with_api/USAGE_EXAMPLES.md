# 股票分析技能使用示例

## 基本用法

```python
from skills.stock_analysis_with_api import analyze_stock

# 分析单个股票
result = analyze_stock("002536.SZ")  # 飞龙股份
```

## 批量分析

```python
from skills.stock_analysis_with_api import analyze_stock

stocks = ["002536.SZ", "600845.SH", "002438.SZ"]

for stock in stocks:
    print(f"正在分析 {stock}...")
    result = analyze_stock(stock)
    print(f"{stock} 分析完成\n")
```

## 获取支持的功能

```python
from skills.stock_analysis_with_api import get_supported_features

features = get_supported_features()
for i, feature in enumerate(features, 1):
    print(f"{i}. {feature}")
```

## 完整分析流程

```python
import os
from skills.stock_analysis_with_api.full_stock_analysis_workflow import main as workflow_main

# 设置API密钥
os.environ['WENXIN_API_KEY'] = 'your_api_key_here'

# 执行完整分析流程
result = workflow_main("002536.SZ")
```

## 高级用法

```python
import sys
import os

# 添加项目路径
sys.path.append("C:/Users/qiaoshuowen/clawd")

# 直接调用底层分析工具
from skills.stock_analysis_with_api.enhanced_stock_analysis_tool import EnhancedStockAnalyzer

token = 'your_token_here'
analyzer = EnhancedStockAnalyzer(token)

# 执行特定分析
result = analyzer.enhanced_analysis_with_waves("002536.SZ", n_days=5)
```

## 注意事项

1. 确保已设置 WENXIN_API_KEY 环境变量
2. 确保已安装所有依赖包
3. API调用可能需要一定时间
4. 股票代码格式：SZ表示深交所，SH表示上交所