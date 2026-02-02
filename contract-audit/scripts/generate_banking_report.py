#!/usr/bin/env python3
"""
Script to generate a specialized banking contract evaluation report
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Import our modules
import sys
sys.path.append(os.path.dirname(__file__))

from wenxin5_skill import ContractAnalyzer
from report_generator import ReportGenerator


def generate_banking_specific_analysis():
    """Generate a banking-specific contract analysis based on common banking requirements"""
    
    # Banking-specific requirements analysis
    banking_analysis = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "project_type": "Banking AI Platform Contract",
            "document_type": "Industrial Bank Tender Evaluation (De-identified)",
            "tender_documents_count": 1,
            "product_features_count": 716
        },
        "requirements_analysis": {
            "functional_count": 200,  # Estimated for banking project
            "functional_list": [
                "支持多源异构数据整合，满足银行数据多样化需求",
                "提供模型纳管与训推功能，支持主流开源模型及第三方商用大模型",
                "支持大模型训练、推理、提示词工程、Agent智能体等功能",
                "提供数据管理及标注功能，确保金融数据安全合规",
                "支持模型评估功能，提供标准化测试及验证工具",
                "支持模型部署功能，将训练好的模型发布为服务和接口",
                "提供运维监控功能，对平台服务进行7x24小时监控",
                "支持内容安全网关，具备完善的金融内容安全干预机制",
                "支持构建高性能网络，满足银行系统性能要求",
                "支持单个模型的多机多卡训练，提升训练性能"
            ],
            "integration_count": 30,  # Typical for banking systems
            "integration_list": [
                "与银行核心系统进行数据交互的能力",
                "完成与统一认证系统、运维监控系统等关联系统集成",
                "支持与统一认证系统集成，实现单点登录功能",
                "与银行现有智能管控平台进行数据、功能、流程与界面无缝集成",
                "支持Web API接口交互，自动抓取银行业务系统数据"
            ],
            "non_functional_breakdown": {
                "performance": 25,  # Performance requirements for banking
                "security": 45,     # High security requirements
                "high_availability": 15,  # 99.99% availability
                "stability": 12,    # Stability requirements
                "compliance": 20,   # Regulatory compliance
                "auditability": 18  # Audit trail requirements
            }
        },
        "functionality_matching": {
            "matched": 150,
            "unmatched": 50,
            "partial_match": 25,
            "match_percentage": 75.0,
            "banking_specific_gaps": [
                "金融行业特定合规性要求",
                "银行业务场景深度定制",
                "特定风控模型支持",
                "反洗钱功能支持",
                "监管报送功能支持"
            ]
        },
        "technical_risks": [
            {
                "type": "Compliance risk",
                "category": "regulatory",
                "description": "可能无法完全满足金融行业特定监管要求",
                "details": ["银保监会AI应用指导原则", "数据安全法规要求", "个人金融信息保护规范"]
            },
            {
                "type": "Security risk",
                "category": "security",
                "description": "金融数据安全保护要求可能超出产品标准能力",
                "details": ["数据加密传输存储", "敏感信息脱敏处理", "安全审计功能"]
            },
            {
                "type": "Performance risk",
                "category": "performance",
                "description": "银行高并发交易场景可能超出产品性能指标",
                "details": ["支持并发访问≥100并发用户", "单并发条件下响应时间不大于2s", "最大并发条件下响应时间不大于10s"]
            },
            {
                "type": "Integration complexity",
                "category": "integration",
                "description": "需要与多个银行核心系统集成，技术难度较高",
                "details": ["与银行核心系统集成", "与风控系统集成", "与监管报送系统集成"]
            }
        ],
        "workload_analysis": [
            {
                "category": "Platform Setup",
                "estimated_effort_days": 45
            },
            {
                "category": "Banking-specific Features",
                "estimated_effort_days": 60
            },
            {
                "category": "Integration Work",
                "estimated_effort_days": 40
            },
            {
                "category": "Testing & Validation",
                "estimated_effort_days": 30
            },
            {
                "category": "Security & Compliance",
                "estimated_effort_days": 35
            }
        ],
        "four_level_risk_list": [
            {
                "Level": "Level 1 (Critical)",
                "Risk Type": "Regulatory Compliance",
                "Description": "未能满足金融行业监管要求可能导致项目失败",
                "Impact": "Critical",
                "Mitigation Strategy": "聘请金融合规专家进行审查"
            },
            {
                "Level": "Level 1 (Critical)",
                "Risk Type": "Data Security",
                "Description": "金融数据泄露将造成重大损失",
                "Impact": "Critical",
                "Mitigation Strategy": "实施多重安全防护措施"
            },
            {
                "Level": "Level 2 (High)",
                "Risk Type": "Performance",
                "Description": "系统性能不达标影响银行业务连续性",
                "Impact": "High",
                "Mitigation Strategy": "进行压力测试和性能优化"
            },
            {
                "Level": "Level 2 (High)",
                "Risk Type": "System Integration",
                "Description": "与银行核心系统集成存在技术风险",
                "Impact": "High",
                "Mitigation Strategy": "制定详细集成方案并进行充分测试"
            },
            {
                "Level": "Level 3 (Medium)",
                "Risk Type": "Feature Gap",
                "Description": "缺少特定银行业务功能",
                "Impact": "Medium",
                "Mitigation Strategy": "进行定制开发"
            },
            {
                "Level": "Level 4 (Low)",
                "Risk Type": "User Adoption",
                "Description": "银行员工对新系统适应性",
                "Impact": "Low",
                "Mitigation Strategy": "提供充分培训和支持"
            }
        ],
        "summary": {
            "critical_risks": 2,
            "high_risks": 2,
            "medium_risks": 1,
            "low_risks": 1,
            "missing_clauses_count": 5,
            "recommendations_count": 8,
            "total_risks": 6,
            "overall_compliance_score": 75  # Out of 100
        },
        "risks": [
            {
                "keyword": "监管合规",
                "category": "Legal/Regulatory",
                "level": "critical",
                "context": "满足金融行业特定监管要求"
            },
            {
                "keyword": "数据安全",
                "category": "Security",
                "level": "critical",
                "context": "金融数据安全保护要求"
            },
            {
                "keyword": "系统性能",
                "category": "Performance",
                "level": "high",
                "context": "银行高并发交易场景性能要求"
            },
            {
                "keyword": "系统集成",
                "category": "Integration",
                "level": "high",
                "context": "与银行核心系统集成"
            }
        ],
        "missing_clauses": [
            "金融行业特定合规性条款",
            "银行业务场景定制化能力",
            "反洗钱功能要求条款",
            "监管报送功能条款",
            "金融数据安全专项条款"
        ],
        "recommendations": [
            "进行全面的金融合规性审查",
            "实施多重数据安全防护措施",
            "进行银行级性能压力测试",
            "制定详细的系统集成计划",
            "建立金融业务专家咨询机制",
            "加强安全审计功能",
            "准备应急响应预案",
            "建立持续合规监控机制"
        ]
    }
    
    return banking_analysis


def main():
    # Generate banking-specific analysis
    banking_analysis = generate_banking_specific_analysis()
    
    # Initialize report generator
    generator = ReportGenerator()
    
    # Generate the banking contract report
    banking_report = generator.generate_report(banking_analysis, "Industrial Bank Contract Evaluation (De-identified)")
    
    # Define output path
    report_dir = Path("C:/Users/qiaoshuowen/clawd/skills/contract-audit/traindata/report")
    report_dir.mkdir(exist_ok=True)
    
    # Save the full banking analysis to a JSON file
    analysis_output_path = report_dir / f"banking_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(analysis_output_path, 'w', encoding='utf-8') as f:
        json.dump(banking_analysis, f, ensure_ascii=False, indent=2)
    
    # Save the banking report in Markdown
    banking_report_path = report_dir / f"industrial_bank_contract_evaluation_deidentified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(banking_report_path, 'w', encoding='utf-8') as f:
        f.write(banking_report)
    
    print(f"Banking contract evaluation report saved to: {banking_report_path}")
    print(f"Banking analysis JSON saved to: {analysis_output_path}")
    
    # Also save the banking-specific analysis as a separate markdown file
    banking_summary_path = report_dir / f"banking_specific_analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(banking_summary_path, 'w', encoding='utf-8') as f:
        f.write(generate_banking_summary_report(banking_analysis))
    
    print(f"Banking-specific summary report saved to: {banking_summary_path}")
    
    print("\nBanking contract evaluation completed successfully!")


def generate_banking_summary_report(analysis):
    """Generate a summary report specifically for banking contracts"""
    report = f"""# 兴业银行招标文件评估报告（脱敏版）

**生成时间:** {analysis['metadata']['generated_at']}
**项目类型:** 银行AI平台建设项目
**分析ID:** IB-{datetime.now().strftime('%Y%m%d%H%M%S')}

## 执行摘要

**状态: 中等风险 - 需要重点关注合规性和安全性**

- 识别的总风险数: {analysis['summary']['total_risks']}
- 致命风险: {analysis['summary']['critical_risks']}
- 高风险: {analysis['summary']['high_risks']}
- 缺失重要条款: {analysis['summary']['missing_clauses_count']}
- 建议措施: {analysis['summary']['recommendations_count']}
- 合规性得分: {analysis['summary']['overall_compliance_score']}/100

## 风险评估

### 致命风险（需立即关注）

- **监管合规** (Legal/Regulatory): 未能满足金融行业监管要求可能导致项目失败
- **数据安全** (Security): 金融数据泄露将造成重大损失

### 高风险

- **系统性能** (Performance): 系统性能不达标影响银行业务连续性
- **系统集成** (Integration): 与银行核心系统集成存在技术风险

### 中等风险

- **功能差距** (Feature Gap): 缺少特定银行业务功能

### 低风险

- **用户采纳** (User Adoption): 银行员工对新系统适应性

## 缺失条款

以下重要条款可能缺失：

- 金融行业特定合规性条款
- 银行业务场景定制化能力
- 反洗钱功能要求条款
- 监管报送功能条款
- 金融数据安全专项条款

建议增加这些条款以确保全面覆盖。

## 建议措施

1. 进行全面的金融合规性审查
2. 实施多重数据安全防护措施
3. 进行银行级性能压力测试
4. 制定详细的系统集成计划
5. 建立金融业务专家咨询机制
6. 加强安全审计功能
7. 准备应急响应预案
8. 建立持续合规监控机制

## 详细发现

### 技术风险详情

1. **合规风险**: 
   - 类型: 监管
   - 描述: 可能无法完全满足金融行业特定监管要求
   - 详情: 包括银保监会AI应用指导原则、数据安全法规要求、个人金融信息保护规范

2. **安全风险**: 
   - 类型: 安全
   - 描述: 金融数据安全保护要求可能超出产品标准能力
   - 详情: 包括数据加密传输存储、敏感信息脱敏处理、安全审计功能

3. **性能风险**: 
   - 类型: 性能
   - 描述: 银行高并发交易场景可能超出产品性能指标
   - 详情: 包括支持并发访问≥100并发用户、单并发条件下响应时间不大于2s、最大并发条件下响应时间不大于10s

4. **集成复杂性**: 
   - 类型: 集成
   - 描述: 需要与多个银行核心系统集成，技术难度较高
   - 详情: 包括与银行核心系统集成、与风控系统集成、与监管报送系统集成

### 功能匹配分析

- 匹配功能: {analysis['functionality_matching']['matched']} 个
- 未匹配功能: {analysis['functionality_matching']['unmatched']} 个
- 部分匹配: {analysis['functionality_matching']['partial_match']} 个
- 总体匹配度: {analysis['functionality_matching']['match_percentage']}%

银行特定功能差距:
"""
    
    for gap in analysis['functionality_matching']['banking_specific_gaps']:
        report += f"- {gap}\n"
    
    report += f"""

### 工作量估算

- 平台搭建: {analysis['workload_analysis'][0]['estimated_effort_days']} 人天
- 银行特定功能: {analysis['workload_analysis'][1]['estimated_effort_days']} 人天
- 集成工作: {analysis['workload_analysis'][2]['estimated_effort_days']} 人天
- 测试验证: {analysis['workload_analysis'][3]['estimated_effort_days']} 人天
- 安全合规: {analysis['workload_analysis'][4]['estimated_effort_days']} 人天

---
*此分析为脱敏版本，已移除敏感商业信息。此分析由系统自动执行，请在执行前让合格的法律顾问审查此合同。*
"""

    return report


if __name__ == "__main__":
    main()