"""
股票分析工具 - 结合实时API和历史数据
"""

import tushare as ts
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# 导入维克多·斯波朗迪策略
try:
    from .vic_sperandeo_strategy import VicSperandeoStrategy
except ImportError:
    print("警告: 未找到维克多·斯波朗迪策略模块")
    VicSperandeoStrategy = None

class StockAnalyzer:
    def __init__(self, token):
        """
        初始化股票分析器
        :param token: tushare token
        """
        self.token = token
        ts.set_token(token)
        self.pro = ts.pro_api()

    def fetch_latest_price_sina(self, stock_code):
        """
        使用新浪财经API获取指定股票最新价格
        :param stock_code: 股票代码 (如 '002438')
        :return: 最新价格信息字典
        """
        try:
            # 根据股票代码确定市场前缀
            prefix = 'sh' if stock_code.startswith(('5', '6')) else 'sz'
            url = f"https://hq.sinajs.cn/list={prefix}{stock_code}"
            headers = {
                'Referer': 'https://finance.sina.com.cn/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.text
                # 解析数据
                pattern = r'hq_str_' + f'{prefix}{stock_code}' + r'="([^"]*)"'
                match = re.search(pattern, data)
                if match:
                    stock_data = match.group(1)
                    values = stock_data.split(',')
                    
                    if len(values) >= 32:
                        name = values[0]      # 股票名字
                        open_price = float(values[1]) if values[1] and values[1] != '' else 0  # 今日开盘价
                        prev_close = float(values[2]) if values[2] and values[2] != '' else 0  # 昨日收盘价
                        current_price = float(values[3]) if values[3] and values[3] != '' else 0  # 当前价格
                        high = float(values[4]) if values[4] and values[4] != '' else 0  # 今日最高价
                        low = float(values[5]) if values[5] and values[5] != '' else 0  # 今日最低价
                        volume = float(values[8]) if values[8] and values[8] != '' else 0  # 成交的股票数量
                        amount = float(values[9]) if values[9] and values[9] != '' else 0  # 成交金额
                        date = values[30]     # 日期
                        time = values[31]     # 时间
                        
                        return {
                            'name': name,
                            'current_price': current_price,
                            'prev_close': prev_close,
                            'open_price': open_price,
                            'high': high,
                            'low': low,
                            'volume': volume,
                            'amount': amount,
                            'date': date,
                            'time': time
                        }
        
            print(f"从新浪财经获取{stock_code}最新价格失败")
            return None
        except Exception as e:
            print(f"获取新浪数据时出错: {str(e)}")
            return None

    def get_historical_data_tushare(self, stock_code, start_date='20240101', end_date=None):
        """
        使用tushare获取历史数据
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: DataFrame
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            # 格式化股票代码为tushare格式
            if stock_code.endswith('.SZ') or stock_code.endswith('.SH'):
                ts_code = stock_code
            else:
                exchange = 'SZ' if stock_code.startswith(('00', '30', '15', '16', '18')) else 'SH'
                ts_code = f"{stock_code}.{exchange}"
            
            print(f"正在获取{ts_code}历史数据...")
            
            # 获取股票历史数据
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df.empty:
                print(f"未能获取到{ts_code}历史数据")
                return None
            
            print(f"成功获取到 {len(df)} 条历史数据")
            print(f"数据时间范围: {df['trade_date'].min()} 至 {df['trade_date'].max()}")
            
            return df
            
        except Exception as e:
            print(f"获取tushare历史数据失败: {str(e)}")
            return None

    def calculate_technical_indicators(self, df):
        """
        计算技术指标
        :param df: 包含OHLCV数据的DataFrame
        :return: 添加技术指标后的DataFrame
        """
        print("正在计算技术指标...")
        
        df = df.copy()
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 移动平均线
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA30'] = df['close'].rolling(window=30).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        
        # RSI (相对强弱指数)
        def calculate_rsi(prices, window=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        df['RSI'] = calculate_rsi(df['close'])
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['DIF'] = exp1 - exp2
        df['DEA'] = df['DIF'].ewm(span=9).mean()
        df['MACD'] = (df['DIF'] - df['DEA']) * 2
        
        # 布林带
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        df['BB_width'] = df['BB_upper'] - df['BB_lower']
        df['BB_position'] = (df['close'] - df['BB_lower']) / df['BB_width']
        
        # 成交量指标
        df['VOLUME_MA10'] = df['vol'].rolling(window=10).mean()
        df['VOLUME_RATIO'] = df['vol'] / df['VOLUME_MA10']
        
        # 价格位置指标
        df['HIGH_20D'] = df['high'].rolling(window=20).max()
        df['LOW_20D'] = df['low'].rolling(window=20).min()
        df['PRICE_POSITION'] = (df['close'] - df['LOW_20D']) / (df['HIGH_20D'] - df['LOW_20D'])
        
        # 删除包含NaN的行
        df = df.dropna()
        
        print(f"技术指标计算完成，剩余 {len(df)} 条有效数据")
        
        return df

    def build_prediction_model(self, df_with_indicators):
        """
        构建预测模型
        :param df_with_indicators: 包含技术指标的DataFrame
        :return: 模型, 清洗后的数据, 特征列表
        """
        print("构建预测模型...")
        
        # 选择技术指标作为特征
        feature_columns = [
            'open', 'high', 'low', 'close', 'vol', 'amount',
            'MA5', 'MA10', 'MA20', 'MA30', 'MA60',
            'RSI', 'DIF', 'DEA', 'MACD',
            'BB_width', 'BB_position',
            'VOLUME_RATIO', 'PRICE_POSITION'
        ]
        
        # 创建目标变量（下一交易日的收盘价）
        df_with_indicators['target'] = df_with_indicators['close'].shift(-1)
        
        # 删除包含NaN的行
        df_clean = df_with_indicators.dropna()
        
        if len(df_clean) < 50:
            print("数据量不足，无法进行有效分析")
            return None, None, None
        
        # 分离特征和目标
        X = df_clean[feature_columns]
        y = df_clean['target']
        
        print(f"特征矩阵形状: {X.shape}")
        print(f"目标变量形状: {y.shape}")
        
        # 分割数据集
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 使用随机森林回归器
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        rf_model.fit(X_train, y_train)
        
        # 预测
        y_pred = rf_model.predict(X_test)
        
        # 评估模型
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        print(f"\n模型评估结果:")
        print(f"MSE: {mse:.4f}")
        print(f"RMSE: {rmse:.4f}")
        print(f"R2: {r2:.4f}")
        
        return rf_model, df_clean, feature_columns

    def predict_next_n_days(self, model, df_clean, feature_columns, n_days=5):
        """
        预测未来N个交易日的股价
        :param model: 训练好的模型
        :param df_clean: 清洗后的数据
        :param feature_columns: 特征列名
        :param n_days: 预测天数
        :return: 预测结果列表
        """
        print(f"\n预测未来{n_days}个交易日股价...")
        
        # 获取最新的特征数据
        latest_features = df_clean[feature_columns].tail(1)
        
        predictions = []
        current_features = latest_features.copy()
        
        # 预测未来N个交易日
        for i in range(n_days):
            # 使用当前特征进行预测
            predicted_price = model.predict(current_features)[0]
            
            # 创建预测记录
            pred_info = {
                'day': i+1,
                'predicted_price': predicted_price,
                'current_price': current_features.iloc[0]['close'] if 'close' in current_features.columns else df_clean['close'].iloc[-1]
            }
            
            predictions.append(pred_info)
            
            # 更新特征（这里简化处理，实际应用中需要更复杂的特征工程）
            # 模拟下一个交易日的特征更新
            next_features = current_features.copy()
            # 这里我们只更新价格相关的特征，其他特征保持不变
            next_features.iloc[0, next_features.columns.get_loc('close')] = predicted_price
            next_features.iloc[0, next_features.columns.get_loc('open')] = predicted_price * (1 + np.random.normal(0, 0.005))
            next_features.iloc[0, next_features.columns.get_loc('high')] = max(next_features.iloc[0]['open'], predicted_price) * (1 + abs(np.random.normal(0, 0.01)))
            next_features.iloc[0, next_features.columns.get_loc('low')] = min(next_features.iloc[0]['open'], predicted_price) * (1 - abs(np.random.normal(0, 0.01)))
            
            current_features = next_features
        
        return predictions

    def generate_recommendation(self, predictions, current_price):
        """
        生成交易建议
        :param predictions: 预测结果
        :param current_price: 当前价格
        :return: 交易建议字符串
        """
        if not predictions:
            return "无法生成建议"
        
        # 计算整体涨跌幅
        final_price = predictions[-1]['predicted_price']
        overall_change = (final_price - current_price) / current_price * 100
        
        # 生成交易建议
        if overall_change > 2.0:
            return "强烈买入"
        elif overall_change > 0.5:
            return "买入"
        elif overall_change > -0.5:
            return "持有"
        elif overall_change > -2.0:
            return "卖出"
        else:
            return "强烈卖出"

    def analyze_with_vic_sperandeo_strategy(self, df_with_indicators):
        """
        使用维克多·斯波朗迪123法则和2B法则分析
        :param df_with_indicators: 包含技术指标的DataFrame
        :return: 策略分析结果
        """
        if VicSperandeoStrategy is None:
            print("维克多·斯波朗迪策略模块不可用")
            return None
        
        try:
            strategy = VicSperandeoStrategy()
            analysis_result = strategy.analyze_trend_reversals(df_with_indicators)
            trading_signals = strategy.generate_trading_signals(df_with_indicators)
            
            # 统计信号
            bullish_count = len(analysis_result['bullish_123']) + len(analysis_result['bullish_2b'])
            bearish_count = len(analysis_result['bearish_123']) + len(analysis_result['bearish_2b'])
            
            vic_sperandeo_analysis = {
                'reversal_signals': analysis_result,
                'trading_signals': trading_signals,
                'signal_counts': {
                    'bullish_signals': bullish_count,
                    'bearish_signals': bearish_count,
                    'total_signals': len(trading_signals)
                },
                'latest_signals': {
                    'bullish': self._get_latest_signal(trading_signals, 'BUY'),
                    'bearish': self._get_latest_signal(trading_signals, 'SELL')
                }
            }
            
            return vic_sperandeo_analysis
            
        except Exception as e:
            print(f"维克多·斯波朗迪策略分析出错: {str(e)}")
            return None

    def _get_latest_signal(self, signals, action_type):
        """
        获取最新的指定类型信号
        :param signals: 信号列表
        :param action_type: 信号类型 ('BUY' 或 'SELL')
        :return: 最新信号或None
        """
        filtered_signals = [s for s in signals if s.get('action') == action_type]
        if filtered_signals:
            return max(filtered_signals, key=lambda x: x['index'])
        return None

    def analyze_stock(self, stock_code, n_days=5):
        """
        完整的股票分析流程
        :param stock_code: 股票代码
        :param n_days: 预测天数
        :return: 分析结果字典
        """
        print(f"开始分析股票: {stock_code}")
        
        # 1. 获取最新价格
        print("\n1. 获取最新股价信息...")
        latest_price_data = self.fetch_latest_price_sina(stock_code)
        if latest_price_data:
            print(f"最新价格: {latest_price_data['current_price']}元")
            print(f"当日涨跌幅: {((latest_price_data['current_price'] - latest_price_data['prev_close']) / latest_price_data['prev_close'] * 100):+.2f}%")
            print(f"数据时间: {latest_price_data['date']} {latest_price_data['time']}")
        else:
            print("获取最新价格失败")
            latest_price_data = None
        
        # 2. 获取历史数据
        print("\n2. 获取历史数据...")
        historical_df = self.get_historical_data_tushare(stock_code)
        if historical_df is None:
            print("获取历史数据失败")
            return None
        
        # 3. 计算技术指标
        print("\n3. 计算技术指标...")
        df_with_indicators = self.calculate_technical_indicators(historical_df)
        
        # 4. 构建预测模型
        print("\n4. 构建预测模型...")
        model, clean_data, features = self.build_prediction_model(df_with_indicators)
        if model is None:
            print("模型构建失败")
            return None
        
        # 5. 使用维克多·斯波朗迪策略分析
        print("\n5. 进行维克多·斯波朗迪123法则和2B法则分析...")
        vic_sperandeo_analysis = self.analyze_with_vic_sperandeo_strategy(df_with_indicators)
        
        # 6. 预测未来N天
        print(f"\n6. 预测未来{n_days}个交易日...")
        predictions = self.predict_next_n_days(model, clean_data, features, n_days)
        
        # 7. 获取当前技术指标状态
        latest = clean_data.iloc[-1]
        current_price = latest['close']
        
        # 8. 生成交易建议
        recommendation = self.generate_recommendation(predictions, current_price)
        
        # 9. 返回完整分析结果
        result = {
            'stock_code': stock_code,
            'current_price': current_price,
            'predictions': predictions,
            'technical_indicators': {
                'RSI': latest['RSI'],
                'MACD': latest['MACD'],
                'MA5': latest['MA5'],
                'MA20': latest['MA20'],
                'MA60': latest['MA60']
            },
            'recommendation': recommendation,
            'model_accuracy': r2_score(clean_data['target'].dropna(), 
                                      model.predict(clean_data[features].dropna())),
            'latest_date': latest['trade_date'],
            'vic_sperandeo_analysis': vic_sperandeo_analysis  # 添加维克多·斯波朗迪策略分析结果
        }
        
        return result

    def print_analysis_report(self, analysis_result):
        """
        打印分析报告
        :param analysis_result: 分析结果
        """
        if analysis_result is None:
            print("分析失败，无法生成报告")
            return
        
        print("\n" + "="*60)
        print(f"股票代码: {analysis_result['stock_code']}")
        print(f"分析日期: {analysis_result['latest_date']}")
        print(f"当前价格: {analysis_result['current_price']:.2f}元")
        print("="*60)
        
        # 打印预测结果
        print("\n未来交易日预测:")
        current_price = analysis_result['current_price']
        for pred in analysis_result['predictions']:
            price_change = pred['predicted_price'] - current_price
            pct_change = (pred['predicted_price'] - current_price) / current_price * 100
            print(f"第{pred['day']}个交易日: 预测价格 {pred['predicted_price']:.2f}元, "
                  f"涨跌 {price_change:+.2f}元 ({pct_change:+.2f}%)")
        
        # 计算整体趋势
        final_price = analysis_result['predictions'][-1]['predicted_price']
        overall_change = (final_price - current_price) / current_price * 100
        print(f"\n整体预测: 期间预计涨跌幅 {overall_change:+.2f}%")
        print(f"交易建议: {analysis_result['recommendation']}")
        
        # 打印技术指标
        ti = analysis_result['technical_indicators']
        print(f"\n当前技术指标:")
        print(f"RSI: {ti['RSI']:.2f}")
        print(f"MACD: {ti['MACD']:.4f}")
        print(f"5日均线: {ti['MA5']:.2f}")
        print(f"20日均线: {ti['MA20']:.2f}")
        print(f"60日均线: {ti['MA60']:.2f}")
        
        # 打印维克多·斯波朗迪策略分析结果
        if 'vic_sperandeo_analysis' in analysis_result and analysis_result['vic_sperandeo_analysis']:
            print(f"\n维克多·斯波朗迪策略分析:")
            vs_analysis = analysis_result['vic_sperandeo_analysis']
            counts = vs_analysis['signal_counts']
            print(f"  看涨信号数量: {counts['bullish_signals']}")
            print(f"  看跌信号数量: {counts['bearish_signals']}")
            print(f"  总信号数量: {counts['total_signals']}")
            
            # 显示最近的信号
            latest_bullish = vs_analysis['latest_signals']['bullish']
            latest_bearish = vs_analysis['latest_signals']['bearish']
            
            if latest_bullish:
                print(f"  最近看涨信号: {latest_bullish['signal_type']} 于 {latest_bullish['date']}, 价格: {latest_bullish['price']:.2f}")
            if latest_bearish:
                print(f"  最近看跌信号: {latest_bearish['signal_type']} 于 {latest_bearish['date']}, 价格: {latest_bearish['price']:.2f}")
        
        print(f"\n模型准确率: R2 = {analysis_result['model_accuracy']:.4f}")
        print("="*60)


# 使用示例
if __name__ == "__main__":
    # 示例使用
    token = 'YOUR_TUSHARE_TOKEN_HERE'  # 需要替换为实际的token
    analyzer = StockAnalyzer(token)
    
    # 分析江苏神通
    result = analyzer.analyze_stock('002438', n_days=5)
    analyzer.print_analysis_report(result)