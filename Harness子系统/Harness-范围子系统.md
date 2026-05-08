# Harness - 范围子系统

> 源码位置：`backend/app/harness/scope.py`

---

## 一、概述

范围子系统定义 Agent 的能力边界和权限范围，提供：

- **分层权限**：free / basic / pro / enterprise 四级会员体系
- **工具访问控制**：全局启用/禁用 + 最低等级要求
- **频率限制**：基于滑动窗口的每小时调用限额
- **功能门控**：按等级开放功能模块
- **数据访问控制**：读/写权限 + 最低等级 + 用户同意
- **审计日志**：每次权限决策记录 structlog

---

## 二、等级体系

```python
_TIER_RANK: Dict[str, int] = {
    "free": 0,
    "basic": 1,
    "pro": 2,
    "enterprise": 3,
}
```

判断逻辑：`user_tier >= required_tier`（按数值比较）。

---

## 三、内置权限表

### 3.1 工具权限

| 工具 | 是否启用 | 最低等级 | 频率限制（次/小时） |
|------|----------|----------|---------------------|
| `web_search` | true | free | 200 |
| `read_skill_reference` | true | free | 无限制 |
| `run_skill_script` | true | basic | 200 |
| `advanced_analysis` | true | pro | 100 |
| `api_access` | true | enterprise | 1000 |
| `delete_data` | **false** | enterprise | 无限制 |

### 3.2 功能权限

| 功能 | 最低等级 |
|------|----------|
| `basic_query` | free |
| `skill_execution` | basic |
| `advanced_analysis` | pro |
| `api_access` | enterprise |

### 3.3 数据访问权限

| 数据类型 | 读 | 写 | 最低等级 | 需用户同意 |
|----------|------|------|----------|-----------|
| `public_data` | true | false | free | 否 |
| `user_data` | true | true | free | 是 |
| `internal_reports` | false | false | enterprise | 否 |

---

## 四、ScopeManager 类

单例模式（`get_scope_manager()`）。

### 4.1 工具权限检查

#### check_tool(tool, user_tier) → (bool, str)

检查流程：
1. 未知工具 → 默认放行（记日志）
2. `allowed == false` → 拒绝（"工具已禁用"）
3. 等级不足 → 拒绝（"需要 X 或以上等级"）
4. 通过 → 返回 `(True, "")`

#### assert_tool(tool, user_tier) → None

同 `check_tool`，但失败时抛出 `ScopeException`。

### 4.2 频率限制

#### check_rate_limit(tool, user_id, user_tier) → (bool, str)

基于 1 小时滑动窗口的计数器：
- `rate_limit == 0` → 不限制
- 窗口过期（>1h）→ 重置计数器
- 计数未超限 → `count++`，放行
- 超限 → 拒绝（"调用超限 X 次/小时"）

内存结构：`Dict[(user_id, tool), _RateWindow]`

```python
@dataclass
class _RateWindow:
    count: int = 0
    window_start: float = time.time()
```

### 4.3 功能检查

#### check_feature(feature, user_tier) → (bool, str)

检查用户等级是否满足功能最低要求。未知功能默认放行。

### 4.4 数据访问检查

#### check_data_access(data_type, operation, user_tier) → (bool, str)

检查流程：
1. 未知数据类型 → 拒绝
2. 操作（read/write）未启用 → 拒绝
3. 等级不足 → 拒绝
4. 通过

### 4.5 批量计划过滤

#### filter_plan(plan, user_tier) → List[Dict]

对计划中的每个步骤进行工具权限检查，标记 `blocked=True` 和 `block_reason`。

### 4.6 查询可用工具

#### allowed_tools(user_tier) → List[str]

返回指定等级可访问的所有工具名列表。

---

## 五、ScopeException

```python
class ScopeException(Exception):
    def __init__(self, action: str, required: str, current: str, reason: str = ""):
        # 生成消息: "权限不足：{action} 需要 {required}，当前为 {current}（{reason}）"
```

属性：`action`, `required`, `current`

---

## 六、审计日志

每次权限决策通过 structlog 记录：

```python
logger.debug/info(
    "scope_check",
    category="tool"|"feature"|"data",
    name=<资源名>,
    tier=<用户等级>,
    allowed=True|False,
    reason=<拒绝原因或"ok">,
)
```

- 允许 → `logger.debug`
- 拒绝 → `logger.info`

---

## 七、在 Engine 中的集成

```python
from app.harness.scope import get_scope_manager

scope = get_scope_manager()

# 工具调用前检查
ok, reason = scope.check_tool(tool_name, user_tier)
if not ok:
    # 返回权限不足提示给用户
    ...

# 频率限制检查
ok, reason = scope.check_rate_limit(tool_name, user_id, user_tier)
if not ok:
    # 返回调用超限提示
    ...

# 计划步骤批量过滤
filtered_plan = scope.filter_plan(plan_steps, user_tier)
```

---

## 八、技术要点

| 要点 | 说明 |
|------|------|
| 存储方式 | 权限表硬编码在代码中（`_DEFAULT_PERMISSIONS`） |
| 频率限制 | 纯内存滑动窗口，进程重启后重置 |
| 默认策略 | 未知工具放行，未知数据类型拒绝 |
| 单例模式 | `get_scope_manager()` 返回模块级单例 |
| 可扩展 | 构造时可传入自定义 `permissions` 字典覆盖默认 |
| 线程安全 | 单进程内安全（GIL 保护字典操作） |
