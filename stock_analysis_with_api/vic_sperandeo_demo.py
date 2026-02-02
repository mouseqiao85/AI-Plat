"""
维克多·斯波朗迪123法则和2B法则集成示例
展示如何使用增强的股票分析工具
"""

from stock_analysis_tool import StockAnalyzer
import os

def demonstrate_enhanced_analysis():
    """
    演示增强后的股票分析功能
    """
    # 注意：在实际使用时，请替换为真实的tushare token
    token = os.getenv('TUSHARE_TOKEN', 'YOUR_TUSHARE_TOKEN_HERE')
    
    if token == 'YOUR_TUSHARE_TOKEN_HERE':
        print("请先设置您的tushare token")
        return
    
    # 创建分析器实例
    analyzer = StockAnalyzer(token)
    
    # 分析示例股票
    stock_code = '000001'  # 平安银行作为示例
    
    print(f"开始分析股票: {stock_code}")
    print("此分析将包括维克多·斯波朗迪123法则和2B法则的趋势反转识别...")
    
    # 执行完整分析
    result = analyzer.analyze_stock(stock_code, n_days=5)
    
    if result:
        # 打印完整分析报告
        analyzer.print_analysis_report(result)
        
        # 单独访问维克多·斯波朗迪策略分析结果
        if 'vic_sperandeo_analysis' in result and result['vic_sperandeo_analysis']:
            vs_analysis = result['vic_sperandeo_analysis']
            
            print("\n" + "-"*50)
            print("维克多·斯波朗迪策略详细分析:")
            print("-"*50)
            
            # 显示所有交易信号
            all_signals = vs_analysis['trading_signals']
            if all_signals:
                print(f"\n检测到 {len(all_signals)} 个交易信号:")
                for signal in all_signals[-5:]:  # 显示最近的5个信号
                    print(f"  - {signal['date']}: {signal['action']} - {signal['description']} "
                          f"(价格: {signal['price']:.2f}, 置信度: {signal['confidence']:.2f})")
            else:
                print("\n未检测到明显的交易信号")
            
            # 显示123法则和2B法则的具体信号
            reversal_signals = vs_analysis['reversal_signals']
            print(f"\n123法则信号:")
            print(f"  看涨123信号: {len(reversal_signals['bullish_123'])} 个")
            print(f"  看跌123信号: {len(reversal_signals['bearish_123'])} 个")
            
            print(f"\n2B法则信号:")
            print(f"  看涨2B信号: {len(reversal_signals['bullish_2b'])} 个")
            print(f"  看跌2B信号: {len(reversal_signals['bearish_2b'])} 个")
        else:
            print("维克多·斯波朗迪策略分析不可用")
    
    else:
        print("分析失败")

def compare_strategies(original_recommendation, vs_signals):
    """
    对比原策略和维克多·斯波朗迪策略
    :param original_recommendation: 原始推荐
    :param vs_signals: 维克多·斯波朗迪信号
    """
    print("\n" + "="*60)
    print("策略对比分析:")
    print("="*60)
    print(f"传统技术分析推荐: {original_recommendation}")
    
    # 简单的信号汇总
    bullish_count = vs_signals['signal_counts']['bullish_signals'] if vs_signals else 0
    bearish_count = vs_signals['signal_counts']['bearish_signals'] if vs_signals else 0
    
    if bullish_count > bearish_count:
        vs_recommendation = "看涨"
    elif bearish_count > bullish_count:
        vs_recommendation = "看跌"
    else:
        vs_recommendation = "中性"
    
    print(f"维克多·斯波朗迪策略: {vs_recommendation} (看涨:{bullish_count}, 看跌:{bearish_count})")
    
    if original_recommendation in ['买入', '强烈买入'] and vs_recommendation == '看跌':
        print("注意: 两种策略给出相反信号，建议谨慎操作")
    elif original_recommendation in ['卖出', '强烈卖出'] and vs_recommendation == '看涨':
        print("注意: 两种策略给出相反信号，建议谨慎操作")
    else:
        print("两种策略方向一致，可增加信心")


if __name__ == "__main__":
    demonstrate_enhanced_analysis()