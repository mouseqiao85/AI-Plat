# -*- coding: utf-8 -*-
"""
优化版文心操盘手解读模块
"""

import os
from openai import OpenAI
import json
from datetime import datetime

class EnhancedWenxinSkill:
    """
    优化版百度文心5.0模型调用技能
    专注于股票分析和操盘手级别的专业解读
    """
    
    def __init__(self, api_key=None):
        """
        初始化文心5.0客户端
        :param api_key: 百度千帆平台API密钥
        """
        self.api_key = api_key or os.getenv('WENXIN_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供API密钥，可通过参数或WENXIN_API_KEY环境变量设置")
        
        self.client = OpenAI(
            base_url='https://qianfan.baidubce.com/v2',
            api_key=self.api_key
        )
        # 使用更适合金融分析的模型
        self.model = "ernie-4.5-8k"
        # 或者保留原来的模型
        # self.model = "deepseek-v3.2-think"
    
    def generate_enhanced_stock_analysis(self, stock_report, stock_code, additional_context=None):
        """
        生成增强版股票分析，按专业操盘手格式输出
        :param stock_report: 股票分析报告内容
        :param stock_code: 股票代码
        :param additional_context: 额外的上下文信息
        :return: 专业分析结果
        """
        # 构建增强的提示词模板
        prompt = self._build_enhanced_prompt(stock_report, stock_code, additional_context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # 降低温度以获得更稳定的金融分析
                top_p=0.8,
                max_tokens=2000,  # 限制token数量以控制成本
                extra_body={
                    "stop": [],
                    "web_search": {
                        "enable": True  # 启用网络搜索以获取最新市场信息
                    }
                }
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"调用文心5.0模型时出错: {str(e)}"
            print(error_msg)
            return self._generate_fallback_analysis(stock_report, stock_code)
    
    def _build_enhanced_prompt(self, stock_report, stock_code, additional_context=None):
        """
        构建增强的提示词
        """
        context_section = ""
        if additional_context:
            context_section = f"\n\n此外，请考虑以下市场背景信息：\n{additional_context}\n"
        
        prompt = f"""尊敬的文心AI模型，

您是一位拥有20年实战经验的专业沪深股市操盘手，具有深厚的市场洞察力和丰富的交易策略。请您仔细研读以下由AI系统生成的{stock_code}股票分析报告，并基于您的专业经验和市场直觉，给出权威的职业判断。

{stock_report}
{context_section}

请严格按照以下结构进行专业分析：

**1. 核心定性（市场定位）**
- 当前市场环境下该股票的总体定位
- 所处行业地位及竞争优势
- 估值水平分析

**2. 操盘细节深度解读**
- 技术面：当前K线形态、均线系统、成交量变化、技术指标状态
- 基本面：财务健康度、盈利能力、成长性评估
- 资金面：主力资金动向、散户情绪、机构关注度
- 消息面：政策影响、行业动态、公司公告

**3. 实战操盘策略（修正AI策略）**
- 短线策略（1-5个交易日）：具体买卖点位、仓位控制、止盈止损建议
- 中线策略（1-3个月）：趋势判断、关键价位、操作节奏
- 长线策略（3个月以上）：价值投资逻辑、持有建议

**4. 风险警示与机会评估**
- 主要风险点：技术面风险、基本面风险、市场系统性风险
- 潜在机会：技术突破机会、基本面改善机会、市场错杀机会
- 关键观察指标：需要重点关注的技术或基本面变化

**5. 职业结论与行动建议**
- 综合评级：强烈推荐/推荐/中性/回避/强烈回避
- 具体操作建议：买入/持有/减仓/卖出的时机和理由
- 风险收益比评估

请注意：分析需结合当前A股市场特点，考虑政策导向、资金偏好、市场情绪等多维度因素，提供真正实用的操盘指导，而非泛泛而谈。"""
        
        return prompt
    
    def analyze_stock_with_professional_insight(self, stock_data_dict):
        """
        基于完整的股票数据字典进行专业分析
        :param stock_data_dict: 包含完整股票分析数据的字典
        :return: 专业分析结果
        """
        # 构建结构化的分析报告
        structured_report = self._format_structured_report(stock_data_dict)
        
        # 获取股票代码
        stock_code = stock_data_dict.get('stock_code', 'UNKNOWN')
        
        # 生成专业分析
        analysis = self.generate_enhanced_stock_analysis(structured_report, stock_code)
        
        return analysis
    
    def _format_structured_report(self, stock_data_dict):
        """
        将股票数据格式化为结构化报告
        """
        report_parts = []
        
        # 基本信息
        report_parts.append(f"# {stock_data_dict.get('stock_code', 'UNKNOWN')} 结构化分析报告")
        report_parts.append(f"**公司名称**: {stock_data_dict.get('company_name', 'N/A')}")
        report_parts.append(f"**所属行业**: {stock_data_dict.get('industry', 'N/A')}")
        report_parts.append(f"**当前价格**: {stock_data_dict.get('current_price', 'N/A'):.2f}元")
        report_parts.append("")
        
        # 技术指标
        tech_ind = stock_data_dict.get('technical_indicators', {})
        if tech_ind:
            report_parts.append("## 技术指标概览")
            report_parts.append(f"- **RSI**: {tech_ind.get('RSI', 'N/A'):.2f}")
            report_parts.append(f"- **MACD**: {tech_ind.get('MACD', 'N/A'):.4f}")
            report_parts.append(f"- **均线系统**: MA5={tech_ind.get('MA5', 'N/A'):.2f}, MA20={tech_ind.get('MA20', 'N/A'):.2f}, MA60={tech_ind.get('MA60', 'N/A'):.2f}")
            report_parts.append(f"- **支撑位**: {tech_ind.get('support', 'N/A'):.2f}")
            report_parts.append(f"- **阻力位**: {tech_ind.get('resistance', 'N/A'):.2f}")
            report_parts.append("")
        
        # 基本面
        fin_data = stock_data_dict.get('financial_data', {})
        if fin_data:
            report_parts.append("## 基本面概览")
            if fin_data.get('pe'):
                report_parts.append(f"- **市盈率(PE)**: {fin_data['pe']:.2f}")
            if fin_data.get('pb'):
                report_parts.append(f"- **市净率(PB)**: {fin_data['pb']:.2f}")
            if fin_data.get('eps'):
                report_parts.append(f"- **每股收益(EPS)**: {fin_data['eps']}")
            if fin_data.get('roe'):
                report_parts.append(f"- **净资产收益率(ROE)**: {fin_data['roe']*100:.2f}%")
            report_parts.append("")
        
        # 波浪理论分析
        wave_analysis = stock_data_dict.get('wave_analysis', {})
        if wave_analysis:
            report_parts.append("## 波浪理论分析概览")
            report_parts.append(f"- **当前波浪阶段**: {wave_analysis.get('current_wave_potential', 'N/A')}")
            wave_char = wave_analysis.get('wave_characteristics', {})
            if wave_char:
                report_parts.append(f"- **波浪特征**: {wave_char.get('potential_wave_type', 'N/A')}")
            trend_str = wave_analysis.get('trend_strength', {})
            if trend_str:
                report_parts.append(f"- **趋势强度**: {trend_str.get('classification', 'N/A')} (得分: {trend_str.get('strength_score', 'N/A')})")
            supp_res = wave_analysis.get('support_resistance', {})
            if supp_res:
                report_parts.append(f"- **关键支撑**: {supp_res.get('support_level', 'N/A'):.2f}")
                report_parts.append(f"- **关键阻力**: {supp_res.get('resistance_level', 'N/A'):.2f}")
            report_parts.append("")
        
        # 预测分析
        predictions = stock_data_dict.get('predictions', [])
        if predictions:
            report_parts.append("## 预测分析概览")
            report_parts.append("**未来5日价格预测:**")
            current_price = stock_data_dict.get('current_price', 0)
            for pred in predictions[:5]:  # 只取前5个预测
                price_change = pred['predicted_price'] - current_price
                pct_change = (pred['predicted_price'] - current_price) / current_price * 100
                report_parts.append(f"- 第{pred['day']}日: 预测价格 {pred['predicted_price']:.2f}元, "
                                  f"涨跌 {price_change:+.2f}元 ({pct_change:+.2f}%)")
            
            final_pred = predictions[-1] if predictions else {'predicted_price': current_price}
            overall_change = (final_pred['predicted_price'] - current_price) / current_price * 100
            report_parts.append(f"- **整体预测**: 期间预计涨跌幅 {overall_change:+.2f}%")
            report_parts.append(f"- **模型准确率**: R2 = {stock_data_dict.get('model_accuracy', 'N/A'):.4f}")
            report_parts.append("")
        
        # 投资策略建议
        strategy = stock_data_dict.get('investment_strategy', {})
        if strategy:
            report_parts.append("## AI投资策略建议概览")
            report_parts.append(f"- **当前建议**: {stock_data_dict.get('recommendation', 'N/A')}")
            report_parts.append(f"- **短期策略 (1-4周)**: {strategy.get('short_term', 'N/A')}")
            report_parts.append(f"- **中期策略 (1-6个月)**: {strategy.get('medium_term', 'N/A')}")
            report_parts.append(f"- **长期策略 (6个月以上)**: {strategy.get('long_term', 'N/A')}")
            report_parts.append(f"- **目标价位**: {strategy.get('target_price', 'N/A'):.2f}元")
            report_parts.append(f"- **止损价位**: {strategy.get('stop_loss', 'N/A'):.2f}元")
            report_parts.append("")
        
        # 市场情绪
        sent_data = stock_data_dict.get('market_sentiment', {})
        if sent_data:
            report_parts.append("## 市场情绪概览")
            if 'recent_volume_ratio' in sent_data:
                report_parts.append(f"- **近期成交量比**: {sent_data['recent_volume_ratio']:.2f}")
            if 'price_volume_correlation' in sent_data:
                report_parts.append(f"- **量价相关性**: {sent_data['price_volume_correlation']:.3f}")
            if 'abnormal_volume_count' in sent_data:
                report_parts.append(f"- **异常成交量天数**: {sent_data['abnormal_volume_count']}天")
            report_parts.append("")
        
        return "\n".join(report_parts)
    
    def _generate_fallback_analysis(self, stock_report, stock_code):
        """
        生成备用分析（当API调用失败时）
        """
        fallback_analysis = f"""# {stock_code} 专业操盘手分析（备用版本）

作为一名专业沪深股市操盘手，我仔细研读了这份 AI 驱动生成的{stock_code}分析报告。基于市场实况，我给出的职业判断如下：

## 1. 核心定性
[由于API调用限制，此处为模板分析] 当前该股票处于[估值合理/偏高/偏低]区间，技术面呈现[震荡整理/上升趋势/下降趋势]态势。行业基本面[稳健/面临挑战]，需要结合当前市场环境综合判断。

## 2. 操盘细节深度解读
- **技术面**: [模板分析] 技术指标显示短期均线趋于[收敛/发散]，成交量[温和/活跃/低迷]，显示多空力量[暂时均衡/多方占优/空方占优]。
- **基本面**: [模板分析] 公司行业地位[稳固/一般/需关注]，具备[一定/有限/待提升]的竞争优势。
- **资金面**: [模板分析] 从成交量变化看，主力资金[积极参与/谨慎观望/有所撤离]。
- **消息面**: [模板分析] 近期相关行业政策[利好/中性/利空]，公司层面消息[积极/中性/需关注]。

## 3. 实战操盘策略（修正 AI 策略）
- **短线策略**: [模板建议] 建议关注[关键支撑位/阻力位]附近的交易机会，合理控制仓位。
- **中线策略**: [模板建议] 如趋势确认向好，可考虑[分批建仓/加仓/减仓]。
- **长线策略**: [模板建议] 基于公司基本面，适合[长期持有/波段操作/谨慎参与]。

## 4. 风险警示与机会评估
- **主要风险**: [模板风险提示] 需关注[宏观经济变化/行业政策调整/公司经营状况]对股价的影响。
- **潜在机会**: [模板机会分析] 在[特定价位/特定事件]可能产生投资机会。
- **关键观察指标**: 需密切关注[技术指标变化/基本面数据/资金流向]。

## 5. 职业结论与行动建议
**综合评级**: [中性/谨慎乐观/谨慎悲观]
**操作建议**: [模板建议] 建议[观望为主/适量参与/谨慎操作]，严格执行风险管理策略。
**风险收益比**: [评估结果] 建议根据个人风险承受能力制定相应策略。

---
*此为备用分析模板，实际操作请结合最新市场信息和个人判断。*
"""
        return fallback_analysis


# 示例使用
if __name__ == "__main__":
    # 从环境变量获取API密钥
    api_key = os.getenv('WENXIN_API_KEY')
    
    if api_key:
        wenxin = EnhancedWenxinSkill(api_key)
        
        # 示例股票数据
        sample_stock_data = {
            'stock_code': '002536.SZ',
            'company_name': '飞龙股份',
            'industry': '汽车零部件',
            'current_price': 29.35,
            'technical_indicators': {
                'RSI': 51.0,
                'MACD': 0.2261,
                'MA5': 28.52,
                'MA20': 29.21,
                'MA60': 26.24,
                'support': 26.84,
                'resistance': 30.98
            },
            'financial_data': {
                'pe': 36.23,
                'pb': 2.54,
                'eps': 0.81,
                'roe': 0.152
            },
            'wave_analysis': {
                'current_wave_potential': '可能处于推动浪阶段（第1、3或5浪）',
                'wave_characteristics': {
                    'potential_wave_type': '第3浪特征（强劲主升浪）'
                },
                'trend_strength': {
                    'classification': '强',
                    'strength_score': 0.75
                },
                'support_resistance': {
                    'support_level': 26.84,
                    'resistance_level': 30.98
                }
            },
            'predictions': [
                {'day': 1, 'predicted_price': 29.50},
                {'day': 2, 'predicted_price': 29.75},
                {'day': 3, 'predicted_price': 30.10},
                {'day': 4, 'predicted_price': 30.35},
                {'day': 5, 'predicted_price': 30.60}
            ],
            'recommendation': '买入',
            'investment_strategy': {
                'short_term': '1-4周：逢低吸纳，关注28.52支撑，目标30.50',
                'medium_term': '1-6个月：盈利能力较强，估值合理，关注29.21支撑/30.98压力',
                'long_term': '6个月以上：汽车零部件行业，营收稳定增长，现金流健康',
                'target_price': 32.00,
                'stop_loss': 27.50
            },
            'market_sentiment': {
                'recent_volume_ratio': 1.25,
                'price_volume_correlation': 0.345,
                'abnormal_volume_count': 3
            },
            'model_accuracy': 0.8234
        }
        
        result = wenxin.analyze_stock_with_professional_insight(sample_stock_data)
        print("文心5.0专业分析结果:")
        print(result)
    else:
        print("请设置WENXIN_API_KEY环境变量以使用文心5.0模型")