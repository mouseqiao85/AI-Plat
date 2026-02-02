#!/usr/bin/env python3
"""
Script to generate all four contract evaluation reports
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


def main():
    # Define the paths
    traindata_path = Path("C:/Users/qiaoshuowen/clawd/skills/contract-audit/traindata")
    report_path = traindata_path / "report"
    
    # Create report directory if it doesn't exist
    report_path.mkdir(exist_ok=True)
    
    # Initialize analyzer and generator
    analyzer = ContractAnalyzer(traindata_path)
    generator = ReportGenerator()
    
    # Generate the main analysis report
    print("Generating main analysis report...")
    analysis_report = analyzer.generate_report()
    
    # Save the full analysis to a JSON file
    analysis_output_path = report_path / f"full_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(analysis_output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)
    
    # Generate the main report in Markdown
    main_report = generator.generate_report(analysis_report, "Full Contract Analysis")
    main_report_path = report_path / f"main_contract_evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(main_report_path, 'w', encoding='utf-8') as f:
        f.write(main_report)
    
    print(f"Main analysis report saved to: {main_report_path}")
    
    # Generate additional reports for each major component
    components = {
        "requirements_analysis": "Requirements Analysis Report",
        "functionality_matching": "Functionality Matching Report", 
        "technical_risks": "Technical Risks Assessment",
        "four_level_risk_list": "Four-Level Risk Matrix"
    }
    
    for comp_key, comp_title in components.items():
        if comp_key in analysis_report:
            # Create a simplified report focusing on this component
            component_data = {
                'summary': analysis_report.get('summary', {}),
                'risks': analysis_report.get('risks', []),
                'missing_clauses': analysis_report.get('missing_clauses', []),
                'recommendations': analysis_report.get('recommendations', [])
            }
            
            # Add the specific component data
            component_data[comp_key] = analysis_report[comp_key]
            
            component_report = generator.generate_report(component_data, comp_title)
            component_report_path = report_path / f"{comp_title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(component_report_path, 'w', encoding='utf-8') as f:
                f.write(component_report)
                
            print(f"Component report '{comp_title}' saved to: {component_report_path}")
    
    print("\nAll reports have been generated successfully!")
    print(f"Reports are located in: {report_path.absolute()}")


if __name__ == "__main__":
    main()