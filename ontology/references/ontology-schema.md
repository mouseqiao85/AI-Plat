# 本体 Schema 定义

本文档定义贷款预审本体的标准数据结构，用于规范化文档抽取和知识存储。

> **理论基础**：本体不是独立工具，而是「四层对象建设链」中的语义层。
> 参见 `references/object-chain-guide.md` 了解完整分层框架与工程落地路径。

## 目录

- [四层对象建设链定位](#四层对象建设链定位)
- [顶层结构](#顶层结构)
- [核心概念节点](#核心概念节点)
- [审批规则节点](#审批规则节点)
- [关系类型](#关系类型)
- [JSON 存储格式示例](#json-存储格式示例)

---

## 四层对象建设链定位

在进行本体抽取之前，应先判断当前输入材料处于哪一层，以确定抽取重点：

| 层级 | 名称 | 核心问题 | 对应本技能操作 |
|------|------|----------|---------------|
| **第1层** | 业务架构层 | 对象归属哪个能力域/价值流？治理责任是谁？ | 识别主题域、划定对象边界 |
| **第2层** | 本体语义层 | 对象的概念/属性/关系/约束是什么？ | **本体抽取核心层**，生成 rules + concepts |
| **第3层** | 知识图谱层 | 实例之间如何连接？多跳关系如何穿透？ | 构建 relations，支撑 review 模式推理 |
| **第4层** | 业务对象数字化层 | 对象如何进入主数据/接口/RAG/Agent？ | 输出结构化 JSON，对接下游系统 |

**适用判断**（摘自企业架构研究会）：
- 若输入材料主要描述**组织职责、流程边界**→ 重点抽取第1层归属关系
- 若输入材料主要描述**制度条款、审批规则**→ 重点抽取第2层本体语义（当前技能主战场）
- 若输入材料包含**历史审批案例、关联事件**→ 同时构建第3层实例关系
- 若目标是**接入RAG/Agent**→ 确保第4层的结构化输出完整

---

## 顶层结构

```json
{
  "version": "1.0",
  "updated_at": "ISO8601时间戳",
  "source_docs": ["来源文件名列表"],
  "concepts": { ... },
  "rules": [ ... ],
  "changelog": [ ... ]
}
```

---

## 核心概念节点

### 1. 客户（Borrower）

```json
{
  "type": "Borrower",
  "subtypes": ["企业客户", "个人客户", "政府客户"],
  "attributes": {
    "credit_rating": { "type": "string", "desc": "信用等级，如AA/A/BBB" },
    "industry": { "type": "string", "desc": "所属行业" },
    "relationship_years": { "type": "number", "unit": "年", "desc": "与行内合作年限" },
    "blacklist_status": { "type": "boolean", "desc": "是否在黑名单中" }
  }
}
```

### 2. 担保（Collateral）

```json
{
  "type": "Collateral",
  "subtypes": ["抵押", "质押", "保证", "信用"],
  "attributes": {
    "collateral_value": { "type": "number", "unit": "万元" },
    "loan_to_value_ratio": { "type": "number", "unit": "%", "desc": "抵押率/质押率" },
    "guarantor_rating": { "type": "string", "desc": "担保人信用等级（保证担保时）" },
    "liquidity": { "type": "enum", "values": ["高", "中", "低"], "desc": "担保品变现能力" }
  }
}
```

### 3. 财务指标（FinancialIndicator）

```json
{
  "type": "FinancialIndicator",
  "attributes": {
    "asset_liability_ratio": { "type": "number", "unit": "%", "desc": "资产负债率" },
    "current_ratio": { "type": "number", "desc": "流动比率" },
    "quick_ratio": { "type": "number", "desc": "速动比率" },
    "interest_coverage": { "type": "number", "desc": "利息保障倍数" },
    "net_profit_margin": { "type": "number", "unit": "%", "desc": "净利润率" },
    "revenue_growth_rate": { "type": "number", "unit": "%", "desc": "营收增长率（近3年均值）" },
    "cash_flow_coverage": { "type": "number", "desc": "现金流覆盖倍数" }
  }
}
```

### 4. 贷款产品（LoanProduct）

```json
{
  "type": "LoanProduct",
  "attributes": {
    "product_type": { "type": "string", "desc": "产品类型，如流动资金贷款/固定资产贷款" },
    "amount": { "type": "number", "unit": "万元" },
    "tenor": { "type": "number", "unit": "月" },
    "interest_rate": { "type": "number", "unit": "%" },
    "purpose": { "type": "string", "desc": "贷款用途" }
  }
}
```

---

## 审批规则节点

每条规则包含以下字段：

```json
{
  "rule_id": "R-001",
  "rule_type": "threshold | veto | exception | condition",
  "source_doc": "制度文件名",
  "source_clause": "第X章第Y条",
  "description": "规则的自然语言描述",
  "applies_to": ["Borrower", "Collateral", "FinancialIndicator"],
  "condition": {
    "field": "asset_liability_ratio",
    "operator": "<=",
    "value": 70,
    "unit": "%"
  },
  "action": "pass | reject | flag | require_supplement",
  "confidence": 0.95,
  "effective_date": "YYYY-MM-DD",
  "expiry_date": null
}
```

### 规则类型说明

| 类型 | 含义 | 示例 |
|------|------|------|
| `threshold` | 数值阈值条件 | 资产负债率不超过70% |
| `veto` | 一票否决条件 | 借款人在黑名单中直接否决 |
| `exception` | 例外条款 | 符合XX政策的企业可豁免YY限制 |
| `condition` | 综合条件 | 满足A且B，或者C时通过 |

---

## 关系类型

```json
{
  "relation_types": [
    { "name": "APPLIES_TO", "desc": "规则适用于某类概念" },
    { "name": "REQUIRES", "desc": "A条款要求B条件成立" },
    { "name": "CONFLICTS_WITH", "desc": "两条规则存在矛盾" },
    { "name": "SUPERSEDES", "desc": "新条款替代旧条款" },
    { "name": "SUPPLEMENTS", "desc": "条款A是条款B的细化补充" },
    { "name": "EXCEPTION_OF", "desc": "例外条款对应的主规则" }
  ]
}
```

---

## JSON 存储格式示例

```json
{
  "version": "1.0",
  "updated_at": "2026-04-30T10:00:00+08:00",
  "source_docs": ["风险管理办法2024版.pdf", "信贷审批指引.docx"],
  "concepts": {
    "Borrower": { "instance_count": 0 },
    "Collateral": { "instance_count": 0 },
    "FinancialIndicator": { "instance_count": 0 },
    "LoanProduct": { "instance_count": 0 }
  },
  "rules": [
    {
      "rule_id": "R-001",
      "rule_type": "threshold",
      "source_doc": "风险管理办法2024版.pdf",
      "source_clause": "第三章第十二条",
      "description": "企业客户资产负债率不得超过70%",
      "applies_to": ["Borrower", "FinancialIndicator"],
      "condition": {
        "field": "asset_liability_ratio",
        "operator": "<=",
        "value": 70,
        "unit": "%"
      },
      "action": "flag",
      "confidence": 0.98,
      "effective_date": "2024-01-01",
      "expiry_date": null
    }
  ],
  "changelog": []
}
```
