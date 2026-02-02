---
name: contract-audit
description: Comprehensive contract auditing and review for legal compliance, risk assessment, and clause verification. Use when Codex needs to analyze contracts for potential risks, compliance issues, missing clauses, or unfavorable terms. Applies legal standards and best practices to identify problematic provisions and suggest improvements.
---

# Contract Audit

## Overview

This skill provides comprehensive contract auditing capabilities to analyze contracts for potential legal risks, compliance issues, missing clauses, and unfavorable terms. The skill applies legal standards and best practices to identify problematic provisions and suggests improvements to protect the client's interests.

## Workflow-Based Structure

This skill follows a systematic workflow for contract review and analysis to ensure comprehensive coverage of all important aspects of the contract. The process is divided into several stages: initial assessment, clause-by-clause review, risk analysis, and final recommendations.

## Initial Assessment

1. Identify the type of contract (employment, service, NDA, licensing, etc.)
2. Determine the parties involved and their roles
3. Establish the primary purpose and scope of the agreement
4. Review effective dates, duration, and renewal terms
5. Identify governing law and jurisdiction clauses

## Clause-by-Clause Review

### Essential Clauses Check
- **Parties Identification**: Verify correct legal names and addresses
- **Recitals**: Ensure accurate background and purpose statements
- **Definitions**: Check for clear, non-conflicting definitions
- **Scope of Work/Deliverables**: Confirm clear and measurable terms
- **Payment Terms**: Review amounts, schedules, and conditions
- **Performance Standards**: Validate measurable criteria
- **Term and Termination**: Examine duration and termination conditions
- **Confidentiality**: Ensure adequate protection of sensitive information
- **Intellectual Property**: Verify ownership and licensing rights
- **Liability and Indemnification**: Assess risk allocation
- **Dispute Resolution**: Check for appropriate mechanisms

### Risk Assessment Categories
- **Financial Risks**: Payment delays, penalties, cost overruns
- **Legal Risks**: Non-compliance, unenforceable terms, regulatory violations
- **Operational Risks**: Performance failures, delivery delays
- **Strategic Risks**: Competitive disadvantage, market changes

## Detailed Review Process

1. **Document Preparation**: Load contract into review system
2. **Initial Scan**: Identify all sections, headings, and major clauses
3. **Gap Analysis**: Compare against standard templates for missing elements
4. **Risk Identification**: Flag potentially problematic clauses
5. **Compliance Check**: Verify alignment with applicable laws/regulations
6. **Negotiation Points**: Highlight areas for potential modification

## Risk Scoring Framework

Rate each identified risk using a standardized scale:
- **Critical**: Could cause severe financial or legal consequences
- **High**: Significant impact on business operations or legal standing
- **Medium**: Moderate concern requiring attention
- **Low**: Minor issue with minimal impact

## Reporting and Recommendations

### Executive Summary
- Overall risk assessment
- Critical issues requiring immediate attention
- Recommended priority actions

### Detailed Findings Report
- Specific clause references
- Risk level assessment
- Recommended modifications or alternatives
- Legal implications discussion

### Action Items
- Short-term fixes for immediate concerns
- Long-term improvements for future contracts
- Follow-up items for legal counsel review

## Best Practices

- Always consider the client's perspective and priorities
- Focus on practical solutions, not just theoretical issues
- Maintain awareness of industry-specific requirements
- Document all findings with specific section references
- Prioritize recommendations based on impact and feasibility

## Limitations

- This skill provides analysis based on standard legal principles but does not constitute legal advice
- Jurisdiction-specific laws may not be fully considered
- Complex or novel contractual arrangements may require specialist review
- Final legal review by qualified attorney is recommended before execution

## Resources

### scripts/
Python scripts for document processing, risk analysis, and report generation to automate portions of the contract review process.

### references/
Legal standards documentation, template clauses, industry-specific requirements, and regulatory compliance guidelines to inform the review process.

### assets/
Report templates, summary formats, and standardized recommendation documents for consistent output.

### traindata/
Training data for contract analysis including:
- Sample contracts for different industries
- Product feature lists for requirement matching (list/ directory)
- Function point evaluation data for workload estimation (功能点工作量评估/ directory)
- Risk assessment examples for four-level risk classification (四级风险清单/ directory)

## Enhanced Workflow for Requirements Analysis

When analyzing procurement documents or technical specifications (like tender documents), apply the following enhanced workflow in addition to standard contract auditing:

### 1. Requirements Decomposition
- Extract functional requirements from the document
- Identify integration requirements with existing systems
- Extract non-functional requirements (performance, security, high availability, stability, innovation compliance, metrics)

### 2. Product Matching Analysis
- Compare requirements against existing product features (in traindata/list/)
- Calculate feature match percentage
- Identify gaps and customization needs

### 3. Technical Risk Identification
- Identify specific points that are not satisfied
- Highlight unclear or undefined requirements
- Document implementation challenges

### 4. Non-functional Requirements Analysis
- Decompose non-functional requirements systematically
- Identify requirement gaps compared to standard benchmarks
- Assess compliance with industry standards

### 5. Workload Estimation
- Reference historical function point evaluations (in traindata/功能点工作量评估/)
- Estimate development effort based on matched and unmatched requirements
- Factor in complexity adjustments

### 6. Risk Consolidation
- Combine product capability and non-functional requirement satisfaction risks
- Consolidate gap requirement risks
- Format risks according to four-level classification system

### 7. Four-Level Risk Classification
- Generate risk register in format matching traindata/四级风险清单/ examples
- Include risk level, status, timeline, impact assessment, and mitigation measures
- Follow standard format for consistency with organization risk management processes

## Report Generation Template

The output should follow the pattern shown in EXAMPLE.md, containing sections for requirements decomposition, product matching analysis, technical risks, non-functional analysis, workload estimates, risk consolidation, and four-level risk register.

## Specialized Scripts

### wenxin5_skill.py
A specialized script for generating comprehensive requirements analysis reports from procurement documents (such as tender documents). This script:

- Analyzes contract content to extract functional and non-functional requirements
- Compares requirements against existing product features from traindata/list/
- Generates detailed mismatch analysis showing what requirements are not satisfied by existing products
- Provides workload estimation based on function point analysis from traindata/功能点工作量评估/
- Creates four-level risk classification following examples from traindata/四级风险清单/
- Outputs reports in either Markdown (.md) or Microsoft Word (.docx) format
- Includes detailed "unsatisfied requirements list" comparing against product feature lists

Usage:
```
python wenxin5_skill.py <contract_file_path> <traindata_path> [output_format]
```
Where output_format can be 'md' for markdown (default) or 'doc' for Word document.
