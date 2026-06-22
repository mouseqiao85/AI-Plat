# -*- coding: utf-8 -*-
"""
股票分析技能主入口
提供统一的接口来调用股票分析功能
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from full_stock_analysis_workflow import main as workflow_main

def analyze_stock(stock_code="002438.SZ"):
    """
    分析指定股票
    :param stock_code: 股票代码，默认为江苏神通
    :return: 分析结果
    """
    print(f"开始分析股票: {stock_code}")
    result = workflow_main(stock_code)
    return result

def get_supported_features():
    """
    获取支持的功能列表
    """
    features = [
        "多维度技术分析（均线、MACD、RSI等）",
        "基本面分析（PE、PB等）",
        "波浪理论分析",
        "情绪分析",
        "价格预测",
        "风险评估",
        "操作建议",
        "文心5.0专业操盘手判断"
    ]
    return features

if __name__ == "__main__":
    # 如果直接运行此文件，执行默认分析
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
    else:
        stock_code = "002536.SZ"  # 默认分析飞龙股份
    
    analyze_stock(stock_code)