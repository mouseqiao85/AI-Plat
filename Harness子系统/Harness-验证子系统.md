# Harness - 验证子系统

> 源码位置：`backend/app/harness/validator.py`

---

## 一、概述

验证子系统提供多层验证管道，确保 Agent 输入输出的安全性和合规性：

- **InputGuard**：用户输入长度、Prompt 注入、敏感词检测
- **ToolValidator**：工具参数格式 + 权限检查
- **OutputGuard**：Agent 输出有害内容检测 + 自动改写
- **ResultValidator**：工具执行结果格式校验
- **Validator**：统一 Facade，整合所有验证器

---

## 二、共享类型

### 2.1 ValidationLevel 枚举

```python
class ValidationLevel(str, Enum):
    STRICT  = "strict"   # 任何问题 → 拒绝
    NORMAL  = "normal"   # 严重问题 → 拒绝（默认）
    LENIENT = "lenient"  # 仅最严重问题 → 拒绝
```

### 2.2 ValidationResult 数据类

```python
@dataclass
class ValidationResult:
    passed: bool                      # 是否通过
    issues: List[str]                 # 问题列表
    level: ValidationLevel            # 验证级别
    rewritten: Optional[str] = None   # 自动改写后的文本（如有）

    def __bool__(self) -> bool:       # 支持 `if result:` 语法
        return self.passed
```

---

## 三、InputGuard — 输入验证

### 3.1 检测项

| 检测 | 级别影响 | 说明 |
|------|----------|------|
| 长度超限 | STRICT/NORMAL → fatal | `MAX_CHARS=0` 时禁用 |
| Prompt 注入 | 所有级别 → fatal | 匹配 7 个正则模式 |
| 敏感词 | STRICT → fatal, NORMAL → warning | 当前列表为空 |

### 3.2 注入检测模式

```python
_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions?",
    r"you\s+are\s+now",
    r"system\s+prompt",
    r"disregard\s+all",
    r"forget\s+your\s+instructions?",
    r"新的?指令",
    r"忽略(之前|前面|上面)的?指令",
]
```

### 3.3 级别判定逻辑

| 级别 | 通过条件 |
|------|----------|
| STRICT | 无任何 issue |
| NORMAL | 无"注入"或"长度"类 issue |
| LENIENT | 无"注入"类 issue |

---

## 四、ToolValidator — 工具参数验证

### 4.1 检测项

1. **必要参数缺失**：按工具名查表检查
2. **权限不足**：调用 `ScopeManager.check_tool()` 检查等级

### 4.2 已注册工具参数

```python
_REQUIRED_PARAMS = {
    "web_search": ["query"],
}
```

未注册的工具跳过参数检查，仅做权限验证。

---

## 五、OutputGuard — 输出验证

### 5.1 功能

- 检测 Agent 输出中的有害短语
- 支持自动改写（`auto_rewrite=True`）
- 当前 `_HARMFUL_PHRASES` 列表为空（通用场景无金融合规需求）

### 5.2 级别判定

| 级别 | 通过条件 |
|------|----------|
| STRICT | 无任何 issue |
| NORMAL/LENIENT | 始终通过（issue 仅作警告） |

### 5.3 自动改写

匹配有害模式时，如模式定义了 `replacement_hint`，自动执行 `re.sub` 替换。改写后的文本存入 `result.rewritten`。

---

## 六、ResultValidator — 工具结果验证

检测工具返回值的基本有效性：

| 条件 | 结果 |
|------|------|
| `result is None` | 失败：工具返回值为 None |
| `isinstance(result, dict) and "error" in result` | 失败：工具执行错误 |
| `isinstance(result, str) and result.strip() == ""` | 失败：工具返回空字符串 |
| 其他 | 通过 |

---

## 七、Validator Facade

统一入口，整合所有验证器：

```python
class Validator:
    def __init__(self, level: ValidationLevel = NORMAL):
        self.input_guard = InputGuard()
        self.tool_validator = ToolValidator()
        self.output_guard = OutputGuard()
        self.result_validator = ResultValidator()

    def validate_input(text, level=None) → ValidationResult
    def validate_tool(tool_name, params, user_tier) → ValidationResult
    def validate_output(text, level=None, auto_rewrite=True) → ValidationResult
    def validate_tool_result(result) → ValidationResult
```

单例模式：`get_validator(level=NORMAL)`

---

## 八、在 Engine 中的集成

```python
from app.harness.validator import get_validator

validator = get_validator()

# 1. 输入验证（用户消息进入时）
input_result = validator.validate_input(user_message)
if not input_result:
    # 返回拒绝消息给用户
    yield error_event(input_result.issues)
    return

# 2. 工具调用前验证
tool_result = validator.validate_tool(tool_name, params, user_tier)
if not tool_result:
    # 跳过该工具调用，记录原因
    ...

# 3. 工具结果验证
exec_result = validator.validate_tool_result(tool_output)
if not exec_result:
    # 工具执行异常处理
    ...

# 4. 输出验证（Agent 回复前）
output_result = validator.validate_output(assistant_response)
if output_result.rewritten:
    assistant_response = output_result.rewritten
```

---

## 九、验证流程示意

```
用户输入
    │
    ▼
InputGuard.validate()
    │
    ├── 失败 → 拒绝，返回错误信息
    │
    └── 通过 → Agent 处理
                    │
                    ▼
           ToolValidator.validate()  ← 工具调用前
                    │
                    ├── 失败 → 跳过工具，报权限/参数问题
                    │
                    └── 通过 → 执行工具
                                    │
                                    ▼
                           ResultValidator.validate()
                                    │
                                    ├── 失败 → 错误处理/重试
                                    │
                                    └── 通过 → 继续
                                                │
                                                ▼
                                    OutputGuard.validate()  ← 输出前
                                                │
                                                ├── 有问题 → 自动改写
                                                │
                                                └── 通过 → 返回给用户
```

---

## 十、技术要点

| 要点 | 说明 |
|------|------|
| 正则引擎 | 标准库 `re`，忽略大小写匹配 |
| 默认级别 | NORMAL（平衡安全性与用户体验） |
| 可扩展 | 通过添加 `_INJECTION_PATTERNS` / `_HARMFUL_PHRASES` 扩展规则 |
| 权限联动 | ToolValidator 内部调用 ScopeManager（懒加载避免循环导入） |
| 单例模式 | `get_validator()` 返回模块级单例 |
| 无外部依赖 | 纯 Python 标准库 + structlog |
