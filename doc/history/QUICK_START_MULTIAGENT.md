# Agent Platform - 快速使用服务器多Agent优化

## 🎯 目标

使用服务器端的 **Hermes CLI + Claude Code** 和 **9个专业Agent** 来优化项目。

---

## 🚀 方式1：运行Python脚本（推荐）

```powershell
cd C:\Projects\agent-platform
python optimize_with_server_multiagent.py
```

**脚本会自动**:
- ✅ 连接服务器 8.215.63.182
- ✅ 检查/安装 Hermes
- ✅ 调用 9 个专业 Agent
- ✅ 使用 Claude Code 生成代码
- ✅ 保存优化报告到 `agent_outputs/`

---

## 🖥️ 方式2：手动SSH操作

### 步骤1：连接服务器

```bash
ssh root@8.215.63.182
# 密码: <redacted>
```

### 步骤2：安装Hermes（如果未安装）

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

### 步骤3：配置Claude Code

```bash
export ANTHROPIC_API_KEY="your_claude_api_key_here"
export CLAUDE_CODE_MODEL="claude-sonnet-4.5"
```

### 步骤4：使用Agent优化

```bash
# 需求分析
hermes skill requirement-analyst --task "分析 Agent Platform 项目的优化需求"

# PRD设计
hermes skill prd-designer --task "设计优化方案和实施计划"

# 架构设计
hermes skill tech-architect --task "设计技术架构优化方案"

# 前端优化（使用Claude Code）
hermes skill frontend-developer --task "优化前端代码，使用Claude Code生成优化后的代码"

# 后端优化（使用Claude Code）
hermes skill backend-developer --task "优化Go和Python代码，使用Claude Code生成优化代码"

# 编写测试
hermes skill unit-tester --task "编写完整的测试用例"

# UAT测试
hermes skill uat-tester --task "设计UAT测试方案"

# 发布计划
hermes skill version-manager --task "制定版本发布计划"
```

---

## 📁 输出文件

优化结果保存在：`C:\Projects\agent-platform\agent_outputs\`

```
agent_outputs/
├── requirement_analysis.md      # 需求分析报告
├── prd_design.md               # PRD设计文档
├── architecture_design.md      # 架构设计
├── frontend_optimization.md    # 前端优化方案
├── backend_optimization.md     # 后端优化方案
├── database_optimization.md    # 数据库优化方案
├── test_plan.md                # 测试计划
├── uat_plan.md                 # UAT测试方案
├── release_plan.md             # 发布计划
└── OPTIMIZATION_REPORT.md      # 最终汇总报告
```

---

## 🤖 9个专业Agent

| # | Agent | 职责 |
|---|-------|------|
| 1 | 需求分析 | 分析项目现状、识别优化点 |
| 2 | PRD设计 | 设计优化方案、制定计划 |
| 3 | 技术架构师 | 架构设计、技术选型 |
| 4 | UI设计 | 界面设计、交互优化 |
| 5 | 前端开发 | 前端代码优化 |
| 6 | 后端开发 | 后端代码优化 |
| 7 | 单元测试 | 编写测试用例 |
| 8 | UAT测试 | 设计验收测试 |
| 9 | 版本管理 | 制定发布计划 |

---

## ⏱️ 预计时间

- **单个Agent**: 10-60秒
- **完整优化**: 5-10分钟

---

## 🔧 示例：优化某个模块

```bash
# 优化认证模块
hermes skill backend-developer --task "优化 authentication 模块，使用Claude Code生成优化代码"

# 优化聊天接口
hermes skill backend-developer --task "优化 chat API 性能，使用Claude Code生成优化代码"

# 优化前端组件
hermes skill frontend-developer --task "优化 React 组件性能，使用Claude Code生成优化代码"
```

---

## ⚠️ 重要提示

1. **API密钥**: 不要泄露 `ANTHROPIC_API_KEY`
2. **结果验证**: 优化后的代码需要人工审核
3. **测试验证**: 运行测试确保功能正常

---

**服务器**: 8.215.63.182  
**密码**: <redacted>  
**工具**: Hermes CLI + Claude Code
