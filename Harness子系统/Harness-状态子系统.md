# Harness - 状态子系统

**版本**：v1.0  
**日期**：2026-04-29  
**对应文件**：state.json, memory.db

---

## 一、概述

状态子系统负责管理 Agent 的运行状态，包括会话状态、任务状态、用户偏好等，支持断点续跑和状态恢复。

> 状态是 Agent 的"记忆"，让 Agent 能在多轮交互中保持上下文连贯。

---

## 二、核心组件

### 2.1 状态类型

| 类型 | 存储 | 生命周期 | 说明 |
|------|------|---------|------|
| **会话状态** | Redis | 30分钟 | 当前对话上下文 |
| **任务状态** | PostgreSQL | 7天 | 执行计划、进度、结果 |
| **用户状态** | PostgreSQL | 永久 | 用户偏好、历史摘要 |
| **系统状态** | 文件 | 持久 | 配置、规则、版本 |

### 2.2 状态结构

```json
// state.json 示例
{
  "session_id": "sess_abc123",
  "user_id": "user_001",
  "status": "running",
  
  "conversation": {
    "messages": [
      {"role": "user", "content": "茅台现在多少钱"},
      {"role": "assistant", "content": "贵州茅台(600519)..."}
    ],
    "turn_count": 5
  },
  
  "task": {
    "current_task": "查询股票行情",
    "plan": [
      {"step": 1, "action": "search_stock", "status": "completed"},
      {"step": 2, "action": "get_quote", "status": "running"}
    ],
    "current_step": 2,
    "results": {
      "stock_info": {"code": "600519", "name": "贵州茅台"},
      "quote": null
    }
  },
  
  "context": {
    "user_tier": "pro",
    "risk_preference": "moderate",
    "watchlist": ["600519", "000858"],
    "retrieved_docs": []
  },
  
  "metadata": {
    "created_at": "2026-04-29T10:00:00Z",
    "last_active": "2026-04-29T10:05:00Z",
    "checkpoints": ["cp_001", "cp_002"]
  }
}
```

---

## 三、LangGraph Checkpointer 集成

### 3.1 Checkpointer 配置

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# 开发环境：内存检查点
memory_checkpointer = MemorySaver()

# 生产环境：PostgreSQL 检查点
pool = ConnectionPool(
    conninfo="postgresql://user:pass@localhost/agent_db",
    min_size=5,
    max_size=20,
    kwargs={"autocommit": True}
)
postgres_checkpointer = PostgresSaver(sync_connection=pool)

# 编译图时注入
def build_agent_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    # ... 添加节点和边
    return graph.compile(checkpointer=checkpointer)
```

### 3.2 状态持久化节点

```python
async def state_persister_node(state: AgentState) -> dict:
    """状态持久化节点"""
    
    # 保存到数据库
    await db.save_state(
        session_id=state["session_id"],
        state={
            "conversation": state["messages"],
            "task": {
                "plan": state["plan"],
                "current_step": state["current_step"],
                "results": state["tool_results"]
            },
            "context": state["context"]
        }
    )
    
    return {"state_saved": True}
```

### 3.3 断点续跑

```python
# 保存检查点
config = {"configurable": {"thread_id": "session_123"}}
result = await agent.ainvoke(input_state, config)

# 从断点恢复
# LangGraph 自动从 Checkpointer 恢复状态
result = await agent.ainvoke(None, config)  # 传入 None 继续

# 获取历史状态
history = list(agent.get_state_history(config))
for state in history:
    print(f"Step {state.metadata['step']}: {state.values}")
```

---

## 四、状态管理流程

```
会话开始
   │
   ▼
┌─────────────────┐
│ 加载历史状态    │ ← Checkpointer / Database
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ 初始化 State    │ ← LangGraph State
└───────┬─────────┘
        │
        ▼
   Agent 执行
        │
        ▼
┌─────────────────┐
│ 每步自动保存    │ ← Checkpointer checkpoint
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ 会话结束保存    │ ← Database 持久化
└─────────────────┘
```

---

## 五、最佳实践

### 5.1 状态设计原则

| 原则 | 说明 |
|------|------|
| 最小状态 | 只保存必要信息，避免冗余 |
| 可序列化 | 所有状态必须能 JSON 序列化 |
| 版本兼容 | 状态结构变更需兼容旧版本 |
| 敏感隔离 | 敏感信息单独加密存储 |
| 定期清理 | 过期状态自动归档或删除 |

### 5.2 状态监控

```python
class StateMonitor:
    """状态监控器"""
    
    def __init__(self):
        self.metrics = {
            "active_sessions": 0,
            "total_checkpoints": 0,
            "recovery_count": 0
        }
    
    def on_checkpoint(self, session_id: str, step: int):
        """检查点事件"""
        self.metrics["total_checkpoints"] += 1
        
    def on_recovery(self, session_id: str):
        """恢复事件"""
        self.metrics["recovery_count"] += 1
        
    def get_stats(self) -> dict:
        """获取统计"""
        return self.metrics
```