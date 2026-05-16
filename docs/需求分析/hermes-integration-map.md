# Hermes 集成面与缺口（截至 2026-05-13）

## 1. Gateway 侧路由表

全部注册在 `internal/api/router.go:186-202`（`setupHermesRoutes`），挂在 `/api/v1/hermes` 下，鉴权中间件 `middleware.AuthMiddleware`。
Handler 统一在 `internal/api/handler/hermes.go`，全部是**透明代理**，无本地业务逻辑。

| Method | Gateway Path                       | Handler                     | 代理到 Bridge 路径（`hermes.go`）              | 出入参                                             |
| ------ | ---------------------------------- | --------------------------- | --------------------------------------------- | -------------------------------------------------- |
| GET    | /api/v1/hermes/health              | `Health` (hermes.go:35)     | GET  `/api/v2/health`                          | 无入参；出参透传 JSON                              |
| POST   | /api/v1/hermes/chat                | `Chat` (hermes.go:49)       | POST `/api/v2/chat`                            | 入参透传 `c.Request.Body`；出参 JSON               |
| POST   | /api/v1/hermes/chat/stream         | `ChatStream` (hermes.go:64) | POST `/api/v2/chat/stream` (SSE)               | 入参透传；出参 `text/event-stream`                 |
| GET    | /api/v1/hermes/skills              | `ListSkills` (hermes.go:126)| GET  `/api/v2/skills`                          | 无入参；出参透传                                   |
| GET    | /api/v1/hermes/skills/:name        | `GetSkill` (hermes.go:131)  | GET  `/api/v2/skills/{name}`                   | path param                                         |
| POST   | /api/v1/hermes/skills/:name/execute| `ExecuteSkill` (hermes.go:136)| POST `/api/v2/skills/{name}/execute`         | 入参透传                                           |
| GET    | /api/v1/hermes/agents              | `ListAgents` (hermes.go:141)| GET  `/api/v2/agents`                          | 无入参                                             |
| POST   | /api/v1/hermes/agents/:name/run    | `RunAgent` (hermes.go:146)  | POST `/api/v2/agents/{name}/run`               | 入参透传                                           |
| GET    | /api/v1/hermes/workspace           | `Workspace` (hermes.go:151) | GET  `/api/v2/workspace`                       | 无入参                                             |
| GET    | /api/v1/hermes/skills/hub          | `SearchHub` (hermes.go:156) | GET  `/api/v2/skills/hub?q=`                   | query `q`                                          |
| POST   | /api/v1/hermes/skills/hub/install  | `InstallHub` (hermes.go:166)| POST `/api/v2/skills/hub/install`              | 入参透传                                           |

**关键点**：
- Gateway 无 `c.ShouldBindJSON` —— 入参 struct **没有在 gateway 侧定义**，完全透传。
- HTTP 客户端配置：`IdleConnTimeout 90s`、`ResponseHeaderTimeout 30s`（`hermes.go:27-28`）；`Content-Type: application/json`，SSE 返回设置 `X-Accel-Buffering: no`（`hermes.go:78`）。
- 配置注入：`handler.NewHermesHandler(cfg.Hermes.ServiceURL, cfg.Hermes.Timeout)`（`router.go:60`），通过 env `HERMES_SERVICE_URL` 覆盖（本次部署已启用）。

## 2. Bridge API 契约（本地有代码）

repo 里**有** `hermes-bridge/` 本地代码，不是独立仓库。

- 入口：`hermes-bridge/main.py:19` `app.include_router(bridge_router, prefix="/api/v2")`，默认 `0.0.0.0:8002`。
- Router：`hermes-bridge/bridge/chat_handler.py`，所有路由对应到 `hermes_cli.py` 的 `subprocess.run(["hermes", ...])` 调用。
- 请求模型：`hermes-bridge/bridge/types.py:4` `ChatRequest`
  ```
  message: str, session_id: str, user_id: int, conversation_id: int,
  skill_name: str, model: str, provider: str
  ```
  但 bridge 当前**只用 `message`**，其他字段未传到 CLI。
- **SSE 不是真流**：`chat/stream` (`chat_handler.py:33-57`) 是 run_in_executor 跑完整 hermes CLI → 再把结果切 50 字符 chunk 重播，间隔 10ms。事件格式：`{"type":"text","content":chunk,"done":false}`，收尾 `{"type":"done","done":true}`。
- Skill 执行：`hermes_cli.py:64` `hermes -s <skill> chat -q <task> --quiet --yolo`，timeout 300。
- Agent workflows：`hermes_cli.py:157` 读 `/root/agent-workflows/*.yaml`，字段 `description / stages / estimated_duration` —— **这是目前唯一近似"多 agent 编排"的契约**。
- Hub 安装后 `shutil.copytree` 到 `/home/admin/agent-platform/agent/skills/<name>` 并 POST `agent/api/v1/skills/admin/reload`（`hermes_cli.py:134-147`）。
- Skill 列表解析：`hermes_cli.py:36-47` 用正则+ `│` 解析 hermes CLI 表格输出 —— **脆弱，角色列表如果只靠 `list_skills` 不稳定**。

## 3. 前端现状

- **前端无 hermes API 客户端**：`web/src/services/api.ts` 只有 `skillApi`（走本地 `/api/v1/skills/`，agent 服务的技能注册表，非 hermes）、`marketplaceApi`、`adminApi`、`conversationApi`、`chatApi`、`streamChat`（`api.ts:146` 打 `/api/v1/chat/`，非 hermes）。grep `hermes` 在 `web/src/` 下仅命中 `package-lock.json` 的无关字串。
- **技能选择是单选**：`web/src/stores/appStore.ts:31` `selectedSkill: string | null`；`App.tsx:315-320` 侧栏点 skill 即 toggle `selectedSkill`，传入 `streamChat(msg, convId, selectedSkill)`（`ChatPanel.tsx:116`）。**无多选、无角色 group、无 scenario**。
- SkillsCenterPage（`web/src/components/SkillsCenterPage.tsx:66-142`）有 `activeCategory / activeFilter / sortBy`，分类来自 `skill.tags` 字符串筛选，**也是展示本地 agent skills，不是 hermes 23 角色**。
- AgentMarketPage = 纯 marketplace CRUD，跟 gstack/hermes agent 无关。
- InputArea（`web/src/components/InputArea.tsx:67-75`）只展示单条 `selectedSkill` 徽章 + provider/model 切换。
- 类型：`web/src/types/index.ts:36-55` `Skill` 有 `tools/keywords/enabled` 等字段，**没有 role/scenario/workspace/tool_group** 概念。

## 4. 多智能体 / 工具分组基础设施

### 4.1 Agent 服务 LangGraph 编排
- `agent/app/graph/graph.py:1-91` 编译一张静态 StateGraph：
  `input_validator → router → (rag_retrieval → planner →) (worker_orchestrator | scope_check → executor) → responder → output_validator`
- **已有的"多 agent"机制**：`agent/app/graph/nodes/worker_orchestrator.py:11` `MAX_CONCURRENT_WORKERS=5`，把 planner 产出的 steps 包成 `WorkerConfig` 并发跑。
- 每个 Worker：`agent/app/workers/worker.py:16-129`，独立 LLM session，max_iterations=3，可直接调 tool 或 LLM 自决策。
- **无 supervisor / team / role 概念**，无 langgraph-supervisor 包引用（grep 结果里零命中）。Worker 之间无 handoff、无共享 scratchpad。
- Planner 产出的 `steps` 每项是 `{tool, args, description}`（`plan_tool.py:27-37`），**不是"把任务交给某角色"，而是"调某个 tool"**。

### 4.2 工具注册表
- `agent/app/tools/registry.py:10-66` 全局单例，平铺 dict，`register / get / list_tools / get_openai_tools`，**没有 group / scenario / tag / category 字段**。
- 现有 Python 侧 tool：`brave_search.py`（BraveSearchTool，`name="brave_search"`，schema 含 query/count/country/safesearch）、`plan_tool.py`（CreatePlanTool）、`file_gen.py`、`skill_tools.py`（`RunSkillScriptTool` name=`skill_<name>_run`，`ReadSkillReferenceTool` name=`skill_<name>_ref` —— 每个 hermes skill 动态注册 2 个 tool）。
- Go 侧 tool：`internal/service/tool/builtin/*` 里 `NewWebSearchTool / NewCalculatorTool`（`router.go:48-49`）。
- **Tool "scenario/preset/group" 概念在全代码库找不到任何对应物**。grep `scenario|preset|tool_group|toolset` 零命中。

## 5. 缺口（对照新需求）

| 新需求 | 现状 | 缺什么 |
|---|---|---|
| **勾选 23 角色** | (1) Hermes 23 角色当前只能通过 `GET /api/v1/hermes/skills` 拉（且靠脆弱的 CLI 表格解析）。(2) 前端 `selectedSkill` 是单选 `string \| null`，UI 是侧栏单击切换。(3) bridge `ChatRequest.skill_name` 是单值，hermes CLI 也只支持 `-s <skill>`。 | • Bridge 契约改造：支持多 skill 并行/串行（新 endpoint e.g. `/api/v2/chat/team`，参数 `roles: [...]`）或在 gateway 层 fan-out。<br>• Gateway 新 route + DTO。<br>• 前端 store 改 `selectedRoles: string[]`、侧栏/弹窗加多选 UI、`streamChat` 签名加 `roles` 数组。<br>• 23 角色元数据（头像/领域/推荐场景）在 hermes skills 输出里不全，需要补来源（yaml 或后端静态表）。 |
| **选工具场景** | 代码库内**零对应物**。工具注册是平铺 dict；前端无场景选择 UI；bridge 也没有概念。 | • 新建"场景→工具集合"元数据（建议 YAML：`configs/tool_scenarios.yaml`）。<br>• Registry 增加 `list_by_scenario(name)` / `get_openai_tools(scenario)` 方法。<br>• Gateway 新接口 `GET /api/v1/tool-scenarios`、`POST /api/v1/chat/` 加 `scenario` 字段。<br>• 前端加场景选择器组件与 store 字段。 |
| **对话流程编排** | worker_orchestrator 支持并发 step，但 DAG 是硬编码在 `graph.py`，前端**完全不可见**，用户不能编辑流程。workflow yaml（`/root/agent-workflows/*.yaml`）只在 bridge 侧列出，无前端渲染、无 run 参数可编辑。 | • 定义"用户级流程"模型（serializable：nodes = roles，edges = handoff/并行/串行）。<br>• 后端：新 workflow CRUD endpoint + 执行器（可基于 langgraph Supervisor 或自定义 orchestrator）。<br>• 前端：流程画布组件（React Flow 之类）+ 流程模板 store。<br>• SSE 事件增加 `role_started / role_output / handoff` 等类型（当前只有 `worker_started/progress/done`）。 |
| **结果输出** | 后端：responder 节点产出最终 text + cards/files/plan/workers（`state.py` AgentState）；SSE event types 散落（ping/text/card/file_download/plan/worker_*）。前端 ChatMessage 支持 `cards/fileDownloads/plan/workers/toolCalls`（`types/index.ts:11-21`）。 | • 需要"按角色分栏"或"按流程阶段分段"的结果聚合结构（当前所有 worker 结果被拍扁）。<br>• 新消息类型：RoleReport（role_name + markdown + citations + artifacts）。<br>• 前端新组件：多角色结果卡片组/时间线/tab 聚合视图。<br>• 导出（PDF/Markdown）当前只有 file_gen tool，需针对"整次流程结果"封装。 |

### 其他风险点

- **Bridge 伪 SSE**：`chat/stream` 先跑完再切片，不是真流。多角色协作时用户等待感会放大。建议改为 `hermes` CLI 加 `--stream` / pipe stdout，或直接走 hermes SDK 而非 subprocess。
- **Skill 列表解析脆弱**：`hermes_cli.py:36-47` 靠 `│` 字符，hermes CLI 输出格式一变就炸。建议 hermes 暴露 JSON 输出（`hermes skills list --json`）。
- **Bridge `ChatRequest` 大量字段未使用**（`session_id/user_id/conversation_id/model/provider` 全丢弃，见 `chat_handler.py:23-28` 只传 `req.message`），新功能要重新走通这些字段，否则会话记忆、provider 选择都无法传递。
- **Worker 与 Role 概念错配**：现有 Worker 以 "tool/step" 为维度，新需求是以 "role/expert" 为维度。要么扩展 Worker 接受 `role_skill` 参数（调 `hermes -s <role>`），要么新增 RoleWorker 类。
