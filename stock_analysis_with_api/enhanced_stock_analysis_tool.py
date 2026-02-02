"""
增强版股票分析工具 - 结合实时API、历史数据、技术分析和波浪理论
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

class EnhancedStockAnalyzer:
    def __init__(self, token):
        """
        初始化增强版股票分析器
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
        import time
        
        max_retries = 3
        for attempt in range(max_retries):
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
                    # 解析数据 - 修复正则表达式以处理中文字符
                    pattern = r'hq_str_' + prefix + stock_code + r'="(.*?)"'
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
                            bid = float(values[6]) if values[6] and values[6] != '' else 0  # 竞买价
                            ask = float(values[7]) if values[7] and values[7] != '' else 0  # 竞卖价
                            volume = float(values[8]) if values[8] and values[8] != '' else 0  # 成交的股票数量
                            amount = float(values[9]) if values[9] and values[9] != '' else 0  # 成交金额
                            b1_v = float(values[10]) if values[10] and values[10] != '' else 0  # 买一量
                            b1_p = float(values[11]) if values[11] and values[11] != '' else 0  # 买一价
                            b2_v = float(values[12]) if values[12] and values[12] != '' else 0  # 买二量
                            b2_p = float(values[13]) if values[13] and values[13] != '' else 0  # 买二价
                            b3_v = float(values[14]) if values[14] and values[14] != '' else 0  # 买三量
                            b3_p = float(values[15]) if values[15] and values[15] != '' else 0  # 买三价
                            b4_v = float(values[16]) if values[16] and values[16] != '' else 0  # 买四量
                            b4_p = float(values[17]) if values[17] and values[17] != '' else 0  # 买四价
                            b5_v = float(values[18]) if values[18] and values[18] != '' else 0  # 买五量
                            b5_p = float(values[19]) if values[19] and values[19] != '' else 0  # 买五价
                            a1_v = float(values[20]) if values[20] and values[20] != '' else 0  # 卖一量
                            a1_p = float(values[21]) if values[21] and values[21] != '' else 0  # 卖一价
                            a2_v = float(values[22]) if values[22] and values[22] != '' else 0  # 卖二量
                            a2_p = float(values[23]) if values[23] and values[23] != '' else 0  # 卖二价
                            a3_v = float(values[24]) if values[24] and values[24] != '' else 0  # 卖三量
                            a3_p = float(values[25]) if values[25] and values[25] != '' else 0  # 卖三价
                            a4_v = float(values[26]) if values[26] and values[26] != '' else 0  # 卖四量
                            a4_p = float(values[27]) if values[27] and values[27] != '' else 0  # 卖四价
                            a5_v = float(values[28]) if values[28] and values[28] != '' else 0  # 卖五量
                            a5_p = float(values[29]) if values[29] and values[29] != '' else 0  # 卖五价
                            date = values[30]     # 日期
                            time = values[31]     # 时间
                            
                            return {
                                'name': name,
                                'current_price': current_price,
                                'prev_close': prev_close,
                                'open_price': open_price,
                                'high': high,
                                'low': low,
                                'bid': bid,
                                'ask': ask,
                                'volume': volume,
                                'amount': amount,
                                'b1_v': b1_v,
                                'b1_p': b1_p,
                                'b2_v': b2_v,
                                'b2_p': b2_p,
                                'b3_v': b3_v,
                                'b3_p': b3_p,
                                'b4_v': b4_v,
                                'b4_p': b4_p,
                                'b5_v': b5_v,
                                'b5_p': b5_p,
                                'a1_v': a1_v,
                                'a1_p': a1_p,
                                'a2_v': a2_v,
                                'a2_p': a2_p,
                                'a3_v': a3_v,
                                'a3_p': a3_p,
                                'a4_v': a4_v,
                                'a4_p': a4_p,
                                'a5_v': a5_v,
                                'a5_p': a5_p,
                                'date': date,
                                'time': time
                            }
                
                print(f"从新浪财经获取{stock_code}最新价格失败 (尝试 {attempt + 1}/{max_retries})")
                
            except Exception as e:
                print(f"获取新浪数据时出错 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            
            # 如果不是最后一次尝试，则等待一段时间再重试
            if attempt < max_retries - 1:
                time.sleep(1)  # 等待1秒后重试
        
        print(f"已达到最大重试次数({max_retries})，仍无法获取{stock_code}最新价格")
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

    def calculate_kline_patterns(self, df):
        """
        K线形态分析
        :param df: 包含OHLC数据的DataFrame
        :return: 添加K线形态分析的DataFrame
        """
        print("正在进行K线形态分析...")
        
        df = df.copy()
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 计算K线实体大小
        df['body_size'] = abs(df['close'] - df['open'])
        df['total_size'] = df['high'] - df['low']
        df['body_ratio'] = df['body_size'] / df['total_size']
        
        # 上影线和下影线
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        
        # K线类型（阳线/阴线）
        df['bullish'] = df['close'] > df['open']
        
        # 识别常见K线形态
        df['pattern'] = 'None'
        
        # 长阳线
        long_candle_threshold = df['body_ratio'].quantile(0.7)
        df.loc[(df['body_ratio'] > long_candle_threshold) & (df['bullish']), 'pattern'] = 'Long Bullish'
        df.loc[(df['body_ratio'] > long_candle_threshold) & (~df['bullish']), 'pattern'] = 'Long Bearish'
        
        # 锤子线
        hammer_condition = (df['lower_shadow'] > df['body_size'] * 2) & (df['upper_shadow'] < df['body_size'])
        df.loc[hammer_condition, 'pattern'] = 'Hammer'
        
        # 上吊线
        hanging_man_condition = (df['lower_shadow'] > df['body_size'] * 2) & (df['upper_shadow'] < df['body_size']) & (df['body_ratio'] > 0.1)
        df.loc[hanging_man_condition, 'pattern'] = 'Hanging Man'
        
        # 倒锤子线
        inverted_hammer_condition = (df['upper_shadow'] > df['body_size'] * 2) & (df['lower_shadow'] < df['body_size'])
        df.loc[inverted_hammer_condition, 'pattern'] = 'Inverted Hammer'
        
        # 十字星
        cross_threshold = 0.1
        df.loc[df['body_ratio'] < cross_threshold, 'pattern'] = 'Doji'
        
        print(f"K线形态分析完成")
        
        return df

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
        
        # 计算支撑位和阻力位
        df['SUPPORT'] = df['LOW_20D']
        df['RESISTANCE'] = df['HIGH_20D']
        
        # 趋势指标
        df['TREND_SHORT'] = df['close'] > df['MA20']
        df['TREND_LONG'] = df['close'] > df['MA60']
        
        # 删除包含NaN的行
        df = df.dropna()
        
        print(f"技术指标计算完成，剩余 {len(df)} 条有效数据")
        
        return df

    def get_financial_data(self, stock_code):
        """
        获取基本面财务数据
        :param stock_code: 股票代码
        :return: 财务数据字典
        """
        try:
            print(f"正在获取{stock_code}财务数据...")
            
            # 获取股票基本信息
            basic_info = self.pro.stock_basic(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code)
            if not basic_info.empty:
                industry = basic_info.iloc[0]['industry'] if 'industry' in basic_info.columns else 'Unknown'
                name = basic_info.iloc[0]['name'] if 'name' in basic_info.columns else 'Unknown'
            else:
                industry = 'Unknown'
                name = 'Unknown'
            
            # 获取盈利数据
            profit_data = self.pro.income(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code, 
                                         period=f"{datetime.now().year}12", fields='ts_code,ann_date,f_ann_date,report_type,comp_type,basic_eps,diluted_eps,total_revenue,revenue_ps,total_cogs,operate_income,operate_profit,prepay_exp,prepay_exp_ttm')
            
            # 获取资产负债表数据
            balance_data = self.pro.balancesheet(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                                period=f"{datetime.now().year}12", fields='ts_code,ann_date,total_share,total_assets,total_liab,roe')
            
            # 获取现金流量表数据
            cashflow_data = self.pro.cashflow(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                             period=f"{datetime.now().year}12", fields='ts_code,ann_date,n_cashflow_act,n_net_interest_cash_flow,n_cashflow_st_inv')
            
            # 获取估值数据
            daily_basic = self.pro.daily_basic(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                              start_date=(datetime.now() - timedelta(days=30)).strftime('%Y%m%d'),
                                              end_date=datetime.now().strftime('%Y%m%d'))
            
            if not daily_basic.empty:
                pe = daily_basic['pe'].iloc[-1] if 'pe' in daily_basic.columns else None
                pb = daily_basic['pb'].iloc[-1] if 'pb' in daily_basic.columns else None
            else:
                pe = None
                pb = None
            
            financial_data = {
                'name': name,
                'industry': industry,
                'eps': profit_data['basic_eps'].iloc[0] if not profit_data.empty and 'basic_eps' in profit_data.columns else None,
                'revenue': profit_data['total_revenue'].iloc[0] if not profit_data.empty and 'total_revenue' in profit_data.columns else None,
                'roe': balance_data['roe'].iloc[0] if not balance_data.empty and 'roe' in balance_data.columns else None,
                'total_assets': balance_data['total_assets'].iloc[0] if not balance_data.empty and 'total_assets' in balance_data.columns else None,
                'pe': pe,
                'pb': pb,
                'cashflow': cashflow_data['n_cashflow_act'].iloc[0] if not cashflow_data.empty and 'n_cashflow_act' in cashflow_data.columns else None
            }
            
            print(f"财务数据获取完成")
            return financial_data
            
        except Exception as e:
            print(f"获取财务数据失败: {str(e)}")
            return {
                'name': 'Unknown',
                'industry': 'Unknown',
                'eps': None,
                'revenue': None,
                'roe': None,
                'total_assets': None,
                'pe': None,
                'pb': None,
                'cashflow': None
            }

    def analyze_market_sentiment(self, stock_code):
        """
        分析市场情绪和成交量
        :param stock_code: 股票代码
        :return: 市场情绪分析结果
        """
        try:
            print(f"正在分析{stock_code}市场情绪...")
            
            # 获取历史数据
            df = self.get_historical_data_tushare(stock_code, start_date=(datetime.now() - timedelta(days=90)).strftime('%Y%m%d'))
            
            if df is None or df.empty:
                return {'error': '无法获取历史数据'}
            
            # 计算成交量相关指标
            df['volume_ma'] = df['vol'].rolling(window=20).mean()
            df['volume_ratio'] = df['vol'] / df['volume_ma']
            df['price_change_pct'] = df['pct_chg']
            
            # 量价关系分析
            avg_volume_ratio = df['volume_ratio'].mean()
            recent_volume_ratio = df['volume_ratio'].iloc[-5:].mean()
            
            # 识别异常成交量
            volume_threshold = df['volume_ratio'].quantile(0.8)
            abnormal_volume_days = df[df['volume_ratio'] > volume_threshold]
            
            sentiment_analysis = {
                'avg_volume_ratio': avg_volume_ratio,
                'recent_volume_ratio': recent_volume_ratio,
                'abnormal_volume_count': len(abnormal_volume_days),
                'abnormal_volume_dates': abnormal_volume_days['trade_date'].tolist(),
                'volume_trend': 'Increasing' if recent_volume_ratio > avg_volume_ratio else 'Decreasing',
                'price_volume_correlation': df['vol'].corr(df['pct_chg']).round(3)
            }
            
            print(f"市场情绪分析完成")
            return sentiment_analysis
            
        except Exception as e:
            print(f"市场情绪分析失败: {str(e)}")
            return {'error': str(e)}

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
            # 使用更真实的模拟方式更新特征
            actual_current_price = current_features.iloc[0]['close'] if 'close' in current_features.columns else df_clean['close'].iloc[-1]
            price_change_pct = (predicted_price - actual_current_price) / actual_current_price
            
            # 根据预测的价格变动更新各项特征
            next_features.iloc[0, next_features.columns.get_loc('close')] = predicted_price
            next_features.iloc[0, next_features.columns.get_loc('open')] = actual_current_price * (1 + np.random.uniform(-0.02, 0.02))  # 随机开盘价变动
            next_features.iloc[0, next_features.columns.get_loc('high')] = max(next_features.iloc[0]['open'], predicted_price) * (1 + abs(np.random.uniform(0, 0.03)))  # 高价通常比收盘价高
            next_features.iloc[0, next_features.columns.get_loc('low')] = min(next_features.iloc[0]['open'], predicted_price) * (1 - abs(np.random.uniform(0, 0.03)))  # 低价通常比收盘价低
            # 成交量等其他特征也随价格趋势变化
            if 'vol' in next_features.columns:
                next_features.iloc[0, next_features.columns.get_loc('vol')] *= (1 + np.random.uniform(-0.1, 0.2))  # 成交量随机变化
            if 'amount' in next_features.columns:
                next_features.iloc[0, next_features.columns.get_loc('amount')] *= (1 + np.random.uniform(-0.1, 0.2))  # 成交额随机变化
            
            current_features = next_features
        
        return predictions

    def generate_recommendation(self, predictions, current_price, technical_indicators, financial_data, market_sentiment):
        """
        生成交易建议
        :param predictions: 预测结果
        :param current_price: 当前价格
        :param technical_indicators: 技术指标
        :param financial_data: 财务数据
        :param market_sentiment: 市场情绪
        :return: 交易建议和投资策略
        """
        if not predictions:
            return "无法生成建议", {}
        
        # 计算整体涨跌幅
        final_price = predictions[-1]['predicted_price']
        overall_change = (final_price - current_price) / current_price * 100
        
        # 综合技术指标分析
        rsi = technical_indicators['RSI']
        macd = technical_indicators['MACD']
        ma5 = technical_indicators['MA5']
        ma20 = technical_indicators['MA20']
        ma60 = technical_indicators['MA60']
        
        # 综合评分
        score = 0
        if overall_change > 2.0:
            score += 3
        elif overall_change > 0.5:
            score += 2
        elif overall_change > -0.5:
            score += 1
        elif overall_change > -2.0:
            score -= 1
        else:
            score -= 3
            
        # RSI评分
        if rsi > 70:
            score -= 2  # 超买
        elif rsi < 30:
            score += 2  # 超卖
        elif 40 <= rsi <= 60:
            score += 1  # 中性偏强
        
        # MACD评分
        if macd > 0:
            score += 1
        else:
            score -= 1
            
        # 均线评分
        if current_price > ma5 > ma20 > ma60:
            score += 2  # 多头排列
        elif current_price < ma5 < ma20 < ma60:
            score -= 2  # 空头排列
        elif current_price > ma5 and ma5 > ma20:
            score += 1  # 短期趋势向上
        elif current_price < ma5 and ma5 < ma20:
            score -= 1  # 短期趋势向下
        
        # 市场情绪评分
        if 'recent_volume_ratio' in market_sentiment:
            if market_sentiment['recent_volume_ratio'] > 1.2:
                score += 1  # 成交量放大
            elif market_sentiment['recent_volume_ratio'] < 0.8:
                score -= 1  # 成交量萎缩
        
        # 生成基本建议
        if score >= 4:
            recommendation = "强烈买入"
        elif score >= 2:
            recommendation = "买入"
        elif score >= 0:
            recommendation = "持有"
        elif score >= -2:
            recommendation = "卖出"
        else:
            recommendation = "强烈卖出"
        
        # 生成详细投资策略
        strategy = {
            'short_term': self._generate_short_term_strategy(score, rsi, macd, current_price, ma5, ma20),
            'medium_term': self._generate_medium_term_strategy(financial_data, current_price, ma20, ma60),
            'long_term': self._generate_long_term_strategy(financial_data, market_sentiment),
            'target_price': self._calculate_target_price(current_price, overall_change, financial_data),
            'stop_loss': self._calculate_stop_loss(current_price, ma5, ma20)
        }
        
        return recommendation, strategy

    def _generate_short_term_strategy(self, score, rsi, macd, current_price, ma5, ma20):
        """生成短期策略"""
        if score >= 2 and 30 < rsi < 70:
            return f"1-4周：逢低吸纳，关注{ma5:.2f}支撑，目标{current_price * 1.05:.2f}"
        elif score <= -2:
            return f"1-4周：逢高减仓，关注{ma5:.2f}压力，止损{ma20:.2f}"
        else:
            return f"1-4周：观望为主，等待方向明确"

    def _generate_medium_term_strategy(self, financial_data, current_price, ma20, ma60):
        """生成中期策略"""
        if financial_data['roe'] and financial_data['roe'] > 0.15:
            roe_text = "盈利能力较强"
        elif financial_data['roe'] and financial_data['roe'] > 0.08:
            roe_text = "盈利能力一般"
        else:
            roe_text = "盈利能力偏弱"
        
        pe_text = ""
        if financial_data['pe']:
            if financial_data['pe'] < 15:
                pe_text = "估值偏低"
            elif financial_data['pe'] > 30:
                pe_text = "估值偏高"
            else:
                pe_text = "估值合理"
        
        return f"1-6个月：{roe_text}{'，' + pe_text if pe_text else ''}，关注{ma20:.2f}支撑/{ma60:.2f}压力"

    def _generate_long_term_strategy(self, financial_data, market_sentiment):
        """生成长期策略"""
        industry_text = f"所属{financial_data['industry']}行业"
        if financial_data['revenue']:
            revenue_growth = "营收稳定增长" if financial_data['revenue'] > 0 else "营收下滑"
        else:
            revenue_growth = "营收情况不明"
        
        cashflow_text = "现金流健康" if financial_data['cashflow'] and financial_data['cashflow'] > 0 else "现金流需关注"
        
        return f"6个月以上：{industry_text}，{revenue_growth}，{cashflow_text}"

    def _calculate_target_price(self, current_price, predicted_change, financial_data):
        """计算目标价位"""
        if predicted_change > 5:
            target = current_price * 1.10  # 激进目标
        elif predicted_change > 2:
            target = current_price * 1.05  # 保守目标
        elif predicted_change < -5:
            target = current_price * 0.90  # 下行目标
        elif predicted_change < -2:
            target = current_price * 0.95  # 保守下行目标
        else:
            target = current_price * (1 + predicted_change/100 * 1.5)  # 基于预测
        
        return round(target, 2)

    def _calculate_stop_loss(self, current_price, ma5, ma20):
        """计算止损位"""
        # 基于移动平均线和当前价格设定止损
        if current_price > ma5 > ma20:
            stop_loss = min(ma5 * 0.95, current_price * 0.92)  # 多头排列，较宽松止损
        elif current_price < ma5 < ma20:
            stop_loss = max(ma5 * 1.05, current_price * 1.08)  # 空头排列，较严格止损
        else:
            stop_loss = current_price * 0.95  # 不确定趋势，中等止损
        
        return round(stop_loss, 2)

    def integrate_wave_analysis(self, df_with_indicators, stock_code):
        """
        集成波浪理论分析
        :param df_with_indicators: 包含技术指标的DataFrame
        :param stock_code: 股票代码
        :return: 波浪分析结果
        """
        print("集成波浪理论分析...")
        
        try:
            import os
            import sys
            # 添加当前目录到模块搜索路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            # 尝试导入UTF-8编码的波浪分析工具
            try:
                from wave_analysis_tool_utf8 import WaveAnalysisTool
            except ImportError:
                from wave_analysis_tool import WaveAnalysisTool
                
            wave_analyzer = WaveAnalysisTool()
            
            # 执行波浪分析
            wave_result = wave_analyzer.identify_wave_structure(df_with_indicators)
            
            # 生成波浪信号
            technical_indicators_for_signal = {
                'RSI': df_with_indicators['RSI'].iloc[-1] if 'RSI' in df_with_indicators.columns else 50,
                'MACD_HIST': df_with_indicators['MACD'].iloc[-1] if 'MACD' in df_with_indicators.columns else 0,
                'current_price': df_with_indicators['close'].iloc[-1],
                'MA5': df_with_indicators['MA5'].iloc[-1] if 'MA5' in df_with_indicators.columns else 0
            }
            
            wave_signals = wave_analyzer.generate_wave_signals(wave_result, technical_indicators_for_signal)
            
            result = {
                'wave_analysis': wave_result,
                'wave_signals': wave_signals
            }
            
            return result
        except ImportError as e:
            print(f"波浪理论分析模块不可用，跳过分析: {str(e)}")
            return {
                'wave_analysis': {},
                'wave_signals': {}
            }
        except Exception as e:
            print(f"波浪理论分析出错: {str(e)}")
            return {
                'wave_analysis': {},
                'wave_signals': {}
            }

    def enhanced_analysis_with_waves(self, stock_code, n_days=5):
        """
        增强版分析，包含波浪理论
        """
        print(f"开始增强版波浪理论分析: {stock_code}")
        
        # 原有的分析流程
        result = self.analyze_stock(stock_code, n_days)
        
        # 添加波浪理论分析
        if result:
            historical_df = self.get_historical_data_tushare(stock_code)
            if historical_df is not None:
                df_with_indicators = self.calculate_technical_indicators(historical_df)
                wave_analysis_result = self.integrate_wave_analysis(df_with_indicators, stock_code)
                
                # 合并波浪分析结果
                result.update(wave_analysis_result)
        
        return result

    def analyze_stock(self, stock_code, n_days=5):
        """
        完整的股票分析流程
        :param stock_code: 股票代码
        :param n_days: 预测天数
        :return: 分析结果字典
        """
        print(f"开始分析股票: {stock_code}")
        
        # 1. 获取历史数据
        print("\n1. 获取历史数据...")
        historical_df = self.get_historical_data_tushare(stock_code)
        if historical_df is None:
            print("获取历史数据失败")
            return None
        
        # 2. 获取最新价格
        print("\n2. 获取最新股价信息...")
        latest_price_data = self.fetch_latest_price_sina(stock_code)
        if latest_price_data:
            print(f"最新价格: {latest_price_data['current_price']}元")
            print(f"当日涨跌幅: {((latest_price_data['current_price'] - latest_price_data['prev_close']) / latest_price_data['prev_close'] * 100):+.2f}%")
            print(f"数据时间: {latest_price_data['date']} {latest_price_data['time']}")
        else:
            print("获取最新价格失败")
            # 如果获取失败，尝试从历史数据中获取最近的价格

        
        # 3. K线形态分析
        print("\n3. 进行K线形态分析...")
        kline_df = self.calculate_kline_patterns(historical_df)
        
        # 4. 计算技术指标
        print("\n4. 计算技术指标...")
        df_with_indicators = self.calculate_technical_indicators(kline_df)
        
        # 5. 获取财务数据
        print("\n5. 获取基本面财务数据...")
        financial_data = self.get_financial_data(stock_code)
        print(f"公司名称: {financial_data['name']}")
        print(f"所属行业: {financial_data['industry']}")
        if financial_data['eps']:
            print(f"每股收益(EPS): {financial_data['eps']}")
        if financial_data['pe']:
            print(f"市盈率(PE): {financial_data['pe']}")
        if financial_data['roe']:
            print(f"净资产收益率(ROE): {financial_data['roe']*100:.2f}%")
        
        # 6. 市场情绪分析
        print("\n6. 分析市场情绪...")
        market_sentiment = self.analyze_market_sentiment(stock_code)
        print(f"近期成交量比: {market_sentiment.get('recent_volume_ratio', 'N/A'):.2f}")
        print(f"量价相关性: {market_sentiment.get('price_volume_correlation', 'N/A'):.3f}")
        
        # 7. 构建预测模型
        print("\n7. 构建预测模型...")
        model, clean_data, features = self.build_prediction_model(df_with_indicators)
        if model is None:
            print("模型构建失败")
            return None
        
        # 8. 预测未来N天
        print(f"\n8. 预测未来{n_days}个交易日...")
        predictions = self.predict_next_n_days(model, clean_data, features, n_days)
        
        # 9. 获取当前技术指标状态
        latest = clean_data.iloc[-1]
        # 确保使用实时API获取的最新价格，如果获取失败则返回错误
        if latest_price_data:
            current_price = latest_price_data['current_price']
        else:
            print("无法获取最新实时价格，分析失败")
            return None
        
        # 10. 生成交易建议
        recommendation, strategy = self.generate_recommendation(
            predictions, current_price, 
            {
                'RSI': latest['RSI'],
                'MACD': latest['MACD'],
                'MA5': latest['MA5'],
                'MA20': latest['MA20'],
                'MA60': latest['MA60']
            },
            financial_data,
            market_sentiment
        )
        
        # 11. 返回完整分析结果
        result = {
            'stock_code': stock_code,
            'company_name': financial_data['name'],
            'industry': financial_data['industry'],
            'current_price': current_price,
            'predictions': predictions,
            'technical_indicators': {
                'RSI': latest['RSI'],
                'MACD': latest['MACD'],
                'MA5': latest['MA5'],
                'MA20': latest['MA20'],
                'MA60': latest['MA60'],
                'support': latest['SUPPORT'],
                'resistance': latest['RESISTANCE'],
                'trend_short': latest['TREND_SHORT'],
                'trend_long': latest['TREND_LONG']
            },
            'financial_data': financial_data,
            'market_sentiment': market_sentiment,
            'recommendation': recommendation,
            'investment_strategy': strategy,
            'model_accuracy': r2_score(clean_data['target'].dropna(), 
                                      model.predict(clean_data[features].dropna())),
            'latest_date': latest['trade_date'],
            'kline_patterns': kline_df['pattern'].iloc[-1]  # 最近K线形态
        }
        
        return result

    def print_analysis_report(self, analysis_result):
        """
        打印完整分析报告
        :param analysis_result: 分析结果
        """
        if analysis_result is None:
            print("分析失败，无法生成报告")
            return
        
        print("\n" + "="*80)
        print(f"股票代码: {analysis_result['stock_code']} | {analysis_result['company_name']}")
        print(f"所属行业: {analysis_result['industry']}")
        print(f"分析日期: {analysis_result['latest_date']}")
        print(f"当前价格: {analysis_result['current_price']:.2f}元")
        print(f"近期K线形态: {analysis_result['kline_patterns']}")
        print("="*80)
        
        # 关键分析结果摘要
        print(" --- 关键分析结果 ---")
        print(f"股票代码: {analysis_result['stock_code']}")
        print(f"当前价格: {analysis_result['current_price']:.2f}")
        
        # 波浪理论关键信息
        if 'wave_analysis' in analysis_result and analysis_result['wave_analysis']:
            wa = analysis_result['wave_analysis']
            print(f"当前波浪阶段: {wa['current_wave_potential']}")
            print(f"趋势强度: {wa['trend_strength']['classification']} (得分: {wa['trend_strength']['strength_score']})")
            print(f"波浪特征: {wa['wave_characteristics']['potential_wave_type']}")
        
        # 波浪理论交易信号
        if 'wave_signals' in analysis_result and analysis_result['wave_signals']:
            ws = analysis_result['wave_signals']
            print(" --- 交易信号 ---")
            print(f"信号类型: {ws['signal_type']}")
            print(f"信号强度: {ws['signal_strength']} (1-3)")
            print(f"信号依据: {ws['rationale']}")
        
        print("="*80)
        
        # 基本面分析
        print(f"\n【基本面分析】")
        fd = analysis_result['financial_data']
        if fd['eps']:
            print(f"  每股收益(EPS): {fd['eps']}")
        if fd['pe']:
            print(f"  市盈率(PE): {fd['pe']:.2f}")
        if fd['pb']:
            print(f"  市净率(PB): {fd['pb']:.2f}")
        if fd['roe']:
            print(f"  净资产收益率(ROE): {fd['roe']*100:.2f}%")
        if fd['revenue']:
            print(f"  总营收: {fd['revenue']/100000000:.2f}亿")
        
        # 技术指标分析
        print(f"\n【技术指标分析】")
        ti = analysis_result['technical_indicators']
        print(f"  RSI: {ti['RSI']:.2f}")
        print(f"  MACD: {ti['MACD']:.4f}")
        print(f"  移动平均线: MA5={ti['MA5']:.2f}, MA20={ti['MA20']:.2f}, MA60={ti['MA60']:.2f}")
        print(f"  支撑位: {ti['support']:.2f}  阻力位: {ti['resistance']:.2f}")
        print(f"  短期趋势: {'上升' if ti['trend_short'] else '下降'}")
        print(f"  长期趋势: {'上升' if ti['trend_long'] else '下降'}")
        
        # 波浪理论分析
        if 'wave_analysis' in analysis_result and analysis_result['wave_analysis']:
            print(f"\n【波浪理论分析】")
            wa = analysis_result['wave_analysis']
            print(f"  当前波浪阶段: {wa['current_wave_potential']}")
            print(f"  波浪特征: {wa['wave_characteristics']['potential_wave_type']}")
            print(f"  趋势强度: {wa['trend_strength']['classification']}")
            print(f"  关键支撑: {wa['support_resistance']['support_level']:.2f}")
            print(f"  关键阻力: {wa['support_resistance']['resistance_level']:.2f}")
            
            # 斐波那契分析
            if 'fibonacci_retracement' in wa and wa['fibonacci_retracement']:
                fib_levels = wa['fibonacci_retracement']
                if 'retracement' in fib_levels:
                    retracements = fib_levels['retracement']
                    fib_382 = retracements.get('Fib_38.2%', retracements.get('Fib_38.2'))
                    fib_618 = retracements.get('Fib_61.8%', retracements.get('Fib_61.8'))
                    if fib_382 is not None and fib_618 is not None:
                        print(f"  斐波那契回撤位: 38.2%={fib_382:.2f}, 61.8%={fib_618:.2f}")
                    elif fib_382 is not None:
                        print(f"  斐波那契回撤位: 38.2%={fib_382:.2f}")
                    elif fib_618 is not None:
                        print(f"  斐波那契回撤位: 61.8%={fib_618:.2f}")
        
        # 波浪信号分析
        if 'wave_signals' in analysis_result and analysis_result['wave_signals']:
            print(f"\n【波浪理论交易信号】")
            ws = analysis_result['wave_signals']
            print(f"  信号类型: {ws['signal_type']}")
            print(f"  信号强度: {ws['signal_strength']}/3")
            print(f"  分析依据: {ws['rationale']}")
            print(f"  需要确认: {'是' if ws['confirmation_needed'] else '否'}")
        
        # 市场情绪分析
        print(f"\n【市场情绪分析】")
        ms = analysis_result['market_sentiment']
        if 'recent_volume_ratio' in ms:
            print(f"  近期成交量比: {ms['recent_volume_ratio']:.2f}")
        if 'price_volume_correlation' in ms:
            print(f"  量价相关性: {ms['price_volume_correlation']:.3f}")
        if 'abnormal_volume_count' in ms:
            print(f"  异常成交量天数: {ms['abnormal_volume_count']}天")
        
        # 未来交易日预测
        print(f"\n【未来交易日预测】")
        current_price = analysis_result['current_price']
        for pred in analysis_result['predictions']:
            price_change = pred['predicted_price'] - current_price
            pct_change = (pred['predicted_price'] - current_price) / current_price * 100
            print(f"  第{pred['day']}个交易日: 预测价格 {pred['predicted_price']:.2f}元, "
                  f"涨跌 {price_change:+.2f}元 ({pct_change:+.2f}%)")
        
        # 计算整体趋势
        final_price = analysis_result['predictions'][-1]['predicted_price']
        overall_change = (final_price - current_price) / current_price * 100
        print(f"  整体预测: 期间预计涨跌幅 {overall_change:+.2f}%")
        
        # 投资策略
        print(f"\n【投资策略】")
        strategy = analysis_result['investment_strategy']
        print(f"  短期策略 (1-4周): {strategy['short_term']}")
        print(f"  中期策略 (1-6个月): {strategy['medium_term']}")
        print(f"  长期策略 (6个月以上): {strategy['long_term']}")
        print(f"  目标价位: {strategy['target_price']:.2f}元")
        print(f"  止损价位: {strategy['stop_loss']:.2f}元")
        
        # 交易建议
        print(f"\n【交易建议】")
        print(f"  建议操作: {analysis_result['recommendation']}")
        
        print(f"\n【模型准确率】")
        print(f"  R2得分: {analysis_result['model_accuracy']:.4f}")
        print("="*80)
        print("【风险提示】以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
        print("="*80)


# 使用示例
if __name__ == "__main__":
    # 示例使用
    token = '8a835a0cbcf32855a41cfe05457833bfd081de082a2699db11a2c484'  # 需要替换为实际的token
    analyzer = EnhancedStockAnalyzer(token)
    
    # 分析江苏神通
    result = analyzer.analyze_stock('002438', n_days=5)
    if result:
        analyzer.print_analysis_report(result)