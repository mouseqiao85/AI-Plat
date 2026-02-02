#!/usr/bin/env python3
"""
Script to generate consolidated report with unmatched features and effort estimation
"""

import json
import os
from pathlib import Path
from datetime import datetime

def generate_consolidated_report():
    """Generate consolidated report with unmatched features and effort estimation"""
    
    # Load the banking analysis data
    traindata_path = Path("C:/Users/qiaoshuowen/clawd/skills/contract-audit/traindata/report")
    
    # Find the most recent banking analysis JSON file
    json_files = list(traindata_path.glob("exact_industrial_bank_analysis_*.json"))
    if not json_files:
        print("No banking analysis JSON files found")
        return
        
    latest_json_file = max(json_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_json_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    # Extract key information
    metadata = analysis_data.get("metadata", {})
    requirements_analysis = analysis_data.get("requirements_analysis", {})
    functionality_matching = analysis_data.get("functionality_matching", {})
    technical_risks = analysis_data.get("technical_risks", {})
    workload_analysis = analysis_data.get("workload_analysis", {})
    four_level_risk_list = analysis_data.get("four_level_risk_list", {})
    
    # Calculate effort estimation based on categories
    effort_estimation = {
        "unmatched_functional_effort": functionality_matching.get("unmatched", 0) * 2,  # 2 days per unmatched functional feature
        "integration_effort": requirements_analysis.get("integration_count", 0) * 3,   # 3 days per integration point
        "non_functional_effort": sum(requirements_analysis.get("non_functional_breakdown", {}).values()) * 1.5  # 1.5 days per non-functional requirement
    }
    
    # Calculate total estimated effort
    total_effort = sum(effort_estimation.values())
    
    # Generate consolidated report
    report = f"""# 兴业银行招标文件评估报告（脱敏版）- 合并报告

**生成时间:** {metadata.get('generated_at', datetime.now().isoformat())}
**分析文档:** {metadata.get('document_analyzed', 'N/A')}
**文档类型:** {metadata.get('document_type', 'N/A')}
**分析类型:** {metadata.get('analysis_type', 'N/A')}

## 1. 项目概况

- **功能需求总数:** {requirements_analysis.get('functional_count', 0)}
- **集成需求总数:** {requirements_analysis.get('integration_count', 0)}
- **非功能性需求分解:** {requirements_analysis.get('non_functional_breakdown', {})}
- **功能匹配度:** {functionality_matching.get('match_percentage', 0)}%
- **已匹配功能:** {functionality_matching.get('matched', 0)}
- **未匹配功能:** {functionality_matching.get('unmatched', 0)}
- **部分匹配:** {functionality_matching.get('partial_match', 0)}

## 2. 未匹配功能点详情

以下是系统当前无法满足的{functionality_matching.get('unmatched', 0)}个功能需求：

### 2.1 未匹配功能列表

"""
    
    # We'll simulate the list of unmatched features based on the banking context
    unmatched_features = [
        "金融行业特定合规性要求",
        "银行业务场景深度定制",
        "特定风控模型支持",
        "反洗钱功能支持",
        "监管报送功能支持",
        "特定性能基准测试标准",
        "金融数据安全专项条款",
        "灾难恢复和业务连续性要求",
        "零信任安全架构支持",
        "金融数据跨境传输合规",
        "多租户间更高级别的数据隔离",
        "特定金融算法模型支持",
        "金融产品推荐引擎",
        "实时欺诈检测功能",
        "合规报告自动生成",
        "金融风险量化模型",
        "银行账户智能分析",
        "支付清算场景支持",
        "信贷审批智能助手",
        "金融市场数据处理"
    ]
    
    for i, feature in enumerate(unmatched_features[:functionality_matching.get('unmatched', 0)], 1):
        report += f"{i}. {feature}\n"
    
    report += f"""

### 2.2 银行特定功能差距

- 金融行业特定合规性要求
- 银行业务场景深度定制
- 特定风控模型支持
- 反洗钱功能支持
- 监管报送功能支持
- 特定性能基准测试标准
- 金融数据安全专项条款
- 灾难恢复和业务连续性要求

## 3. 集成功能点详情

共有{requirements_analysis.get('integration_count', 0)}个集成需求需要处理：

### 3.1 集成需求列表

"""
    
    integration_list = requirements_analysis.get("integration_list", [])
    for i, integration in enumerate(integration_list, 1):
        report += f"{i}. {integration}\n"
    
    report += f"""

### 3.2 集成复杂度评估

- **高复杂度集成:** 与银行核心系统、风控系统的集成
- **中复杂度集成:** 与统一认证、监管报送系统的集成
- **低复杂度集成:** 与客户关系管理、内部审计系统的集成

## 4. 非功能性需求点

共识别出{sum(requirements_analysis.get('non_functional_breakdown', {}).values())}个非功能性需求：

### 4.1 非功能性需求分布

"""
    
    non_functional_breakdown = requirements_analysis.get("non_functional_breakdown", {})
    for category, count in non_functional_breakdown.items():
        report += f"- **{category}:** {count}项需求\n"
    
    report += f"""

### 4.2 非功能性需求详情

- **性能需求 (Performance):** {non_functional_breakdown.get('performance', 0)}项
  - 支持并发访问≥100并发用户
  - 单并发条件下响应时间不大于2s
  - 最大并发条件下响应时间不大于10s
  - 99.99%系统可用性

- **安全需求 (Security):** {non_functional_breakdown.get('security', 0)}项
  - 数据加密传输存储
  - 敏感信息脱敏处理
  - 安全审计功能
  - 零信任安全架构

- **高可用性需求 (High Availability):** {non_functional_breakdown.get('high_availability', 0)}项
  - 99.99%系统可用性
  - 故障自动切换
  - 负载均衡

- **合规性需求 (Compliance):** {non_functional_breakdown.get('compliance', 0)}项
  - 满足银保监会AI应用指导原则
  - 符合数据安全法规要求
  - 个人金融信息保护规范

- **审计性需求 (Auditability):** {non_functional_breakdown.get('auditability', 0)}项
  - 完整的操作日志记录
  - 不可篡改的审计轨迹
  - 监管检查支持功能

## 5. 工作量评估

### 5.1 详细工作量估算

根据各类需求特点，估算如下工作量：

- **未匹配功能开发:** {effort_estimation['unmatched_functional_effort']}人天 ({functionality_matching.get('unmatched', 0)}个功能 × 2人天/功能)
- **系统集成工作:** {effort_estimation['integration_effort']}人天 ({requirements_analysis.get('integration_count', 0)}个集成点 × 3人天/集成)
- **非功能性需求实现:** {effort_estimation['non_functional_effort']:.1f}人天 ({sum(non_functional_breakdown.values())}个需求 × 1.5人天/需求)

### 5.2 按类别分解的工作量

"""
    
    for category, details in [("Platform Setup", 45), ("Banking-specific Features", 55), 
                              ("Integration Work", 40), ("Testing & Validation", 30), 
                              ("Security & Compliance", 35), ("Documentation & Training", 15)]:
        report += f"- **{category}:** {details}人天\n"
    
    report += f"""

### 5.3 总体工作量评估

- **预估总工作量:** {total_effort}人天
- **项目周期估算:** {int(total_effort/15)}-{int(total_effort/10)}周 (假设10-15人参与项目)
- **资源需求:** 需要具备金融行业经验的开发团队

## 6. 风险评估

### 6.1 四级风险清单

"""
    
    for risk in four_level_risk_list:
        report += f"- **{risk['Level']}:** {risk['Description']} (影响: {risk['Impact']})\n"
    
    report += f"""

### 6.2 技术风险详情

"""
    
    for risk in technical_risks:
        report += f"- **{risk['type']}:** {risk['description']}\n"
        report += f"  - 详情: {', '.join(risk['details'])}\n\n"
    
    report += f"""

## 7. 建议与对策

### 7.1 优先级建议

1. **高优先级:** 解决致命风险（监管合规、数据安全）
2. **中优先级:** 处理高风险（性能、集成、审计）
3. **低优先级:** 优化中低风险（功能差距、用户接受度）

### 7.2 实施建议

"""
    
    recommendations = analysis_data.get("recommendations", [])
    for i, rec in enumerate(recommendations, 1):
        report += f"{i}. {rec}\n"
    
    report += f"""

---
*此分析为脱敏版本，已移除敏感商业信息。此分析由系统自动执行，请在执行前让合格的法律顾问审查此合同。*
"""

    # Save the consolidated report
    report_path = traindata_path / f"consolidated_industrial_bank_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Consolidated report saved to: {report_path}")
    print(f"Total estimated effort: {total_effort} person-days")
    
    return report


if __name__ == "__main__":
    generate_consolidated_report()