# 智能体低代码平台 - 主从协作模式实施方案（Part 1）

**版本**: v2.0 Implementation  
**日期**: 2026-05-25  
**优先级**: P0 - 核心功能  
**实施周期**: 4周

---

## 📋 执行摘要

**核心目标**：优先实现主从协作模式，支持多Agent协作解决复杂业务问题

**技术选型**：
- ✅ **协作模式**：主从协作（Hierarchical）
- ✅ **前端画布**：React Flow
- ✅ **消息路由**：Redis Streams

**实施周期**：4周完成MVP

**预期成果**：
- 可视化编排主从协作工作流
- 支持主控Agent + 多个子Agent协作
- 实时消息路由和执行监控
- 一键测试和发布

---

## 一、架构设计

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    前端层 (React)                        │
│                                                           │
│  CreateAgentPage                                         │
│  ├─ CollaborationTab (协作配置)                          │
│  │  ├─ MasterAgentSelector (主控Agent选择)              │
│  │  ├─ SubAgentList (子Agent列表)                       │
│  │  └─ CollaborationPreview (流程预览)                  │
│  │                                                       │
│  └─ WorkflowTab (工作流编排)                             │
│     ├─ NodeLibrary (节点库)                              │
│     ├─ ReactFlowCanvas (画布)                            │
│     └─ ConfigPanel (配置面板)                            │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API + SSE
┌───────────────────────▼─────────────────────────────────┐
│                  后端层 (Python + FastAPI)               │
│                                                           │
│  CollaborationOrchestrator (协作编排器)                  │
│  ├─ HierarchicalMode (主从模式)                          │
│  │  ├─ TaskDispatcher (任务分配器)                      │
│  │  ├─ ResultAggregator (结果汇总器)                    │
│  │  └─ ConflictResolver (冲突解决器)                    │
│  │                                                       │
│  └─ AgentMessenger (消息路由器)                          │
│     ├─ RedisStreamClient (Redis客户端)                  │
│     ├─ MessageQueue (消息队列)                           │
│     └─ MessageRouter (路由器)                            │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 基础设施层                               │
│                                                           │
│  Redis Streams (消息中间件)                              │
│  ├─ collaboration:messages (协作消息流)                 │
│  ├─ collaboration:events (事件流)                        │
│  └─ collaboration:results (结果流)                       │
│                                                           │
│  SQLite/PostgreSQL (持久化)                              │
│  ├─ collaboration_workflows                              │
│  ├─ collaboration_messages                               │
│  └─ workflow_executions                                  │
└─────────────────────────────────────────────────────────┘
```

### 1.2 主从协作流程

```
用户输入
   ↓
主控Agent分析任务
   ↓
任务分解（规划）
   ├─ 子任务1 → Agent A
   ├─ 子任务2 → Agent B
   └─ 子任务3 → Agent C
   ↓
并行/顺序执行
   ├─ Agent A 执行 → 返回结果1
   ├─ Agent B 执行 → 返回结果2
   └─ Agent C 执行 → 返回结果3
   ↓
主控Agent汇总结果
   ↓
冲突解决（如有）
   ↓
最终输出
```

---

## 二、实施计划（4周）

### Week 1：基础架构搭建

**目标**：建立项目框架和数据库

**后端任务**：
- [x] 创建`agent/app/collaboration/`目录结构
- [x] 数据库迁移脚本（5张表）
- [x] Redis Streams客户端
- [x] 基础数据模型

**前端任务**：
- [x] 安装React Flow依赖
- [x] 创建`CreateAgentPage`页面框架
- [x] 实现`CollaborationTab`基础组件

**交付物**：
- 完整的项目结构
- 可运行的数据库
- 基础UI框架

---

### Week 2：核心协作逻辑

**目标**：实现主从协作编排器

**后端任务**：
- [ ] `CollaborationOrchestrator`编排器
- [ ] `HierarchicalMode`主从模式
- [ ] Agent注册表和管理
- [ ] 协作执行API

**前端任务**：
- [ ] 主控Agent选择器
- [ ] 子Agent列表管理
- [ ] 协作流程预览
- [ ] 配置面板

**交付物**：
- 完整的主从协作逻辑
- 可配置的协作流程

---

### Week 3：可视化编排

**目标**：React Flow画布实现

**前端任务**：
- [ ] React Flow画布集成
- [ ] Agent节点组件
- [ ] 连接线组件
- [ ] 拖拽功能
- [ ] 节点配置面板

**后端任务**：
- [ ] 工作流保存/加载API
- [ ] 工作流验证

**交付物**：
- 可视化工作流编排
- 拖拽式节点编辑

---

### Week 4：测试与优化

**目标**：完整测试和性能优化

**测试任务**：
- [ ] 单元测试（覆盖率>80%）
- [ ] 集成测试
- [ ] 端到端测试
- [ ] 性能测试

**优化任务**：
- [ ] 性能优化
- [ ] 错误处理
- [ ] 日志完善
- [ ] 文档编写

**交付物**：
- 完整测试覆盖
- 性能报告
- 用户文档

---

## 三、快速启动指南

### 3.1 环境准备

```bash
# 1. 后端环境
cd agent
pip install redis aioredis

# 2. 启动Redis（如果没有）
# Windows: 下载Redis并启动
# Linux: sudo systemctl start redis

# 3. 前端环境
cd web
npm install reactflow @reactflow/core @reactflow/controls
```

### 3.2 数据库迁移

```bash
# 执行SQL脚本
sqlite3 data/agent.db < scripts/collaboration_tables.sql
```

### 3.3 启动服务

```bash
# 1. 启动Redis
redis-server

# 2. 启动后端
cd agent
python main.py

# 3. 启动前端
cd web
npm run dev
```

---

## 四、核心API设计

### 4.1 协作工作流API

```yaml
# 创建协作工作流
POST /api/v1/collaboration/workflows
Request:
  {
    "agent_id": 123,
    "name": "银行贷款审批协作",
    "master_agent_id": "bank_manager",
    "sub_agents": ["credit_analyst", "risk_officer"],
    "execution_mode": "parallel",
    "conflict_resolution": "master",
    "workflow_json": {...}
  }
Response:
  {
    "id": 1,
    "created_at": "2026-05-25T12:00:00Z"
  }

# 执行协作工作流
POST /api/v1/collaboration/workflows/{id}/execute
Request:
  {
    "message": "帮我审核张三的贷款申请",
    "session_id": "session_123"
  }
Response (SSE):
  data: {"event": "master_start", "agent": "bank_manager"}
  data: {"event": "sub_agent_start", "agent": "credit_analyst"}
  data: {"event": "sub_agent_complete", "result": {...}}
  data: {"event": "workflow_complete", "output": "..."}

# 获取工作流详情
GET /api/v1/collaboration/workflows/{id}
```

### 4.2 Agent注册API

```yaml
# 注册Agent
POST /api/v1/agents
Request:
  {
    "agent_id": "bank_manager",
    "agent_name": "银行行长助手",
    "agent_type": "master",
    "capabilities": ["任务分配", "结果汇总"],
    "system_prompt": "...",
    "model_config": {
      "provider": "deepseek",
      "model": "deepseek-v4-pro"
    }
  }

# 获取Agent列表
GET /api/v1/agents?type=master
```

---

## 五、数据库表设计

### 5.1 核心表

```sql
-- 1. 协作工作流表
CREATE TABLE collaboration_workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  master_agent_id TEXT NOT NULL,
  sub_agents TEXT DEFAULT '[]',
  execution_mode TEXT DEFAULT 'parallel',
  workflow_json TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Agent注册表
CREATE TABLE agent_registry (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT NOT NULL UNIQUE,
  agent_name TEXT NOT NULL,
  agent_type TEXT NOT NULL,
  capabilities TEXT DEFAULT '[]',
  system_prompt TEXT,
  model_config TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. 执行记录表
CREATE TABLE workflow_executions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id INTEGER NOT NULL,
  execution_id TEXT NOT NULL UNIQUE,
  input_message TEXT,
  output_message TEXT,
  agent_results TEXT,
  execution_time_ms INTEGER,
  status TEXT DEFAULT 'running',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、下一步行动

需要我创建：

1. ✅ **Part 2: 后端完整代码实现**
   - CollaborationOrchestrator
   - HierarchicalMode
   - RedisStreamClient

2. ✅ **Part 3: 前端完整代码实现**
   - CollaborationTab组件
   - React Flow画布
   - 配置面板

3. ✅ **Part 4: 测试与部署**
   - 单元测试
   - 集成测试
   - 部署脚本

告诉我你想先看哪一部分的详细代码！
