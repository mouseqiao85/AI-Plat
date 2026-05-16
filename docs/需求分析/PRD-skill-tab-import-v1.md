# PRD：多智能体流程页 - Skill Tab 扩展与 GitHub 仓库一键导入

> 版本：v1.0 | 日期：2026-05-15 | 状态：Draft

---

## 1. 背景与目标

当前多智能体流程创建页（FlowsPage）中，角色来源为本地 gstack 仓库，分类维度为功能类型（规划/实现/发布/运维/浏览器/安全）。所有角色属于**软件工程**领域。

随着平台向金融、运维等垂直领域扩展，需要：
1. 支持按**行业 Tab** 组织 skill 集合（当前 = 软件工程，新增 = 金融等）
2. 支持从 GitHub 仓库一键导入新的 skill 包
3. 由 LLM 自动分析 skill 元数据，完成分类与角色规划

---

## 2. 术语定义

| 术语 | 定义 |
|------|------|
| Skill Tab | 流程创建页中按行业/领域分组的标签页 |
| Skill Pack | 一个 GitHub 仓库，包含若干 SKILL.md 定义的专家角色 |
| Expert Role | 一个 SKILL.md 对应的专家身份（含 system prompt、triggers、tools） |
| Tool Scenario | 工具场景，描述一组推荐的角色+工具组合 |

---

## 3. 功能需求

### 3.1 新增行业 Tab 系统

#### 3.1.1 Tab 结构

在 FlowsPage 的角色选择区域，顶部新增 Tab 栏：

```
┌──────────────┬──────────┬──────────┬─────────┐
│ 软件工程 (默认) │  金融    │  [+ 新增]  │         │
└──────────────┴──────────┴──────────┴─────────┘
```

- 默认 Tab "软件工程"：对应当前全部 gstack 角色（规划/实现/发布/运维/浏览器/安全）
- 新增 Tab "金融"：展示从 `financial-services` 仓库导入的角色
- `[+ 新增]` 按钮：允许用户创建自定义 Tab 并关联 GitHub 仓库

#### 3.1.2 Tab 数据模型

```typescript
interface SkillTab {
  id: string;             // 唯一标识，如 "software-engineering", "finance"
  name: string;           // 显示名称，如 "软件工程", "金融"
  description?: string;   // Tab 描述
  source_type: "builtin" | "github";  // 来源类型
  source_url?: string;    // GitHub 仓库 URL（source_type=github 时必填）
  imported_at?: string;   // 导入时间
  role_count: number;     // 该 Tab 下角色数量
  icon?: string;          // Tab 图标
  order: number;          // 排列顺序
}
```

#### 3.1.3 Tab 管理操作

- 新增 Tab：填写名称 + GitHub 仓库链接 → 触发一键导入
- 编辑 Tab：修改名称、描述、图标
- 删除 Tab：删除 Tab 及其关联的所有角色（需二次确认）
- 刷新 Tab：重新从 GitHub 拉取最新代码并更新角色

---

### 3.2 GitHub 仓库一键导入

#### 3.2.1 导入流程

```
用户粘贴 GitHub URL → 校验 URL 格式 → Clone 仓库到项目文件夹
→ 扫描 SKILL.md 文件 → LLM 分析分类 → 生成角色列表 → 展示预览
→ 用户确认 → 写入角色索引 → Tab 可用
```

#### 3.2.2 导入输入

- **GitHub URL**：支持以下格式
  - `https://github.com/{owner}/{repo}`
  - `https://github.com/{owner}/{repo}/tree/{branch}`
  - `https://github.com/{owner}/{repo}/tree/{branch}/{path}`（子目录导入）
- **目标 Tab**：选择已有 Tab 或新建 Tab
- **可选参数**：
  - 分支名（默认 main/master）
  - 子目录路径（仅扫描该目录下的 skill）

#### 3.2.3 导入实现

1. **Clone 阶段**
   - 目标路径：`{PROJECT_ROOT}/skill-packs/{tab_id}/{repo_name}/`
   - 使用 `git clone --depth 1` 浅克隆（减少体积）
   - 支持 SSH 和 HTTPS 两种克隆方式

2. **扫描阶段**
   - 递归扫描仓库中所有 `SKILL.md` 文件
   - 解析 YAML frontmatter 提取：name, description, triggers, allowed_tools
   - 解析 body 作为 system_prompt

3. **LLM 分析阶段**（详见 3.3）

4. **注册阶段**
   - 将解析后的角色写入 expert_roles 索引
   - 关联到对应 Tab

#### 3.2.4 示例：金融 Tab 导入

```
仓库 URL: https://github.com/anthropics/financial-services
目标 Tab: 金融

预期扫描结果:
├── skills/
│   ├── risk-analysis/SKILL.md      → 角色：风险分析师
│   ├── compliance-review/SKILL.md  → 角色：合规审查员
│   ├── market-research/SKILL.md    → 角色：市场研究员
│   ├── portfolio-optimizer/SKILL.md → 角色：组合优化器
│   └── fraud-detection/SKILL.md    → 角色：欺诈检测
```

---

### 3.3 LLM 分析与自动分类

#### 3.3.1 分析目标

对每个导入的 SKILL.md，由 LLM 生成结构化元数据：

```typescript
interface SkillAnalysis {
  role_id: string;        // 角色 ID（从 skill 名称推导）
  display_name: string;   // 中文显示名
  category: string;       // 分类（由 LLM 判定）
  description: string;    // 一句话描述
  capabilities: string[]; // 能力标签
  recommended_tools: string[];  // 推荐工具
  compatible_scenarios: string[]; // 适用场景
  complexity: "low" | "medium" | "high";  // 复杂度评级
  classification: "planning" | "implementation"; // 规划 or 实现
}
```

#### 3.3.2 分类维度

LLM 需判断每个 skill 属于：

| 分类 | 说明 | 示例 |
|------|------|------|
| **规划类 (planning)** | 分析、评审、建议、决策支持 | 风险分析、市场研究、合规审查 |
| **实现类 (implementation)** | 执行、操作、产出、自动化 | 交易执行、报告生成、数据提取 |

#### 3.3.3 LLM Prompt 模板

```
你是一个 skill 分类专家。分析以下 SKILL.md 内容，判断该 skill 的：
1. 所属行业分类
2. 功能类型（规划 or 实现）
3. 推荐的工具场景
4. 与其他 skill 的协作关系

SKILL.md 内容：
{skill_content}

输出 JSON 格式...
```

#### 3.3.4 自动生成 Tool Scenario

当导入的 skill 数量 >= 3 时，LLM 额外生成推荐的 Tool Scenario：

```typescript
interface GeneratedScenario {
  id: string;
  name: string;           // 如 "金融风控闭环"
  description: string;
  tools: string[];
  recommended_roles: string[];  // 来自当前 Tab 的角色 ID 列表
  tab_id: string;         // 所属 Tab
}
```

---

### 3.4 流程创建页集成

#### 3.4.1 UI 变更

FlowsPage Composer Modal 中角色选择区域改为：

```
┌─ 角色选择 ──────────────────────────────────────────────┐
│                                                          │
│  [软件工程] [金融] [+ 新增]          <- Tab 切换         │
│                                                          │
│  搜索: [________________]  分类: [全部 ▼]               │
│                                                          │
│  ┌─ 规划 ─────────────────────────────────────────┐     │
│  │ ☐ 风险分析师  ☐ 合规审查员  ☐ 市场研究员      │     │
│  └────────────────────────────────────────────────┘     │
│  ┌─ 实现 ─────────────────────────────────────────┐     │
│  │ ☐ 组合优化器  ☐ 欺诈检测   ☐ 报告生成         │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

#### 3.4.2 跨 Tab 组合

- 一个流程可以混用不同 Tab 的角色（如 "代码评审" + "合规审查员"）
- 场景推荐按当前 Tab 过滤
- 已选角色列表显示来源 Tab 标签

---

## 4. 非功能需求

| 维度 | 要求 |
|------|------|
| 性能 | GitHub clone 超时 60s，LLM 分析单 skill < 10s |
| 存储 | skill-packs 总体积限制 500MB，支持清理 |
| 安全 | 仅允许 HTTPS clone；扫描 SKILL.md 做沙箱隔离（不执行其中代码） |
| 兼容 | 兼容 gstack 现有 SKILL.md 格式；支持无 frontmatter 的 markdown |
| 错误处理 | clone 失败提示网络/权限问题；SKILL.md 解析失败跳过并汇报 |

---

## 5. 技术方案概要

### 5.1 后端改动（hermes-bridge）

| 文件 | 改动 |
|------|------|
| `bridge/skill_tabs.py` (新增) | Tab CRUD + SQLite 存储 |
| `bridge/github_importer.py` (新增) | Git clone + SKILL.md 扫描 |
| `bridge/llm_classifier.py` (新增) | LLM 分析调用 + Prompt 管理 |
| `bridge/gstack_loader.py` | 改造为支持多 source（gstack + github packs） |
| `bridge/chat_handler.py` | 新增 /api/v2/tabs/* 路由 |
| `bridge/scenarios.py` | 支持动态 scenario（LLM 生成的） |

### 5.2 前端改动

| 文件 | 改动 |
|------|------|
| `web/src/components/FlowsPage.tsx` | 角色选择区加 Tab 切换 |
| `web/src/components/ImportSkillModal.tsx` (新增) | GitHub 导入弹窗 |
| `web/src/components/TabManager.tsx` (新增) | Tab 管理面板 |
| `web/src/services/api.ts` | 新增 tabsApi 方法组 |
| `web/src/types/index.ts` | 新增 SkillTab, SkillAnalysis 类型 |

### 5.3 API 新增

| Method | Path | 说明 |
|--------|------|------|
| GET | /api/v2/tabs | 获取所有 Tab 列表 |
| POST | /api/v2/tabs | 创建新 Tab |
| PUT | /api/v2/tabs/{id} | 更新 Tab |
| DELETE | /api/v2/tabs/{id} | 删除 Tab |
| POST | /api/v2/tabs/{id}/import | 触发 GitHub 导入 |
| GET | /api/v2/tabs/{id}/import/status | 查询导入进度 |
| POST | /api/v2/tabs/{id}/refresh | 重新拉取 GitHub 更新 |
| GET | /api/v2/tabs/{id}/roles | 获取 Tab 下的角色列表 |
| GET | /api/v2/tabs/{id}/scenarios | 获取 Tab 下的场景列表 |

### 5.4 数据库 Schema (SQLite)

```sql
CREATE TABLE skill_tabs (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  source_type TEXT NOT NULL DEFAULT 'builtin',
  source_url TEXT,
  branch TEXT DEFAULT 'main',
  sub_path TEXT,
  imported_at TEXT,
  updated_at TEXT,
  role_count INTEGER DEFAULT 0,
  icon TEXT,
  tab_order INTEGER DEFAULT 0
);

CREATE TABLE tab_roles (
  id TEXT PRIMARY KEY,
  tab_id TEXT NOT NULL REFERENCES skill_tabs(id) ON DELETE CASCADE,
  role_id TEXT NOT NULL,
  display_name TEXT,
  category TEXT,
  classification TEXT,  -- 'planning' | 'implementation'
  description TEXT,
  capabilities TEXT,    -- JSON array
  recommended_tools TEXT, -- JSON array
  skill_md_path TEXT,
  system_prompt TEXT,
  created_at TEXT
);

CREATE TABLE tab_scenarios (
  id TEXT PRIMARY KEY,
  tab_id TEXT NOT NULL REFERENCES skill_tabs(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  tools TEXT,            -- JSON array
  recommended_roles TEXT, -- JSON array
  generated_by TEXT DEFAULT 'llm',
  created_at TEXT
);
```

---

## 6. 导入流程时序图

```
User          Frontend           Gateway          Bridge             GitHub       LLM
 │               │                  │                │                  │           │
 │─ 粘贴URL ────►│                  │                │                  │           │
 │               │─ POST /tabs/import ──────────────►│                  │           │
 │               │                  │                │─ git clone ─────►│           │
 │               │                  │                │◄─ repo files ────│           │
 │               │                  │                │                  │           │
 │               │                  │                │─ scan SKILL.md ──┤           │
 │               │                  │                │                  │           │
 │               │                  │                │─ analyze ────────────────────►│
 │               │                  │                │◄─ classification ─────────────│
 │               │                  │                │                  │           │
 │               │◄─ SSE: progress ─────────────────│                  │           │
 │               │◄─ SSE: preview ──────────────────│                  │           │
 │               │                  │                │                  │           │
 │─ 确认导入 ───►│─ POST confirm ──────────────────►│                  │           │
 │               │                  │                │─ save to DB ─────┤           │
 │               │◄─ 200 OK ────────────────────────│                  │           │
 │◄─ Tab 刷新 ──│                  │                │                  │           │
```

---

## 7. 里程碑

| 阶段 | 内容 | 预估工期 |
|------|------|----------|
| P1 | Tab 数据模型 + API + 前端 Tab 切换 UI | 3 天 |
| P2 | GitHub clone + SKILL.md 扫描 + 导入弹窗 | 3 天 |
| P3 | LLM 分析分类 + 自动生成 Scenario | 2 天 |
| P4 | 跨 Tab 组合流程 + 预览确认 UX | 2 天 |
| P5 | 金融 Tab 预置 + 端到端测试 | 2 天 |

---

## 8. 开放问题

1. **认证**：GitHub 私有仓库是否需要支持？若支持则需 PAT / SSH key 管理
2. **更新策略**：仓库更新时，已创建的流程中引用的角色如何处理？版本锁定 or 滚动更新？
3. **角色冲突**：不同 Tab 导入了同名角色如何处理？（建议加 tab 前缀）
4. **LLM 选择**：分类分析用 DeepSeek 还是其他模型？需平衡成本与准确率
5. **离线模式**：clone 后的仓库是否作为离线缓存？网络不可用时是否仍可使用已导入的 skill？

---

## 9. 验收标准

- [ ] 流程创建页显示多个 Tab（软件工程 + 金融）
- [ ] 点击 [+ 新增] 弹出导入弹窗，支持粘贴 GitHub URL
- [ ] 导入完成后新 Tab 出现，展示扫描到的角色（带分类标签）
- [ ] 角色按 LLM 分析结果分为"规划"/"实现"两类
- [ ] 自动生成至少 1 个 Tool Scenario
- [ ] 跨 Tab 混合选择角色创建流程并成功执行
- [ ] Tab 的刷新/删除操作正常
