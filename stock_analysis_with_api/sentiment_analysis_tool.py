"""
股市舆情分析工具
"""

import tushare as ts
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import re
from textblob import TextBlob
import jieba
from snownlp import SnowNLP
import warnings
warnings.filterwarnings('ignore')

class SentimentAnalysisTool:
    def __init__(self, token):
        """
        初始化舆情分析工具
        :param token: tushare token
        """
        self.token = token
        ts.set_token(token)
        self.pro = ts.pro_api()

    def get_news_sentiment(self, keyword, days=30):
        """
        获取关键词相关的新闻情感分析
        :param keyword: 搜索关键词
        :param days: 搜索天数
        :return: 情感分析结果
        """
        print(f"正在获取关于'{keyword}'的新闻舆情分析...")
        
        try:
            # 获取财经新闻（使用tushare的财经新闻接口）
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            end_date = datetime.now().strftime('%Y%m%d')
            
            # 由于tushare的财经新闻接口可能需要额外权限，这里提供模拟实现
            # 实际应用中可以根据需要调用相应的API
            news_data = []
            
            # 模拟新闻数据获取
            print(f"模拟获取过去{days}天内关于'{keyword}'的新闻...")
            
            # 模拟情感分析结果
            sample_titles = [
                f"{keyword}业绩增长超预期，市场看好未来发展",
                f"{keyword}遭遇监管问询，股价短期承压",
                f"{keyword}新产品发布，机构上调评级",
                f"{keyword}行业景气度提升，多家券商看好",
                f"{keyword}面临原材料涨价压力，成本上升"
            ]
            
            sentiments = []
            for title in sample_titles:
                # 使用SnowNLP进行中文情感分析
                s = SnowNLP(title)
                sentiment_score = s.sentiments  # 0-1之间，越接近1越积极
                sentiment_label = "积极" if sentiment_score > 0.6 else ("消极" if sentiment_score < 0.4 else "中性")
                
                sentiments.append({
                    'title': title,
                    'sentiment_score': sentiment_score,
                    'sentiment_label': sentiment_label,
                    'date': (datetime.now() - timedelta(days=np.random.randint(0, days))).strftime('%Y-%m-%d')
                })
            
            avg_sentiment = sum([s['sentiment_score'] for s in sentiments]) / len(sentiments)
            
            result = {
                'keyword': keyword,
                'total_articles': len(sample_titles),
                'positive_articles': len([s for s in sentiments if s['sentiment_label'] == '积极']),
                'negative_articles': len([s for s in sentiments if s['sentiment_label'] == '消极']),
                'neutral_articles': len([s for s in sentiments if s['sentiment_label'] == '中性']),
                'average_sentiment': avg_sentiment,
                'articles': sentiments,
                'overall_sentiment': "积极" if avg_sentiment > 0.6 else ("消极" if avg_sentiment < 0.4 else "中性")
            }
            
            print(f"新闻舆情分析完成，平均情感得分: {avg_sentiment:.2f}")
            return result
            
        except Exception as e:
            print(f"获取新闻舆情失败: {str(e)}")
            return None

    def get_social_media_sentiment(self, keyword, platform="weibo"):
        """
        获取社交媒体舆情分析
        :param keyword: 搜索关键词
        :param platform: 平台名称（目前模拟实现）
        :return: 社交媒体情感分析结果
        """
        print(f"正在获取关于'{keyword}'在{platform}的舆情分析...")
        
        # 模拟社交媒体数据分析
        sample_posts = [
            f"看好{keyword}的发展前景，准备加仓",
            f"{keyword}今天又跌了，真是让人心疼",
            f"{keyword}的业绩确实不错，继续持有",
            f"听说{keyword}要出新品了，期待",
            f"{keyword}管理层有点问题，不太看好"
        ]
        
        sentiments = []
        for post in sample_posts:
            s = SnowNLP(post)
            sentiment_score = s.sentiments
            sentiment_label = "积极" if sentiment_score > 0.6 else ("消极" if sentiment_score < 0.4 else "中性")
            
            sentiments.append({
                'post': post,
                'sentiment_score': sentiment_score,
                'sentiment_label': sentiment_label
            })
        
        avg_sentiment = sum([s['sentiment_score'] for s in sentiments]) / len(sentiments)
        
        result = {
            'keyword': keyword,
            'platform': platform,
            'total_posts': len(sample_posts),
            'positive_posts': len([s for s in sentiments if s['sentiment_label'] == '积极']),
            'negative_posts': len([s for s in sentiments if s['sentiment_label'] == '消极']),
            'neutral_posts': len([s for s in sentiments if s['sentiment_label'] == '中性']),
            'average_sentiment': avg_sentiment,
            'overall_sentiment': "积极" if avg_sentiment > 0.6 else ("消极" if avg_sentiment < 0.4 else "中性")
        }
        
        print(f"社交媒体舆情分析完成，平均情感得分: {avg_sentiment:.2f}")
        return result

    def get_policy_impact_analysis(self, industry):
        """
        获取政策对行业的影响分析
        :param industry: 行业名称
        :return: 政策影响分析结果
        """
        print(f"正在分析政策对'{industry}'行业的影响...")
        
        # 模拟政策影响分析
        policy_effects = {
            '新能源': {
                'supportive_policies': ['新能源补贴政策', '碳中和目标', '绿色金融支持'],
                'restrictive_policies': [],
                'impact_level': '积极',
                'impact_description': '多项政策利好，行业发展前景广阔'
            },
            '房地产': {
                'supportive_policies': ['刚需购房支持', '改善型住房优惠'],
                'restrictive_policies': ['限购政策', '房贷收紧', '房产税试点'],
                'impact_level': '中性偏消极',
                'impact_description': '调控政策较多，行业发展面临压力'
            },
            '医药': {
                'supportive_policies': ['医保目录扩容', '创新药支持政策', '医疗改革'],
                'restrictive_policies': ['药品降价政策', '一致性评价要求'],
                'impact_level': '中性偏积极',
                'impact_description': '政策机遇与挑战并存，创新药企受益'
            },
            '互联网': {
                'supportive_policies': ['数字经济规划', '平台经济健康发展'],
                'restrictive_policies': ['反垄断监管', '数据安全法', '算法治理'],
                'impact_level': '中性',
                'impact_description': '监管趋严但长期发展路径明确'
            }
        }
        
        if industry in policy_effects:
            return policy_effects[industry]
        else:
            # 默认返回通用模板
            return {
                'supportive_policies': ['行业支持政策示例'],
                'restrictive_policies': ['行业限制政策示例'],
                'impact_level': '待分析',
                'impact_description': f'关于{industry}行业的政策影响待进一步分析'
            }

    def get_market_sentiment_indicators(self, stock_code):
        """
        获取市场情绪指标
        :param stock_code: 股票代码
        :return: 市场情绪指标
        """
        print(f"正在获取{stock_code}的市场情绪指标...")
        
        try:
            # 获取股票历史数据
            df = self.pro.daily(ts_code=f'{stock_code}.SZ' if not stock_code.endswith('.SZ') and not stock_code.endswith('.SH') else stock_code,
                                start_date=(datetime.now() - timedelta(days=90)).strftime('%Y%m%d'),
                                end_date=datetime.now().strftime('%Y%m%d'))
            
            if df is None or df.empty:
                print("无法获取历史数据，返回默认情绪指标")
                return {
                    'volatility': '中等',
                    'volume_trend': '平稳',
                    'price_momentum': '中性',
                    'market_breadth': '待计算'
                }
            
            # 计算情绪指标
            df_sorted = df.sort_values('trade_date')
            recent_data = df_sorted.tail(20)  # 最近20个交易日
            
            # 波动率
            price_change_std = recent_data['pct_chg'].std()
            if price_change_std > 3:
                volatility = '高'
            elif price_change_std > 1.5:
                volatility = '中等'
            else:
                volatility = '低'
            
            # 成交量趋势
            volume_ma = recent_data['vol'].rolling(window=10).mean()
            current_volume_avg = recent_data['vol'].iloc[-5:].mean()
            volume_trend = '放量' if current_volume_avg > volume_ma.iloc[-1] else '缩量'
            
            # 价格动量
            recent_returns = recent_data['pct_chg'].tail(5).mean()
            if recent_returns > 1:
                price_momentum = '强势'
            elif recent_returns > 0:
                price_momentum = '温和'
            elif recent_returns > -1:
                price_momentum = '弱势'
            else:
                price_momentum = '疲软'
            
            result = {
                'volatility': volatility,
                'volume_trend': volume_trend,
                'price_momentum': price_momentum,
                'market_breadth': '待进一步分析'
            }
            
            print(f"市场情绪指标获取完成: 波动率{volatility}, 成交量{volume_trend}, 动量{price_momentum}")
            return result
            
        except Exception as e:
            print(f"获取市场情绪指标失败: {str(e)}")
            return {
                'volatility': '未知',
                'volume_trend': '未知',
                'price_momentum': '未知',
                'market_breadth': '未知'
            }

    def analyze_overall_sentiment(self, stock_code, company_name, industry):
        """
        综合舆情分析
        :param stock_code: 股票代码
        :param company_name: 公司名称
        :param industry: 所属行业
        :return: 综合舆情分析结果
        """
        print(f"正在对{company_name}({stock_code})进行综合舆情分析...")
        
        # 获取新闻舆情
        news_sentiment = self.get_news_sentiment(company_name)
        
        # 获取社交媒体舆情
        social_sentiment = self.get_social_media_sentiment(company_name)
        
        # 获取政策影响分析
        policy_impact = self.get_policy_impact_analysis(industry)
        
        # 获取市场情绪指标
        market_sentiment = self.get_market_sentiment_indicators(stock_code)
        
        # 综合分析
        overall_sentiment_score = 0
        if news_sentiment:
            overall_sentiment_score += news_sentiment['average_sentiment'] * 0.4
        if social_sentiment:
            overall_sentiment_score += social_sentiment['average_sentiment'] * 0.2
        # 政策影响转换为数值
        policy_score = 0.7 if policy_impact['impact_level'] == '积极' else (0.3 if policy_impact['impact_level'] == '消极' else 0.5)
        overall_sentiment_score += policy_score * 0.3
        # 市场情绪转换为数值
        momentum_score = 0.7 if market_sentiment['price_momentum'] in ['强势', '温和'] else (0.3 if market_sentiment['price_momentum'] in ['弱势', '疲软'] else 0.5)
        overall_sentiment_score += momentum_score * 0.1
        
        overall_sentiment = "积极" if overall_sentiment_score > 0.6 else ("消极" if overall_sentiment_score < 0.4 else "中性")
        
        result = {
            'stock_info': {
                'code': stock_code,
                'name': company_name,
                'industry': industry
            },
            'news_sentiment': news_sentiment,
            'social_sentiment': social_sentiment,
            'policy_impact': policy_impact,
            'market_sentiment': market_sentiment,
            'overall_sentiment_score': overall_sentiment_score,
            'overall_sentiment': overall_sentiment,
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        return result

    def print_sentiment_report(self, analysis_result):
        """
        打印舆情分析报告
        :param analysis_result: 分析结果
        """
        if analysis_result is None:
            print("舆情分析失败，无法生成报告")
            return
        
        print("\n" + "="*80)
        print(f"股票舆情分析报告")
        print(f"股票: {analysis_result['stock_info']['name']}({analysis_result['stock_info']['code']})")
        print(f"行业: {analysis_result['stock_info']['industry']}")
        print(f"分析日期: {analysis_result['analysis_date']}")
        print(f"综合情绪评分: {analysis_result['overall_sentiment_score']:.2f} ({analysis_result['overall_sentiment']})")
        print("="*80)
        
        # 新闻舆情
        if analysis_result['news_sentiment']:
            ns = analysis_result['news_sentiment']
            print(f"\n【新闻舆情分析】")
            print(f"  文章总数: {ns['total_articles']}")
            print(f"  积极文章: {ns['positive_articles']}篇")
            print(f"  消极文章: {ns['negative_articles']}篇")
            print(f"  中性文章: {ns['neutral_articles']}篇")
            print(f"  平均情感: {ns['average_sentiment']:.2f} ({ns['overall_sentiment']})")
        
        # 社交媒体舆情
        if analysis_result['social_sentiment']:
            ss = analysis_result['social_sentiment']
            print(f"\n【社交媒体舆情】")
            print(f"  平台: {ss['platform']}")
            print(f"  发帖总数: {ss['total_posts']}")
            print(f"  积极发帖: {ss['positive_posts']}条")
            print(f"  消极发帖: {ss['negative_posts']}条")
            print(f"  中性发帖: {ss['neutral_posts']}条")
            print(f"  平均情感: {ss['average_sentiment']:.2f} ({ss['overall_sentiment']})")
        
        # 政策影响
        pi = analysis_result['policy_impact']
        print(f"\n【政策影响分析】")
        print(f"  影响程度: {pi['impact_level']}")
        print(f"  利好政策: {', '.join(pi['supportive_policies'])}")
        print(f"  利空政策: {', '.join(pi['restrictive_policies'])}")
        print(f"  描述: {pi['impact_description']}")
        
        # 市场情绪指标
        ms = analysis_result['market_sentiment']
        print(f"\n【市场情绪指标】")
        print(f"  波动率: {ms['volatility']}")
        print(f"  成交量趋势: {ms['volume_trend']}")
        print(f"  价格动量: {ms['price_momentum']}")
        
        print(f"\n【综合评价】")
        print(f"  整体舆情: {analysis_result['overall_sentiment']}")
        if analysis_result['overall_sentiment'] == '积极':
            print(f"  评价: 市场情绪乐观，正面信息占主导")
        elif analysis_result['overall_sentiment'] == '消极':
            print(f"  评价: 市场情绪悲观，负面信息占主导")
        else:
            print(f"  评价: 市场情绪中性，多空信息相对平衡")
        
        print("="*80)
        print("【风险提示】舆情分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
        print("="*80)


# 使用示例
if __name__ == "__main__":
    # 示例使用
    token = 'YOUR_TUSHARE_TOKEN_HERE'  # 需要替换为实际的token
    sentiment_analyzer = SentimentAnalysisTool(token)
    
    # 分析江苏神通
    result = sentiment_analyzer.analyze_overall_sentiment('002438', '江苏神通', '专用设备')
    sentiment_analyzer.print_sentiment_report(result)