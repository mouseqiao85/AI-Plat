# session-header.sh — 每次 Bash 调用开头 source
# 恢复上次 init 写入的状态，暴露 playwright-cli / _pw_snap / _pw_* 等函数

_SKILL_DIR="${_SKILL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_LIB_DIR="${_SKILL_DIR}/scripts/lib"

. "${_LIB_DIR}/env.sh"
. "${_LIB_DIR}/log.sh"
. "${_LIB_DIR}/state.sh"
. "${_LIB_DIR}/relay-api.sh"
. "${_LIB_DIR}/prompts.sh"
. "${_LIB_DIR}/pw-cli.sh"

_diag_session_start "session-header"

state_ensure_defaults

_BROWSER_MODE="$(state_get_mode)"
[ -z "$_BROWSER_MODE" ] && _BROWSER_MODE="cdp"
_CONN_ID="$(state_get_connid)"
_PW_SESSION="${_CONN_ID:-${SANDBOX_SESSION_ID:-default}}"

# pending 状态：等待 Agent 选择 CDP 模式
if [ "$_BROWSER_MODE" = "pending" ]; then
  echo "[ERROR] Browser mode pending - LLM has not selected headed or headless mode yet." >&2
  prompt_mode "pending" >&2
  return 1 2>/dev/null || exit 1
fi

# Extension 模式：确保 config.json 含 connId
if [ "$_BROWSER_MODE" = "extension" ] && [ -n "$_CONN_ID" ]; then
  state_ensure_extension_config "$_CONN_ID"
fi

# daemon 状态诊断（仅 Extension）
if [ "$_BROWSER_MODE" = "extension" ]; then
  _diag_daemon_pid=$(ps aux 2>/dev/null | grep "cli-daemon/program.js" | grep "${_PW_SESSION}" | grep -v grep | awk '{print $2}' | head -1)
  if [ -n "$_diag_daemon_pid" ]; then
    _diag "DAEMON_CHECK | session=${_PW_SESSION} | pid=${_diag_daemon_pid} | alive=$(kill -0 "$_diag_daemon_pid" 2>/dev/null && echo Y || echo N)"
  else
    _diag "DAEMON_CHECK | session=${_PW_SESSION} | no daemon process found"
  fi
  unset _diag_daemon_pid
fi
