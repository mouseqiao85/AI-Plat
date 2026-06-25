# Harness - 状态子系统

> 源码位置：`backend/app/harness/state.py`

---

## 一、概述

状态子系统管理 Agent 的运行时状态，支持：

- **AgentState 数据类**：存储会话消息、任务计划、执行进度、用户上下文
- **StateManager**：创建 / 获取 / 更新 / 检查点 / 恢复
- **双层检查点**：内存快照 + 可选 Redis 持久化（TTL 30 min）
- **StateMonitor**：轻量运行时指标收集

---

## 二、核心数据结构

### 2.1 Message 数据类

```python
@dataclass
class Message:
    role: str              # "user" | "assistant" | "tool"
    content: str
    timestamp: float       # time.time()
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
```

### 2.2 PlanStep 数据类

```python
@dataclass
class PlanStep:
    step: int              # 步骤序号
    action: str            # 工具名或子任务标签
    description: str       # 人可读的步骤描述
    status: str            # pending | running | completed | failed
    result: Any = None     # 执行结果
    error: Optional[str] = None
```

### 2.3 AgentState 数据类

```python
@dataclass
class AgentState:
    session_id: str
    user_id: int

    # 对话历史
    messages: List[Message]
    turn_count: int = 0

    # 任务执行
    current_task: str = ""
    plan: List[PlanStep]           # 执行计划
    plan_id: Optional[str] = None  # 计划唯一 ID
    current_step: int = 0
    tool_results: Dict[str, Any]   # 工具执行结果缓存
    child_workers: Dict[str, Dict] # Worker 子进程追踪

    # 用户上下文
    user_tier: str = "free"
    skill_name: Optional[str] = None
    system_prompt: str = ""

    # 验证 / 安全
    input_valid: bool = True
    safety_passed: bool = True
    retry_count: int = 0

    # 元数据
    created_at: float
    last_active: float
    checkpoints: List[str]         # 已创建的检查点 ID 列表
```

### 2.4 AgentState 便捷方法

| 方法 | 说明 |
|------|------|
| `add_message(role, content, **kwargs)` | 添加消息，自动更新 `last_active`，user 消息 `turn_count++` |
| `add_plan_step(action, description)` | 追加计划步骤 |
| `mark_step_done(action, result)` | 标记步骤完成 |
| `mark_step_failed(action, error)` | 标记步骤失败 |
| `active_steps()` | 返回 pending/running 状态的步骤 |
| `to_dict()` | 序列化为 JSON 兼容字典 |

---

## 三、Checkpoint 机制

### 3.1 Checkpoint 数据类

```python
@dataclass
class Checkpoint:
    checkpoint_id: str           # 8 位 UUID 前缀
    session_id: str
    step: int                    # 创建时的 current_step
    state_snapshot: Dict         # AgentState 的深拷贝快照
    created_at: float
```

### 3.2 双层存储

| 层级 | 存储位置 | TTL | 用途 |
|------|----------|-----|------|
| L1 | 进程内存 | 随进程生命周期 | 快速恢复 |
| L2 | Redis | 30 min | 跨进程恢复（uvicorn worker 重启后） |

- 每个 session 最多保留 20 个检查点（`_CHECKPOINT_LIMIT`）
- Redis key 格式：`session_checkpoint:{session_id}`

---

## 四、StateManager 类

单例模式（`get_state_manager()`）。

### 4.1 生命周期方法

#### create(session_id, user_id, user_tier, skill_name) → AgentState

创建并注册新状态，触发 `monitor.on_session_created()`。

#### get(session_id) → Optional[AgentState]

获取指定 session 的当前状态。

#### update(session_id, **fields) → bool

批量更新状态字段，自动刷新 `last_active`，触发 `monitor.on_update()`。

#### end(session_id) → None / end_async(session_id) → None

移除状态和检查点，清理 Redis（async 版本），触发 `monitor.on_session_ended()`。

### 4.2 检查点方法

#### checkpoint(session_id) → Optional[str]

创建内存快照：
1. 深拷贝当前 AgentState
2. 生成 8 位 checkpoint_id
3. 存入 `_checkpoints[session_id]` 列表
4. 超过 20 条时淘汰最早的

#### checkpoint_async(session_id) → Optional[str]

在内存快照基础上，额外将快照 JSON 写入 Redis（TTL 30 min）。

#### restore(session_id, checkpoint_id=None) → Optional[AgentState]

从内存检查点恢复（无 checkpoint_id 时取最新）。

#### restore_from_redis(session_id) → Optional[AgentState]

从 Redis 恢复（跨进程恢复场景）。

### 4.3 导出 / 查询

```python
export_state(session_id) → Optional[str]       # JSON 字符串
list_checkpoints(session_id) → List[Dict]      # [{checkpoint_id, step, created_at}]
metrics() → Dict                               # 统计信息
```

---

## 五、StateMonitor

轻量指标收集器，追踪：

```python
{
    "active_sessions": int,        # 活跃会话数
    "total_checkpoints": int,      # 累计检查点数
    "recovery_count": int,         # 累计恢复次数
    "state_updates": int,          # 累计状态更新次数
}
```

事件回调：`on_session_created()`, `on_session_ended()`, `on_checkpoint()`, `on_recovery()`, `on_update()`

---

## 六、在 Engine 中的集成

```python
from app.harness.state import get_state_manager

state_mgr = get_state_manager()

# 创建状态
agent_state = state_mgr.create(session_id, user_id, user_tier=tier, skill_name=skill)

# 更新任务
state_mgr.update(session_id, current_task="搜索股票信息")

# 创建检查点（带 Redis 持久化）
cp_id = await state_mgr.checkpoint_async(session_id)

# 异常后恢复
restored = state_mgr.restore(session_id)
# 或从 Redis 跨进程恢复
restored = await state_mgr.restore_from_redis(session_id)

# 结束清理
await state_mgr.end_async(session_id)
```

---

## 七、状态恢复流程

```
异常/中断发生
    │
    ▼
尝试内存恢复（restore）
    │
    ├── 成功 → 继续执行
    │
    └── 失败 → 尝试 Redis 恢复（restore_from_redis）
                │
                ├── 成功 → 继续执行
                │
                └── 失败 → 重新初始化状态
```

---

## 八、技术要点

| 要点 | 说明 |
|------|------|
| 存储方式 | 内存为主 + Redis 可选持久化 |
| 序列化 | `dataclasses.asdict()` + `json.dumps(default=str)` |
| 深拷贝 | 检查点使用 `copy.deepcopy` 避免引用问题 |
| Redis 可选 | 通过 `attach_redis(client)` 注入，未注入时纯内存工作 |
| 上限保护 | 每 session 最多 20 个检查点，FIFO 淘汰 |
| 单例模式 | `get_state_manager()` 返回模块级单例 |
