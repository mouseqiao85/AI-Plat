#!/usr/bin/env python3
"""
Contract Analyzer - A script for automated contract review and risk assessment
"""

import re
import sys
from typing import Dict, List, Tuple, Optional
import json


class ContractAnalyzer:
    """
    Analyzes contracts to identify risks, missing clauses, and problematic provisions
    """
    
    def __init__(self):
        self.risk_keywords = {
            'financial': [
                'penalty', 'fee', 'cost', 'expense', 'liability', 'indemnify',
                'liquidated damages', 'termination fee', 'overage charges'
            ],
            'legal': [
                'waive', 'release', 'hold harmless', 'exclusive remedy',
                'limitation of liability', 'no warranty', 'as is'
            ],
            'operational': [
                'sole discretion', 'unilateral', 'at will', 'unlimited',
                'indefinite term', 'automatic renewal'
            ]
        }
        
        self.essential_clauses = [
            'parties', 'scope of work', 'payment terms', 'term and termination',
            'confidentiality', 'intellectual property', 'dispute resolution',
            'governing law', 'liability limitation', 'warranties'
        ]
        
        self.risk_levels = {
            'critical': ['indemnify', 'hold harmless', 'waive', 'sole discretion'],
            'high': ['penalty', 'liability', 'expense', 'terminate', 'automatic renewal'],
            'medium': ['fee', 'cost', 'unilateral', 'as is', 'limitation']
        }

    def analyze_contract(self, contract_text: str) -> Dict:
        """
        Performs comprehensive analysis of the contract text
        """
        results = {
            'summary': {},
            'risks': [],
            'missing_clauses': [],
            'recommendations': []
        }
        
        # Clean the text
        clean_text = self._clean_text(contract_text.lower())
        
        # Identify risks
        results['risks'] = self._identify_risks(clean_text)
        
        # Check for essential clauses
        results['missing_clauses'] = self._check_missing_clauses(clean_text)
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results['risks'], results['missing_clauses'])
        
        # Create summary
        results['summary'] = self._create_summary(results)
        
        return results

    def _clean_text(self, text: str) -> str:
        """Clean and normalize the contract text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _identify_risks(self, text: str) -> List[Dict]:
        """Identifies potential risks in the contract"""
        risks = []
        
        for level, keywords in self.risk_levels.items():
            for keyword in keywords:
                if keyword in text:
                    # Find context around the keyword
                    pattern = r'(?:\w+\s+){0,10}' + re.escape(keyword) + r'(?:\s+\w+){0,10}'
                    matches = re.findall(pattern, text)
                    
                    for match in matches:
                        risk = {
                            'level': level,
                            'keyword': keyword,
                            'context': match.strip(),
                            'category': self._get_risk_category(keyword)
                        }
                        
                        # Avoid duplicates
                        if risk not in risks:
                            risks.append(risk)
        
        # Sort by risk level
        risk_order = {'critical': 0, 'high': 1, 'medium': 2}
        risks.sort(key=lambda x: risk_order.get(x['level'], 3))
        
        return risks

    def _get_risk_category(self, keyword: str) -> str:
        """Determines the category of risk based on keyword"""
        for category, keywords in self.risk_keywords.items():
            if keyword in keywords:
                return category
        return 'other'

    def _check_missing_clauses(self, text: str) -> List[str]:
        """Checks for missing essential clauses in the contract"""
        missing = []
        
        for clause in self.essential_clauses:
            # Simple check - in a real implementation, this would be more sophisticated
            if not any(part in text for part in clause.split()):
                missing.append(clause)
                
        return missing

    def _generate_recommendations(self, risks: List[Dict], missing_clauses: List[str]) -> List[str]:
        """Generates recommendations based on identified issues"""
        recommendations = []
        
        # Recommendations for risks
        critical_risks = [r for r in risks if r['level'] == 'critical']
        high_risks = [r for r in risks if r['level'] == 'high']
        
        if critical_risks:
            recommendations.append("CRITICAL: Review and negotiate critical risk items before signing")
            
        if high_risks:
            recommendations.append("HIGH PRIORITY: Address high-risk items in negotiations")
            
        if missing_clauses:
            recommendations.append(f"IMPROVEMENT: Add missing clauses: {', '.join(missing_clauses)}")
            
        if not critical_risks and not high_risks and not missing_clauses:
            recommendations.append("CONTRACT APPEARS COMPREHENSIVE WITH MINIMAL RISKS IDENTIFIED")
            
        return recommendations

    def _create_summary(self, results: Dict) -> Dict:
        """Creates a summary of the analysis"""
        return {
            'total_risks': len(results['risks']),
            'critical_risks': len([r for r in results['risks'] if r['level'] == 'critical']),
            'high_risks': len([r for r in results['risks'] if r['level'] == 'high']),
            'missing_clauses_count': len(results['missing_clauses']),
            'recommendations_count': len(results['recommendations'])
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python contract_analyzer.py <contract_file.txt>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            contract_text = f.read()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        sys.exit(1)
    
    analyzer = ContractAnalyzer()
    results = analyzer.analyze_contract(contract_text)
    
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()