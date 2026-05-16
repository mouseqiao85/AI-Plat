# Agent Platform

**多智能体编排平台 — Golang Gateway + Python LangGraph + 远端 Hermes Bridge**

[![CI](https://github.com/mouseqiao85/AI-Plat/actions/workflows/ci.yml/badge.svg)](https://github.com/mouseqiao85/AI-Plat/actions/workflows/ci.yml)

## 架构

```
Web (React/Vite) ──► Go Gateway (:8080) ──► Python Agent (:8001) ──► LLM (DeepSeek / OpenAI)
                          │                       │                       
                     SQLite (本地)           LangGraph StateGraph
                     JWT Auth                Harness 子系统
                     工具注册表 / Tool 执行    Skills / RAG / Memory
                          │
                          └──► Hermes Bridge (远端 :8002) ──► hermes CLI / 多角色 Flow
```

- **Web (`web/`)**: Vite + React 前端，已编译产物可由 Gateway 直接静态托管
- **Go Gateway (`cmd/gateway/`)**: 入口、认证、SSE 流式中转、工具与会话管理
- **Python Agent (`agent/`)**: FastAPI + LangGraph，节点化对话流程、Provider 适配（含 DeepSeek thinking 模式）、Skills/RAG/Memory
- **Hermes Bridge (`hermes-bridge/`)**: 远端 Python 服务，桥接 hermes CLI / 多 Agent 流（FlowsPage）

## 快速开始

### 环境要求

- Go ≥ 1.23
- Python ≥ 3.11
- Node ≥ 18（仅前端开发）
- SQLite ≥ 3.40

### 启动核心服务

```bash
# 1. Python Agent (port 8001)
cd agent
pip install -e ".[dev]"
python main.py

# 2. Go Gateway (port 8080)
go run ./cmd/gateway

# 3. 前端开发模式（可选，默认由 Gateway 托管 web/dist）
cd web && npm install && npm run dev
```

Windows 一键启动：`./start.ps1`

### 配置

复制 `.env.example` 并填入凭证：

```bash
cp agent/.env.example agent/.env
# 必填：LLM_API_KEY 或 LLM_DEEPSEEK_API_KEY
# Provider 也可在 UI 的「Provider 管理」中动态配置，存储于 llm_providers.json
```

> ⚠️ **不要把 `.env` 或任何包含密钥的文件提交到 git**，仓库已通过 `.gitignore` 排除。

### 开发登录

```bash
curl -X POST http://localhost:8080/api/v1/auth/dev-login
# 返回 dev-token-agent；ENVIRONMENT=production 时此端点禁用
```

### 发送消息（SSE）

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Authorization: Bearer dev-token-agent" \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

## 主要 API

| 模块 | 路径 | 说明 |
|------|------|------|
| 健康 | `GET /api/v1/health` | 健康检查 |
| 认证 | `POST /api/v1/auth/{register,login,dev-login}` | 用户认证 |
| 会话 | `POST /api/v1/chat` · `GET /api/v1/conversations` | 对话与历史 |
| 工具 | `GET /api/v1/tools` · `POST /api/v1/tools/execute` | 工具列表与调用 |
| 技能 | `GET/POST/PUT/DELETE /api/v1/skills/...` | Skills 管理与启停 |
| Provider | `GET/POST /api/v1/admin/providers` | 动态 LLM Provider |
| Agent 市场 | `GET/POST /api/v1/market/agents` | Agent / Flow 元数据 |
| Hermes Bridge | `POST /api/v1/hermes/chat/stream` 等 | 远端多 Agent 流 |

## 项目结构

```
agent-platform/
├── cmd/gateway/          # Go 入口
├── internal/             # Go 内部包（api / service / store / middleware）
├── pkg/                  # Go 公共库
├── agent/                # Python Agent
│   ├── app/
│   │   ├── api/          # FastAPI 路由
│   │   ├── core/         # 配置、Provider、安全
│   │   ├── graph/        # LangGraph 节点 / 边
│   │   ├── harness/      # Harness 子系统
│   │   ├── llm/          # 多 Provider 客户端
│   │   ├── memory/       # 会话/用户记忆
│   │   ├── rag/          # 检索增强
│   │   ├── skill/        # Skills 注册
│   │   └── tools/        # Tool 回调
│   ├── data/             # SQLite / 上传文件 / 默认 skills 数据（git 忽略）
│   ├── skills/           # 内置 Skills
│   └── tests/            # pytest
├── hermes-bridge/        # 远端 hermes 桥接服务
├── web/                  # React 前端
├── configs/              # 配置文件
├── deployments/          # Docker / k8s
└── proto/                # gRPC 定义（设计稿，未实现）
```

## 测试

```bash
# Go
go test -race ./...

# Python
cd agent && python -m pytest tests/ -v
```

CI 已配置 GitHub Actions（`.github/workflows/ci.yml`），覆盖 Go vet/build/test、Python pytest、密钥泄露扫描。

## LLM Provider

支持 OpenAI 兼容协议；DeepSeek（含 thinking 模式）已内置识别与适配：

```python
# 自动通过 provider_id 或 model 名识别 deepseek，并启用 reasoning_content 流
from app.llm.client import build_llm_client
client = build_llm_client(provider_id="deepseek", model="deepseek-v4-pro")
```

DeepSeek 不支持 tools + thinking 同时启用；当请求带 tools 时自动关闭 thinking。

## 技术栈

| 层级 | 技术 |
|------|------|
| API 网关 | Golang + Gin |
| Agent 执行 | Python + LangGraph + FastAPI |
| 前端 | React 18 + Vite + TypeScript |
| 通信 | HTTP REST + SSE（gRPC 仅设计稿） |
| 本地存储 | SQLite |
| 生产存储 | ⚠️ PostgreSQL + pgvector（规划中） |
| 缓存 | ⚠️ Redis（规划中） |
| 部署 | Docker + Kubernetes |

> 本地开发使用 Go 1.25.x；CI 与 Dockerfile 锁定 1.23。

## 已知限制 / Known Limitations

1. **存储后端仅 SQLite**：Redis 与 Postgres+pgvector 仍在规划，Go 网关层只依赖 SQLite。
2. **gRPC 未落地**：`proto/agent.proto` 仅作为设计参考，Gateway ↔ Agent 通信完全走 HTTP REST。
3. **开发后门有环境门禁**：`POST /api/v1/auth/dev-login` 在 `ENVIRONMENT=production` 下禁用。
4. **Hermes Bridge 部署独立**：需要在远端服务器单独运行（参见 `server_deployment/`，注意脚本中不要写入真实凭证）。
5. **多 Agent 流转**：`FlowsPage` 已支持 sequential 流；单角色失败不中断整链（P0 修复完成）。

## 贡献

提交前请确保：

- 不提交 `.env` / 密钥 / 服务器 IP
- 通过 `go vet ./...` 与 `pytest tests/`
- 跨平台路径与脚本兼容 Windows / Linux
