# Harness - 会话生命周期子系统

**版本**：v1.0
**日期**：2026-04-29
**对应文件**：session.ts, lifecycle.py

---

## 一、概述

会话生命周期子系统管理 Agent 会话的完整生命周期，包括创建、运行、暂停、恢复和销毁，确保会话状态可控、资源可管理。

> 会话是 Agent 与用户的交互单元，生命周期管理确保每个会话都能被正确追踪和管理。

---

## 二、核心组件

### 2.1 会话状态机

```
┌─────────┐     创建      ┌─────────┐
│  初始   │──────────────▶│  活跃   │
└─────────┘               └────┬────┘
                               │
                    ┌─────────┼─────────┐
                    │         │         │
                    ▼         ▼         ▼
               ┌────────┐ ┌────────┐ ┌────────┐
               │ 暂停   │ │ 等待   │ │ 错误   │
               │(中断)  │ │(人工)  │ │(异常)  │
               └───┬────┘ └───┬────┘ └───┬────┘
                   │         │         │
                   └─────────┼─────────┘
                             │
                             ▼
                        ┌─────────┐
                        │  结束   │
                        └─────────┘
```

### 2.2 会话状态定义

```python
from enum import Enum
from datetime import datetime
from typing import Optional, List

class SessionStatus(Enum):
    """会话状态"""
    CREATED = "created"        # 已创建
    ACTIVE = "active"          # 活跃中
    PAUSED = "paused"          # 已暂停（中断）
    WAITING = "waiting"        # 等待人工
    ERROR = "error"            # 错误状态
    COMPLETED = "completed"    # 已完成
    EXPIRED = "expired"        # 已过期

class Session:
    """会话对象"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.status = SessionStatus.CREATED
        
        # 时间戳
        self.created_at = datetime.now()
        self.last_active_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        
        # 运行时信息
        self.current_node: Optional[str] = None
        self.current_step: int = 0
        self.checkpoint_id: Optional[str] = None
        
        # 元数据
        self.metadata = {
            "turn_count": 0,
            "tool_calls": 0,
            "errors": []
        }
```

---

## 三、LangGraph 集成

### 3.1 会话管理器

```python
from langgraph.checkpoint.base import BaseCheckpointSaver

class SessionManager:
    """会话管理器"""
    
    def __init__(self, checkpointer: BaseCheckpointSaver):
        self.checkpointer = checkpointer
        self.sessions: dict[str, Session] = {}
    
    async def create_session(self, user_id: str) -> Session:
        """创建新会话"""
        session_id = f"sess_{uuid4().hex[:12]}"
        session = Session(session_id, user_id)
        
        # 初始化检查点
        await self.checkpointer.put(
            {
                "configurable": {
                    "thread_id": session_id
                }
            },
            {
                "v": 1,
                "ts": datetime.now().isoformat(),
                "channel_values": {}
            }
        )
        
        self.sessions[session_id] = session
        return session
    
    async def resume_session(self, session_id: str) -> Optional[Session]:
        """恢复会话"""
        session = self.sessions.get(session_id)
        
        if not session:
            # 从数据库恢复
            session = await self._load_from_db(session_id)
        
        if session and session.status in [SessionStatus.PAUSED, SessionStatus.WAITING]:
            session.status = SessionStatus.ACTIVE
            session.last_active_at = datetime.now()
        
        return session
    
    async def pause_session(self, session_id: str, reason: str = ""):
        """暂停会话"""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.PAUSED
            await self._save_checkpoint(session_id)
    
    async def close_session(self, session_id: str):
        """关闭会话"""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.now()
            
            # 保存最终状态
            await self._save_final_state(session)
            
            # 清理内存
            del self.sessions[session_id]
    
    async def get_session_state(self, session_id: str) -> dict:
        """获取会话状态"""
        config = {"configurable": {"thread_id": session_id}}
        
        # 从检查点读取
        checkpoint = await self.checkpointer.aget(config)
        
        if checkpoint:
            return {
                "session_id": session_id,
                "checkpoint": checkpoint,
                "status": self.sessions.get(session_id, Session(session_id, "")).status.value
            }
        
        return {}
```

### 3.2 生命周期钩子

```python
class LifecycleHooks:
    """生命周期钩子"""
    
    async def on_session_start(self, session: Session):
        """会话开始"""
        logger.info(f"Session {session.session_id} started")
        
        # 初始化上下文
        await context_manager.initialize(session)
    
    async def on_node_enter(self, session: Session, node_name: str):
        """进入节点"""
        session.current_node = node_name
        session.last_active_at = datetime.now()
        
        logger.debug(f"Session {session.session_id} entering node {node_name}")
    
    async def on_node_exit(self, session: Session, node_name: str, result: dict):
        """退出节点"""
        session.metadata["turn_count"] += 1
        
        # 记录工具调用
        if "tool_calls" in result:
            session.metadata["tool_calls"] += len(result["tool_calls"])
        
        logger.debug(f"Session {session.session_id} exited node {node_name}")
    
    async def on_session_pause(self, session: Session, reason: str):
        """会话暂停"""
        session.status = SessionStatus.PAUSED
        
        # 发送通知
        await notification_manager.notify(
            user_id=session.user_id,
            message=f"会话已暂停：{reason}"
        )
    
    async def on_session_resume(self, session: Session):
        """会话恢复"""
        session.status = SessionStatus.ACTIVE
        session.last_active_at = datetime.now()
        
        logger.info(f"Session {session.session_id} resumed")
    
    async def on_session_end(self, session: Session, reason: str):
        """会话结束"""
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now()
        
        # 生成会话摘要
        summary = await self._generate_summary(session)
        
        # 保存到历史
        await history_manager.save(session, summary)
        
        logger.info(f"Session {session.session_id} ended: {reason}")
    
    async def on_error(self, session: Session, error: Exception):
        """错误处理"""
        session.status = SessionStatus.ERROR
        session.metadata["errors"].append({
            "time": datetime.now().isoformat(),
            "error": str(error),
            "node": session.current_node
        })
        
        logger.error(f"Session {session.session_id} error: {error}")
```

---

## 四、会话超时管理

```python
class SessionTimeoutManager:
    """会话超时管理器"""
    
    TIMEOUTS = {
        "idle": 1800,      # 30分钟空闲超时
        "max_duration": 3600,  # 1小时最大时长
        "pause": 86400     # 24小时暂停保留
    }
    
    async def check_timeouts(self):
        """检查超时会话"""
        now = datetime.now()
        
        for session_id, session in session_manager.sessions.items():
            # 检查空闲超时
            idle_time = (now - session.last_active_at).total_seconds()
            if idle_time > self.TIMEOUTS["idle"]:
                await self._handle_idle_timeout(session)
                continue
            
            # 检查总时长超时
            total_time = (now - session.created_at).total_seconds()
            if total_time > self.TIMEOUTS["max_duration"]:
                await self._handle_max_duration_timeout(session)
                continue
            
            # 检查暂停超时
            if session.status == SessionStatus.PAUSED:
                pause_time = (now - session.last_active_at).total_seconds()
                if pause_time > self.TIMEOUTS["pause"]:
                    await self._handle_pause_timeout(session)
    
    async def _handle_idle_timeout(self, session: Session):
        """处理空闲超时"""
        await session_manager.pause_session(
            session.session_id,
            reason="空闲超时"
        )
    
    async def _handle_max_duration_timeout(self, session: Session):
        """处理最大时长超时"""
        await session_manager.close_session(session.session_id)
    
    async def _handle_pause_timeout(self, session: Session):
        """处理暂停超时"""
        session.status = SessionStatus.EXPIRED
        await session_manager.close_session(session.session_id)
```

---

## 五、会话监控

```python
class SessionMonitor:
    """会话监控器"""
    
    def __init__(self):
        self.metrics = {
            "active_sessions": 0,
            "total_sessions": 0,
            "avg_duration": 0,
            "error_rate": 0
        }
    
    async def record_session_start(self, session: Session):
        """记录会话开始"""
        self.metrics["active_sessions"] += 1
        self.metrics["total_sessions"] += 1
    
    async def record_session_end(self, session: Session):
        """记录会话结束"""
        self.metrics["active_sessions"] -= 1
        
        # 计算时长
        duration = (session.completed_at - session.created_at).total_seconds()
        
        # 更新平均时长
        total = self.metrics["total_sessions"]
        current_avg = self.metrics["avg_duration"]
        self.metrics["avg_duration"] = (current_avg * (total - 1) + duration) / total
    
    async def record_error(self, session: Session):
        """记录错误"""
        errors = sum(1 for s in session_manager.sessions.values() if s.status == SessionStatus.ERROR)
        total = len(session_manager.sessions)
        self.metrics["error_rate"] = errors / total if total > 0 else 0
    
    def get_metrics(self) -> dict:
        """获取指标"""
        return self.metrics.copy()
```

---

## 六、最佳实践

### 6.1 会话管理原则

| 原则 | 说明 |
|------|------|
| 资源限制 | 限制最大并发会话数 |
| 及时清理 | 过期会话自动清理 |
| 状态追踪 | 所有状态变更记录日志 |
| 优雅降级 | 超负载时优先保证核心功能 |
| 用户通知 | 关键状态变更通知用户 |

### 6.2 配置示例

```yaml
# session_config.yaml
session:
  # 超时配置
  timeouts:
    idle: 1800          # 30分钟空闲
    max_duration: 3600  # 1小时最大时长
    pause: 86400        # 24小时暂停保留
  
  # 资源限制
  limits:
    max_concurrent: 100     # 最大并发
    max_per_user: 5         # 每用户最大会话
    max_history: 50         # 最大历史消息
  
  # 检查点配置
  checkpoint:
    enabled: true
    interval: 10            # 每10步检查点
    retention: 7            # 保留7天
  
  # 清理配置
  cleanup:
    enabled: true
    interval: 3600          # 每小时清理
    expired_only: true      # 只清理过期
```