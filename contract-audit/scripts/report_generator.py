#!/usr/bin/env python3
"""
Report Generator - Creates formatted reports from contract analysis results
"""

import json
import sys
from datetime import datetime
from typing import Dict, List


class ReportGenerator:
    """
    Generates professional reports from contract analysis results
    """
    
    def __init__(self):
        self.report_template = """
# Contract Analysis Report

**Generated on:** {date}
**Document Analyzed:** {filename}
**Analysis ID:** {analysis_id}

## Executive Summary

{executive_summary}

## Risk Assessment

{risk_assessment}

## Missing Clauses

{missing_clauses}

## Recommendations

{recommendations}

## Detailed Findings

{detailed_findings}

---

*This analysis was performed automatically. Please have a qualified attorney review this contract before execution.*
        """

    def generate_report(self, analysis_results: Dict, filename: str = "Unknown") -> str:
        """
        Generates a formatted report from analysis results
        """
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analysis_id = f"CA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        executive_summary = self._generate_executive_summary(analysis_results)
        risk_assessment = self._generate_risk_assessment(analysis_results)
        missing_clauses = self._generate_missing_clauses_section(analysis_results)
        recommendations = self._generate_recommendations_section(analysis_results)
        detailed_findings = self._generate_detailed_findings(analysis_results)
        
        report = self.report_template.format(
            date=date_str,
            filename=filename,
            analysis_id=analysis_id,
            executive_summary=executive_summary,
            risk_assessment=risk_assessment,
            missing_clauses=missing_clauses,
            recommendations=recommendations,
            detailed_findings=detailed_findings
        )
        
        return report
    
    def _generate_executive_summary(self, results: Dict) -> str:
        """Generates the executive summary section"""
        summary = results.get('summary', {})
        
        critical_risks = summary.get('critical_risks', 0)
        high_risks = summary.get('high_risks', 0)
        missing_clauses = summary.get('missing_clauses_count', 0)
        
        if critical_risks > 0:
            status = "**STATUS: HIGH RISK - EXTENSIVE REVIEW REQUIRED**"
        elif high_risks > 0:
            status = "**STATUS: MEDIUM RISK - CAREFUL REVIEW ADVISED**"
        elif missing_clauses > 0:
            status = "**STATUS: MEDIUM RISK - MISSING KEY CLAUSES**"
        else:
            status = "**STATUS: LOW RISK - RELATIVELY COMPLETE**"
        
        summary_text = f"{status}\n\n"
        summary_text += f"- Total risks identified: {summary.get('total_risks', 0)}\n"
        summary_text += f"- Critical risks: {critical_risks}\n"
        summary_text += f"- High risks: {high_risks}\n"
        summary_text += f"- Missing essential clauses: {missing_clauses}\n"
        summary_text += f"- Recommendations: {summary.get('recommendations_count', 0)}"
        
        return summary_text
    
    def _generate_risk_assessment(self, results: Dict) -> str:
        """Generates the risk assessment section"""
        risks = results.get('risks', [])
        
        if not risks:
            return "No significant risks were identified in the contract."
        
        # Group risks by level
        critical_risks = [r for r in risks if r['level'] == 'critical']
        high_risks = [r for r in risks if r['level'] == 'high']
        medium_risks = [r for r in risks if r['level'] == 'medium']
        
        risk_text = ""
        
        if critical_risks:
            risk_text += "### CRITICAL RISKS (Require Immediate Attention)\n\n"
            for risk in critical_risks:
                risk_text += f"- **{risk['keyword'].upper()}** ({risk['category']}): {risk['context']}\n\n"
        
        if high_risks:
            risk_text += "### HIGH RISKS\n\n"
            for risk in high_risks:
                risk_text += f"- **{risk['keyword'].upper()}** ({risk['category']}): {risk['context']}\n\n"
        
        if medium_risks:
            risk_text += "### MEDIUM RISKS\n\n"
            for risk in medium_risks:
                risk_text += f"- **{risk['keyword'].upper()}** ({risk['category']}): {risk['context']}\n\n"
        
        if not critical_risks and not high_risks and not medium_risks:
            risk_text = "No risks were identified."
        
        return risk_text
    
    def _generate_missing_clauses_section(self, results: Dict) -> str:
        """Generates the missing clauses section"""
        missing = results.get('missing_clauses', [])
        
        if not missing:
            return "No essential clauses appear to be missing from the contract."
        
        missing_text = "The following essential clauses may be missing from the contract:\n\n"
        for clause in missing:
            missing_text += f"- {clause.title()}\n"
        
        missing_text += "\nConsider adding these clauses to ensure comprehensive coverage."
        
        return missing_text
    
    def _generate_recommendations_section(self, results: Dict) -> str:
        """Generates the recommendations section"""
        recommendations = results.get('recommendations', [])
        
        if not recommendations:
            return "No specific recommendations were generated."
        
        rec_text = ""
        for i, rec in enumerate(recommendations, 1):
            # Format recommendation with proper emphasis
            if 'CRITICAL:' in rec:
                rec_text += f"{i}. **{rec}**\n"
            elif 'HIGH PRIORITY:' in rec:
                rec_text += f"{i}. **{rec}**\n"
            elif 'IMPROVEMENT:' in rec:
                rec_text += f"{i}. {rec}\n"
            elif 'CONTRACT APPEARS' in rec:
                rec_text += f"{i}. {rec}\n"
            else:
                rec_text += f"{i}. {rec}\n"
        
        return rec_text
    
    def _generate_detailed_findings(self, results: Dict) -> str:
        """Generates the detailed findings section"""
        risks = results.get('risks', [])
        missing = results.get('missing_clauses', [])
        
        if not risks and not missing:
            return "No specific findings to report."
        
        findings_text = ""
        
        if risks:
            findings_text += "### Detailed Risk Analysis\n\n"
            for risk in risks:
                findings_text += f"**Risk Level:** {risk['level'].title()}\n"
                findings_text += f"**Keyword:** {risk['keyword']}\n"
                findings_text += f"**Category:** {risk['category']}\n"
                findings_text += f"**Context:** \"{risk['context']}\"\n\n"
        
        if missing:
            findings_text += "### Missing Clauses Details\n\n"
            for clause in missing:
                findings_text += f"**Missing Clause:** {clause.title()}\n"
                findings_text += f"**Importance:** Essential for comprehensive contract coverage\n\n"
        
        return findings_text


def main():
    if len(sys.argv) < 3:
        print("Usage: python report_generator.py <analysis_results.json> <output_report.md>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            analysis_results = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {input_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {input_file}")
        sys.exit(1)
    
    generator = ReportGenerator()
    report = generator.generate_report(analysis_results, input_file)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report generated successfully: {output_file}")


if __name__ == "__main__":
    main()