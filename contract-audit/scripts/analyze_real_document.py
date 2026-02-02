#!/usr/bin/env python3
"""
Script to analyze the actual Industrial Bank document
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
    
    # Look for the specific bank document
    bank_doc_path = None
    for file_path in traindata_path.iterdir():
        if file_path.suffix in ['.docx', '.doc'] and 'ҵ' in file_path.name:
            bank_doc_path = file_path
            break
    
    if not bank_doc_path:
        print("Industrial Bank document not found in traindata directory")
        return
    
    print(f"Analyzing document: {bank_doc_path}")
    
    # Process the specific bank document
    try:
        # Get the full analysis report
        analysis_report = analyzer.generate_report()
        
        # Save the full analysis to a JSON file
        analysis_output_path = report_path / f"real_industrial_bank_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(analysis_output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_report, f, ensure_ascii=False, indent=2)
        
        # Generate the report in Markdown
        bank_report = generator.generate_report(analysis_report, "Real Industrial Bank Document Analysis")
        bank_report_path = report_path / f"real_industrial_bank_contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(bank_report_path, 'w', encoding='utf-8') as f:
            f.write(bank_report)
        
        print(f"Real Industrial Bank document analysis report saved to: {bank_report_path}")
        print(f"Analysis JSON saved to: {analysis_output_path}")
        
        # Print summary
        summary = analysis_report.get('summary', {})
        print("\n--- ANALYSIS SUMMARY ---")
        print(f"Total risks identified: {summary.get('total_risks', 'N/A')}")
        print(f"Critical risks: {summary.get('critical_risks', 'N/A')}")
        print(f"High risks: {summary.get('high_risks', 'N/A')}")
        print(f"Missing clauses: {summary.get('missing_clauses_count', 'N/A')}")
        print(f"Recommendations: {summary.get('recommendations_count', 'N/A')}")
        
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()