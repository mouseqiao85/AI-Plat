# Harness - 指令子系统

> 源码位置：`backend/app/harness/instructions.py`

---

## 一、概述

指令子系统管理 Agent 的所有提示词（Prompt）模板，负责：

- **五种指令类型**：System / Task / Tool / Context / Safety
- **模板渲染**：使用 Python `string.Template`（`$variable` 语法）进行变量注入
- **版本管理**：支持多版本注册和回滚
- **组合构建**：`build_full_system()` 将多类型指令拼装为完整系统提示词

---

## 二、指令类型定义

```python
class InstructionType(str, Enum):
    SYSTEM  = "system"    # Agent 角色定义 & 行为约束
    TASK    = "task"      # 具体任务描述
    TOOL    = "tool"      # 工具调用指引
    CONTEXT = "context"   # 动态上下文注入
    SAFETY  = "safety"    # 安全约束 & 边界规则
```

| 类型 | 用途 | 模板变量示例 |
|------|------|-------------|
| SYSTEM | 定义 Agent 身份、规则、用户等级 | `${role}`, `${rules}`, `${user_tier}`, `${timestamp}` |
| TASK | 描述当前任务和可用工具 | `${task}`, `${context}`, `${tools}` |
| TOOL | 工具调用参数格式说明 | `${tool_name}`, `${tool_description}`, `${tool_params}` |
| CONTEXT | 注入历史摘要等上下文 | `${history_summary}` |
| SAFETY | 安全红线和违规处理 | `${safety_rules}`, `${violation_action}` |

---

## 三、内置默认模板

### 3.1 系统指令（SYSTEM）

```
你是${role}。

行为规则：
${rules}

当前时间：${timestamp}
用户等级：${user_tier}
```

默认值：
- `role` = "通用智能助手"
- `rules` = "- 回答准确简洁\n- 不确定时明确说明\n- 需要实时信息时调用工具"
- `timestamp` = 自动填充当前时间
- `user_tier` = "free"

### 3.2 安全指令（SAFETY）

```
安全约束（必须遵守）：
${safety_rules}

违规处理：${violation_action}
```

默认值：
- 不得协助违法活动
- 不得生成有害、歧视性内容
- 数据引用必须注明来源
- 不确定时明确说明
- 违规处理：礼貌拒绝并说明原因

---

## 四、InstructionBuilder 类

单例模式（`get_instruction_builder()`），负责模板注册、渲染、版本管理。

### 4.1 核心方法

#### build(instruction_type, version=None, **variables) → str

渲染指定类型的模板：
1. 从注册表获取模板（无 version 参数时取最新版本）
2. 用 defaults 填充基础值
3. 如模板含 `timestamp`，自动注入当前时间
4. 用传入的 `**variables` 覆盖对应字段
5. 调用 `string.Template.safe_substitute()` 渲染

#### build_full_system(user_tier, skill_description, user_profile_str, **extras) → str

组装完整系统提示词，按以下顺序拼接：

```
1. SYSTEM 模板（角色 + 规则 + 时间 + 等级）
2. 当前技能描述（如有）
3. 用户画像摘要（如有，来自长期记忆）
4. CONTEXT 模板（历史摘要）
5. SAFETY 模板（安全约束）
6. 工具调用优先级 & 执行策略指令（硬编码）
```

工具调用优先级部分的关键规则：
- 优先使用已有技能工具（`read_skill_reference` / `run_skill_script`）
- 技能无法满足时才使用 `web_search`，且最多 2 次
- 复杂任务先调用 `create_plan` 创建执行计划
- 简单问题直接回答，无需创建计划

#### register(name, template, version, defaults=None, description="") → None

注册新模板版本，追加到版本列表末尾。

#### rollback(name) → bool

移除最新版本，回退到上一版本。至少保留一个版本时才允许回滚。

#### list_versions(name) → List[Dict]

返回指定指令的所有版本元数据（version, description, created_at）。

### 4.2 便捷方法

```python
build_system_prompt(**variables)   # 快捷调用 build(SYSTEM, ...)
build_task_prompt(task, **vars)    # 快捷调用 build(TASK, task=task, ...)
build_safety_prompt(**variables)   # 快捷调用 build(SAFETY, ...)
build_context_prompt(**variables)  # 快捷调用 build(CONTEXT, ...)
```

---

## 五、版本管理机制

### 5.1 PromptVersion 数据类

```python
@dataclass
class PromptVersion:
    template: str                 # 模板文本
    version: str                  # 版本号（如 "1.0.0"）
    defaults: Dict[str, Any]      # 默认变量值
    created_at: float             # 创建时间戳
    description: str              # 版本说明
```

### 5.2 版本存储

内部注册表 `_registry: Dict[str, List[PromptVersion]]`：

- Key = 指令类型名（"system", "task" 等）
- Value = 版本列表，最新版本在末尾
- `build()` 无 version 参数时自动取 `[-1]`（最新）

---

## 六、在 Engine 中的集成

`AgentEngine` 启动时调用 `InstructionBuilder.build_full_system()` 生成完整系统提示词：

```python
from app.harness.instructions import get_instruction_builder

builder = get_instruction_builder()
system_prompt = builder.build_full_system(
    user_tier=user_tier,
    skill_description=skill_desc,
    user_profile_str=profile_str,
)
```

该 system_prompt 作为 OpenAI API 调用的第一条 system message。

---

## 七、模板语法说明

使用 Python 标准库 `string.Template`：

- 变量引用：`${variable}` 或 `$variable`
- 未提供的变量保留原样（`safe_substitute`）
- 不支持条件/循环逻辑（保持简单）

---

## 八、技术要点

| 要点 | 说明 |
|------|------|
| 模板引擎 | `string.Template.safe_substitute()`，安全且不会抛异常 |
| 单例模式 | `get_instruction_builder()` 返回模块级单例 |
| 默认值填充 | 每个模板自带 defaults，调用时可选覆盖 |
| 时间自动注入 | 含 `timestamp` 字段的模板自动填充 `datetime.now()` |
| 日志记录 | structlog 记录每次构建和注册事件 |
