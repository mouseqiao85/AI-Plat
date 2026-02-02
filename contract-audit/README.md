# Contract Audit Skill

## Overview
This skill provides comprehensive contract auditing and requirements analysis capabilities. It analyzes contracts for potential legal risks, compliance issues, missing clauses, and unfavorable terms, with special focus on procurement documents and technical specifications.

## Key Features
- Standard contract auditing (legal compliance, risk assessment, clause verification)
- Requirements decomposition from procurement documents
- Product-feature matching analysis
- Technical risk identification
- Workload estimation
- Four-level risk classification
- Support for both Markdown and Word document output formats

## Directory Structure
```
contract-audit/
├── SKILL.md          # Main skill definition
├── EXAMPLE.md        # Example report output
├── wenxin5_skill.py  # Specialized analysis script
├── traindata/        # Training data for analysis
│   ├── list/         # Product feature lists
│   ├── 功能点工作量评估/  # Function point evaluation data
│   └── 四级风险清单/    # Risk classification examples
└── README.md         # This file
```

## Usage

### Standard Contract Analysis
Use the standard contract auditing workflow for general contracts.

### Procurement Document Analysis
For procurement documents (like tender documents), use the specialized script:

```bash
python wenxin5_skill.py <contract_file_path> <traindata_path> [output_format]
```

Parameters:
- `<contract_file_path>`: Path to the contract file to analyze
- `<traindata_path>`: Path to the traindata directory
- `[output_format]`: Output format ('md' for markdown, 'doc' for Word document; defaults to 'md')

### Example
```bash
python wenxin5_skill.py ./tender_document.txt ./traindata doc
```

## Output Components
1. **Requirements Decomposition**: Functional, integration, and non-functional requirements
2. **Product Matching Analysis**: Feature match percentage and gap analysis
3. **Technical Risk Identification**: Unsatisfied points and unclear requirements
4. **Non-functional Analysis**: Performance, security, availability requirements
5. **Workload Estimation**: Based on function point analysis
6. **Risk Consolidation**: Combined risk assessment
7. **Four-level Risk Register**: Detailed risk classification with mitigation strategies

## Training Data Requirements
The skill requires the following training data in the `traindata/` directory:
- `list/`: Product feature lists in Excel format
- `功能点工作量评估/`: Function point evaluation data
- `四级风险清单/`: Risk classification examples

## Report Features
- Detailed "unsatisfied requirements list" comparing against product feature lists
- Quantified match percentage analysis
- Structured risk assessment
- Workload estimation based on historical data
- Professional formatting in both Markdown and Word formats