"""
优化版财经和历史数据获取模块
整合多个数据源以提高准确性
"""

import tushare as ts
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime, timedelta
import akshare as ak
import yfinance as yf
from typing import Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')

class EnhancedDataFetcher:
    """
    增强版数据获取器，整合多个数据源以提高财经和历史数据的准确性
    """
    
    def __init__(self, tushare_token: str = None):
        """
        初始化数据获取器
        :param tushare_token: tushare API token
        """
        self.tushare_token = tushare_token
        if tushare_token:
            ts.set_token(tushare_token)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            print("警告: 未提供tushare token，部分功能受限")
    
    def fetch_comprehensive_stock_data(self, stock_code: str, 
                                     start_date: str = '20240101', 
                                     end_date: str = None) -> Dict[str, Any]:
        """
        获取全面的股票数据，整合多个来源
        :param stock_code: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 综合数据字典
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        print(f"正在获取{stock_code}的综合数据...")
        
        # 获取不同来源的数据
        tushare_data = self._fetch_tushare_data(stock_code, start_date, end_date)
        akshare_data = self._fetch_akshare_data(stock_code, start_date, end_date)
        
        # 整合数据
        comprehensive_data = self._integrate_data_sources(tushare_data, akshare_data, stock_code)
        
        # 验证数据准确性
        validated_data = self._validate_and_clean_data(comprehensive_data)
        
        print(f"数据获取完成，共{len(validated_data)}条记录")
        
        return validated_data
    
    def _fetch_tushare_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从tushare获取数据
        """
        if not self.pro:
            print("tushare token未设置，跳过tushare数据获取")
            return None
        
        try:
            print("正在从tushare获取数据...")
            
            # 格式化股票代码
            if stock_code.endswith('.SZ') or stock_code.endswith('.SH'):
                ts_code = stock_code
            else:
                exchange = 'SZ' if stock_code.startswith(('00', '30', '15', '16', '18')) else 'SH'
                ts_code = f"{stock_code}.{exchange}"
            
            # 获取日线数据
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df.empty:
                print(f"tushare: 未能获取到{ts_code}的历史数据")
                return None
            
            # 重命名列以与其他数据源兼容
            df.rename(columns={'vol': 'volume'}, inplace=True)
            
            print(f"tushare: 成功获取 {len(df)} 条数据")
            return df
            
        except Exception as e:
            print(f"从tushare获取数据失败: {str(e)}")
            return None
    
    def _fetch_akshare_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从akshare获取数据
        """
        try:
            print("正在从akshare获取数据...")
            
            # akshare需要标准格式的股票代码
            if '.' in stock_code:
                standard_code = stock_code.split('.')[0]
            else:
                standard_code = stock_code
            
            # 根据股票代码判断交易所
            if stock_code.startswith(('00', '30', '15', '16', '18')):
                # 深圳股票
                df = ak.stock_zh_a_hist(symbol=standard_code, period="daily", 
                                        start_date=start_date, end_date=end_date, adjust="")
            else:
                # 上海股票
                df = ak.stock_zh_a_hist(symbol=standard_code, period="daily", 
                                        start_date=start_date, end_date=end_date, adjust="")
            
            if df.empty:
                print(f"akshare: 未能获取到{stock_code}的历史数据")
                return None
            
            # 重命名列以匹配tushare格式
            column_mapping = {
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close', 
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '涨跌幅': 'pct_chg',
                '涨跌额': 'change'
            }
            df.rename(columns=column_mapping, inplace=True)
            
            # 确保trade_date为datetime格式
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
            
            print(f"akshare: 成功获取 {len(df)} 条数据")
            return df
            
        except Exception as e:
            print(f"从akshare获取数据失败: {str(e)}")
            return None
    
    def _integrate_data_sources(self, tushare_data: pd.DataFrame, 
                               akshare_data: pd.DataFrame, 
                               stock_code: str) -> pd.DataFrame:
        """
        整合不同来源的数据
        """
        print("正在整合多源数据...")
        
        combined_data = None
        
        # 如果两个数据源都有数据，则进行整合
        if tushare_data is not None and akshare_data is not None:
            # 首先尝试基于日期合并
            merged = pd.merge(tushare_data, akshare_data, on='trade_date', how='outer', suffixes=('_tushare', '_akshare'))
            
            # 对于相同字段，优先使用tushare数据，如果为空则使用akshare数据
            final_data = tushare_data.copy() if len(tushare_data) > len(akshare_data) else akshare_data.copy()
            
            # 合并数据，优先使用质量更高的数据源
            common_cols = set(tushare_data.columns) & set(akshare_data.columns) - {'trade_date'}
            
            for col in common_cols:
                t_col = f"{col}_tushare"
                a_col = f"{col}_akshare"
                
                if t_col in merged.columns and a_col in merged.columns:
                    # 创建合并后的列，优先使用tushare数据
                    merged[col] = merged[t_col].fillna(merged[a_col])
            
            # 只保留非重复后缀的列
            cols_to_keep = [col for col in merged.columns if not col.endswith(('_tushare', '_akshare')) or col in ['trade_date']]
            final_data = merged[cols_to_keep]
            
            combined_data = final_data
            
        elif tushare_data is not None:
            combined_data = tushare_data
        elif akshare_data is not None:
            combined_data = akshare_data
        else:
            raise ValueError(f"无法从任何数据源获取{stock_code}的数据")
        
        # 按日期排序
        combined_data = combined_data.sort_values('trade_date').reset_index(drop=True)
        
        print(f"数据整合完成，共有 {len(combined_data)} 条记录")
        return combined_data
    
    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清理数据
        """
        print("正在验证和清理数据...")
        
        original_len = len(df)
        
        # 1. 删除完全重复的行
        df = df.drop_duplicates(subset=['trade_date'])
        
        # 2. 检查价格数据的合理性
        # 确保价格为正数
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                df = df[df[col] > 0]
        
        # 确保高>=开>=低，高>=收>=低
        if all(col in df.columns for col in ['high', 'open', 'low']):
            df = df[(df['high'] >= df['open']) & (df['open'] >= df['low'])]
        if all(col in df.columns for col in ['high', 'close', 'low']):
            df = df[(df['high'] >= df['close']) & (df['close'] >= df['low'])]
        
        # 3. 处理异常值（使用IQR方法）
        for col in price_cols:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        
        # 4. 检查成交量和成交额
        if 'volume' in df.columns:
            df = df[df['volume'] >= 0]
        if 'amount' in df.columns:
            df = df[df['amount'] >= 0]
        
        # 5. 填补缺失的百分比涨跌数据
        if 'pct_chg' not in df.columns and all(col in df.columns for col in ['close', 'prev_close']):
            df['pct_chg'] = (df['close'] - df['prev_close']) / df['prev_close'] * 100
        elif 'pct_chg' not in df.columns and 'close' in df.columns:
            df['pct_chg'] = df['close'].pct_change() * 100
        
        # 6. 按日期排序
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        cleaned_len = len(df)
        print(f"数据验证完成: {original_len} -> {cleaned_len} 条记录")
        
        return df
    
    def fetch_real_time_data_sina(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        使用新浪财经API获取实时数据
        """
        try:
            print(f"正在从新浪财经获取{stock_code}实时数据...")
            
            # 根据股票代码确定市场前缀
            prefix = 'sh' if stock_code.startswith(('5', '6', '9')) else 'sz'
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
                        open_price = float(values[1]) if values[1] and values[1] != '' else 0
                        prev_close = float(values[2]) if values[2] and values[2] != '' else 0
                        current_price = float(values[3]) if values[3] and values[3] != '' else 0
                        high = float(values[4]) if values[4] and values[4] != '' else 0
                        low = float(values[5]) if values[5] and values[5] != '' else 0
                        volume = float(values[8]) if values[8] and values[8] != '' else 0
                        amount = float(values[9]) if values[9] and values[9] != '' else 0
                        date = values[30] if len(values) > 30 else ''
                        time = values[31] if len(values) > 31 else ''
                        
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
                            'time': time,
                            'timestamp': datetime.now().isoformat()
                        }
        
            print(f"从新浪财经获取{stock_code}实时数据失败")
            return None
        except Exception as e:
            print(f"获取新浪实时数据时出错: {str(e)}")
            return None
    
    def fetch_financial_highlights(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取财务亮点数据
        """
        if not self.pro:
            print("tushare token未设置，无法获取财务数据")
            return None
        
        try:
            print(f"正在获取{stock_code}财务亮点数据...")
            
            # 获取股票基本信息
            basic_info = self.pro.stock_basic(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code)
            
            if basic_info.empty:
                print(f"无法获取{stock_code}的基本信息")
                return None
            
            name = basic_info.iloc[0]['name'] if 'name' in basic_info.columns else 'Unknown'
            industry = basic_info.iloc[0]['industry'] if 'industry' in basic_info.columns else 'Unknown'
            
            # 获取最新的财务数据
            today = datetime.now().strftime('%Y%m%d')
            start_of_year = f"{datetime.now().year}0101"
            
            # 获取估值数据
            daily_basic = self.pro.daily_basic(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                              start_date=start_of_year, end_date=today)
            
            latest_financial = {}
            if not daily_basic.empty:
                latest_row = daily_basic.iloc[-1]
                latest_financial = {
                    'pe': latest_row['pe'] if 'pe' in latest_row else None,
                    'pe_ttm': latest_row['pe_ttm'] if 'pe_ttm' in latest_row else None,
                    'pb': latest_row['pb'] if 'pb' in latest_row else None,
                    'ps': latest_row['ps'] if 'ps' in latest_row else None,
                    'pcf': latest_row['pcf'] if 'pcf' in latest_row else None
                }
            
            # 获取盈利能力数据
            profit_data = self.pro.income(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                         period=f"{datetime.now().year}12",
                                         fields='ts_code,basic_eps,diluted_eps,total_revenue,revenue_ps,operate_profit,profit_to_op,roe,roa')
            
            if not profit_data.empty:
                profit_row = profit_data.iloc[0]
                latest_financial.update({
                    'eps': profit_row['basic_eps'] if 'basic_eps' in profit_row and pd.notna(profit_row['basic_eps']) else None,
                    'revenue': profit_row['total_revenue'] if 'total_revenue' in profit_row and pd.notna(profit_row['total_revenue']) else None,
                    'revenue_ps': profit_row['revenue_ps'] if 'revenue_ps' in profit_row and pd.notna(profit_row['revenue_ps']) else None,
                    'operate_profit': profit_row['operate_profit'] if 'operate_profit' in profit_row and pd.notna(profit_row['operate_profit']) else None,
                    'roe': profit_row['roe'] if 'roe' in profit_row and pd.notna(profit_row['roe']) else None,
                    'roa': profit_row['roa'] if 'roa' in profit_row and pd.notna(profit_row['roa']) else None
                })
            
            # 获取资产负债数据
            balancesheet_data = self.pro.balancesheet(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                                     period=f"{datetime.now().year}12",
                                                     fields='ts_code,total_share,total_assets,total_liab,total_hldr_eqy_exc_min_int')
            
            if not balancesheet_data.empty:
                bs_row = balancesheet_data.iloc[0]
                latest_financial.update({
                    'total_share': bs_row['total_share'] if 'total_share' in bs_row and pd.notna(bs_row['total_share']) else None,
                    'total_assets': bs_row['total_assets'] if 'total_assets' in bs_row and pd.notna(bs_row['total_assets']) else None,
                    'total_liab': bs_row['total_liab'] if 'total_liab' in bs_row and pd.notna(bs_row['total_liab']) else None,
                    'equity': bs_row['total_hldr_eqy_exc_min_int'] if 'total_hldr_eqy_exc_min_int' in bs_row and pd.notna(bs_row['total_hldr_eqy_exc_min_int']) else None
                })
            
            result = {
                'stock_code': stock_code,
                'name': name,
                'industry': industry,
                **latest_financial
            }
            
            print(f"财务亮点数据获取完成")
            return result
            
        except Exception as e:
            print(f"获取财务亮点数据失败: {str(e)}")
            return None
    
    def validate_price_accuracy(self, historical_data: pd.DataFrame, real_time_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证价格数据的准确性
        """
        if historical_data.empty or real_time_data is None:
            return {'accuracy_status': 'insufficient_data', 'confidence': 0.0}
        
        # 获取最新历史数据
        latest_history = historical_data.iloc[-1] if len(historical_data) > 0 else None
        
        if latest_history is None:
            return {'accuracy_status': 'no_history', 'confidence': 0.0}
        
        validation_results = {}
        
        # 检查价格一致性
        if 'close' in latest_history:
            close_diff = abs(latest_history['close'] - real_time_data['current_price'])
            relative_diff = close_diff / real_time_data['current_price'] if real_time_data['current_price'] != 0 else float('inf')
            
            validation_results['price_match'] = relative_diff < 0.02  # 2%以内认为一致
            validation_results['price_diff_abs'] = close_diff
            validation_results['price_diff_rel'] = relative_diff
        
        # 检查日期一致性
        if 'trade_date' in latest_history:
            hist_date = latest_history['trade_date']
            rt_date = real_time_data['date'].replace('-', '') if '-' in real_time_data['date'] else real_time_data['date']
            
            # 比较日期
            validation_results['date_match'] = hist_date == rt_date
        
        # 计算综合准确性信心值
        accuracy_factors = []
        
        if 'price_match' in validation_results:
            # 价格匹配度
            accuracy_factors.append(0.9 if validation_results['price_match'] else 0.3)
        
        if 'date_match' in validation_results:
            # 日期匹配度
            accuracy_factors.append(0.8 if validation_results['date_match'] else 0.4)
        
        # 如果没有其他验证因素，使用默认值
        if not accuracy_factors:
            accuracy_factors.append(0.6)  # 默认中等信任度
        
        overall_confidence = sum(accuracy_factors) / len(accuracy_factors)
        
        validation_results['accuracy_status'] = 'consistent' if all([
            validation_results.get('price_match', True),
            validation_results.get('date_match', True)
        ]) else 'inconsistent'
        validation_results['confidence'] = round(overall_confidence, 3)
        
        return validation_results


# 使用示例
if __name__ == "__main__":
    # 示例使用
    token = '8a835a0cbcf32855a41cfe05457833bfd081de082a2699db11a2c484'  # 替换为实际的tushare token
    fetcher = EnhancedDataFetcher(token)
    
    # 获取飞龙股份的数据
    stock_code = '002536'  # 飞龙股份
    comprehensive_data = fetcher.fetch_comprehensive_stock_data(stock_code, start_date='20240101')
    
    # 获取实时数据
    real_time_data = fetcher.fetch_real_time_data_sina(stock_code)
    
    # 获取财务数据
    financial_data = fetcher.fetch_financial_highlights(stock_code)
    
    # 验证数据准确性
    if not comprehensive_data.empty and real_time_data:
        accuracy_validation = fetcher.validate_price_accuracy(comprehensive_data, real_time_data)
        print(f"数据准确性验证结果: {accuracy_validation}")
    
    print(f"获取了 {len(comprehensive_data)} 条历史数据")
    if real_time_data:
        print(f"实时价格: {real_time_data['current_price']}元")
    if financial_data:
        print(f"市盈率(PE): {financial_data.get('pe', 'N/A')}")
        print(f"净资产收益率(ROE): {financial_data.get('roe', 'N/A')}")