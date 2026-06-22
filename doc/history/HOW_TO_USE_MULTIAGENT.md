# 使用服务器端多Agent系统优化项目

## 📋 说明

通过服务器端（8.215.63.182）的 **Hermes CLI** 调用 **Claude Code**，使用 **9个专业Agent** 协作优化 Agent Platform 项目。

---

## 🏗️ 架构

```
本地项目 (C:\Projects\agent-platform)
         ↓ (SSH)
服务器 (8.215.63.182)
    ├── Hermes CLI
    ├── Claude Code API
    └── 9个专业Agent
        ├── 需求分析Agent
        ├── PRD设计Agent
        ├── 技术架构师Agent
        ├── UI设计Agent
        ├── 前端开发Agent
        ├── 后端开发Agent
        ├── 单元测试Agent
        ├── UAT测试Agent
        └── 版本管理Agent
         ↓
   优化报告和代码
         ↓
    同步回本地
```

---

## 🚀 快速使用

### 方式1：Python脚本（推荐）

```powershell
# 在本地运行
cd C:\Projects\agent-platform
python optimize_with_server_multiagent.py
```

**脚本会自动**:
1. ✅ 连接服务器
2. ✅ 检查/安装Hermes
3. ✅ 调用9个Agent
4. ✅ 使用Claude Code生成代码
5. ✅ 保存优化报告

### 方式2：手动SSH操作

```bash
# 1. 连接服务器
ssh root@8.215.63.182
# 密码: <redacted>

# 2. 安装Hermes（如果未安装）
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 3. 配置Claude Code API
export ANTHROPIC_API_KEY="your_api_key_here"

# 4. 使用Agent优化
hermes skill requirement-analyst --task "分析项目优化需求"
hermes skill prd-designer --task "设计优化方案"
hermes skill tech-architect --task "设计技术架构"
hermes skill frontend-developer --task "优化前端代码"
hermes skill backend-developer --task "优化后端代码"
hermes skill unit-tester --task "编写测试"
hermes skill uat-tester --task "设计UAT测试"
hermes skill version-manager --task "制定发布计划"
```

---

## 🤖 9个专业Agent的职责

| Agent | 职责 | 输出 |
|-------|------|------|
| **需求分析** | 分析项目现状、识别优化点 | 需求分析报告 |
| **PRD设计** | 设计优化方案、制定计划 | PRD文档 |
| **技术架构师** | 架构设计、技术选型 | 架构设计文档 |
| **UI设计** | 界面设计、交互优化 | UI设计方案 |
| **前端开发** | 前端代码优化 | 优化后的前端代码 |
| **后端开发** | 后端代码优化 | 优化后的后端代码 |
| **单元测试** | 编写测试用例 | 测试代码 |
| **UAT测试** | 设计验收测试 | 测试方案 |
| **版本管理** | 制定发布计划 | CHANGELOG |

---

## 📁 输出文件

所有优化结果保存在：`C:\Projects\agent-platform\agent_outputs\`

```
agent_outputs/
├── requirement_analysis.md      # 需求分析
├── prd_design.md               # PRD设计
├── architecture_design.md      # 架构设计
├── frontend_optimization.md    # 前端优化
├── backend_optimization.md     # 后端优化
├── database_optimization.md    # 数据库优化
├── test_plan.md                # 测试计划
├── uat_plan.md                 # UAT计划
├── release_plan.md             # 发布计划
└── OPTIMIZATION_REPORT.md      # 最终报告
```

---

## ⚙️ 配置要求

### 服务器端

- **操作系统**: Linux (Ubuntu/CentOS)
- **Hermes**: 最新版本
- **Claude Code API Key**: `ANTHROPIC_API_KEY`

### 本地端

- **Python**: >= 3.8
- **paramiko**: SSH库
- **网络**: 能连接到服务器

---

## 🔧 高级用法

### 单独调用某个Agent

```python
# Python代码示例
import paramiko

client = paramiko.SSHClient()
client.connect("8.215.63.182", username="root", password="<redacted>")

# 调用前端优化Agent
stdin, stdout, stderr = client.exec_command(
    "hermes skill frontend-developer --task '优化React组件性能'"
)

print(stdout.read().decode())

client.close()
```

### 批量优化多个模块

```bash
# 在服务器上运行
for module in "auth" "chat" "tools"; do
    hermes skill backend-developer --task "优化 $module 模块"
done
```

---

## 📊 工作流程

```
1. 连接服务器
   ↓
2. 检查Hermes环境
   ↓
3. Agent 1-9 依次执行
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
4. 生成汇总报告
   ↓
5. 同步结果到本地
```

---

## ⚠️ 注意事项

1. **API密钥安全**
   - 不要在代码中硬编码API密钥
   - 使用环境变量: `export ANTHROPIC_API_KEY="xxx"`

2. **网络连接**
   - 确保能SSH连接到服务器
   - 端口22需要开放

3. **执行时间**
   - 完整优化约需5-10分钟
   - 可以单独调用某个Agent

4. **结果验证**
   - 优化后的代码需要人工审核
   - 运行测试验证功能

---

## 🎯 预期效果

### 代码质量
- ✅ 性能提升 20-50%
- ✅ 代码可维护性提高
- ✅ 测试覆盖率 > 80%

### 架构优化
- ✅ 微服务架构清晰
- ✅ 数据库性能提升
- ✅ 缓存命中率提高

### 安全性
- ✅ 安全漏洞修复
- ✅ 认证授权完善
- ✅ 数据保护加强

---

## 📞 故障排查

### 问题1: 无法连接服务器
```bash
# 检查网络
ping 8.215.63.182

# 检查SSH端口
telnet 8.215.63.182 22
```

### 问题2: Hermes未安装
```bash
# 手动安装
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

### 问题3: Agent调用失败
```bash
# 检查Hermes状态
hermes status

# 查看日志
tail -f ~/.hermes/logs/hermes.log
```

---

## 📚 参考文档

- **Hermes文档**: https://hermes-agent.nousresearch.com/docs/
- **Claude Code**: https://docs.anthropic.com/claude/docs/claude-code
- **项目路径**: `C:\Projects\agent-platform`

---

**创建时间**: 2026-05-11  
**服务器**: 8.215.63.182  
**工具**: Hermes CLI + Claude Code
