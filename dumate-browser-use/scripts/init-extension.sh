# init-extension.sh — Extension 模式初始化入口
# 流程（两阶段）：
#   Decide  : 查询 relay 状态 → decide_mode 得到决策
#   Execute : 根据决策写状态 / 输出提示

if ! command -v playwright-cli &>/dev/null; then
  npm install -g @playwright/cli@latest --registry https://registry.npmmirror.com -q 2>/dev/null
fi

_SKILL_DIR="${_SKILL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_LIB_DIR="${_SKILL_DIR}/scripts/lib"

. "${_LIB_DIR}/env.sh"
. "${_LIB_DIR}/log.sh"
. "${_LIB_DIR}/state.sh"
. "${_LIB_DIR}/relay-api.sh"
. "${_LIB_DIR}/decision.sh"
. "${_LIB_DIR}/prompts.sh"
. "${_LIB_DIR}/pw-cli.sh"

_diag_session_start "init-extension"

# ─── Decide 阶段 ─────────────────────────────────────────────
_enabled=$(relay_get_enable_status)
_diag "DECIDE_STEP1 | ${_RELAY_LAST_URL} | ${_RELAY_LAST_RAW} | enabled=${_enabled}"

_connected=""
if decision_need_status "$_enabled"; then
  _connected=$(relay_get_connected_status)
  _diag "DECIDE_STEP2 | ${_RELAY_LAST_URL} | ${_RELAY_LAST_RAW} | connected=${_connected}"
fi

_notice=""
if decision_need_notice "$_enabled" "$_connected"; then
  _notice=$(relay_get_notice_status)
  _diag "DECIDE_STEP3 | ${_RELAY_LAST_URL} | ${_RELAY_LAST_RAW} | notice=${_notice}"
fi

_decision=$(decide_mode "$_enabled" "$_connected" "$_notice")
_diag "DECISION | enabled=${_enabled} connected=${_connected} notice=${_notice} => ${_decision}"

# ─── Execute 阶段 ────────────────────────────────────────────
case "$_decision" in
  extension)
    state_set_extension_mode "$_CONN_ID"
    _BROWSER_MODE="extension"
    echo "Extension connected ✓"
    echo "Extension mode ready (connId: ${_CONN_ID})"
    _diag "EXECUTE | mode=extension | connId=${_CONN_ID}"
    ;;
  mode_prompt:disabled)
    state_set_pending_mode
    _BROWSER_MODE="pending"
    prompt_mode "disabled"
    _diag "EXECUTE | mode=pending | reason=disabled"
    ;;
  mode_prompt:declined)
    state_set_pending_mode
    _BROWSER_MODE="pending"
    prompt_mode "declined"
    _diag "EXECUTE | mode=pending | reason=declined"
    ;;
  extension_prompt)
    state_set_pending_mode
    _BROWSER_MODE="pending"
    prompt_extension "not_connected"
    prompt_mode "extension_unavailable"
    _diag "EXECUTE | mode=pending | reason=not_connected | fallback=mode_prompt"
    ;;
esac
