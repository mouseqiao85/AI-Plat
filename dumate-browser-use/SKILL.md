---
name: dumate-browser-use
version: "0.1.0"
description: 浏览器自动化技能，支持网页访问、点击、输入、截图等操作。默认通过 Extension 模式复用用户已打开的 Chrome 及登录态，也支持 CDP 模式自动启动独立 Chrome 完成无头抓取和自动化任务。
author: DuMate
license: MIT
enabled: true
keywords:
  - browser
  - automation
  - playwright
  - web-scraping
  - cdp
  - browser-extension
tools:
  - name: browser_init
    description: 初始化浏览器会话，支持 Extension 模式（复用用户 Chrome）和 CDP 模式（独立 Chrome）
  - name: browser_navigate
    description: 导航到指定 URL，支持安全导航验证和多 agent 并发防串 tab
  - name: browser_snapshot
    description: 获取页面 ARIA 快照，用于读取页面结构和元素引用
  - name: browser_interact
    description: 与页面元素交互（点击、填写、选择、拖拽、上传等），基于快照中的 ref
  - name: browser_screenshot
    description: 截取页面或指定元素的屏幕截图
  - name: browser_tabs
    description: 管理浏览器标签页（列出、新建、切换、关闭）
  - name: browser_storage
    description: 管理浏览器存储（cookies、localStorage）
  - name: browser_run_code
    description: 执行任意 Playwright 代码，用于复杂交互和自定义逻辑
---


# Browser Automation with playwright-cli

## Installation

本 skill 使用 shell 脚本（`.sh`），在 Windows 上需要 Git Bash 或 MSYS2 等 Unix 兼容 shell。首次使用时运行以下 **检查并安装** 序列 — 可安全重复执行，已安装的会自动跳过。

```shell
# Step 1: 检查 Git Bash（提供 bash / source / grep / curl 等）
if ! bash --version >/dev/null 2>&1; then
  echo "[INSTALL] 未检测到 Git Bash。请安装 Git for Windows: https://git-scm.com/download/win"
  echo "          安装时勾选 'Use Git and optional Unix tools from the Command Prompt'。"
  echo "          安装完成后重启终端，再重新运行此脚本。"
  exit 1
fi

# Step 2: 检查 Node.js（提供 npm / npx）
if ! node --version >/dev/null 2>&1; then
  echo "[INSTALL] 未检测到 Node.js。请从 https://nodejs.org/ 安装（推荐 LTS 版本）"
  echo "          安装完成后重启终端，再重新运行此脚本。"
  exit 1
fi

# Step 3: 安装 playwright-cli（已安装则跳过）
if ! command -v playwright-cli >/dev/null 2>&1; then
  echo "[INSTALL] 正在安装 playwright-cli..."
  npm install -g @playwright/cli@latest --registry https://registry.npmmirror.com
fi

# 验证
echo "bash:            $(bash --version | head -1)"
echo "node:            $(node --version)"
echo "playwright-cli:  $(playwright-cli --version 2>/dev/null || echo 'not found')"
```

> 如果 `playwright-cli` 全局安装失败，可在后续命令中使用 `npx playwright-cli` 替代。

---

## 适用场景

**适合使用：**
- 访问网页、搜索网页内容、读取网页信息
- 点击网页元素、填写表单、提交输入
- 截图网页或指定元素
- 复用已打开 Chrome 的登录态执行自动化任务
- 多 agent 并发浏览器操作

**不适合使用：**
- 纯文本写作、翻译、总结、问答等不涉及浏览器的任务
- 与网页访问或浏览器自动化无关的系统操作
- 需要启动或管理 relay 进程（本技能不负责此事）

---

## 文件结构

本 SKILL.md 所在目录即为 `_SKILL_DIR`。模型加载此文件时，应从文件路径中提取目录作为 `_SKILL_DIR`，后续所有 `source` 和 `Read` 命令使用此变量。

目录结构：
- `scripts/` — 初始化脚本（init-extension.sh、init-headed.sh、init-headless.sh）和辅助函数（session-header.sh）
  - `scripts/lib/` — 内部模块（env/log/state/relay-api/decision/prompts/pw-cli/cdp-launch），Agent 无需直接 source
- `references/` — 参考文档（pagination.md 翻页策略等）

例如，若此文件路径为 `/path/to/dumate-browser-use/SKILL.md`，则：
```bash
_SKILL_DIR="/path/to/dumate-browser-use"
# 执行脚本
source "${_SKILL_DIR}/scripts/init-extension.sh"
# 读取参考文档
Read "${_SKILL_DIR}/references/pagination.md"
```

> 严禁使用 `find` 命令定位路径！路径含空格时 find+xargs 会导致路径被截断。禁止使用 `source scripts/xxx.sh`（相对路径），会因 CWD 不同而失败。

---

## Guidance

### 必须遵守

1. **从 snapshot 判断页面需要登录/验证码时，必须立即调用 `_pw_wait_login` 并停止所有自动化操作** — 绝对禁止继续点击、填表、导航或任何自动化操作，必须暂停等待用户完成登录/验证后回复"已完成"。登录/验证码判断信号包括：密码输入框、验证码/人机验证、2FA、登录墙遮挡目标内容等。思考模型应结合页面上下文综合判断
2. **每次 Bash 调用开头必须执行** `source "${_SKILL_DIR}/scripts/session-header.sh"`，否则报 "not open" 错误
3. **所有脚本必须使用绝对路径 source**，禁止 `source scripts/xxx.sh`（CWD 不同会失败）
4. **`playwright-cli snapshot` 与 `_pw_snap` 必须在同一个 Bash 块中执行**，变量不跨 Bash 进程继承
5. **非视频页面导航必须使用 `_pw_open <url>`**，仅在明确不需要时才可用 `playwright-cli open <url>`
6. **先 snapshot 再交互**，确保获取最新 refs
7. **点击后检查新 tab** — `click` → `tab-list` → 有新 tab 则 `tab-select`
8. **涉及翻页操作时，必须先读取详细指南** — 使用 Read 工具读取 `${_SKILL_DIR}/references/pagination.md`，了解该网站的分页类型和翻页方法后再执行。详见下方"分页策略"章节

   **触发场景（满足任一即需读取）：**
   - 任务关键词：统计、收集、遍历、获取"所有"、导出列表数据
   - 页面有分页控件：页码、"下一页"、"加载更多"、"查看更多"，等等
   - 需要获取的数据明显超过一页显示数量
9. **Extension 安装提示卡片** — 当 Extension 未连接时，会展示卡片供用户选择"跳过"或"开启连接"。**卡片展示后 Agent 必须保持静默**，不要输出任何文字说明、不要解释卡片内容、不要主动询问用户。只需等待用户点击卡片按钮，然后根据回调继续执行。
10. **`[MODE_PROMPT]` 提示必须响应**，根据任务类型选择 headed 或 headless 模式
11. **不得向用户暴露 Extension 内部状态与后台配置动作** — 响应 `[MODE_PROMPT]` 时，禁止在思考过程或回复中说明 Extension 不可用的具体原因（disabled / declined / TTL 未过期 / notice 等均为内部状态），也禁止复述 TTL 设置之类后台配置动作（"已设置 TTL"、"7 天不再提示"等）。只需说明最终选择了哪种 CDP 模式及基于任务的理由。所有内部状态均已写入 `browser-use.log`，用户询问时再从日志查询。

### 禁止操作

- 禁止使用相对路径 `source scripts/...`
- 禁止用 Read 工具或 cat 读取 `.dumate/` 下的 yml 快照文件
- 禁止对视频/直播页面使用 `playwright-cli open <url>` 或 `goto <url>` 直接导航
- 禁止对视频/直播/大型 SPA（电商、社交媒体）页面等待 `networkidle`，会导致超时断连
- 禁止在 `_pw_open` 返回 `[WARNING] Domain mismatch` 后继续操作
- 禁止在检测到登录/验证码/人机验证时继续自动化
- 禁止在输出 `[LOGIN_REQUIRED]` 后继续任何自动化操作（点击、填表、导航等）
- 禁止尝试自动填入用户名/密码绕过登录
- 禁止在 Extension 模式下启动、查找或管理 relay 进程
- 禁止因其他 agent 对话内容而跨域导航

### 操作技巧

- **SPA 渲染等待** — 优先 `waitForSelector` 或 `sleep 2`，避免 `networkidle`（电商/社交站点会超时）
- **页面跳转等待** — `run-code "async page => { await page.waitForLoadState('load'); }"` 或 `waitForURL`
- **视频/大型 SPA 等待** — 用 `domcontentloaded` 或 `sleep`，禁止 `networkidle`
- **元素找不到** — `mousewheel 0 500` 滚动后重新 `snapshot`
- **Tab 复用** — 同一 SANDBOX_SESSION_ID 下 `close` 后再 `open`，会复用之前的 tab（Extension 模式）
- **CDP 遇登录/验证码** — 运行 `_pw_check_extension_prompt` 检查是否可切 Extension 模式，Extension 复用用户登录态可避免反复验证

### 分页策略

**重要**：涉及翻页操作时，**必须先使用 Read 工具读取 `${_SKILL_DIR}/references/pagination.md`**，了解目标网站的分页类型和正确翻页方法后再执行。

#### 快速参考：分页类型识别

从 snapshot 底部检查分页控件：

| 类型 | 识别信号 | 翻页方式 |
|------|---------|---------|
| **无限滚动** | 底部无分页控件，内容随滚动增加 | `mousewheel 0 800` 滚动 |
| **页码分页** | 底部有页码数字（1,2,3...）或"下一页"/"Next"/">"按钮 | 点击页码或"下一页"按钮 |
| **加载更多按钮** | 底部有"加载更多"/"Load more"/"查看更多"按钮 | 点击该按钮 |

#### 常见错误

**一直滚动但不加载新内容** → 可能是页码分页网站，检查底部是否有"下一页"按钮并点击。

> 各网站分页类型、翻页代码示例、成功判断方法等详细内容见 `${_SKILL_DIR}/references/pagination.md`

### 日志排查

所有 browser-use 命令执行日志记录在 `${XDG_DATA_HOME:-$HOME/.local/share}/logs/dialog/browser-use.log`

```bash
# 查看最新日志
tail -50 "${XDG_DATA_HOME:-$HOME/.local/share}/logs/dialog/browser-use.log"

# 实时监控日志
tail -f "${XDG_DATA_HOME:-$HOME/.local/share}/logs/dialog/browser-use.log"
```

日志格式：`[DIAG HH:MM:SS.mmm] CMD_START | <command> | mode=<mode> | ...`

### 错误排查

- **"The browser 'default' is not open"** — 遗漏了 `source session-header.sh`，或需要执行 Recovery Flow
- **`Execution context was destroyed`** — 正常跳转信号，继续 `tab-list`
- **daemon 卡死** — `playwright-cli kill-all` 然后重新 `open`
- **ECONNREFUSED** — CDP 模式：Chrome 未启动或 CDP 未就绪；Extension 模式：Relay 未启动
- **Extension not connected** — 提示用户确认 Chrome 已打开且 DuMate Browser Extension 已启用

### Recovery Flow

会话异常时，按以下步骤恢复：

```bash
source "${_SKILL_DIR}/scripts/session-header.sh"
playwright-cli kill-all
source "${_SKILL_DIR}/scripts/init-extension.sh"
```

如果输出 `[MODE_PROMPT]`（Extension 不可用），根据任务类型选择：
```bash
# headed 模式（需要登录/验证码、调试网页）
source "${_SKILL_DIR}/scripts/init-headed.sh"

# 或 headless 模式（纯信息抓取、批量任务）
source "${_SKILL_DIR}/scripts/init-headless.sh"
```

然后继续：
```bash
source "${_SKILL_DIR}/scripts/session-header.sh"
playwright-cli open
playwright-cli snapshot && _pw_snap
```

恢复后若页面状态仍异常，停止操作并向用户报告，不要继续执行。

---

## 响应脚本输出标记

`init-extension.sh` 会根据 Extension 启用/连接/提示 TTL 的组合自动判断，Agent **不参与决策**，只需响应脚本输出中的标记。

### `[MODE_PROMPT]` — 选择 CDP 模式

脚本已确定 Extension 不可用，Agent 根据任务类型选择 headed / headless：

| 任务类型 | 推荐模式 | 执行命令 |
|---------|---------|---------|
| 需要登录/验证码 | headed | `source "${_SKILL_DIR}/scripts/init-headed.sh"` |
| 调试网页问题 | headed | `source "${_SKILL_DIR}/scripts/init-headed.sh"` |
| 用户明确要求看浏览器 | headed | `source "${_SKILL_DIR}/scripts/init-headed.sh"` |
| 纯信息抓取/搜索 | headless | `source "${_SKILL_DIR}/scripts/init-headless.sh"` |
| 批量自动化任务 | headless | `source "${_SKILL_DIR}/scripts/init-headless.sh"` |
| 不确定任务类型 | headless | `source "${_SKILL_DIR}/scripts/init-headless.sh"` |

> **禁止向用户转述 Extension 不可用的原因**（"Extension 被禁用"、"之前拒绝过"、"TTL 未过期" 等均为内部状态，已由脚本写入 `browser-use.log`）。只说明基于任务类型的模式选择理由，例如"需要登录，使用 headed 模式"。

---

## 模式对比

| 模式 | Init Script | 适用场景 | Chrome 管理 |
|------|------------|---------|------------|
| **Extension**（默认） | `init-extension.sh` | 复用用户已打开的 Chrome，操作用户浏览器 | 用户自行管理，需安装扩展 |
| **CDP 无头** | `init-headless.sh` | 信息抓取、搜索、截图、自动化任务 | 宿主机自动启动，无窗口 |
| **CDP 有头** | `init-headed.sh` | 需要看到浏览器窗口，或登录/验证码切换 | 宿主机自动启动，有窗口 |

**Extension 模式的优势：**
- 复用用户已有的 Chrome 登录态，无需重复登录
- 天然绕过大部分反爬检测（使用真实用户浏览器）
- 登录态自动持久化，跨任务自动保留

**前置条件：**
- CDP 模式：运行 Init Script 即可（自动启动 Chrome）
- Extension 模式：用户已在 Chrome 中安装并启用 DuMate Browser Extension。**Relay 由应用自动管理，Skill 不负责启动 Relay，不要尝试查找或启动 relay 相关文件。**

**默认必须优先执行 `init-extension.sh`。** 除非用户明确要求 headed 模式或已确定需要人工登录/验证码处理，否则不要直接使用 `init-headless.sh` 或 `init-headed.sh` 作为首选入口。

---

## connId Tab 复用机制

本 skill 的核心能力：**基于 SANDBOX_SESSION_ID 生成稳定的 connId，写入 cdpEndpoint URL，实现 tab 复用**。

### 工作原理

1. `init-extension.sh` 根据 `SANDBOX_SESSION_ID` 生成 `connId=session-<id>`
2. 写入 config.json 的 cdpEndpoint 为 `ws://127.0.0.1:19228/cdp?connId=session-<id>`
3. `--session=<connId>` 为每个 agent 创建独立的 daemon 进程，确保命令路由到正确的 tab
4. 不同 agent 使用不同 `SANDBOX_SESSION_ID` → 不同 connId → 不同 `--session` → 独立 daemon → 各自独立的 tab
5. `playwright-cli open` 连接 relay 时，relay 解析 URL 中的 connId：
   - **首次连接**：分配 connId，创建新 tab
   - **再次连接**（同一 SANDBOX_SESSION_ID）：复用已有 tab，无需重新创建

> connId 仅在 Extension 模式下生效。CDP 模式（headless/headed）不经过 relay，无 connId 路由，但 `--session` 仍用于隔离 daemon 进程。

### 多 Agent 并发

```
Agent A (SANDBOX_SESSION_ID=abc)
  → cdpEndpoint=ws://127.0.0.1:19228/cdp?connId=session-abc
  → 操作 Tab1 (百度)，不影响其他 agent

Agent B (SANDBOX_SESSION_ID=def)
  → cdpEndpoint=ws://127.0.0.1:19228/cdp?connId=session-def
  → 操作 Tab2 (京东)，不影响其他 agent
```

### Tab 隔离规则（必读）

多 agent 并发时，每个 agent 通过 `connId` 绑定到独立的 Chrome tab。**relay 层路由已验证隔离正确**，但 LLM agent 可能因上下文混淆而导航到错误 URL。必须遵守以下规则：

1. **只操作自己 tab 的目标网站** — 如果你的任务是搜索百度，只导航到 `baidu.com` 域名下的 URL；如果是搜索京东，只导航到 `jd.com` 域名下的 URL
2. **禁止跨域导航** — 不要因为看到其他 agent 的对话内容而导航到其他网站的 URL
3. **导航前验证** — 使用 `_pw_open <url>` 代替 `playwright-cli open <url>`，它会自动检查当前页面并验证导航结果
4. **导航后确认** — 每次 `open` 或 `goto` 后，必须 snapshot 确认页面 URL 的域名与你期望的一致
5. **发现串域时** — 如果 snapshot 显示的 URL 域名与你的任务不匹配，**不要继续操作**，立即报告异常

### connId 持久化

- connId 与 mode 统一存储在 `${_DATA_DIR}/config.json` 中（字段 `mode` / `connId`）
- `session-header.sh` 每次 bash 调用时读取并确保 config.json 的 `browser.cdpEndpoint` 包含 connId
- relay 侧的 session 映射持久化在 `${XDG_DATA_HOME:-/tmp}/dumate-browser-extension-relay-{port}-sessions.json`

---

**核心工作流：**
1. Init → `source "${_SKILL_DIR}/scripts/init-extension.sh"`
2. 每次 Bash 调用开头必须 **source "${_SKILL_DIR}/scripts/session-header.sh"**（见下方），否则 daemon 找不到 session
3. 导航 → **必须使用** `_pw_open <url>`。仅在明确不需要时才可用 `playwright-cli open <url>`（视频/直播页面禁止此方式，见"视频/动态内容页面处理"）
4. 检查 → snapshot + `_pw_snap` 读取快照，**必须在同一 Bash 块中**：
   ```bash
   playwright-cli snapshot && _pw_snap
5. 检测登录/验证码 → 见下方"登录 & 验证码处理"
6. 交互 → `playwright-cli click <ref>`、`playwright-cli fill <ref> "text"` 等
7. 新 tab → 点击后 `tab-list`，有新 tab 则 `tab-select <index>`
8. 结束 → `playwright-cli close`（CDP 模式自动关闭 Chrome；Extension 模式仅断开连接）

**Session Header — 每次 Bash 调用开头必须 source 此脚本：**
```bash
source "${_SKILL_DIR}/scripts/session-header.sh"
```
> 环境变量和 shell 函数不跨 Bash 调用继承。每次新的 Bash 调用都必须先 source session-header.sh，否则报 "The browser 'default' is not open"。

---

## 登录 & 验证码处理

当 snapshot 中出现以下任一信号时，必须立即处理：
- 登录表单（用户名/密码输入框、"登录"/"Sign in"/"Log in" 按钮）
- 验证码（captcha、滑块验证、图形验证、"请验证您是人类"/"Verify you are human"）
- 二次验证（短信验证码、邮箱验证、2FA 提示）
- 任何阻止自动化继续的人机验证页面

### CDP 模式处理步骤：
0. **检查是否可切换 Extension 模式** — 运行 `_pw_check_extension_prompt`，若展示 Extension 安装提示卡片：
   - **用户点击"开启连接"** → 引导用户按 [DuMate浏览器插件安装指南](https://cloud.baidu.com/doc/Dumate/s/Fmo30bfx1) 安装，安装完成后重新 `source "${_SKILL_DIR}/scripts/init-extension.sh"`
   - **用户点击"跳过"** → 继续下面的 CDP 处理流程
   - 若未展示卡片（Extension 已连通或用户已禁用），直接继续下面的步骤
1. `playwright-cli close` — 关闭当前会话并停止 Chrome
2. `source "${_SKILL_DIR}/scripts/init-headed.sh"` — 切换有头模式
3. `playwright-cli open <目标URL>` — 重新导航
4. 直接回复用户："请在浏览器中完成登录/验证操作，完成后回复 **'已完成'** 继续任务。"
5. **等待用户回复"已完成"后**，先 `playwright-cli snapshot` 确认登录/验证已通过，再继续后续自动化步骤。

### Extension 模式处理步骤（必须严格遵守）：

1. 从 snapshot 判断页面需要登录/验证（思考模型结合页面上下文综合判断，不使用正则匹配）
2. **立即调用 `_pw_wait_login`**，输出 `[LOGIN_REQUIRED]` 标记
3. 通知用户："检测到页面需要登录/验证，请在浏览器中完成操作，完成后回复 **'已完成'** 继续任务。"
4. **等待用户回复"已完成"**（期间绝对禁止任何自动化操作：点击、填表、导航、snapshot 等）
5. 用户回复后，执行 `playwright-cli snapshot && _pw_snap` 确认登录已通过
6. 如果仍需登录，重复步骤 1-5
7. 登录通过后，继续后续自动化步骤

> Extension 模式下用户已能看到 Chrome 窗口，无需切换模式。

**绝对禁止：**
- 在输出 `[LOGIN_REQUIRED]` 后继续任何自动化操作
- 尝试自动填入用户名/密码绕过登录
- 刷新页面或重新导航来"绕过"登录
- 忽略 `[LOGIN_REQUIRED]` 标记继续任务

---

## 视频/动态内容页面处理

当页面满足以下任一特征时，**必须使用特殊处理方式**：

### 识别信号
- **URL 特征**：包含 `youtube.com/watch`、`bilibili.com/video`、`vimeo.com`、`youku.com`、`iqiyi.com`、`douyin.com` 等视频域名
- **页面元素**：snapshot 中出现 `<video>` 标签、播放器组件
- **关键词**：页面包含 "播放"、"pause"、"视频"、"live"、"直播" 等

### 问题说明
`playwright-cli open <url>` 和 `goto <url>` 在视频页面默认等待 `load` 事件，视频流持续加载导致**无限卡住**。

### 必须使用的方案：手动打开 + tab-select
```bash
source "${_SKILL_DIR}/scripts/session-header.sh"

# 1. 让用户在 Chrome 中手动打开视频链接
# 2. playwright-cli 连接浏览器（不传 URL）
playwright-cli open

# 3. 查看所有标签页，找到视频标签
playwright-cli tab-list

# 4. 选择视频标签页（根据 tab-list 输出确定 index）
playwright-cli tab-select <index>

# 5. 截图（禁用动画，设置超时）
playwright-cli run-code "async page => { await page.screenshot({ path: 'video.png', animations: 'disabled', timeout: 10000 }); }"
```

> **禁止对视频/大型 SPA（电商、社交）页面使用 `networkidle`** — 会超时断连。用 `domcontentloaded`、`waitForSelector` 或 `sleep` 替代。

---

## 登录态持久化

playwright-cli 使用 `"isolated":false` 配置，直接复用 Chrome 的默认 context（Chrome profile 中的 cookies、localStorage、session），而非创建隔离的 in-memory context。

- CDP 模式：Chrome profile 持久化在宿主机 `$XDG_DATA_HOME/dumate_server/browser-profile`，跨任务自动保留
- Extension 模式：直接使用用户 Chrome 的 profile，登录态天然可用

无需 `state-save`/`state-load`。

---

## 窗口模式（仅 CDP 模式）

Chrome 启动时固定窗口模式，之后无法更改：
- `"headless":true` — 无窗口（**默认**）
- `"headless":false` — 有窗口
- **自动切有头**：snapshot 检测到登录/验证码/人机验证 → 按"登录 & 验证码处理"流程切换
- **主动用有头**：用户明确要求看到浏览器窗口（"有头"、"headed"、"让我看到浏览器"等）

> Extension 模式无此区分，Chrome 始终由用户自行管理。

---

## Init Script

Extension 模式（默认，必须优先使用）：
```bash
source "${_SKILL_DIR}/scripts/init-extension.sh"
```
> 脚本会自动判断 Extension 状态，输出 `[MODE_PROMPT]` 或展示 Extension 安装提示卡片。
>
> **重要**：`enabled` 状态由脚本自动检查，Agent 无需判断。

CDP 无头：
```bash
source "${_SKILL_DIR}/scripts/init-headless.sh"
```

CDP 有头（用户要求可见窗口，或检测到登录/验证码需要切换时）：
```bash
source "${_SKILL_DIR}/scripts/init-headed.sh"
```

> 脚本路径依赖 `$XDG_DATA_HOME` 环境变量。若报 `No such file`，运行 `ls -d "${XDG_DATA_HOME}/skills/"*"/"*browser*extension*/scripts` 定位后 `source <绝对路径>/init-extension.sh`。

---

## Commands

```bash
# Session
playwright-cli open <url>           # 连接 Chrome 并导航（Extension 模式带 connId 自动复用 tab）
playwright-cli open                 # 连接 Chrome（不导航，复用已有 tab）
playwright-cli close                # 关闭浏览器（CDP 模式关闭 Chrome；Extension 模式仅断开）
playwright-cli kill-all             # 强制终止残留 daemon
playwright-cli delete-data          # 清除会话数据

# Navigation
playwright-cli goto <url>           # 导航
_pw_open <url>                      # 安全导航（必须使用）：导航 + 验证，多 agent 并发时防止串 tab
playwright-cli go-back / go-forward / reload

# 视频/动态页面导航（禁止直接用 open/goto，会卡死）
playwright-cli open                 # 先连接浏览器（不传URL）
playwright-cli run-code "async page => { await page.goto('<url>', { waitUntil: 'domcontentloaded' }); }"  # 用 domcontentloaded 导航

# Page State
playwright-cli snapshot             # 输出快照文件链接（用 _pw_snap 读取）
_pw_check_extension_prompt          # CDP 模式遇登录/验证码/反爬时，检查是否可切换 Extension 模式
playwright-cli screenshot           # 截图整页
playwright-cli screenshot <ref>     # 截图指定元素
playwright-cli pdf                  # 保存为 PDF
playwright-cli eval "document.title"
playwright-cli eval "<func>" <ref>  # 在指定元素上执行 JS

# 读取最新快照（snapshot 后在同一 Bash 块中执行）
_pw_snap

# 登录/验证码等待（思考模型判断页面需要登录后调用）
_pw_wait_login                     # 输出 [LOGIN_REQUIRED] 标记，暂停自动化，等待用户完成登录

# Interactions（ref 从快照获取，如 e15）
playwright-cli click <ref>
playwright-cli click <ref> right    # 右键点击
playwright-cli dblclick <ref>
playwright-cli fill <ref> "text"    # 清空并填入
playwright-cli type "text"          # 追加输入到焦点元素
playwright-cli press Enter          # 支持 "Control+a"、"ArrowLeft" 等
playwright-cli keydown <key>        # 按住键
playwright-cli keyup <key>          # 抬起键
playwright-cli hover <ref>
playwright-cli select <ref> "opt"   # 下拉选择
playwright-cli check <ref>          # 勾选 checkbox
playwright-cli uncheck <ref>
playwright-cli drag <ref> <target>
playwright-cli upload <file>        # 上传文件
playwright-cli dialog-accept        # 接受弹窗（alert/confirm/prompt）
playwright-cli dialog-accept "text" # 接受 prompt 并输入文字
playwright-cli dialog-dismiss       # 取消弹窗
playwright-cli resize <w> <h>       # 调整窗口大小

# Mouse
playwright-cli mousewheel 0 500     # 向下滚动
playwright-cli mousewheel 0 -500    # 向上滚动
playwright-cli mousemove <x> <y>    # 移动鼠标到坐标
playwright-cli mousedown / mouseup  # 鼠标按下/抬起

# Tabs
playwright-cli tab-list             # 列出所有 tab
playwright-cli tab-new [url]
playwright-cli tab-select <index>
playwright-cli tab-close <index>

# Storage（调试用，登录态已由 Chrome profile 自动维护）
playwright-cli cookie-list          # 列出所有 cookies
playwright-cli cookie-get <name>
playwright-cli cookie-set <name> <value>
playwright-cli cookie-delete <name>
playwright-cli cookie-clear
playwright-cli localstorage-list
playwright-cli localstorage-get <key>
playwright-cli localstorage-set <key> <value>
playwright-cli localstorage-delete <key>
playwright-cli localstorage-clear

# Network
playwright-cli network              # 列出本次页面加载的所有网络请求
playwright-cli route <pattern>      # Mock 网络请求（拦截匹配 URL）
playwright-cli route-list
playwright-cli unroute [pattern]

# DevTools
playwright-cli console              # 列出控制台消息
playwright-cli console error        # 只看 error 级别
playwright-cli run-code "<code>"    # 执行任意 Playwright 代码
playwright-cli tracing-start / tracing-stop
playwright-cli video-start / video-stop

# Wait
playwright-cli run-code "async page => { await page.waitForLoadState('load'); }"  # 推荐：等待页面加载
playwright-cli run-code "async page => { await page.locator('.target').waitFor({ timeout: 10000 }); }"  # 推荐：等待特定元素
sleep 2 && playwright-cli snapshot   # 简单等待后快照
# 注意：避免使用 networkidle，电商/社交/视频等 SPA 页面会超时断连

# 大型 SPA 页面专用（电商、社交、视频等）
playwright-cli run-code "async page => { await page.waitForLoadState('domcontentloaded'); }" && sleep 2 && playwright-cli screenshot
playwright-cli run-code "async page => { await page.waitForLoadState('domcontentloaded', { timeout: 5000 }); }" && playwright-cli snapshot
```

---

## Architecture

### CDP 模式
```
sandbox agent
  → POST ${DUMATE_HOST_URL}/browser/launch  {"headless":true/false}
    → Chrome on host (headless:true=无窗口; headless:false=有窗口)
    → Chrome profile: $XDG_DATA_HOME/dumate_server/browser-profile（宿主机持久）
    → CDP endpoint: ${BROWSER_USE_CDP_URL:-http://127.0.0.1:19222}
  → playwright-cli config: $XDG_DATA_HOME/dumate-browser/${SANDBOX_SESSION_ID}/config.json
    → cdpEndpoint + isolated:false → 直接复用 Chrome 默认 context
  → snapshot output: .dumate/${SANDBOX_SESSION_ID}/（通过 PLAYWRIGHT_MCP_OUTPUT_DIR）
```

### Extension 模式（带 connId 复用）
```
宿主机
  → ws-relay (独立进程，监听 ws://0.0.0.0:19228，由用户预先启动)
    → /cdp?connId=session-abc  ← Agent A 的 playwright-cli WebSocket 连接
    → /cdp?connId=session-def  ← Agent B 的 playwright-cli WebSocket 连接
    → /extension               ← Chrome DuMate Browser Extension 连接
    → 按 connId 路由 CDP 命令/事件到对应 tab
  → 用户自行打开 Chrome + DuMate Browser Extension

sandbox agent (SANDBOX_SESSION_ID=abc)
  → init-extension.sh: connId=session-abc
  → config.json: cdpEndpoint=ws://127.0.0.1:19228/cdp?connId=session-abc
  → playwright-cli open https://baidu.com  → relay 创建 Tab1
  → playwright-cli close                   → 断开连接，Tab1 保留
  → playwright-cli open https://baidu.com  → relay 复用 Tab1 ✅
  → snapshot output: .dumate/${SANDBOX_SESSION_ID}/

sandbox agent (SANDBOX_SESSION_ID=def)
  → init-extension.sh: connId=session-def
  → config.json: cdpEndpoint=ws://127.0.0.1:19228/cdp?connId=session-def
  → playwright-cli open https://jd.com    → relay 创建 Tab2（不影响 Tab1）
```
