"""
分析上一代功能点，提取有价值的信息用于AI-Plat平台开发
"""

import pandas as pd
import json
from typing import Dict, List, Any


def load_and_clean_data(file_path: str) -> pd.DataFrame:
    """
    加载并清理数据
    """
    df = pd.read_excel(file_path)
    
    # 重命名列以便处理
    column_mapping = {
        '': '序号',
        'ģ': '模块名称',
        'һ': '一级功能',
        '': '二级功能', 
        '': '三级功能',
        'ļ': '四级功能',
        '(ܶ)': '功能描述',
        'ڶϱƷSOW͹ʵ·Ϳ͹ָܣ': '产品SOW描述',
        'Ƿر\nΪأΪпأΪǿ': '是否控标'
    }
    
    # 由于原始列名是乱码，我们根据位置来映射
    actual_columns = df.columns.tolist()
    renamed_columns = [
        '序号', '模块名称', '一级功能', '二级功能', '三级功能', '四级功能', 
        '功能描述', '产品SOW描述', '是否控标'
    ]
    
    df_renamed = df.copy()
    df_renamed.columns = renamed_columns
    
    return df_renamed


def extract_main_modules(df: pd.DataFrame) -> Dict[str, Any]:
    """
    提取主要模块信息
    """
    modules = {}
    
    # 获取所有非空的模块名称
    for idx, row in df.iterrows():
        if pd.notna(row['模块名称']):
            module_name = row['模块名称']
            if module_name not in modules:
                modules[module_name] = {
                    '一级功能': [],
                    '功能总数': 0,
                    '描述': row['功能描述'] if pd.notna(row['功能描述']) else ''
                }
        
        # 统计功能数量
        if pd.notna(row['三级功能']) or pd.notna(row['四级功能']):
            if pd.notna(row['模块名称']):
                module_name = row['模块名称']
                modules[module_name]['功能总数'] += 1
    
    # 收集每个模块的一级功能
    for idx, row in df.iterrows():
        if pd.notna(row['模块名称']) and pd.notna(row['一级功能']):
            module_name = row['模块名称']
            feature = row['一级功能']
            if feature not in modules[module_name]['一级功能']:
                modules[module_name]['一级功能'].append(feature)
    
    return modules


def analyze_feature_hierarchy(df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析功能层次结构
    """
    hierarchy = {}
    
    for idx, row in df.iterrows():
        module = row['模块名称'] if pd.notna(row['模块名称']) else None
        level1 = row['一级功能'] if pd.notna(row['一级功能']) else None
        level2 = row['二级功能'] if pd.notna(row['二级功能']) else None
        level3 = row['三级功能'] if pd.notna(row['三级功能']) else None
        level4 = row['四级功能'] if pd.notna(row['四级功能']) else None
        
        if module:
            if module not in hierarchy:
                hierarchy[module] = {}
            
            if level1:
                if level1 not in hierarchy[module]:
                    hierarchy[module][level1] = {}
                
                if level2:
                    if level2 not in hierarchy[module][level1]:
                        hierarchy[module][level1][level2] = {}
                    
                    if level3:
                        if level3 not in hierarchy[module][level1][level2]:
                            hierarchy[module][level1][level2][level3] = []
                        
                        if level4:
                            hierarchy[module][level1][level2][level3].append(level4)
    
    return hierarchy


def extract_valuable_features(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    提取有价值的功能点
    """
    valuable_features = []
    
    for idx, row in df.iterrows():
        feature_entry = {}
        
        for col in ['序号', '模块名称', '一级功能', '二级功能', '三级功能', '四级功能', '功能描述', '产品SOW描述', '是否控标']:
            if pd.notna(row[col]):
                feature_entry[col] = str(row[col])
        
        if feature_entry:  # 只有当条目包含至少一个非空值时才添加
            valuable_features.append(feature_entry)
    
    return valuable_features


def map_to_ai_plat_concepts(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将上一代功能映射到AI-Plat概念
    """
    ai_plat_mapping = {
        'ontology_related': [],  # 与本体论相关的功能
        'agent_related': [],     # 与智能体相关的功能  
        'vibecoding_related': [], # 与Vibecoding相关的功能
        'platform_features': []   # 平台级功能
    }
    
    # 关键词映射
    ontology_keywords = ['模型', '数据集', '数据广场', '组件广场', 'MCP广场', 'Prompt广场', '模型管理', '模型评估']
    agent_keywords = ['作业', '任务', '训练', '蒸馏', 'SFT', 'LoRA', 'DPO', 'RFT', 'notebook', '建模']
    vibecoding_keywords = ['notebook', '代码', '建模', '编程', '开发']
    platform_keywords = ['部署', '评估', '加速', '服务', 'API', '管理', '配置']
    
    for feature in features:
        feature_text = ' '.join([str(v) for v in feature.values()])
        feature_text_lower = feature_text.lower()
        
        # 检查本体论相关
        if any(keyword in feature_text for keyword in ontology_keywords):
            ai_plat_mapping['ontology_related'].append(feature)
        
        # 检查智能体相关
        if any(keyword in feature_text for keyword in agent_keywords):
            ai_plat_mapping['agent_related'].append(feature)
        
        # 检查Vibecoding相关
        if any(keyword in feature_text for keyword in vibecoding_keywords):
            ai_plat_mapping['vibecoding_related'].append(feature)
        
        # 检查平台功能
        if any(keyword in feature_text for keyword in platform_keywords):
            ai_plat_mapping['platform_features'].append(feature)
    
    return ai_plat_mapping


def generate_insights(modules: Dict[str, Any], hierarchy: Dict[str, Any], 
                     mapped_features: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成分析洞察
    """
    insights = {
        'module_summary': {
            'total_modules': len(modules),
            'modules_list': list(modules.keys()),
            'top_modules_by_features': sorted(
                [(name, info['功能总数']) for name, info in modules.items()], 
                key=lambda x: x[1], reverse=True
            )[:5]
        },
        'feature_distribution': {
            'ontology_related_count': len(mapped_features['ontology_related']),
            'agent_related_count': len(mapped_features['agent_related']), 
            'vibecoding_related_count': len(mapped_features['vibecoding_related']),
            'platform_features_count': len(mapped_features['platform_features'])
        },
        'architecture_implications': [],
        'recommendations': []
    }
    
    # 架构影响分析
    if insights['feature_distribution']['ontology_related_count'] > 50:
        insights['architecture_implications'].append(
            "需要强大的本体论和知识管理功能来处理大量模型和数据集管理需求"
        )
    
    if insights['feature_distribution']['agent_related_count'] > 50:
        insights['architecture_implications'].append(
            "需要灵活的智能体系统来处理多样化的训练和推理任务"
        )
    
    if insights['feature_distribution']['vibecoding_related_count'] > 20:
        insights['architecture_implications'].append(
            "需要完善的代码生成和开发辅助功能"
        )
    
    # 推荐
    insights['recommendations'].append(
        "基于分析，AI-Plat应重点关注模型管理、训练作业调度和开发体验优化"
    )
    
    if '模型广场' in modules:
        insights['recommendations'].append(
            f"模型广场模块功能丰富（{modules['模型广场']['功能总数']}个功能），应作为核心功能重点建设"
        )
    
    if '模型训练' in modules:
        insights['recommendations'].append(
            f"模型训练模块复杂度高，需要设计灵活的任务调度和资源管理系统"
        )
    
    return insights


def main():
    """
    主函数
    """
    print("[INFO] 开始分析上一代功能点...")
    
    # 加载数据
    df = load_and_clean_data(r"C:\Users\qiaoshuowen\Desktop\上一代功能点.xlsx")
    print(f"[DATA] 加载了 {len(df)} 行数据")
    
    # 提取主要模块
    modules = extract_main_modules(df)
    print(f"[MODULES] 识别出 {len(modules)} 个主要模块")
    
    # 分析功能层次
    hierarchy = analyze_feature_hierarchy(df)
    print(f"[HIERARCHY] 分析了功能层次结构")
    
    # 提取有价值的功能
    valuable_features = extract_valuable_features(df)
    print(f"[FEATURES] 提取了 {len(valuable_features)} 个有价值的功能点")
    
    # 映射到AI-Plat概念
    mapped_features = map_to_ai_plat_concepts(valuable_features)
    print("[MAPPING] 完成功能映射到AI-Plat概念")
    
    # 生成洞察
    insights = generate_insights(modules, hierarchy, mapped_features)
    print("[INSIGHTS] 生成分析洞察")
    
    # 输出结果
    print("\n" + "="*60)
    print("[REPORT] 分析报告")
    print("="*60)
    
    print(f"\n[SUMMARY] 模块摘要:")
    print(f"   总模块数: {insights['module_summary']['total_modules']}")
    print(f"   模块列表: {', '.join(insights['module_summary']['modules_list'])}")
    print(f"   功能最多的模块: {insights['module_summary']['top_modules_by_features']}")
    
    print(f"\n[DISTRIBUTION] 功能分布:")
    for feature_type, count in insights['feature_distribution'].items():
        print(f"   {feature_type}: {count}")
    
    print(f"\n[ARCH] 架构影响:")
    for implication in insights['architecture_implications']:
        print(f"   - {implication}")
    
    print(f"\n[RECOMMEND] 推荐:")
    for recommendation in insights['recommendations']:
        print(f"   - {recommendation}")
    
    # 保存详细分析结果
    analysis_results = {
        'modules': modules,
        'hierarchy': hierarchy,
        'valuable_features': valuable_features,
        'mapped_features': mapped_features,
        'insights': insights
    }
    
    with open('legacy_features_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SAVE] 详细分析结果已保存到 legacy_features_analysis.json")
    
    # 特别关注与AI-Plat三大核心模块相关的功能
    print(f"\n" + "="*60)
    print("[CORE ANALYSIS] 与AI-Plat核心模块相关的功能分析")
    print("="*60)
    
    print(f"\n[ONTOLOGY] 本体论相关功能 ({len(mapped_features['ontology_related'])} 个):")
    for i, feature in enumerate(mapped_features['ontology_related'][:5]):  # 只显示前5个
        print(f"   {i+1}. 模块: {feature.get('模块名称', 'N/A')}, 功能: {feature.get('一级功能', 'N/A')}")
    
    print(f"\n[AGENT] 智能体相关功能 ({len(mapped_features['agent_related'])} 个):")
    for i, feature in enumerate(mapped_features['agent_related'][:5]):  # 只显示前5个
        print(f"   {i+1}. 模块: {feature.get('模块名称', 'N/A')}, 功能: {feature.get('一级功能', 'N/A')}")
    
    print(f"\n[VIBECODING] Vibecoding相关功能 ({len(mapped_features['vibecoding_related'])} 个):")
    for i, feature in enumerate(mapped_features['vibecoding_related'][:5]):  # 只显示前5个
        print(f"   {i+1}. 模块: {feature.get('模块名称', 'N/A')}, 功能: {feature.get('一级功能', 'N/A')}")
    
    return analysis_results


if __name__ == "__main__":
    results = main()