# Harness - 指令子系统

**版本**：v1.0  
**日期**：2026-04-29  
**对应文件**：instructions.md, prompts.yaml

---

## 一、概述

指令子系统负责管理 Agent 的所有指令和提示词（Prompt），确保 Agent 能准确理解任务意图并执行。

> 对 Agent 来说，它在运行时无法在情境中访问的任何内容都是不存在的。

---

## 二、核心组件

### 2.1 指令分类

| 类型 | 说明 | 示例 |
|------|------|------|
| **系统指令** | Agent 角色定义、行为约束 | "你是一个专业助手..." |
| **任务指令** | 具体任务描述 | "分析股票行情..." |
| **工具指令** | 工具调用描述 | "使用 search_stock 工具..." |
| **上下文指令** | 动态上下文注入 | "用户偏好：风险偏好保守" |
| **安全指令** | 约束与边界 | "禁止提供投资建议" |

### 2.2 Prompt 模板管理

```yaml
# prompts.yaml
prompts:
  system:
    name: system_prompt
    template: |
      你是 {{role}}，专注于 {{domain}}。
      
      行为规则：
      {{#rules}}
      - {{.}}
      {{/rules}}
      
      当前时间：{{timestamp}}
      用户等级：{{user_tier}}
    variables:
      - role
      - domain
      - rules
      - timestamp
      - user_tier

  task:
    name: task_planning
    template: |
      任务：{{task}}
      上下文：{{context}}
      可用工具：{{tools}}
      
      请制定执行计划。
    variables:
      - task
      - context
      - tools

  safety:
    name: output_check
    template: |
      检查以下内容是否合规：
      {{content}}
      
      规则：{{safety_rules}}
```

---

## 三、LangGraph 集成

### 3.1 Prompt Builder 节点

```python
from langgraph.graph import StateGraph
from jinja2 import Template

class PromptBuilder:
    """指令构建器"""
    
    def __init__(self, prompts_config: str):
        self.prompts = self._load_prompts(prompts_config)
    
    def build_system_prompt(self, context: dict) -> str:
        """构建系统提示词"""
        template = self.prompts["system"]["template"]
        return Template(template).render(**context)
    
    def build_task_prompt(self, task: str, context: dict) -> str:
        """构建任务提示词"""
        template = self.prompts["task"]["template"]
        return Template(template).render(
            task=task,
            context=context,
            tools=self._list_tools()
        )


# LangGraph 节点
async def prompt_builder_node(state: AgentState) -> dict:
    """构建指令节点"""
    builder = PromptBuilder("config/prompts.yaml")
    
    system_prompt = builder.build_system_prompt({
        "role": "金融助手",
        "domain": "A股和基金",
        "rules": ["禁止投资建议", "必须风险提示"],
        "timestamp": datetime.now(),
        "user_tier": state["user_tier"]
    })
    
    return {
        "system_prompt": system_prompt,
        "messages": [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_input"])
        ]
    }
```

### 3.2 指令版本管理

```python
class PromptVersionManager:
    """指令版本管理"""
    
    def __init__(self):
        self.versions = {}
    
    def register(self, name: str, template: str, version: str):
        """注册新版本的指令"""
        self.versions[name] = {
            "template": template,
            "version": version,
            "created_at": datetime.now()
        }
    
    def get(self, name: str, version: str = None) -> str:
        """获取指定版本的指令"""
        if version:
            return self.versions[name][version]
        # 返回最新版本
        return self.versions[name]["latest"]
```

---

## 四、指令注入流程

```
用户输入
   │
   ▼
┌─────────────┐
│ 加载基础指令 │ ← prompts.yaml
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 注入用户上下文│ ← 会员等级、偏好、历史
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 注入安全约束 │ ← safety_rules.yaml
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 构建完整Prompt│
└──────┬──────┘
       │
       ▼
   LangGraph State
```

---

## 五、最佳实践

### 5.1 指令设计原则

| 原则 | 说明 |
|------|------|
| 明确角色 | 清楚定义 Agent 身份和能力边界 |
| 约束行为 | 明确什么能做、什么不能做 |
| 结构化输出 | 指定输出格式，便于解析 |
| 动态注入 | 根据上下文动态调整指令 |
| 版本控制 | 指令变更可追溯、可回滚 |

### 5.2 指令模板示例

```yaml
# instructions.md
## 角色定义
- 身份：金融信息助手
- 边界：信息展示工具，非投资顾问
- 语气：专业、客观、谨慎

## 行为规则
1. 禁止提供买入/卖出建议
2. 禁止预测股价走势
3. 涉及个股必须附加风险提示
4. 数据来源必须标注
5. 不确定时明确说明

## 输出格式
- 股票行情 → 卡片格式
- 财务数据 → 表格格式
- 新闻 → 列表格式
- 分析 → 分点论述 + 风险提示

## 安全约束
- 敏感词过滤：内幕消息、庄家、必涨
- 投资建议拦截：建议买入→改写为信息展示
```