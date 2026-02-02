"""
维克多·斯波朗迪123法则和2B法则实现模块
用于增强趋势反转识别能力
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats


class VicSperandeoStrategy:
    """
    维克多·斯波朗迪123法则和2B法则策略实现类
    """
    
    def __init__(self):
        pass
    
    def identify_trend_lines(self, df, lookback_period=20):
        """
        识别趋势线
        :param df: 包含OHLC数据的DataFrame
        :param lookback_period: 回溯周期
        :return: 上升趋势线和下降趋势线
        """
        # 计算局部高点和低点
        highs = df['high'].rolling(window=lookback_period, center=True).max()
        lows = df['low'].rolling(window=lookback_period, center=True).min()
        
        # 找到确切的局部极值点
        peak_indices = []
        valley_indices = []
        
        for i in range(lookback_period, len(df) - lookback_period):
            if df['high'][i] == highs[i]:
                peak_indices.append(i)
            if df['low'][i] == lows[i]:
                valley_indices.append(i)
        
        return peak_indices, valley_indices
    
    def detect_123_rule_reversal(self, df, trend_type='bullish'):
        """
        检测123法则反转信号
        :param df: 包含OHLC数据的DataFrame
        :param trend_type: 'bullish'(看涨反转) 或 'bearish'(看跌反转)
        :return: 反转信号详情
        """
        signals = []
        
        # 计算移动平均线以辅助趋势判断
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA50'] = df['close'].rolling(window=50).mean()
        
        # 找到趋势线突破点
        for i in range(5, len(df)-2):
            if trend_type == 'bearish':  # 看跌反转（上升趋势结束）
                # 条件1：趋势线被突破（价格跌破支撑线或均线下方）
                condition1 = (df['close'][i] < df['MA20'][i] and 
                             df['close'][i-1] > df['MA20'][i-1])
                
                # 条件2：上升趋势不再创新高
                condition2 = (i >= 2 and df['high'][i] < df['high'][i-1] and 
                             df['high'][i-1] < df['high'][i-2])
                
                # 条件3：价格向下穿越先前的短期回调低点
                if i >= 3:
                    prev_low_point = min(df['low'][i-3:i-1])
                    condition3 = df['close'][i] < prev_low_point
                
                if condition1 and condition2:
                    signal = {
                        'index': i,
                        'date': df.index[i],
                        'signal_type': '123_bearish_reversal',
                        'conditions_met': [],
                        'price': df['close'][i],
                        'description': '123法则看跌反转信号'
                    }
                    
                    if condition1:
                        signal['conditions_met'].append('趋势线突破')
                    if condition2:
                        signal['conditions_met'].append('不再创新高')
                    if 'condition3' in locals() and condition3:
                        signal['conditions_met'].append('跌破前期低点')
                        
                    signals.append(signal)
            
            elif trend_type == 'bullish':  # 看涨反转（下降趋势结束）
                # 条件1：趋势线被突破（价格突破阻力线或均线上方）
                condition1 = (df['close'][i] > df['MA20'][i] and 
                             df['close'][i-1] < df['MA20'][i-1])
                
                # 条件2：下降趋势不再创新低
                condition2 = (i >= 2 and df['low'][i] > df['low'][i-1] and 
                             df['low'][i-1] > df['low'][i-2])
                
                # 条件3：价格向上突破前期反弹高点
                if i >= 3:
                    prev_high_point = max(df['high'][i-3:i-1])
                    condition3 = df['close'][i] > prev_high_point
                
                if condition1 and condition2:
                    signal = {
                        'index': i,
                        'date': df.index[i],
                        'signal_type': '123_bullish_reversal',
                        'conditions_met': [],
                        'price': df['close'][i],
                        'description': '123法则看涨反转信号'
                    }
                    
                    if condition1:
                        signal['conditions_met'].append('趋势线突破')
                    if condition2:
                        signal['conditions_met'].append('不再创新低')
                    if 'condition3' in locals() and condition3:
                        signal['conditions_met'].append('突破前期高点')
                        
                    signals.append(signal)
        
        return signals
    
    def detect_2b_rule_signal(self, df, trend_type='bullish'):
        """
        检测2B法则信号
        :param df: 包含OHLC数据的DataFrame
        :param trend_type: 'bullish'(看涨2B) 或 'bearish'(看跌2B)
        :return: 2B信号详情
        """
        signals = []
        
        for i in range(3, len(df)-1):
            if trend_type == 'bearish':  # 看跌2B（假突破顶部）
                # 价格创新高后回落并跌破前高点
                if (i >= 2 and 
                    df['high'][i-1] == df['high'].rolling(window=20).max()[i-1] and  # 创近期新高
                    df['close'][i] < df['high'][i-1] * 0.995):  # 紧随其后价格回落（假设2B信号）
                    
                    signal = {
                        'index': i,
                        'date': df.index[i],
                        'signal_type': '2b_bearish',
                        'price': df['close'][i],
                        'description': '2B法则看跌信号（假突破顶部）',
                        'breakout_high': df['high'][i-1],
                        'confirmation_price': df['close'][i]
                    }
                    signals.append(signal)
            
            elif trend_type == 'bullish':  # 看涨2B（假突破底部）
                # 价格创新低后回升并突破前低点
                if (i >= 2 and 
                    df['low'][i-1] == df['low'].rolling(window=20).min()[i-1] and  # 创近期新低
                    df['close'][i] > df['low'][i-1] * 1.005):  # 紧随其后价格上涨
                    
                    signal = {
                        'index': i,
                        'date': df.index[i],
                        'signal_type': '2b_bullish',
                        'price': df['close'][i],
                        'description': '2B法则看涨信号（假突破底部）',
                        'breakout_low': df['low'][i-1],
                        'confirmation_price': df['close'][i]
                    }
                    signals.append(signal)
        
        return signals
    
    def analyze_trend_reversals(self, df):
        """
        综合分析趋势反转信号
        :param df: 包含OHLC数据的DataFrame
        :return: 所有反转信号的综合分析
        """
        # 检测123法则信号
        bullish_123_signals = self.detect_123_rule_reversal(df, 'bullish')
        bearish_123_signals = self.detect_123_rule_reversal(df, 'bearish')
        
        # 检测2B法则信号
        bullish_2b_signals = self.detect_2b_rule_signal(df, 'bullish')
        bearish_2b_signals = self.detect_2b_rule_signal(df, 'bearish')
        
        all_signals = {
            'bullish_123': bullish_123_signals,
            'bearish_123': bearish_123_signals,
            'bullish_2b': bullish_2b_signals,
            'bearish_2b': bearish_2b_signals
        }
        
        return all_signals
    
    def generate_trading_signals(self, df):
        """
        基于123法则和2B法则生成交易信号
        :param df: 包含OHLC数据的DataFrame
        :return: 交易信号列表
        """
        reversal_analysis = self.analyze_trend_reversals(df)
        
        trading_signals = []
        
        # 处理看涨信号（买入信号）
        for signal in reversal_analysis['bullish_123'] + reversal_analysis['bullish_2b']:
            signal['action'] = 'BUY'
            signal['confidence'] = self._calculate_confidence(signal)
            trading_signals.append(signal)
        
        # 处理看跌信号（卖出信号）
        for signal in reversal_analysis['bearish_123'] + reversal_analysis['bearish_2b']:
            signal['action'] = 'SELL'
            signal['confidence'] = self._calculate_confidence(signal)
            trading_signals.append(signal)
        
        # 按时间排序
        trading_signals.sort(key=lambda x: x['index'])
        
        return trading_signals
    
    def _calculate_confidence(self, signal):
        """
        计算信号置信度
        :param signal: 信号字典
        :return: 置信度分数 (0-1)
        """
        base_confidence = 0.6  # 基础置信度
        
        # 根据信号类型调整置信度
        if '2b' in signal['signal_type']:
            # 2B信号通常具有更高的置信度
            base_confidence += 0.15
        elif '123' in signal['signal_type']:
            # 123信号的置信度取决于满足的条件数量
            if 'conditions_met' in signal:
                base_confidence += 0.1 * len(signal['conditions_met']) / 3.0
        
        # 限制置信度在合理范围内
        return min(max(base_confidence, 0.1), 1.0)
    
    def plot_signals_on_chart(self, df, signals, title="维克多·斯波朗迪123法则和2B法则信号"):
        """
        在价格图表上绘制信号
        :param df: 包含OHLC数据的DataFrame
        :param signals: 信号列表
        :param title: 图表标题
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制价格线
        ax.plot(df.index, df['close'], label='收盘价', color='black')
        ax.plot(df.index, df['MA20'], label='MA20', color='blue', linestyle='--', alpha=0.7)
        ax.plot(df.index, df['MA50'], label='MA50', color='red', linestyle='--', alpha=0.7)
        
        # 标记买入信号
        buy_signals = [s for s in signals if s['action'] == 'BUY']
        if buy_signals:
            buy_dates = [s['date'] for s in buy_signals]
            buy_prices = [s['price'] for s in buy_signals]
            ax.scatter(buy_dates, buy_prices, marker='^', color='green', s=100, label='买入信号', zorder=5)
        
        # 标记卖出信号
        sell_signals = [s for s in signals if s['action'] == 'SELL']
        if sell_signals:
            sell_dates = [s['date'] for s in sell_signals]
            sell_prices = [s['price'] for s in sell_signals]
            ax.scatter(sell_dates, sell_prices, marker='v', color='red', s=100, label='卖出信号', zorder=5)
        
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()


def integrate_with_existing_analysis(analyzer_instance, df_with_indicators):
    """
    将维克多·斯波朗迪策略集成到现有分析中
    :param analyzer_instance: 现有分析器实例
    :param df_with_indicators: 包含技术指标的数据框
    :return: 增强的分析结果
    """
    # 创建策略实例
    strategy = VicSperandeoStrategy()
    
    # 生成反转信号
    reversal_signals = strategy.analyze_trend_reversals(df_with_indicators)
    
    # 生成交易信号
    trading_signals = strategy.generate_trading_signals(df_with_indicators)
    
    # 将信号整合到现有分析中
    enhanced_analysis = {
        'reversal_signals': reversal_signals,
        'trading_signals': trading_signals,
        'strategy_summary': _generate_strategy_summary(reversal_signals, trading_signals),
        'original_analysis': analyzer_instance.__dict__ if hasattr(analyzer_instance, '__dict__') else {}
    }
    
    return enhanced_analysis


def _generate_strategy_summary(reversal_signals, trading_signals):
    """
    生成策略摘要
    :param reversal_signals: 反转信号
    :param trading_signals: 交易信号
    :return: 策略摘要
    """
    summary = {
        'total_bullish_signals': len(reversal_signals['bullish_123']) + len(reversal_signals['bullish_2b']),
        'total_bearish_signals': len(reversal_signals['bearish_123']) + len(reversal_signals['bearish_2b']),
        'latest_bullish_signal': None,
        'latest_bearish_signal': None,
        'trading_opportunities': len(trading_signals)
    }
    
    # 获取最新的看涨信号
    all_bullish = reversal_signals['bullish_123'] + reversal_signals['bullish_2b']
    if all_bullish:
        latest_bullish = max(all_bullish, key=lambda x: x['index'])
        summary['latest_bullish_signal'] = latest_bullish
    
    # 获取最新的看跌信号
    all_bearish = reversal_signals['bearish_123'] + reversal_signals['bearish_2b']
    if all_bearish:
        latest_bearish = max(all_bearish, key=lambda x: x['index'])
        summary['latest_bearish_signal'] = latest_bearish
    
    return summary