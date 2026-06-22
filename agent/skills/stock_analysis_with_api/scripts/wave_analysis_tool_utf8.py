# -*- coding: utf-8 -*-
"""
波浪理论分析工具 - 结合艾略特波浪理论进行趋势分析
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class WaveAnalysisTool:
    """
    一个结合艾略特波浪理论进行趋势分析的工具。
    该工具通过分析价格行为、移动平均线、波动率和动量，
    尝试识别市场所处的波浪阶段（推动浪或调整浪），并提供交易信号。
    """

    # --- 类常量，用于配置分析参数 ---
    # 波动率阈值
    VOLATILITY_HIGH_THRESHOLD = 0.03
    VOLATILITY_MEDIUM_THRESHOLD = 0.015
    # 动量阈值
    MOMENTUM_STRONG_THRESHOLD = 0.02
    MOMENTUM_WEAK_THRESHOLD = -0.01
    # RSI/MACD 信号阈值
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    MACD_BULLISH_THRESHOLD = 0

    def __init__(self):
        """
        初始化波浪理论分析工具。
        """
        pass

    def identify_wave_structure(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        识别波浪结构的核心方法。
        :param price_data: 包含OHLC数据的DataFrame，必须有 'trade_date', 'open', 'high', 'low', 'close', 'pct_chg' 列。
        :return: 包含波浪结构分析结果的字典。
        """
        print("正在进行波浪结构分析...")
        df = price_data.copy()
        df = df.sort_values('trade_date').reset_index(drop=True)

        # --- 1. 数据预处理和指标计算 ---
        df['trend_direction'] = np.where(df['close'] > df['close'].shift(1), 1, -1)
        df['price_change'] = df['close'] - df['close'].shift(1)
        # 确保 pct_chg 存在且为数值类型
        if 'pct_chg' not in df.columns or not np.issubdtype(df['pct_chg'].dtype, np.number):
            df['pct_chg'] = df['close'].pct_change() * 100
        df['pct_change'] = df['pct_chg'] / 100.0

        # --- 2. 执行各项分析 ---
        wave_analysis = {
            'current_wave_potential': self._analyze_current_wave_phase(df),
            'wave_characteristics': self._identify_wave_features(df),
            'trend_strength': self._calculate_trend_strength(df),
            'support_resistance': self._identify_key_levels(df),
            'fibonacci_retracement': self._calculate_fibonacci_levels(df)  # 新增功能
        }

        print("波浪结构分析完成")
        return wave_analysis

    def _analyze_current_wave_phase(self, df: pd.DataFrame) -> str:
        """
        分析当前可能所处的波浪阶段。
        修复了原始代码中可能因数据不足导致NaN的问题。
        """
        # 确保有足够的数据计算均线
        if len(df) < 60:
            return "数据不足，无法判断波浪阶段"
        
        latest_data = df.tail(60)  # 使用最近60个交易日进行分析

        # 基于均线和价格行为判断
        ma5 = latest_data['close'].rolling(5).mean().iloc[-1]
        ma20 = latest_data['close'].rolling(20).mean().iloc[-1]
        ma60 = latest_data['close'].rolling(60).mean().iloc[-1]

        # 检查均线是否有效计算
        if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma60):
            return "均线计算中，请等待更多数据"

        current_price = df['close'].iloc[-1]

        # 分析趋势结构
        if ma5 > ma20 > ma60 and current_price > ma20:
            return "可能处于推动浪阶段（第1、3或5浪）"
        elif ma5 < ma20 and current_price < ma20 and ma20 < ma60:
            return "可能处于调整浪阶段（第2或4浪）"
        elif ma20 > ma60 and ma5 < ma20:  # 处于ma20和ma60之间
            return "可能处于第4浪调整或B浪反弹"
        else:
            return "趋势结构复杂或处于盘整期，需进一步确认"

    def _identify_wave_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        识别波浪的详细特征，如波动率、动量等。
        """
        recent_data = df.tail(60)
        volatility = recent_data['pct_change'].std()
        trend_length_info = self._measure_trend_length(recent_data)
        momentum = recent_data['pct_change'].mean()

        features = {
            'volatility_level': '高' if volatility > self.VOLATILITY_HIGH_THRESHOLD else (
                '中' if volatility > self.VOLATILITY_MEDIUM_THRESHOLD else '低'),
            'trend_length_info': trend_length_info,
            'momentum': momentum,
            'potential_wave_type': self._classify_wave_type(volatility, momentum)
        }
        return features

    def _measure_trend_length(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        测量最近一段趋势的长度和方向。
        """
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        trend_duration = len(df)

        return {
            'direction': 'up' if end_price > start_price else 'down',
            'duration_trading_days': trend_duration,
            'total_return': (end_price - start_price) / start_price if start_price != 0 else 0
        }

    def _classify_wave_type(self, volatility: float, momentum: float) -> str:
        """
        根据波动率和动量分类波浪类型。
        """
        if momentum > self.MOMENTUM_STRONG_THRESHOLD and volatility < 0.025:
            return "第3浪特征（强劲主升浪）"
        elif momentum > 0 and volatility > self.VOLATILITY_MEDIUM_THRESHOLD:
            return "第1浪或第5浪特征（情绪化推动）"
        elif momentum < self.MOMENTUM_WEAK_THRESHOLD and volatility < self.VOLATILITY_MEDIUM_THRESHOLD:
            return "调整浪特征（第2、4浪或A、C浪）"
        elif momentum > 0 and volatility < self.VOLATILITY_MEDIUM_THRESHOLD:
            return "B浪反弹特征"
        else:
            return "混合特征，需结合形态进一步分析"

    def _calculate_trend_strength(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算趋势强度，提供一个量化的分数。
        优化了计算公式，使其更具意义。
        """
        recent_data = df.tail(20)
        
        # 1. 均线排列得分 (0-1)
        ma5 = recent_data['close'].rolling(5).mean()
        ma20 = recent_data['close'].rolling(20).mean()
        ma60 = recent_data['close'].rolling(60).mean()

        # 确保均线有效
        if pd.isna(ma5.iloc[-1]) or pd.isna(ma20.iloc[-1]) or pd.isna(ma60.iloc[-1]):
            return {'strength_score': 0, 'classification': '弱'}

        ma_score = 0
        if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
            ma_score = 1.0  # 完美多头排列
        elif ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1]:
            ma_score = -1.0  # 完美空头排列
        elif ma20.iloc[-1] > ma60.iloc[-1] and ma5.iloc[-1] > ma20.iloc[-1]:
            ma_score = 0.5  # 初步多头
        elif ma20.iloc[-1] < ma60.iloc[-1] and ma5.iloc[-1] < ma20.iloc[-1]:
            ma_score = -0.5  # 初步空头

        # 2. 价格偏离度得分 (0-1)
        price_deviation = abs((df['close'].iloc[-1] - ma20.iloc[-1]) / ma20.iloc[-1])
        # 偏离度越小，趋势越稳定，得分越高
        deviation_score = max(0, 1 - price_deviation * 10)  # 乘以10放大影响

        # 3. 成交量配合得分 (0-1)
        if 'vol' in df.columns:
            vol_ma20 = df['vol'].rolling(20).mean().iloc[-1]
            current_vol = df['vol'].iloc[-1]
            vol_score = min(1, current_vol / (vol_ma20 * 1.5)) if vol_ma20 > 0 else 0.5
        else:
            vol_score = 0.5  # 如果没有成交量数据，给一个中性分

        # 综合得分 (加权平均)
        strength_score = (ma_score * 0.5) + (deviation_score * 0.3) + (vol_score * 0.2)
        classification = '强' if strength_score > 0.3 else ('中' if strength_score > -0.3 else '弱')

        return {
            'strength_score': round(strength_score, 2),
            'classification': classification
        }

    def _identify_key_levels(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        识别关键支撑阻力位（近期高低点）。
        """
        lookback_period = 60
        recent_data = df.tail(lookback_period)
        support = recent_data['low'].min()
        resistance = recent_data['high'].max()
        pivot = (support + resistance) / 2

        return {
            'support_level': support,
            'resistance_level': resistance,
            'pivot_level': pivot,
            'channel_width': resistance - support
        }

    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        计算斐波那契回撤和扩展位。
        这是波浪理论中预测目标位和回调位的关键。
        """
        if len(df) < 60:
            return {}

        # 寻找最近的显著高点和低点
        # 简化处理：直接使用最近60日的最高和最低点
        high_point = df['high'].tail(60).max()
        low_point = df['low'].tail(60).min()

        if high_point == low_point:
            return {}

        diff = high_point - low_point
        current_price = df['close'].iloc[-1]

        # 常见的斐波那契回撤位
        retracement_levels = {
            'Fib_0.0%': high_point,
            'Fib_23.6%': high_point - 0.236 * diff,
            'Fib_38.2%': high_point - 0.382 * diff,
            'Fib_50.0%': high_point - 0.500 * diff,
            'Fib_61.8%': high_point - 0.618 * diff,  # 黄金分割位
            'Fib_100.0%': low_point,
        }

        # 常见的斐波那契扩展位 (用于预测第3浪或第5浪目标)
        extension_levels = {
            'Fib_161.8%': high_point + 0.618 * diff,
            'Fib_261.8%': high_point + 1.618 * diff,
        }

        return {
            'retracement': retracement_levels,
            'extension': extension_levels,
            'range_high': high_point,
            'range_low': low_point
        }

    def find_pivots(self, df: pd.DataFrame, window: int = 5) -> Tuple[List[int], List[int]]:
        """
        寻找局部波峰和波谷（Pivots）。
        :param window: 判断 pivot 的窗口大小
        :return: (波峰索引列表, 波谷索引列表)
        """
        df_copy = df.copy()
        df_copy['is_peak'] = df_copy['high'].rolling(window * 2 + 1, center=True).max() == df_copy['high']
        df_copy['is_trough'] = df_copy['low'].rolling(window * 2 + 1, center=True).min() == df_copy['low']
        peak_indices = df_copy[df_copy['is_peak']].index.tolist()
        trough_indices = df_copy[df_copy['is_trough']].index.tolist()
        return peak_indices, trough_indices

    def multi_timeframe_analysis(self, daily_data: pd.DataFrame, weekly_data: pd.DataFrame, monthly_data: pd.DataFrame) -> Dict[str, Any]:
        """
        进行多周期波浪分析，并检查一致性。
        """
        print("进行多周期波浪分析...")
        daily_wave = self.identify_wave_structure(daily_data)
        weekly_wave = self.identify_wave_structure(weekly_data)
        monthly_wave = self.identify_wave_structure(monthly_data)

        consistency_check = self._check_multi_timeframe_consistency(
            daily_wave, weekly_wave, monthly_wave
        )

        multi_timeframe_result = {
            'daily_analysis': daily_wave,
            'weekly_analysis': weekly_wave,
            'monthly_analysis': monthly_wave,
            'consistency_check': consistency_check
        }
        return multi_timeframe_result

    def _check_multi_timeframe_consistency(self, daily: Dict, weekly: Dict, monthly: Dict) -> Dict[str, Any]:
        """
        检查多周期分析结果的一致性，提供更可靠的交易信号。
        """
        daily_trend = daily['current_wave_potential']
        weekly_trend = weekly['current_wave_potential']
        monthly_trend = monthly['current_wave_potential']

        consistency_score = 0
        rationale = []

        # 规则1: 大周期决定方向
        if "推动浪" in monthly_trend:
            consistency_score += 2
            rationale.append("月线处于推动浪，大方向向上")
        elif "调整浪" in monthly_trend:
            consistency_score -= 2
            rationale.append("月线处于调整浪，大方向向下或盘整")

        # 规则2: 中周期验证
        if "推动浪" in weekly_trend and "推动浪" in monthly_trend:
            consistency_score += 2
            rationale.append("周线与月线共振向上")
        elif "调整浪" in weekly_trend and "调整浪" in monthly_trend:
            consistency_score -= 2
            rationale.append("周线与月线共振向下")
        elif "推动浪" in weekly_trend and "调整浪" in monthly_trend:
            consistency_score -= 1
            rationale.append("周线反弹，但月线为调整，需谨慎")

        # 规则3: 小周期寻找入场点
        if "调整浪" in daily_trend and ("推动浪" in weekly_trend or "推动浪" in monthly_trend):
            consistency_score += 1
            rationale.append("日线回调，但大周期向上，是潜在买点")
        elif "推动浪" in daily_trend and ("调整浪" in weekly_trend or "调整浪" in monthly_trend):
            consistency_score -= 1
            rationale.append("日线冲高，但大周期向下，是潜在卖点或诱多")

        interpretation = "高一致性" if consistency_score >= 3 else \
                       "中等一致性" if consistency_score >= 1 else \
                       "低一致性/冲突" if consistency_score >= -1 else \
                       "高度冲突"

        return {
            'score': consistency_score,
            'interpretation': interpretation,
            'rationale': rationale
        }

    def generate_wave_signals(self, wave_analysis: Dict[str, Any], technical_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        结合波浪分析和技术指标生成交易信号。
        """
        print("生成波浪理论交易信号...")
        
        signal_strength = 0
        signal_type = "HOLD"
        rationale = []

        wave_phase = wave_analysis['current_wave_potential']
        wave_type = wave_analysis['wave_characteristics']['potential_wave_type']
        trend_strength = wave_analysis['trend_strength']['classification']

        # 从技术指标字典中获取值，提供默认值以防缺失
        rsi = technical_indicators.get('RSI', 50)
        macd_hist = technical_indicators.get('MACD_HIST', 0)  # MACD柱状图
        macd_line = technical_indicators.get('MACD_LINE', 0)
        signal_line = technical_indicators.get('SIGNAL_LINE', 0)
        current_price = technical_indicators.get('current_price', 0)
        ma5 = technical_indicators.get('MA5', 0)

        # --- 信号生成逻辑 ---

        # 强烈的买入信号：大周期向上，小周期回调结束
        if "推动浪" in wave_phase and trend_strength == '强' and "第3浪" in wave_type and rsi < 70 and macd_hist > 0:
            signal_type = "STRONG_BUY"
            signal_strength = 3
            rationale.append("主升浪（第3浪）特征明显，趋势强劲，MACD金叉")

        # 常规买入信号：处于推动浪，技术指标配合
        elif "推动浪" in wave_phase and rsi < 65 and macd_hist > 0 and current_price > ma5:
            signal_type = "BUY"
            signal_strength = 2
            rationale.append("处于推动浪阶段，技术指标显示多头占优")

        # 回调买入信号（抄底）：大周期向上，小周期进入调整
        elif "调整浪" in wave_phase and ("推动浪" in wave_analysis['weekly_analysis']['current_wave_potential'] if 'weekly_analysis' in wave_analysis else True) \
             and rsi < 30 and current_price < ma5:
            signal_type = "BUY_DIP"
            signal_strength = 2
            rationale.append("大周期向上，日线级别回调至超卖区，潜在买点")

        # 卖出/减仓信号：可能处于第5浪末端或B浪反弹结束
        elif "第5浪" in wave_type and rsi > 60:
            signal_type = "SELL_CAUTION"
            signal_strength = 2
            rationale.append("可能处于第5浪末端，RSI超买，警惕顶部")

        elif "B浪" in wave_type and rsi > 65:
            signal_type = "SELL"
            signal_strength = 2
            rationale.append("B浪反弹可能结束，RSI超买")

        # 强烈的卖出信号：进入明确的调整浪
        elif "调整浪" in wave_phase and rsi > 70:
            signal_type = "STRONG_SELL"
            signal_strength = 3
            rationale.append("进入调整浪阶段，且RSI严重超买，建议卖出")

        if not rationale:
            rationale.append(f"当前波浪阶段: {wave_phase}，趋势强度: {trend_strength}，无明确交易信号")

        return {
            'signal_type': signal_type,
            'signal_strength': signal_strength,
            'rationale': " | ".join(rationale),
            'wave_phase_info': wave_phase,
            'confirmation_needed': signal_strength > 0 and signal_strength < 3  # 中等强度信号需要进一步确认
        }