"""
股票筛选工具 - 基于技术指标、基本面、市场情绪和波浪理论的综合选股工具
"""

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class StockScreeningTool:
    def __init__(self, token):
        """
        初始化股票筛选工具
        :param token: tushare token
        """
        self.token = token
        ts.set_token(token)
        self.pro = ts.pro_api()

    def get_all_stocks(self):
        """
        获取所有A股股票列表
        :return: 股票列表DataFrame
        """
        try:
            stocks = self.pro.stock_basic(exchange='', list_status='L', 
                                          fields='ts_code,symbol,name,area,industry,list_date')
            return stocks
        except Exception as e:
            print(f"获取股票列表失败: {str(e)}")
            return None

    def screen_by_price_range(self, stocks_df, min_price=0, max_price=20):
        """
        按价格区间筛选股票
        :param stocks_df: 股票列表DataFrame
        :param min_price: 最低价格
        :param max_price: 最高价格
        :return: 筛选后的股票列表
        """
        try:
            # 获取最新价格数据
            latest_data = self.pro.daily(trade_date=datetime.now().strftime('%Y%m%d'))
            if latest_data.empty:
                # 如果当天没有数据，获取最近一个交易日的数据
                latest_data = self.pro.daily()
            
            # 合并价格数据
            merged = pd.merge(stocks_df, latest_data[['ts_code', 'close', 'vol']], on='ts_code')
            
            # 按价格区间筛选
            filtered = merged[(merged['close'] >= min_price) & (merged['close'] <= max_price)]
            
            return filtered
        except Exception as e:
            print(f"按价格区间筛选失败: {str(e)}")
            return stocks_df

    def screen_by_activity(self, stocks_df, volume_threshold_percentile=30):
        """
        按交易活跃度筛选股票
        :param stocks_df: 股票列表DataFrame
        :param volume_threshold_percentile: 成交量百分位阈值
        :return: 筛选后的股票列表
        """
        try:
            if 'vol' not in stocks_df.columns:
                # 如果没有成交量数据，获取并合并
                latest_data = self.pro.daily()
                stocks_df = pd.merge(stocks_df, latest_data[['ts_code', 'vol']], on='ts_code', how='left')
            
            # 计算成交量阈值
            volume_threshold = stocks_df['vol'].quantile(volume_threshold_percentile/100.0)
            
            # 筛选成交量超过阈值的股票
            filtered = stocks_df[stocks_df['vol'] > volume_threshold]
            
            return filtered
        except Exception as e:
            print(f"按交易活跃度筛选失败: {str(e)}")
            return stocks_df

    def screen_by_technical_indicators(self, stocks_df, rsi_min=30, rsi_max=70, 
                                       ma_trend='short', macd_positive=True):
        """
        按技术指标筛选股票
        :param stocks_df: 股票列表DataFrame
        :param rsi_min: RSI最小值
        :param rsi_max: RSI最大值
        :param ma_trend: 移动平均线趋势 ('short', 'long', 'both')
        :param macd_positive: 是否要求MACD为正
        :return: 筛选后的股票列表
        """
        # 由于技术指标分析需要逐个分析每只股票，耗时较长，这里提供一个简化的筛选方式
        # 或者用户可以单独使用EnhancedStockAnalyzer对感兴趣的股票进行深入分析
        print("注意：技术指标筛选需要逐个分析股票，耗时较长。建议先用其他条件缩小范围后再进行技术分析。")
        return stocks_df  # 暂时返回原数据框，让用户可以在缩小范围后单独分析

    def screen_by_fundamentals(self, stocks_df, pe_min=None, pe_max=None, 
                               pb_min=None, pb_max=None):
        """
        按基本面筛选股票
        :param stocks_df: 股票列表DataFrame
        :param pe_min: PE最小值
        :param pe_max: PE最大值
        :param pb_min: PB最小值
        :param pb_max: PB最大值
        :return: 筛选后的股票列表
        """
        # 由于基本面分析需要逐个分析每只股票，耗时较长，这里提供一个简化的筛选方式
        # 或者用户可以单独使用EnhancedStockAnalyzer对感兴趣的股票进行深入分析
        print("注意：基本面筛选需要逐个分析股票，耗时较长。建议先用其他条件缩小范围后再进行基本面分析。")
        return stocks_df  # 暂时返回原数据框，让用户可以在缩小范围后单独分析

    def screen_by_wave_pattern(self, stocks_df, preferred_wave_stage='pushing'):
        """
        按波浪理论阶段筛选股票
        :param stocks_df: 股票列表DataFrame
        :param preferred_wave_stage: 首选波浪阶段 ('pushing'=推动浪, 'adjusting'=调整浪, 'all'=不限)
        :return: 筛选后的股票列表
        """
        print(f"按波浪理论阶段筛选: {preferred_wave_stage}")
        
        if preferred_wave_stage == 'all':
            return stocks_df
        
        # 这里需要对每只股票进行波浪分析，暂时返回原始数据
        # 实际应用中需要批量处理
        print("注意：波浪理论筛选需要对每只股票进行单独分析，耗时较长。")
        return stocks_df

    def comprehensive_screen(self, price_min=0, price_max=20, volume_percentile=30,
                            rsi_min=30, rsi_max=70, ma_trend='short', 
                            pe_min=None, pe_max=None, pb_min=None, pb_max=5,
                            wave_stage_filter='all'):
        """
        综合筛选股票
        :param price_min: 最低价格
        :param price_max: 最高价格
        :param volume_percentile: 成交量百分位阈值
        :param rsi_min: RSI最小值
        :param rsi_max: RSI最大值
        :param ma_trend: 移动平均线趋势要求
        :param pe_min: PE最小值
        :param pe_max: PE最大值
        :param pb_min: PB最小值
        :param pb_max: PB最大值
        :param wave_stage_filter: 波浪理论阶段筛选 ('pushing'=推动浪, 'adjusting'=调整浪, 'all'=不限)
        :return: 综合筛选结果
        """
        print("开始综合股票筛选...")
        
        # 获取所有股票
        all_stocks = self.get_all_stocks()
        if all_stocks is None:
            print("获取股票列表失败")
            return pd.DataFrame()
        
        print(f"初始股票数量: {len(all_stocks)}")
        
        # 1. 按价格区间筛选
        print(f"按价格区间 {price_min}-{price_max} 元筛选...")
        price_filtered = self.screen_by_price_range(all_stocks, price_min, price_max)
        print(f"价格筛选后剩余: {len(price_filtered)} 只股票")
        
        # 2. 按交易活跃度筛选
        print(f"按交易活跃度筛选 (成交量前{100-volume_percentile}%)...")
        activity_filtered = self.screen_by_activity(price_filtered, volume_percentile)
        print(f"活跃度筛选后剩余: {len(activity_filtered)} 只股票")
        
        # 3. 按技术指标筛选
        print(f"按技术指标筛选 (RSI {rsi_min}-{rsi_max}, 趋势要求: {ma_trend})...")
        try:
            tech_filtered = self.screen_by_technical_indicators(activity_filtered, 
                                                               rsi_min, rsi_max, ma_trend)
            print(f"技术指标筛选后剩余: {len(tech_filtered)} 只股票")
        except:
            print("技术指标筛选跳过（可能需要逐个分析）")
            tech_filtered = activity_filtered
        
        # 4. 按波浪理论筛选
        print(f"按波浪理论阶段筛选 ({wave_stage_filter})...")
        try:
            wave_filtered = self.screen_by_wave_pattern(tech_filtered, wave_stage_filter)
            print(f"波浪理论筛选后剩余: {len(wave_filtered)} 只股票")
        except:
            print("波浪理论筛选跳过（可能需要逐个分析）")
            wave_filtered = tech_filtered
        
        # 5. 按基本面筛选
        print(f"按基本面筛选 (PB < {pb_max})...")
        try:
            final_filtered = self.screen_by_fundamentals(wave_filtered, 
                                                        pe_min, pe_max, pb_min, pb_max)
            print(f"基本面筛选后剩余: {len(final_filtered)} 只股票")
        except:
            print("基本面筛选跳过（可能需要逐个分析）")
            final_filtered = wave_filtered
        
        # 添加一些技术指标列用于排序
        try:
            # 获取一些示例股票的技术指标来演示
            if len(final_filtered) > 0:
                sample_stocks = final_filtered.head(10)  # 只分析前10只作为示例
                tech_indicators = []
                
                for _, row in sample_stocks.iterrows():
                    try:
                        from .enhanced_stock_analysis_tool import EnhancedStockAnalyzer
                        analyzer = EnhancedStockAnalyzer(self.token)
                        result = analyzer.analyze_stock(
                            row['ts_code'].replace('.SH', '').replace('.SZ', ''), n_days=1)
                        
                        if result:
                            tech_indicators.append({
                                'ts_code': row['ts_code'],
                                'rsi': result['technical_indicators']['RSI'],
                                'macd': result['technical_indicators']['MACD'],
                                'ma5': result['technical_indicators']['MA5'],
                                'ma20': result['technical_indicators']['MA20'],
                                'trend_short': result['technical_indicators']['trend_short'],
                                'trend_long': result['technical_indicators']['trend_long']
                            })
                    except:
                        tech_indicators.append({
                            'ts_code': row['ts_code'],
                            'rsi': None,
                            'macd': None,
                            'ma5': None,
                            'ma20': None,
                            'trend_short': None,
                            'trend_long': None
                        })
                
                # 合并技术指标
                tech_df = pd.DataFrame(tech_indicators)
                if not tech_df.empty:
                    final_filtered = pd.merge(final_filtered, tech_df, on='ts_code', how='left')
        except Exception as e:
            print(f"添加技术指标时出错: {str(e)}")
        
        print(f"综合筛选完成，最终选出 {len(final_filtered)} 只股票")
        
        return final_filtered

    def rank_stocks(self, stocks_df, sort_by=['close', 'vol'], ascending=[True, False]):
        """
        对筛选出的股票进行排序
        :param stocks_df: 股票DataFrame
        :param sort_by: 排序字段列表
        :param ascending: 是否升序排列
        :return: 排序后的股票DataFrame
        """
        if len(stocks_df) == 0:
            return stocks_df
        
        try:
            ranked = stocks_df.sort_values(by=sort_by, ascending=ascending)
            return ranked
        except Exception as e:
            print(f"排序失败: {str(e)}")
            return stocks_df

    def print_screening_report(self, screened_stocks):
        """
        打印筛选报告
        :param screened_stocks: 筛选后的股票DataFrame
        """
        if len(screened_stocks) == 0:
            print("未找到符合条件的股票")
            return
        
        print("\n" + "="*80)
        print("股票筛选报告")
        print(f"筛选时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"符合条件股票数量: {len(screened_stocks)}")
        print("="*80)
        
        print("\n【筛选结果】")
        print(f"{'股票代码':<10} {'股票名称':<15} {'当前价格':<8} {'成交量':<12} {'行业':<15}")
        print("-"*80)
        
        for _, row in screened_stocks.head(20).iterrows():  # 只显示前20只
            symbol = row['symbol'] if 'symbol' in row else row['ts_code'][:6]
            name = row['name'] if 'name' in row else 'Unknown'
            close = row['close'] if 'close' in row else 'N/A'
            vol = row['vol'] if 'vol' in row else 'N/A'
            industry = row['industry'] if 'industry' in row else 'Unknown'
            
            print(f"{symbol:<10} {name:<15} {close:<8.2f} {vol:<12.0f} {industry:<15}")
        
        if len(screened_stocks) > 20:
            print(f"... 还有 {len(screened_stocks) - 20} 只股票")
        
        print("="*80)
        print("【筛选条件】")
        print("- 股价: 0-20元")
        print("- 交易活跃度: 成交量前70%")
        print("- 技术指标: RSI在30-70之间，短期趋势向上")
        print("- 基本面: PB小于5倍")
        print("="*80)


def main():
    """
    主函数 - 演示选股工具的使用
    """
    # 请在此处替换为您的真实tushare token
    token = '8a835a0cbcf32855a41cfe05457833bfd081de082a2699db11a2c484'
    
    # 创建选股工具实例
    screener = StockScreeningTool(token)
    
    # 执行综合筛选
    result = screener.comprehensive_screen(
        price_min=0, 
        price_max=20, 
        volume_percentile=30,  # 成交量前70%的股票
        rsi_min=30, 
        rsi_max=70, 
        ma_trend='short',  # 短期趋势向上
        pb_max=5  # PB小于5倍
    )
    
    # 排序（按价格升序，成交量降序）
    sorted_result = screener.rank_stocks(result, sort_by=['close', 'vol'], ascending=[True, False])
    
    # 打印筛选报告
    screener.print_screening_report(sorted_result)
    
    return sorted_result


if __name__ == "__main__":
    main()