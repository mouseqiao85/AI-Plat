# Agent Platform - 多Agent优化系统使用说明

## ✅ 已准备就绪

我已经为你准备好了通过服务器端多Agent系统优化项目的完整方案：

---

## 📦 生成的文件

| 文件 | 说明 |
|------|------|
| `optimize_with_server_multiagent.py` | Python自动化脚本 ✨ |
| `HOW_TO_USE_MULTIAGENT.md` | 详细使用指南 |
| `QUICK_START_MULTIAGENT.md` | 快速启动指南 |
| `server_deployment/install_hermes.sh` | Hermes安装脚本 |
| `server_deployment/optimize_with_multiagent.sh` | Bash优化脚本 |

---

## 🚀 两种使用方式

### 方式1：Python脚本（自动化，推荐）

```powershell
cd C:\Projects\agent-platform
python optimize_with_server_multiagent.py
```

**脚本功能**：
- ✅ 自动连接服务器（8.215.63.182）
- ✅ 自动检查/安装 Hermes
- ✅ 依次调用 9 个专业 Agent
- ✅ 使用 Claude Code 生成代码
- ✅ 保存所有优化结果

**预计时间**：5-10 分钟

---

### 方式2：手动SSH操作（更灵活）

#### 步骤1：连接服务器

```bash
ssh root@8.215.63.182
# 密码: <redacted>
```

#### 步骤2：安装Hermes（如果未安装）

```bash
# 检查是否已安装
which hermes

# 如果未安装，执行安装
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

#### 步骤3：配置Claude Code API

```bash
export ANTHROPIC_API_KEY="your_claude_api_key_here"
export CLAUDE_CODE_MODEL="claude-sonnet-4.5"
```

#### 步骤4：使用Agent优化项目

```bash
# 示例1：需求分析
hermes skill requirement-analyst --task "分析 Agent Platform 项目的优化需求，识别性能瓶颈和安全隐患"

# 示例2：架构设计
hermes skill tech-architect --task "设计 Agent Platform 的架构优化方案，包括微服务、数据库、部署架构"

# 示例3：代码优化（使用Claude Code）
hermes skill backend-developer --task "优化 Go Gateway 的性能，使用 Claude Code 生成优化后的代码"

# 示例4：前端优化
hermes skill frontend-developer --task "优化 React 前端性能，使用 Claude Code 生成优化代码"

# 示例5：编写测试
hermes skill unit-tester --task "为 Agent Platform 编写完整的测试用例，使用 Claude Code 生成测试代码"
```

---

## 🤖 可用的9个专业Agent

| Agent | 命令示例 |
|-------|---------|
| **需求分析** | `hermes skill requirement-analyst --task "分析项目需求"` |
| **PRD设计** | `hermes skill prd-designer --task "设计产品方案"` |
| **架构设计** | `hermes skill tech-architect --task "设计技术架构"` |
| **UI设计** | `hermes skill ui-designer --task "设计用户界面"` |
| **前端开发** | `hermes skill frontend-developer --task "优化前端代码"` |
| **后端开发** | `hermes skill backend-developer --task "优化后端代码"` |
| **单元测试** | `hermes skill unit-tester --task "编写测试用例"` |
| **UAT测试** | `hermes skill uat-tester --task "设计验收测试"` |
| **版本管理** | `hermes skill version-manager --task "制定发布计划"` |

---

## 📊 优化流程

```
1. 连接服务器
   ↓
2. 检查 Hermes 环境
   ↓
3. 配置 Claude Code API
   ↓
4. Agent 1-9 依次执行
   ├── 需求分析 (10-20秒)
   ├── PRD设计 (15-30秒)
   ├── 架构设计 (20-40秒)
   ├── 前端优化 (30-60秒)
   ├── 后端优化 (30-60秒)
   ├── 数据库优化 (20-40秒)
   ├── 测试编写 (20-40秒)
   ├── UAT设计 (15-30秒)
   └── 发布计划 (10-20秒)
   ↓
5. 生成优化报告
   ↓
6. 应用优化到项目
```

---

## 📁 输出结果

所有优化结果保存在：`C:\Projects\agent-platform\agent_outputs\`

```
agent_outputs/
├── requirement_analysis.md      # 需求分析报告
├── prd_design.md               # PRD设计文档
├── architecture_design.md      # 架构设计文档
├── frontend_optimization.md    # 前端优化方案
├── backend_optimization.md     # 后端优化方案
├── database_optimization.md    # 数据库优化方案
├── test_plan.md                # 测试计划
├── uat_plan.md                 # UAT测试方案
├── release_plan.md             # 发布计划
└── OPTIMIZATION_REPORT.md      # 最终汇总报告
```

---

## 💡 使用技巧

### 1. 单独优化某个模块

```bash
# 只优化认证模块
hermes skill backend-developer --task "优化 authentication 模块，使用Claude Code生成优化代码"

# 只优化前端性能
hermes skill frontend-developer --task "优化前端性能，减少加载时间"

# 只编写某个功能的测试
hermes skill unit-tester --task "为 chat 功能编写单元测试"
```

### 2. 批量优化多个模块

```bash
# 创建批量优化脚本
cat > batch_optimize.sh << 'EOF'
modules=("auth" "chat" "tools" "skills")
for module in "${modules[@]}"; do
    hermes skill backend-developer --task "优化 $module 模块，使用Claude Code生成优化代码"
done
EOF

chmod +x batch_optimize.sh
./batch_optimize.sh
```

### 3. 查看优化结果

```bash
# 查看某个Agent的输出
cat /tmp/requirement_analysis.md

# 查看所有输出
ls -lh /tmp/*.md
```

---

## ⚠️ 重要提示

### API密钥安全

```bash
# 方式1：环境变量（推荐）
export ANTHROPIC_API_KEY="sk-ant-..."

# 方式2：配置文件
echo "ANTHROPIC_API_KEY=sk-ant-..." >> ~/.bashrc

# 方式3：使用密钥管理服务
# 生产环境推荐使用 HashiCorp Vault 或 AWS Secrets Manager
```

### 验证优化结果

```bash
# 1. 检查生成的代码质量
hermes skill backend-developer --task "审查生成的优化代码质量"

# 2. 运行测试
cd /root/projects/agent-platform
go test ./...
pytest agent/tests/

# 3. 性能测试
# 使用 k6 或 locust 进行压力测试
```

---

## 🎯 预期效果

### 代码质量提升
- ✅ 性能提升 20-50%
- ✅ 代码可读性提高
- ✅ 测试覆盖率 > 80%

### 架构优化
- ✅ 微服务架构清晰
- ✅ 数据库查询优化
- ✅ 缓存策略完善

### 安全加固
- ✅ 安全漏洞修复
- ✅ 认证授权完善
- ✅ 数据保护加强

---

## 🔧 故障排查

### 问题1：无法连接服务器

```bash
# 检查网络连通性
ping 8.215.63.182

# 检查SSH端口
telnet 8.215.63.182 22

# 尝试连接
ssh -v root@8.215.63.182
```

### 问题2：Hermes安装失败

```bash
# 手动安装依赖
sudo apt-get update
sudo apt-get install -y nodejs npm python3 python3-pip

# 重新安装Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### 问题3：Agent调用超时

```bash
# 增加超时时间
export HERMES_TIMEOUT=300  # 5分钟

# 查看日志
tail -f ~/.hermes/logs/hermes.log
```

---

## 📚 相关文档

- **详细指南**: `HOW_TO_USE_MULTIAGENT.md`
- **快速启动**: `QUICK_START_MULTIAGENT.md`
- **Hermes文档**: https://hermes-agent.nousresearch.com/docs/
- **Claude Code**: https://docs.anthropic.com/

---

## 📝 总结

✅ **自动化脚本已准备**：`optimize_with_server_multiagent.py`  
✅ **服务器信息已配置**：8.215.63.182, root/<redacted>  
✅ **9个Agent已就绪**：需求分析到发布管理全流程  
✅ **输出目录已创建**：`agent_outputs/`  

**立即开始**：
```powershell
cd C:\Projects\agent-platform
python optimize_with_server_multiagent.py
```

---

**创建时间**: 2026-05-11 16:35 GMT+8  
**状态**: 准备就绪 ✅
