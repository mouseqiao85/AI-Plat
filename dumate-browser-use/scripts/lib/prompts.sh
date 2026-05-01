# lib/prompts.sh — 提示输出模块
# 统一输出 [MODE_PROMPT] / [EXTENSION_PROMPT] 文本，供 Agent 读取。
# 依赖：relay-api.sh (relay_http_base)

if [ -n "$_LIB_PROMPTS_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_PROMPTS_LOADED=1

# $1: reason  (disabled | declined | not_connected | pending)
# 原因仅写入诊断日志，不输出到 stdout，避免 Agent 将内部状态复述给用户。
prompt_mode() {
  local reason="$1"
  _diag "PROMPT_MODE | reason=${reason}"
  echo ""
  echo "[MODE_PROMPT] 需要选择 CDP 模式。"
  echo "[MODE_PROMPT] 请根据任务类型选择："
  echo "[MODE_PROMPT]   - headed:   source \${_SKILL_DIR}/scripts/init-headed.sh   （需要登录/验证码、调试网页、用户要求看浏览器）"
  echo "[MODE_PROMPT]   - headless: source \${_SKILL_DIR}/scripts/init-headless.sh （纯信息抓取、批量任务、无需人工干预）"
  echo "[MODE_PROMPT] 默认推荐 headless，除非任务明确需要看到浏览器窗口。"
  echo "[MODE_PROMPT] 注意：不要向用户解释 Extension 模式不可用的具体原因（属于内部状态，已记入后台日志）。"
  echo ""
}

# $1: reason (not_connected | cdp_blocked)
# 卡片 UI 自描述，无需文本提示。只输出标记触发卡片创建。
prompt_extension() {
  local reason="$1"
  _diag "PROMPT_EXTENSION | reason=${reason}"
  echo "[EXTENSION_CARD_MARK]"
}
