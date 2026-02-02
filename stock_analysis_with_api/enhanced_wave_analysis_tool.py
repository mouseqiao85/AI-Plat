"""
增强版波浪理论分析工具 - 结合艾略特波浪理论进行高级趋势分析
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class EnhancedWaveAnalysisTool:
    """
    增强版波浪理论分析工具。
    该工具通过分析价格行为、移动平均线、波动率和动量，
    识别市场所处的波浪阶段（推动浪或调整浪），并提供交易信号。
    新增功能包括波浪计数、模式识别、更精确的斐波那契分析等。
    """

    def __init__(self):
        """
        初始化增强版波浪理论分析工具。
        """
        # 波动率阈值
        self.VOLATILITY_HIGH_THRESHOLD = 0.03
        self.VOLATILITY_MEDIUM_THRESHOLD = 0.015
        # 动量阈值
        self.MOMENTUM_STRONG_THRESHOLD = 0.02
        self.MOMENTUM_WEAK_THRESHOLD = -0.01
        # RSI/MACD 信号阈值
        self.RSI_OVERBOUGHT = 70
        self.RSI_OVERSOLD = 30
        self.MACD_BULLISH_THRESHOLD = 0

    def enhanced_identify_wave_structure(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        增强版波浪结构识别方法。
        :param price_data: 包含OHLC数据的DataFrame，必须有 'trade_date', 'open', 'high', 'low', 'close', 'pct_chg' 列。
        :return: 包含增强波浪结构分析结果的字典。
        """
        print("正在进行增强版波浪结构分析...")
        df = price_data.copy()
        df = df.sort_values('trade_date').reset_index(drop=True)

        # 确保 pct_chg 存在且为数值类型
        if 'pct_chg' not in df.columns or not np.issubdtype(df['pct_chg'].dtype, np.number):
            df['pct_chg'] = df['close'].pct_change() * 100
        df['pct_change'] = df['pct_chg'] / 100.0

        # 执行各项分析
        wave_analysis = {
            'current_wave_potential': self._analyze_current_wave_phase(df),
            'wave_characteristics': self._identify_wave_features(df),
            'wave_count': self._perform_wave_counting(df),
            'trend_strength': self._calculate_trend_strength(df),
            'support_resistance': self._identify_key_levels(df),
            'fibonacci_analysis': self._calculate_enhanced_fibonacci_levels(df),
            'pattern_recognition': self._recognize_wave_patterns(df),
            'multi_timeframe_alignment': self._assess_multi_timeframe_alignment(df)
        }

        print("增强版波浪结构分析完成")
        return wave_analysis

    def _analyze_current_wave_phase(self, df: pd.DataFrame) -> str:
        """
        分析当前可能所处的波浪阶段。
        """
        if len(df) < 60:
            return "数据不足，无法判断波浪阶段"
        
        latest_data = df.tail(60)

        # 计算均线
        ma5 = latest_data['close'].rolling(5).mean().iloc[-1]
        ma20 = latest_data['close'].rolling(20).mean().iloc[-1]
        ma60 = latest_data['close'].rolling(60).mean().iloc[-1]

        if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma60):
            return "均线计算中，请等待更多数据"

        current_price = df['close'].iloc[-1]

        # 更细致的波浪阶段判断
        if ma5 > ma20 > ma60 and current_price > ma20:
            # 多头排列且价格在均线上方
            if self._is_strong_up_move(latest_data):
                return "可能处于第3浪推动（强劲主升浪）"
            else:
                return "可能处于第1或第5浪推动"
        elif ma5 < ma20 and current_price < ma20 and ma20 < ma60:
            # 空头排列且价格在均线下方
            if self._is_strong_down_move(latest_data):
                return "可能处于第3浪下跌（强劲主跌浪）"
            else:
                return "可能处于第2或第4浪调整"
        elif ma20 > ma60 and ma5 < ma20 and current_price > ma60:
            # 价格在60日均线上方，但5日均线下穿20日均线
            return "可能处于第4浪调整或B浪反弹"
        elif ma20 < ma60 and ma5 > ma20 and current_price < ma60:
            # 价格在60日均线下方，但5日均线上穿20日均线
            return "可能处于调整结束，准备进入推动浪"
        else:
            return "趋势结构复杂或处于盘整期，需进一步确认"

    def _is_strong_up_move(self, df_recent: pd.DataFrame) -> bool:
        """
        判断是否为强劲上涨走势
        """
        returns = df_recent['close'].pct_change().dropna()
        avg_positive_return = returns[returns > 0].mean() if any(returns > 0) else 0
        return avg_positive_return > 0.015  # 平均日涨幅超过1.5%

    def _is_strong_down_move(self, df_recent: pd.DataFrame) -> bool:
        """
        判断是否为强劲下跌走势
        """
        returns = df_recent['close'].pct_change().dropna()
        avg_negative_return = returns[returns < 0].mean() if any(returns < 0) else 0
        return avg_negative_return < -0.015  # 平均日跌幅超过1.5%

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
            'potential_wave_type': self._classify_wave_type(volatility, momentum),
            'wave_intensity': self._calculate_wave_intensity(df)
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
            return "第3浪特征（强劲主升/跌浪）"
        elif momentum > 0 and volatility > self.VOLATILITY_MEDIUM_THRESHOLD:
            return "第1浪或第5浪特征（情绪化推动）"
        elif momentum < self.MOMENTUM_WEAK_THRESHOLD and volatility < self.VOLATILITY_MEDIUM_THRESHOLD:
            return "调整浪特征（第2、4浪或A、C浪）"
        elif momentum > 0 and volatility < self.VOLATILITY_MEDIUM_THRESHOLD:
            return "B浪反弹特征"
        else:
            return "混合特征，需结合形态进一步分析"

    def _calculate_wave_intensity(self, df: pd.DataFrame) -> str:
        """
        计算波浪强度
        """
        recent_returns = df['close'].pct_change().tail(20).dropna()
        avg_return = recent_returns.mean()
        std_return = recent_returns.std()
        
        if std_return == 0:
            return "数据不足"
        
        intensity_ratio = abs(avg_return) / std_return
        
        if intensity_ratio > 0.5:
            return "高强度"
        elif intensity_ratio > 0.2:
            return "中等强度"
        else:
            return "低强度"

    def _perform_wave_counting(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行波浪计数功能
        """
        # 寻找显著的高点和低点作为潜在的波浪节点
        highs_lows = self._find_significant_highs_lows(df)
        
        # 基于高点低点进行波浪计数
        wave_count_analysis = self._count_waves_from_highs_lows(highs_lows, df)
        
        return wave_count_analysis

    def _find_significant_highs_lows(self, df: pd.DataFrame, window: int = 10) -> List[Dict[str, Any]]:
        """
        寻找显著的高点和低点
        """
        df_copy = df.copy()
        
        # 使用滚动窗口找到局部极值
        df_copy['is_peak'] = ((df_copy['high'] >= df_copy['high'].rolling(window, center=True).max()) &
                             (df_copy['high'] >= df_copy['high'].shift(-window//2).rolling(window).max()))
        df_copy['is_trough'] = ((df_copy['low'] <= df_copy['low'].rolling(window, center=True).min()) &
                               (df_copy['low'] <= df_copy['low'].shift(-window//2).rolling(window).min()))
        
        peaks = df_copy[df_copy['is_peak']].copy()
        troughs = df_copy[df_copy['is_trough']].copy()
        
        # 合并高点和低点，并按时间排序
        significant_points = []
        
        for idx, row in peaks.iterrows():
            significant_points.append({
                'index': idx,
                'date': row['trade_date'],
                'price': row['high'],
                'type': 'high',
                'volume': row.get('vol', 0)
            })
        
        for idx, row in troughs.iterrows():
            significant_points.append({
                'index': idx,
                'date': row['trade_date'],
                'price': row['low'],
                'type': 'low',
                'volume': row.get('vol', 0)
            })
        
        # 按时间排序
        significant_points.sort(key=lambda x: x['index'])
        
        # 过滤掉过于接近的点
        filtered_points = []
        min_distance = window // 2  # 最小距离
        
        for point in significant_points:
            if not filtered_points or (point['index'] - filtered_points[-1]['index']) >= min_distance:
                filtered_points.append(point)
        
        return filtered_points

    def _count_waves_from_highs_lows(self, highs_lows: List[Dict], df: pd.DataFrame) -> Dict[str, Any]:
        """
        从高点低点进行波浪计数
        """
        if len(highs_lows) < 2:
            return {
                'possible_counts': [],
                'most_likely_count': '无法确定',
                'confidence': '低'
            }
        
        # 尝试不同的波浪计数可能性
        possible_counts = []
        
        # 识别可能的5浪推动结构
        for i in range(len(highs_lows) - 4):
            # 检查是否符合推动浪的基本特征
            points = highs_lows[i:i+5]
            if self._validate_impulse_wave(points):
                possible_counts.append({
                    'type': 'impulse',
                    'start_idx': i,
                    'end_idx': i+4,
                    'points': points,
                    'validity_score': self._calculate_validity_score(points)
                })
        
        # 识别可能的3浪调整结构
        for i in range(len(highs_lows) - 2):
            points = highs_lows[i:i+3]
            if self._validate_corrective_wave(points):
                possible_counts.append({
                    'type': 'corrective',
                    'start_idx': i,
                    'end_idx': i+2,
                    'points': points,
                    'validity_score': self._calculate_validity_score(points)
                })
        
        # 确定最可能的波浪计数
        if possible_counts:
            best_count = max(possible_counts, key=lambda x: x['validity_score'])
            return {
                'possible_counts': possible_counts,
                'most_likely_count': f"{best_count['type']} wave from {best_count['points'][0]['date']} to {best_count['points'][-1]['date']}",
                'confidence': '高' if best_count['validity_score'] > 0.7 else ('中' if best_count['validity_score'] > 0.4 else '低'),
                'details': best_count
            }
        else:
            return {
                'possible_counts': [],
                'most_likely_count': '未识别到清晰的波浪结构',
                'confidence': '低'
            }

    def _validate_impulse_wave(self, points: List[Dict]) -> bool:
        """
        验证是否符合推动浪特征
        """
        if len(points) != 5:
            return False
        
        # 推动浪基本规则：
        # 1. 浪1、3、5是推动浪，浪2、4是调整浪
        # 2. 浪3通常是最重要的，不应是最短的
        # 3. 浪4不应进入浪1的价格区域
        
        try:
            # 检查浪的交替模式（假设推动浪为高-低-高-低-高的模式）
            directions = [p['type'] for p in points]
            
            # 应该是 high-low-high-low-high 或 low-high-low-high-low 的模式
            if directions not in [['high', 'low', 'high', 'low', 'high'], 
                                  ['low', 'high', 'low', 'high', 'low']]:
                return False
            
            prices = [p['price'] for p in points]
            
            # 检查推动浪的基本特征
            if directions[0] == 'high':  # 下降推动浪
                # 检查浪1、3、5向下，浪2、4向上
                wave_lengths = [prices[0]-prices[1], prices[2]-prices[1], prices[2]-prices[3], prices[4]-prices[3]]
                return all(length > 0 for length in [wave_lengths[0], wave_lengths[2]]) and all(length > 0 for length in [wave_lengths[1], wave_lengths[3]])
            else:  # 上升推动浪
                # 检查浪1、3、5向上，浪2、4向下
                wave_lengths = [prices[1]-prices[0], prices[1]-prices[2], prices[3]-prices[2], prices[3]-prices[4]]
                return all(length > 0 for length in [wave_lengths[0], wave_lengths[2]]) and all(length > 0 for length in [wave_lengths[1], wave_lengths[3]])
        except:
            return False

    def _validate_corrective_wave(self, points: List[Dict]) -> bool:
        """
        验证是否符合调整浪特征
        """
        if len(points) != 3:
            return False
        
        try:
            directions = [p['type'] for p in points]
            prices = [p['price'] for p in points]
            
            # 调整浪通常是3波结构：A-B-C
            # 对于下降调整浪：高-低-高
            # 对于上升调整浪：低-高-低
            if directions == ['high', 'low', 'high']:  # 下降调整浪
                return prices[0] > prices[1] and prices[2] > prices[1]
            elif directions == ['low', 'high', 'low']:  # 上升调整浪
                return prices[0] < prices[1] and prices[2] < prices[1]
            else:
                return False
        except:
            return False

    def _calculate_validity_score(self, points: List[Dict]) -> float:
        """
        计算波浪结构的有效性分数
        """
        if len(points) < 2:
            return 0.0
        
        # 基于价格幅度、时间跨度、成交量等因素计算有效性
        price_changes = []
        time_spans = []
        
        for i in range(1, len(points)):
            price_change = abs(points[i]['price'] - points[i-1]['price']) / points[i-1]['price']
            price_changes.append(price_change)
            
            time_span = (pd.to_datetime(points[i]['date']) - pd.to_datetime(points[i-1]['date'])).days
            time_spans.append(time_span)
        
        avg_price_change = np.mean(price_changes) if price_changes else 0
        avg_time_span = np.mean(time_spans) if time_spans else 0
        
        # 综合评分
        price_score = min(avg_price_change * 100, 1.0)  # 价格变化越大，分数越高，但不超过1.0
        time_score = min(avg_time_span / 30, 1.0)  # 时间跨度适中为佳
        
        return (price_score * 0.6 + time_score * 0.4)

    def _calculate_trend_strength(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算趋势强度，提供一个量化的分数。
        """
        recent_data = df.tail(20)
        
        # 均线排列得分
        ma5 = recent_data['close'].rolling(5).mean()
        ma20 = recent_data['close'].rolling(20).mean()
        ma60 = recent_data['close'].rolling(60).mean()

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

        # 价格偏离度得分
        price_deviation = abs((df['close'].iloc[-1] - ma20.iloc[-1]) / ma20.iloc[-1])
        deviation_score = max(0, 1 - price_deviation * 10)

        # 成交量配合得分
        if 'vol' in df.columns:
            vol_ma20 = df['vol'].rolling(20).mean().iloc[-1]
            current_vol = df['vol'].iloc[-1]
            vol_score = min(1, current_vol / (vol_ma20 * 1.5)) if vol_ma20 > 0 else 0.5
        else:
            vol_score = 0.5

        # 综合得分
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

    def _calculate_enhanced_fibonacci_levels(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算增强版斐波那契回撤和扩展位。
        """
        if len(df) < 60:
            return {}

        # 寻找最近的趋势高点和低点
        recent_df = df.tail(60).copy()
        highest_high = recent_df['high'].max()
        lowest_low = recent_df['low'].min()
        
        # 找到这些极值对应的日期
        high_date = recent_df[recent_df['high'] == highest_high]['trade_date'].iloc[0]
        low_date = recent_df[recent_df['low'] == lowest_low]['trade_date'].iloc[0]
        
        # 确定趋势方向
        trend_direction = 'up' if high_date > low_date else 'down'
        
        if highest_high == lowest_low:
            return {}

        diff = highest_high - lowest_low
        current_price = df['close'].iloc[-1]

        # 斐波那契回撤位
        if trend_direction == 'up':
            # 上升趋势的回撤位
            retracement_levels = {
                'Fib_0.0%': highest_high,  # 起始位
                'Fib_23.6%': highest_high - 0.236 * diff,
                'Fib_38.2%': highest_high - 0.382 * diff,
                'Fib_50.0%': highest_high - 0.500 * diff,
                'Fib_61.8%': highest_high - 0.618 * diff,  # 黄金分割位
                'Fib_78.6%': highest_high - 0.786 * diff,
                'Fib_100.0%': lowest_low,  # 结束位
            }
            # 扩展位
            extension_levels = {
                'Fib_127.2%': highest_high + 0.272 * diff,
                'Fib_161.8%': highest_high + 0.618 * diff,
                'Fib_200.0%': highest_high + 1.000 * diff,
                'Fib_261.8%': highest_high + 1.618 * diff,
                'Fib_300.0%': highest_high + 2.000 * diff,
            }
        else:
            # 下降趋势的回撤位（实际上是反弹位）
            retracement_levels = {
                'Fib_0.0%': lowest_low,  # 起始位
                'Fib_23.6%': lowest_low + 0.236 * diff,
                'Fib_38.2%': lowest_low + 0.382 * diff,
                'Fib_50.0%': lowest_low + 0.500 * diff,
                'Fib_61.8%': lowest_low + 0.618 * diff,  # 黄金分割位
                'Fib_78.6%': lowest_low + 0.786 * diff,
                'Fib_100.0%': highest_high,  # 结束位
            }
            # 扩展位（向下）
            extension_levels = {
                'Fib_127.2%': lowest_low - 0.272 * diff,
                'Fib_161.8%': lowest_low - 0.618 * diff,
                'Fib_200.0%': lowest_low - 1.000 * diff,
                'Fib_261.8%': lowest_low - 1.618 * diff,
                'Fib_300.0%': lowest_low - 2.000 * diff,
            }

        return {
            'trend_direction': trend_direction,
            'retracement': retracement_levels,
            'extension': extension_levels,
            'range_high': highest_high,
            'range_low': lowest_low,
            'current_position_in_fib_range': self._calculate_position_in_fib_range(current_price, lowest_low, highest_high)
        }

    def _calculate_position_in_fib_range(self, current_price, low, high):
        """
        计算当前价格在斐波那契区间的位置
        """
        if high == low:
            return 0.5  # 中间位置
        
        position = (current_price - low) / (high - low)
        return min(max(position, 0), 1)  # 确保在0-1范围内

    def _recognize_wave_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        识别常见的波浪模式
        """
        patterns = []
        
        # 检查头肩顶/底模式
        hs_pattern = self._detect_head_and_shoulders(df)
        if hs_pattern:
            patterns.append(hs_pattern)
        
        # 检查双顶/双底模式
        db_pattern = self._detect_double_top_bottom(df)
        if db_pattern:
            patterns.append(db_pattern)
        
        # 检查三角形模式
        tri_pattern = self._detect_triangle_pattern(df)
        if tri_pattern:
            patterns.append(tri_pattern)
        
        return {
            'detected_patterns': patterns,
            'count': len(patterns)
        }

    def _detect_head_and_shoulders(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        检测头肩顶/底模式
        """
        # 简化实现：查找连续的高-更高-较低的高点序列（头肩顶）
        # 或连续的低-更低-较高低点序列（头肩底）
        recent = df.tail(30)
        
        # 寻找局部高点
        highs = recent[recent['high'] == recent['high'].rolling(5, center=True).max()]
        
        if len(highs) >= 3:
            # 获取最近的三个显著高点
            top_three = highs.nlargest(3, 'high')
            
            # 检查是否形成头肩顶模式（中间最高，两边稍低）
            sorted_highs = top_three.sort_values('trade_date')
            if len(sorted_highs) >= 3:
                h1, h2, h3 = sorted_highs['high'].values[:3]
                
                # 检查中间的高点是否明显高于两边
                if h2 > h1 and h2 > h3 and abs(h1 - h3) < (h2 - max(h1, h3)) * 0.3:
                    return {
                        'pattern_type': 'head_and_shoulders_top',
                        'description': '检测到潜在头肩顶模式',
                        'confidence': '中等',
                        'key_points': {
                            'left_shoulder': {'date': sorted_highs.iloc[0]['trade_date'], 'price': h1},
                            'head': {'date': sorted_highs.iloc[1]['trade_date'], 'price': h2},
                            'right_shoulder': {'date': sorted_highs.iloc[2]['trade_date'], 'price': h3}
                        }
                    }
        
        return None

    def _detect_double_top_bottom(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        检测双顶/双底模式
        """
        recent = df.tail(30)
        
        # 寻找局部高点
        highs = recent[recent['high'] == recent['high'].rolling(5, center=True).max()]
        lows = recent[recent['low'] == recent['low'].rolling(5, center=True).min()]
        
        # 检查双顶
        if len(highs) >= 2:
            top_two = highs.nlargest(2, 'high')
            if len(top_two) == 2:
                h1, h2 = top_two['high'].values
                if abs(h1 - h2) / min(h1, h2) < 0.03:  # 价格相近（差异小于3%）
                    return {
                        'pattern_type': 'double_top',
                        'description': '检测到潜在双顶模式',
                        'confidence': '中等',
                        'key_points': {
                            'top1': {'date': top_two.iloc[0]['trade_date'], 'price': h1},
                            'top2': {'date': top_two.iloc[1]['trade_date'], 'price': h2}
                        }
                    }
        
        # 检查双底
        if len(lows) >= 2:
            bottom_two = lows.nsmallest(2, 'low')
            if len(bottom_two) == 2:
                l1, l2 = bottom_two['low'].values
                if abs(l1 - l2) / min(l1, l2) < 0.03:  # 价格相近（差异小于3%）
                    return {
                        'pattern_type': 'double_bottom',
                        'description': '检测到潜在双底模式',
                        'confidence': '中等',
                        'key_points': {
                            'bottom1': {'date': bottom_two.iloc[0]['trade_date'], 'price': l1},
                            'bottom2': {'date': bottom_two.iloc[1]['trade_date'], 'price': l2}
                        }
                    }
        
        return None

    def _detect_triangle_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        检测三角形模式
        """
        recent = df.tail(30)
        
        # 简单的三角形检测：价格波动范围逐渐收窄
        window_size = 5
        rolling_high_max = recent['high'].rolling(window_size).max()
        rolling_low_min = recent['low'].rolling(window_size).min()
        
        # 计算波动范围
        volatility_range = rolling_high_max - rolling_low_min
        
        # 检查最后几个窗口的波动范围是否在缩小
        if len(volatility_range) >= 6:
            recent_volatility = volatility_range.tail(6).dropna()
            if len(recent_volatility) >= 3:
                # 检查是否呈下降趋势
                slope = np.polyfit(range(len(recent_volatility)), recent_volatility.values, 1)[0]
                if slope < 0:  # 波动范围在缩小
                    return {
                        'pattern_type': 'triangle_consolidation',
                        'description': '检测到潜在三角形整理模式',
                        'confidence': '低',
                        'characteristic': '价格波动范围逐渐收窄'
                    }
        
        return None

    def _assess_multi_timeframe_alignment(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        评估多时间框架一致性
        """
        # 这里我们模拟多时间框架分析
        # 在实际应用中，这需要不同时间框架的数据
        
        recent_short = df.tail(10)  # 短期
        recent_medium = df.tail(30)  # 中期
        recent_long = df.tail(60)   # 长期
        
        short_trend = "up" if recent_short['close'].iloc[-1] > recent_short['close'].iloc[0] else "down"
        medium_trend = "up" if recent_medium['close'].iloc[-1] > recent_medium['close'].iloc[0] else "down"
        long_trend = "up" if recent_long['close'].iloc[-1] > recent_long['close'].iloc[0] else "down"
        
        alignment_score = 0
        if short_trend == medium_trend == long_trend:
            alignment_score = 1.0  # 完全一致
        elif short_trend == medium_trend or medium_trend == long_trend:
            alignment_score = 0.7  # 部分一致
        else:
            alignment_score = 0.3  # 不一致
        
        return {
            'short_term_trend': short_trend,
            'medium_term_trend': medium_trend,
            'long_term_trend': long_trend,
            'alignment_score': alignment_score,
            'alignment_description': "高度一致" if alignment_score > 0.8 else ("基本一致" if alignment_score > 0.5 else "存在分歧")
        }

    def generate_enhanced_wave_signals(self, wave_analysis: Dict[str, Any], technical_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成增强版波浪理论交易信号。
        """
        print("生成增强版波浪理论交易信号...")
        
        signal_strength = 0
        signal_type = "HOLD"
        rationale = []
        confidence = "中等"

        wave_phase = wave_analysis['current_wave_potential']
        wave_type = wave_analysis['wave_characteristics']['potential_wave_type']
        trend_strength = wave_analysis['trend_strength']['classification']
        wave_count_info = wave_analysis['wave_count']
        
        # 从技术指标字典中获取值
        rsi = technical_indicators.get('RSI', 50)
        macd_hist = technical_indicators.get('MACD_HIST', 0)
        macd_line = technical_indicators.get('MACD_LINE', 0)
        signal_line = technical_indicators.get('SIGNAL_LINE', 0)
        current_price = technical_indicators.get('current_price', 0)
        ma5 = technical_indicators.get('MA5', 0)

        # 增强的信号生成逻辑
        
        # 强烈买入信号：确认处于第3浪推动，技术指标配合
        if ("第3浪推动" in wave_phase or "第3浪特征" in wave_type) and trend_strength == '强':
            if rsi < 70 and macd_hist > 0 and current_price > ma5:
                signal_type = "STRONG_BUY"
                signal_strength = 4  # 增加强度
                rationale.append("确认处于第3浪推动，趋势强劲，技术指标多头排列")
                confidence = "高"
        
        # 常规买入信号：处于推动浪，技术指标配合
        elif "推动" in wave_phase and rsi < 65 and macd_hist > 0 and current_price > ma5:
            signal_type = "BUY"
            signal_strength = 2
            rationale.append("处于推动浪阶段，技术指标显示多头占优")
        
        # 调整浪结束买入信号：调整浪特征明显，且出现底部迹象
        elif "调整浪" in wave_phase and rsi < 35 and macd出现底背离迹象:
            signal_type = "BUY_AT_SUPPORT"
            signal_strength = 3
            rationale.append("处于调整浪末期，RSI超卖，出现潜在底部信号")
            confidence = "中等"
        
        # 潜在反转信号：在高位出现调整浪特征
        elif "调整浪" in wave_phase and rsi > 65:
            signal_type = "CAUTION_SELL"
            signal_strength = 2
            rationale.append("进入调整浪阶段，且RSI偏高，警惕短期回调")
        
        # 强烈卖出信号：确认进入下跌调整
        elif "调整" in wave_type and rsi > 75:
            signal_type = "STRONG_SELL"
            signal_strength = 4
            rationale.append("确认进入调整阶段，且RSI严重超买，建议减仓")
            confidence = "高"
        
        # 波浪计数信号：根据波浪计数结果
        if wave_count_info['confidence'] == '高':
            likely_count = wave_count_info['most_likely_count']
            if 'impulse' in likely_count and 'end' in likely_count:
                rationale.append(f"波浪计数显示{likely_count}，提供额外确认")
        
        # 模式识别信号：如果有识别到特定模式
        if wave_analysis['pattern_recognition']['count'] > 0:
            patterns = wave_analysis['pattern_recognition']['detected_patterns']
            for pattern in patterns:
                if pattern['pattern_type'] == 'double_top':
                    signal_type = "SELL_SIGNAL"
                    signal_strength = 3
                    rationale.append(f"检测到{pattern['description']}，可能预示趋势反转")
                    confidence = max(confidence, pattern['confidence'])
                elif pattern['pattern_type'] == 'double_bottom':
                    if signal_type in ["HOLD", "CAUTION_SELL"]:
                        signal_type = "BUY_SIGNAL"
                        signal_strength = 2
                        rationale.append(f"检测到{pattern['description']}，可能预示趋势反转")
                        confidence = max(confidence, pattern['confidence'])

        if not rationale:
            rationale.append(f"当前波浪阶段: {wave_phase}，趋势强度: {trend_strength}，未识别到明确交易信号")

        return {
            'signal_type': signal_type,
            'signal_strength': signal_strength,
            'rationale': " | ".join(rationale),
            'wave_phase_info': wave_phase,
            'confidence': confidence,
            'additional_confirmation': signal_strength > 0 and signal_strength < 4  # 中等强度信号需要进一步确认
        }