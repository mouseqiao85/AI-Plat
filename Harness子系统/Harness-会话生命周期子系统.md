# Harness - 会话生命周期子系统

> 源码位置：`backend/app/harness/session.py`

---

## 一、概述

会话生命周期子系统管理 Agent 会话的完整生命周期，包括：

- **状态机**：initial → active → paused / waiting / error → ended
- **并发控制**：系统级 + 用户级会话数上限
- **超时管理**：空闲超时 / 最大时长 / 暂停超时
- **沙箱隔离**：每个会话独立的工作目录
- **僵尸清理**：自动回收泄漏的长时间不活跃会话

---

## 二、核心数据结构

### 2.1 SessionStatus 枚举

```python
class SessionStatus(str, Enum):
    INITIAL  = "initial"    # 刚创建，尚未开始处理
    ACTIVE   = "active"     # 正在处理用户请求
    PAUSED   = "paused"     # 用户主动暂停
    WAITING  = "waiting"    # 等待工具执行结果返回
    ERROR    = "error"      # 发生错误
    ENDED    = "ended"      # 已结束
```

### 2.2 Session 数据类

```python
@dataclass
class Session:
    session_id: str              # UUID 唯一标识
    user_id: int                 # 所属用户 ID
    status: SessionStatus        # 当前状态

    # 时间戳
    created_at: float            # 创建时间 (time.time())
    last_active: float           # 最近活跃时间
    paused_at: Optional[float]   # 暂停时间点

    # 执行位置
    current_node: str = "start"  # 当前执行节点标记
    current_step: int = 0        # 当前步骤序号

    # 运行时指标
    turn_count: int = 0          # 对话轮次
    tool_calls: int = 0          # 工具调用次数
    error_count: int = 0         # 累计错误次数

    # 元数据 & 沙箱
    metadata: Dict[str, Any]     # 附加信息（skill_name, conversation_id 等）
    sandbox_dir: Optional[str]   # 沙箱目录路径
```

---

## 三、配置常量

| 常量 | 值 | 说明 |
|------|------|------|
| `IDLE_TIMEOUT` | 60 min | 无用户活动则超时关闭 |
| `MAX_DURATION` | 120 min | 会话硬性最大时长 |
| `PAUSE_TIMEOUT` | 24 h | 暂停后必须在此时间内恢复 |
| `MAX_SESSIONS_TOTAL` | 100 | 系统同时活跃会话上限 |
| `MAX_SESSIONS_PER_USER` | 20 | 单用户并发会话上限 |

---

## 四、SessionManager 类

单例模式（通过 `get_session_manager()` 获取），内存存储，适用于单进程 uvicorn 部署。

### 4.1 核心方法

#### create_session(user_id, metadata=None) → Session

创建新会话，流程：
1. 调用 `_evict_expired()` 清理过期会话
2. 检查系统总并发 ≤ `MAX_SESSIONS_TOTAL`
3. 检查用户并发 ≤ `MAX_SESSIONS_PER_USER`
4. 生成 UUID 作为 session_id
5. 创建 Session 实例
6. 调用 `_create_sandbox()` 创建沙箱目录
7. 注册到 `_sessions` 和 `_user_sessions` 索引

超限时抛出 `RuntimeError`。

#### get(session_id) → Optional[Session]

按 session_id 查找会话。

#### get_user_sessions(user_id) → List[Session]

获取指定用户的所有活跃会话列表。

#### close_session(session_id) → None

关闭并清理会话：
1. 从 `_sessions` 字典移除
2. 调用 `session.end()` 标记 ENDED 状态
3. 调用 `_cleanup_sandbox()` 删除沙箱目录
4. 从 `_user_sessions` 索引移除
5. 记录结构化日志（turns, duration）

#### force_cleanup_zombies() → int

清理"僵尸会话"——状态为 ACTIVE/WAITING 但 `last_active` 超过 `IDLE_TIMEOUT` 的会话。返回清理数量。适合在定时任务中调用。

#### metrics() → Dict

返回运行时统计信息：
```python
{
    "active_sessions": int,     # 非 ENDED 状态的会话数
    "total_sessions": int,      # 所有跟踪中的会话数
    "error_sessions": int,      # ERROR 状态会话数
    "avg_duration_s": float,    # 平均会话时长（秒）
}
```

---

## 五、Session 状态转换

### 5.1 状态方法

| 方法 | 效果 |
|------|------|
| `activate()` | → ACTIVE，更新 last_active |
| `mark_waiting()` | → WAITING（等待工具返回） |
| `resume_from_waiting()` | WAITING → ACTIVE，更新 last_active |
| `pause()` | → PAUSED，记录 paused_at |
| `resume()` | → ACTIVE，清除 paused_at |
| `end()` | → ENDED |
| `mark_error()` | → ERROR，error_count++ |

### 5.2 状态机示意

```
initial ──activate()──→ active ──pause()──→ paused
                          │                    │
                          ├──mark_waiting()──→ waiting
                          │                    │
                          ├──mark_error()───→ error
                          │
                          └──end()─────────→ ended

（所有超时/异常状态最终通过 close_session() → ended）
```

### 5.3 超时检测方法

| 方法 | 触发条件 |
|------|----------|
| `is_idle_expired()` | ACTIVE 且 last_active 距今 > 60 min |
| `is_max_duration_exceeded()` | created_at 距今 > 120 min |
| `is_pause_expired()` | PAUSED 且 paused_at 距今 > 24 h |

---

## 六、沙箱机制

每个会话创建独立的工作目录，用于隔离技能脚本的文件 IO。

- **路径规则**：`{SANDBOX_BASE_DIR}/{session_id[:8]}`
- **默认基目录**：`~/.joeyagent`（可通过 `settings.SANDBOX_BASE_DIR` 覆盖）
- **创建时机**：`create_session()` 时自动创建
- **清理时机**：`close_session()` 时调用 `shutil.rmtree` 删除

```python
# 创建沙箱
base = settings.SANDBOX_BASE_DIR or os.path.join(os.path.expanduser("~"), ".joeyagent")
sandbox = os.path.join(base, session_id[:8])
os.makedirs(sandbox, exist_ok=True)
```

---

## 七、在 Engine 中的集成

`AgentEngine.run()` 主循环中的会话管理流程：

```python
session = session_mgr.create_session(user_id, metadata={...})
try:
    session.activate()
    # ... agent 主循环 ...
    # 工具调用前: session.mark_waiting()
    # 工具完成后: session.resume_from_waiting()
    # 异常时: session.mark_error()
finally:
    session_mgr.close_session(session.session_id)  # 保证资源释放
```

---

## 八、技术要点

| 要点 | 说明 |
|------|------|
| 存储方式 | 纯内存 Dict，无持久化 |
| 并发安全 | 适用于单进程；多 worker 需扩展 Redis 存储 |
| 自动清理 | 每次 `create_session()` 前触发 `_evict_expired()` |
| 日志记录 | 使用 structlog 记录所有生命周期事件 |
| 单例模式 | `get_session_manager()` 返回模块级单例 |
