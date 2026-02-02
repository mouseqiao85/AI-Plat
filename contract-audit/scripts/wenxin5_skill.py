#!/usr/bin/env python3
"""
Wenxin5 Skill - Contract Analysis and Evaluation Tool
This script analyzes tender documents and generates evaluation reports
"""

import os
import sys
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import zipfile
import xml.etree.ElementTree as ET
import re

# Try to import docx and doc libraries for different Word formats
try:
    from docx import Document
except ImportError:
    Document = None

try:
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

class ContractAnalyzer:
    """
    Analyzes tender documents and generates comprehensive evaluation reports
    """
    
    def __init__(self, traindata_path):
        self.traindata_path = Path(traindata_path)
        self.product_features_path = self.traindata_path / "list"
        self.workload_eval_path = self.traindata_path / "功能点工作量评估"
        self.risk_list_path = self.traindata_path / "文件需求清单"  # Assuming this is where risk lists are
        
    def read_docx_content(self, file_path):
        """
        Extract text content from a .docx or .doc file
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.docx':
            # Handle .docx files (OpenXML format)
            try:
                with zipfile.ZipFile(file_path, 'r') as docx:
                    content = docx.read('word/document.xml')
                    tree = ET.fromstring(content)
                    
                    # Define namespace
                    namespaces = {
                        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                    }
                    
                    # Extract text from paragraphs
                    paragraphs = tree.findall('.//w:p', namespaces)
                    text = []
                    for para in paragraphs:
                        texts = para.findall('.//w:t', namespaces)
                        para_text = ''.join([t.text for t in texts if t.text])
                        # Clean up special characters that cause encoding issues
                        para_text = para_text.replace('\u200b', '')  # Zero-width space
                        para_text = para_text.replace('\ufeff', '')  # BOM
                        if para_text.strip():
                            text.append(para_text.strip())
                    
                    return '\n'.join(text)
            except Exception as e:
                print(f"Error reading {file_path}: {str(e)}")
                return ""
        
        elif file_ext == '.doc':
            # Handle .doc files (legacy format)
            try:
                # First try with win32com if available
                if HAS_WIN32COM:
                    word_app = win32com.client.Dispatch("Word.Application")
                    word_app.Visible = False
                    doc = word_app.Documents.Open(file_path)
                    content = doc.Content.Text
                    doc.Close()
                    word_app.Quit()
                    return content.replace('\u200b', '').replace('\ufeff', '')
                else:
                    # If win32com is not available, skip .doc files
                    print(f"Skipping .doc file {file_path} (requires win32com)")
                    return ""
            except Exception as e:
                print(f"Error reading .doc file {file_path}: {str(e)}")
                return ""
        
        else:
            print(f"Unsupported file format: {file_path}")
            return ""

    def extract_requirements_from_document(self, content):
        """
        Extract functional, integration, and non-functional requirements from document content
        """
        # Define requirement categories
        requirements = {
            'functional': [],
            'integration': [],
            'non_functional': {
                'performance': [],
                'security': [],
                'high_availability': [],
                'stability': [],
                'innovation': [],
                'metrics': []
            }
        }
        
        # Normalize content for easier searching
        normalized_content = content.lower()
        
        # Keywords for different requirement types
        functional_keywords = [
            '功能', '模块', '系统', '实现', '提供', '支持', '管理', '操作', 
            '查询', '统计', '报表', '导入', '导出', '上传', '下载', '编辑',
            '删除', '新增', '修改', '审批', '流程', '通知', '监控'
        ]
        
        integration_keywords = [
            '接口', '集成', '对接', '数据交换', '同步', '第三方', '外部系统',
            'API', 'webservice', '单点登录', '统一认证', '数据共享'
        ]
        
        performance_keywords = [
            '响应时间', '并发', '吞吐量', 'TPS', 'QPS', '负载', '压力',
            '性能', '速度', '效率', '容量', '扩展性'
        ]
        
        security_keywords = [
            '安全', '加密', '权限', '认证', '授权', '审计', '日志', '防护',
            '漏洞', 'SSL', 'HTTPS', '防火墙', '认证', '密码', '密钥'
        ]
        
        availability_keywords = [
            '高可用', '容错', '冗余', '备份', '恢复', '灾备', '故障转移',
            '99.', 'uptime', '可用性', '稳定性', '可靠性'
        ]
        
        # Extract functional requirements
        for keyword in functional_keywords:
            if keyword in normalized_content:
                # Find sentences containing the keyword
                pattern = r'[^。！!?]*' + keyword + r'[^。！!?]*[。！!?]'
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.strip() and match not in requirements['functional']:
                        requirements['functional'].append(match.strip())
        
        # Extract integration requirements
        for keyword in integration_keywords:
            if keyword in normalized_content:
                pattern = r'[^。！!?]*' + keyword + r'[^。！!?]*[。！!?]'
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.strip() and match not in requirements['integration']:
                        requirements['integration'].append(match.strip())
        
        # Extract non-functional requirements
        for keyword in performance_keywords:
            if keyword in normalized_content:
                pattern = r'[^。！!?]*' + keyword + r'[^。！!?]*[。！!?]'
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.strip() and match not in requirements['non_functional']['performance']:
                        requirements['non_functional']['performance'].append(match.strip())
        
        for keyword in security_keywords:
            if keyword in normalized_content:
                pattern = r'[^。！!?]*' + keyword + r'[^。！!?]*[。！!?]'
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.strip() and match not in requirements['non_functional']['security']:
                        requirements['non_functional']['security'].append(match.strip())
        
        for keyword in availability_keywords:
            if keyword in normalized_content:
                pattern = r'[^。！!?]*' + keyword + r'[^。！!?]*[。！!?]'
                matches = re.findall(pattern, content)
                for match in matches:
                    if match.strip() and match not in requirements['non_functional']['high_availability']:
                        requirements['non_functional']['high_availability'].append(match.strip())
        
        return requirements

    def load_product_features(self):
        """
        Load existing product features from Excel file
        """
        product_features = []
        
        if self.product_features_path.exists():
            for file in self.product_features_path.glob("*.xlsx"):
                try:
                    df = pd.read_excel(str(file))
                    # Convert DataFrame to list of features
                    for _, row in df.iterrows():
                        feature = {}
                        for col, val in row.items():
                            if pd.notna(val):
                                feature[col] = str(val)
                        if feature:
                            product_features.append(feature)
                except Exception as e:
                    print(f"Error reading {file}: {str(e)}")
        
        return product_features

    def match_functionality(self, requirements, product_features):
        """
        Match tender requirements against existing product features
        """
        functional_reqs = requirements.get('functional', [])
        
        matches = {
            'matched': [],
            'unmatched': [],
            'partial_match': []
        }
        
        # Simple text matching algorithm
        for req in functional_reqs:
            req_lower = req.lower()
            matched = False
            
            for feature in product_features:
                # Check if any feature value matches the requirement
                for key, value in feature.items():
                    if value.lower() in req_lower or req_lower in value.lower():
                        matches['matched'].append({
                            'requirement': req,
                            'feature': feature
                        })
                        matched = True
                        break
                
                if matched:
                    break
            
            if not matched:
                matches['unmatched'].append(req)
        
        # Calculate match percentage
        total_reqs = len(functional_reqs)
        matched_count = len(matches['matched'])
        match_percentage = (matched_count / total_reqs * 100) if total_reqs > 0 else 0
        
        matches['match_percentage'] = match_percentage
        
        return matches

    def identify_technical_risks(self, requirements, product_features):
        """
        Identify technical risks based on requirements and product capabilities
        """
        risks = []
        
        # Check for non-functional gaps
        for category, items in requirements['non_functional'].items():
            if items:  # If there are requirements in this category
                # Check if product has corresponding capabilities
                has_capability = False
                for feature in product_features:
                    for key, value in feature.items():
                        if category in key.lower() or category in value.lower():
                            has_capability = True
                            break
                    if has_capability:
                        break
                
                if not has_capability:
                    risks.append({
                        'type': 'Non-functional gap',
                        'category': category,
                        'description': f'Product may not meet {category} requirements',
                        'details': items[:3]  # Show first 3 requirement examples
                    })
        
        # Check for integration complexity
        integration_reqs = requirements.get('integration', [])
        if len(integration_reqs) > 3:  # Arbitrary threshold
            risks.append({
                'type': 'Integration complexity',
                'category': 'Integration',
                'description': f'Multiple integration points required ({len(integration_reqs)})',
                'details': integration_reqs[:3]
            })
        
        return risks

    def analyze_workload(self):
        """
        Analyze workload based on historical data
        """
        workload_data = []
        
        if self.workload_eval_path.exists():
            for file in self.workload_eval_path.glob("*.xlsx"):
                try:
                    df = pd.read_excel(str(file))
                    workload_data.append({
                        'file': file.name,
                        'data': df.to_dict('records') if not df.empty else []
                    })
                except Exception as e:
                    print(f"Error reading workload file {file}: {str(e)}")
        
        return workload_data

    def generate_four_level_risk_list(self, risks, requirements):
        """
        Generate four-level risk list based on identified risks and requirements
        """
        risk_matrix = []
        
        # Define risk levels
        risk_levels = {
            'Level 1 (Critical)': ['安全', '认证', '授权', '审计', '漏洞', '故障', '崩溃'],
            'Level 2 (High)': ['性能', '响应时间', '并发', '可用性', '稳定性', '备份', '恢复'],
            'Level 3 (Medium)': ['接口', '集成', '数据', '传输', '同步', '兼容性'],
            'Level 4 (Low)': ['界面', '体验', '辅助', '帮助', '提示', '文档']
        }
        
        # Categorize risks
        for level, keywords in risk_levels.items():
            level_risks = []
            for keyword in keywords:
                # Look for risks related to this keyword
                for category, items in requirements['non_functional'].items():
                    if keyword in category or any(keyword in item for item in items):
                        level_risks.extend(items[:2])  # Add first 2 items as examples
                
                # Also check functional requirements
                for req in requirements.get('functional', []):
                    if keyword in req:
                        level_risks.append(req)
            
            for risk_item in level_risks:
                risk_matrix.append({
                    'Level': level,
                    'Risk Type': 'Requirement Gap',
                    'Description': risk_item[:100] + ('...' if len(risk_item) > 100 else ''),
                    'Impact': level.split()[1][1:-1] if '(' in level else 'Medium',
                    'Mitigation Strategy': 'Implementation required'
                })
        
        # Add technical risks identified earlier
        for risk in risks:
            risk_matrix.append({
                'Level': 'Level 2 (High)' if risk['type'] == 'Non-functional gap' else 'Level 3 (Medium)',
                'Risk Type': risk['type'],
                'Description': risk['description'],
                'Impact': 'High' if 'gap' in risk['type'].lower() else 'Medium',
                'Mitigation Strategy': 'Evaluate technical solution'
            })
        
        return risk_matrix

    def generate_report(self):
        """
        Generate comprehensive contract analysis report
        """
        print("Starting contract analysis...")
        
        # Find all tender documents
        tender_docs = []
        for ext in ['.doc', '.docx']:
            tender_docs.extend(list(self.traindata_path.glob(f'*{ext}')))
        
        print(f"Found {len(tender_docs)} tender documents")
        
        all_requirements = {
            'functional': [],
            'integration': [],
            'non_functional': {
                'performance': [],
                'security': [],
                'high_availability': [],
                'stability': [],
                'innovation': [],
                'metrics': []
            }
        }
        
        # Process each tender document
        for doc_path in tender_docs:
            print(f"Processing {doc_path.name}...")
            content = self.read_docx_content(str(doc_path))
            if content:
                doc_requirements = self.extract_requirements_from_document(content)
                
                # Combine requirements
                all_requirements['functional'].extend(doc_requirements['functional'])
                all_requirements['integration'].extend(doc_requirements['integration'])
                
                for category in all_requirements['non_functional']:
                    all_requirements['non_functional'][category].extend(
                        doc_requirements['non_functional'][category]
                    )
        
        # Remove duplicates
        all_requirements['functional'] = list(set(all_requirements['functional']))
        all_requirements['integration'] = list(set(all_requirements['integration']))
        
        for category in all_requirements['non_functional']:
            all_requirements['non_functional'][category] = list(set(all_requirements['non_functional'][category]))
        
        # Load product features
        print("Loading product features...")
        product_features = self.load_product_features()
        print(f"Loaded {len(product_features)} product features")
        
        # Perform functionality matching
        print("Performing functionality matching...")
        functionality_match = self.match_functionality(all_requirements, product_features)
        
        # Identify technical risks
        print("Identifying technical risks...")
        technical_risks = self.identify_technical_risks(all_requirements, product_features)
        
        # Analyze workload
        print("Analyzing workload...")
        workload_analysis = self.analyze_workload()
        
        # Generate four-level risk list
        print("Generating four-level risk list...")
        four_level_risks = self.generate_four_level_risk_list(technical_risks, all_requirements)
        
        # Generate final report
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'tender_documents_count': len(tender_docs),
                'product_features_count': len(product_features)
            },
            'requirements_analysis': {
                'functional_count': len(all_requirements['functional']),
                'functional_list': all_requirements['functional'][:10],  # First 10 as sample
                'integration_count': len(all_requirements['integration']),
                'integration_list': all_requirements['integration'][:10],
                'non_functional_breakdown': {
                    cat: len(items) for cat, items in all_requirements['non_functional'].items()
                }
            },
            'functionality_matching': functionality_match,
            'technical_risks': technical_risks,
            'workload_analysis': workload_analysis,
            'four_level_risk_list': four_level_risks
        }
        
        return report

def main():
    if len(sys.argv) < 2:
        print("Usage: python wenxin5_skill.py <traindata_path>")
        sys.exit(1)
    
    traindata_path = sys.argv[1]
    
    analyzer = ContractAnalyzer(traindata_path)
    report = analyzer.generate_report()
    
    # Output report as JSON, handling encoding properly
    import io
    output = json.dumps(report, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(output.encode('utf-8'))

if __name__ == "__main__":
    main()