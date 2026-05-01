# Harness - 范围子系统

**版本**：v1.0
**日期**：2026-04-29
**对应文件**：scope.md, permissions.yaml

---

## 一、概述

范围子系统定义 Agent 的能力边界、权限范围和执行约束，确保 Agent 在授权范围内安全运行。

> 约束动作空间，让 Agent 的决策能稳定落到工程动作上，同时让错误动作尽可能被系统拦住。

---

## 二、核心组件

### 2.1 范围定义

| 维度 | 说明 | 示例 |
|------|------|------|
| **功能范围** | Agent 能做什么 | 查询行情、分析数据 |
| **数据范围** | 能访问哪些数据 | 公开数据、用户授权数据 |
| **工具范围** | 能调用哪些工具 | search_stock、get_quote |
| **权限范围** | 操作权限等级 | 只读、读写、管理 |
| **安全范围** | 安全约束 | 禁止执行、需要审批 |

### 2.2 权限配置

```yaml
# permissions.yaml
permissions:
  # 工具权限
  tools:
    search_stock:
      allowed: true
      rate_limit: 100/hour
    
    get_stock_quote:
      allowed: true
      rate_limit: 1000/hour
    
    execute_trade:
      allowed: false  # 禁止交易
      requires_approval: true
    
    delete_data:
      allowed: false
      scope: ["admin"]
  
  # 数据权限
  data:
    public_market_data:
      read: true
      write: false
    
    user_portfolio:
      read: true
      write: false
      requires_consent: true
    
    internal_reports:
      read: false
      scope: ["analyst", "admin"]
  
  # 功能权限
  features:
    basic_query:
      allowed: true
      tiers: ["free", "basic", "pro"]
    
    advanced_analysis:
      allowed: true
      tiers: ["pro"]
    
    api_access:
      allowed: true
      tiers: ["enterprise"]
```

---

## 三、LangGraph 集成

### 3.1 权限检查节点

```python
async def permission_check_node(state: AgentState) -> dict | Command:
    """权限检查节点"""
    
    user_tier = state["user_tier"]
    intent = state["intent"]
    
    # 检查功能权限
    feature_allowed = await permission_manager.check_feature(
        feature=intent,
        tier=user_tier
    )
    
    if not feature_allowed:
        return Command(
            update={
                "error": "权限不足",
                "required_tier": "pro",
                "current_tier": user_tier
            },
            goto="error_handler"
        )
    
    # 检查工具权限
    plan = state.get("plan", [])
    for step in plan:
        tool = step.get("tool")
        tool_allowed = await permission_manager.check_tool(
            tool=tool,
            tier=user_tier
        )
        
        if not tool_allowed:
            step["blocked"] = True
            step["reason"] = f"工具 {tool} 需要更高权限"
    
    return {"plan": plan, "permission_checked": True}
```

### 3.2 范围约束实现

```python
class ScopeManager:
    """范围管理器"""
    
    def __init__(self, config_path: str):
        self.permissions = self._load_permissions(config_path)
    
    async def check_tool(self, tool: str, tier: str) -> bool:
        """检查工具权限"""
        tool_config = self.permissions["tools"].get(tool, {})
        
        if not tool_config.get("allowed", False):
            return False
        
        # 检查等级限制
        allowed_tiers = tool_config.get("tiers", [])
        if allowed_tiers and tier not in allowed_tiers:
            return False
        
        return True
    
    async def check_rate_limit(self, tool: str, user_id: str) -> bool:
        """检查频率限制"""
        tool_config = self.permissions["tools"].get(tool, {})
        limit = tool_config.get("rate_limit", "100/hour")
        
        # 解析限制
        count, period = limit.split("/")
        count = int(count)
        
        # 检查当前使用量
        current_usage = await rate_limiter.get_usage(user_id, tool, period)
        return current_usage < count
    
    async def check_data_access(self, data_type: str, user_id: str) -> dict:
        """检查数据访问权限"""
        data_config = self.permissions["data"].get(data_type, {})
        
        return {
            "read": data_config.get("read", False),
            "write": data_config.get("write", False),
            "requires_consent": data_config.get("requires_consent", False)
        }
```

---

## 四、范围约束升级路径

```
文档管不住 → 升级成代码
   │
   ▼
┌─────────────────┐
│ 1. 文档约束     │ ← scope.md
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ 2. 配置约束     │ ← permissions.yaml
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ 3. 代码约束     │ ← ScopeManager
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ 4. 运行时约束   │ ← LangGraph 节点检查
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ 5. 审计日志     │ ← 操作记录
└─────────────────┘
```

---

## 五、范围定义示例

```markdown
# scope.md

## Agent 能力范围

### 可以做的 ✅
- 查询股票/基金实时行情
- 搜索股票/基金信息
- 获取财务数据
- 搜索财经新闻
- 获取市场概览
- 管理自选股列表

### 不可以做的 ❌
- 执行交易操作
- 修改用户账户信息
- 访问其他用户数据
- 预测股价走势
- 提供买入/卖出建议
- 访问内部未公开数据

## 数据访问范围

### 公开数据
- 市场行情数据
- 公司基本信息
- 公开财务报表
- 新闻资讯

### 用户授权数据
- 自选股列表
- 对话历史
- 用户偏好设置

### 禁止访问
- 交易记录
- 账户余额
- 其他用户信息
- 内部研究报告

## 工具权限

| 工具 | 免费版 | 基础版 | 专业版 | 企业版 |
|------|--------|--------|--------|--------|
| search_stock | ✅ | ✅ | ✅ | ✅ |
| get_quote | ✅ | ✅ | ✅ | ✅ |
| get_financial | ❌ | ✅ | ✅ | ✅ |
| get_news | ✅ | ✅ | ✅ | ✅ |
| advanced_analysis | ❌ | ❌ | ✅ | ✅ |
| api_access | ❌ | ❌ | ❌ | ✅ |
```

---

## 六、最佳实践

### 6.1 权限设计原则

| 原则 | 说明 |
|------|------|
| 最小权限 | 只授予完成任务所需的最小权限 |
| 默认拒绝 | 未明确允许的默认拒绝 |
| 分层授权 | 不同等级不同权限 |
| 动态检查 | 运行时验证权限 |
| 审计追踪 | 所有权限操作记录日志 |

### 6.2 错误处理

```python
class ScopeException(Exception):
    """范围异常"""
    
    def __init__(self, action: str, required: str, current: str):
        self.action = action
        self.required = required
        self.current = current
        super().__init__(
            f"权限不足：{action} 需要 {required}，当前为 {current}"
        )

# 使用
if not await scope_manager.check_tool(tool, user_tier):
    raise ScopeException(
        action=f"使用工具 {tool}",
        required="pro",
        current=user_tier
    )
```