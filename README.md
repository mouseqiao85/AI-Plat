# Agent Platform

**基于 Golang + LangGraph 的通用 AI Agent 框架**

## 架构

```
Client → Go Gateway (:8080) → HTTP → Python Agent (:8001) → LLM
              │                              │
        SQLite (local)              LangGraph StateGraph
        Redis (optional,                Checkpointer (SQLite)
          not implemented in Go gateway)
```

- **Go Gateway**: HTTP/SSE, auth (JWT), sessions, tool registry & execution
- **Python Agent**: FastAPI, LangGraph StateGraph, LLM calls, RAG, Harness subsystems

## 快速开始

### 环境要求

- Go >= 1.23
- Python >= 3.11
- SQLite >= 3.40

### 启动服务

```bash
# 启动 Python Agent (port 8001)
cd agent
pip install -r requirements.txt
python main.py

# 启动 Go Gateway (port 8080)
cd cmd/gateway
go run main.go
```

### 开发登录

```bash
curl -X POST http://localhost:8080/api/v1/auth/dev-login
# 返回 token: dev-token-agent
# 注意：当 ENVIRONMENT=production 时此端点已禁用
```

### 发送消息

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Authorization: Bearer dev-token-agent" \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/health | 健康检查 |
| POST | /api/v1/auth/register | 用户注册 |
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/dev-login | 开发登录（生产环境禁用） |
| GET | /api/v1/auth/me | 当前用户 |
| POST | /api/v1/chat | SSE 流式对话 |
| GET | /api/v1/conversations | 会话列表 |
| GET | /api/v1/conversations/messages | 会话消息 |
| POST | /api/v1/tools/execute | 工具执行 |
| GET | /api/v1/tools | 工具列表 |

## 项目结构

```
agent-platform/
├── cmd/gateway/          # Go 入口
├── internal/             # Go 内部包
│   ├── api/              # HTTP 接口
│   ├── service/          # 业务逻辑
│   └── store/            # 数据访问
├── pkg/                  # Go 公共库
├── agent/                # Python Agent
│   ├── app/
│   │   ├── graph/        # LangGraph 状态图
│   │   ├── harness/      # Harness 子系统
│   │   ├── memory/       # 记忆管理
│   │   ├── rag/          # RAG 系统
│   │   └── tools/        # 工具回调
│   └── tests/            # Python 测试
├── configs/              # 配置文件
├── deployments/          # Docker, k8s
├── proto/                # gRPC 定义（设计稿，未实现）
└── scripts/              # 脚本
```

## 测试

```bash
# Go 测试
GOPROXY=https://goproxy.cn,direct go test ./...

# Python 测试
cd agent && python -m pytest tests/ -v
```

## 技术栈

| 层级 | 技术 |
|------|------|
| API 网关 | Golang + Gin |
| Agent 执行 | Python + LangGraph |
| 通信 | HTTP REST (gRPC 仅设计稿 proto/agent.proto，未实现) |
| 本地存储 | SQLite |
| 生产存储 | ⚠️ PostgreSQL + pgvector（规划中 / not yet implemented） |
| 缓存 | ⚠️ Redis（规划中 / not yet implemented） |
| 部署 | Docker + Kubernetes |

> 本地开发使用 Go 1.25.8，CI 与 Dockerfile 锁定 1.23。

## 已知限制 / Known Limitations

1. **存储后端仅 SQLite**：Redis 与 Postgres+pgvector 虽在文档与规划中出现，Go 网关层当前仅依赖 SQLite（`go-sqlite3`）；`go.mod` 中不包含 `redis/go-redis`、`pgx`、`pgvector` 等依赖。
2. **gRPC 未落地**：`proto/agent.proto` 仅保留作为设计参考，未生成 `*.pb.go`，`go.mod` 中也无 `google.golang.org/grpc`。Gateway ↔ Agent 间通信目前完全走 HTTP REST。
3. **session 目录为空**：`internal/service/session/` 目录当前为空，session 相关能力由 `internal/service/` 下的其他模块（如 conversation、chat）承担。
4. **开发后门有环境门禁**：默认开发登录 `POST /api/v1/auth/dev-login` 在 `ENVIRONMENT=production` 下已被禁用，仅限本地 / 开发环境使用。
5. **main.go 历史整合**：`cmd/gateway/` 历史上曾存在 `main_secure.go` 作为安全加固实验版本，现已删除；环境变量端口绑定等能力已吸收进当前 `main.go`。
