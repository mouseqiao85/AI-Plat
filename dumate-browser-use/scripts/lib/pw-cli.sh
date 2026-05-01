# lib/pw-cli.sh — playwright-cli 包装 + 辅助函数（Windows / Git Bash）
# 依赖：env.sh, log.sh, relay-api.sh
# 通过 _BROWSER_MODE 变量分支（extension / cdp）

if [ -n "$_LIB_PW_CLI_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_PW_CLI_LOADED=1

playwright-cli() {
  local _cmd_epoch_start; _cmd_epoch_start=$(date +%s)

  # daemon 状态（Windows: ps -W 显示 Windows 进程，ps -ef 兼容 MSYS）
  local _daemon_pid=""
  _daemon_pid=$(ps -ef 2>/dev/null | grep "cli-daemon/program.js" | grep "${_PW_SESSION}" | grep -v grep | awk '{print $2}' | head -1)
  if [ -z "$_daemon_pid" ]; then
    # fallback: ps -W 只显示 Windows 进程，字段为 WINPID
    _daemon_pid=$(ps -W 2>/dev/null | grep "node" | grep -v grep | awk '{print $1}' | head -1)
  fi
  local _daemon_status="unknown"
  if [ -n "$_daemon_pid" ]; then
    kill -0 "$_daemon_pid" 2>/dev/null && _daemon_status="alive(${_daemon_pid})" || _daemon_status="DEAD(${_daemon_pid})"
  fi

  # 网络端点健康
  local _relay_check="" _cdp_check=""
  if [ "$_BROWSER_MODE" = "extension" ]; then
    local _http; _http=$(relay_http_base)
    _relay_check=$(curl -s --max-time 1 "${_http}/extension/status" 2>/dev/null || echo "unreachable")
  elif [ "$_BROWSER_MODE" = "cdp" ]; then
    local _cdp="${BROWSER_USE_CDP_URL:-http://127.0.0.1:19222}"
    _cdp_check=$(curl -s --max-time 1 "${_cdp}/json/version" 2>/dev/null | head -1 || echo "unreachable")
    if [ -z "$_cdp_check" ] || [ "$_cdp_check" = "unreachable" ]; then
      _cdp_check="unreachable(${_cdp})"
    else
      _cdp_check="connected(${_cdp})"
    fi
  fi

  # 构建日志用完整命令
  local _full_cmd=""
  if [ "$_BROWSER_MODE" = "extension" ]; then
    if [ "$1" = "open" ] || [ "$1" = "attach" ]; then
      _full_cmd="playwright-cli --session=${_PW_SESSION} --config ${_DATA_DIR}/config.json $*"
    else
      _full_cmd="playwright-cli --session=${_PW_SESSION} $*"
    fi
  else
    if [ "$1" = "open" ] || [ "$1" = "attach" ]; then
      _full_cmd="playwright-cli --config ${_DATA_DIR}/config.json $*"
    else
      _full_cmd="playwright-cli $*"
    fi
  fi
  _diag "CMD_START | ${_full_cmd} | mode=${_BROWSER_MODE} | daemon=${_daemon_status} | relay=${_relay_check} | cdp=${_cdp_check}"

  local _rc=0
  local _stderr_file="${_LOG_DIR}/stderr-$$.tmp"
  if [ "$_BROWSER_MODE" = "extension" ]; then
    if [ "$1" = "open" ] || [ "$1" = "attach" ]; then
      command "$_PW_CLI_BIN" --session="${_PW_SESSION}" --config "${_DATA_DIR}/config.json" "$@" 2>"$_stderr_file" || _rc=$?
    else
      command "$_PW_CLI_BIN" --session="${_PW_SESSION}" "$@" 2>"$_stderr_file" || _rc=$?
    fi
  else
    if [ "$1" = "open" ] || [ "$1" = "attach" ]; then
      command "$_PW_CLI_BIN" --config "${_DATA_DIR}/config.json" "$@" 2>"$_stderr_file" || _rc=$?
    else
      command "$_PW_CLI_BIN" "$@" 2>"$_stderr_file" || _rc=$?
    fi
  fi

  local _cmd_epoch_end; _cmd_epoch_end=$(date +%s)
  local _cmd_elapsed=$(( _cmd_epoch_end - _cmd_epoch_start ))
  if [ $_rc -ne 0 ]; then
    _diag "CMD_FAIL  | ${_full_cmd} | rc=$_rc | ${_cmd_elapsed}s"
    if [ -s "$_stderr_file" ]; then
      local _stderr_content
      _stderr_content=$(cat "$_stderr_file" | head -5 | tr '\n' ' ' | sed 's/  */ /g')
      _diag "CMD_ERR   | ${_full_cmd} | stderr: ${_stderr_content}"
    fi
  else
    _diag "CMD_OK    | ${_full_cmd} | ${_cmd_elapsed}s"
  fi
  rm -f "$_stderr_file" 2>/dev/null || true

  # close 命令的善后
  if [ "$1" = "close" ] && [ "$_BROWSER_MODE" = "extension" ]; then
    local _http; _http=$(relay_http_base)
    curl -s --max-time 5 -X POST "${_http}/session/close?connId=${_CONN_ID}" 2>/dev/null || true
    _diag "EXT_CLOSE | session/close sent to relay for connId=${_CONN_ID}"
  fi
  if [ "$1" = "close" ] && [ "$_BROWSER_MODE" = "cdp" ]; then
    curl -s --max-time 30 -X POST "${DUMATE_HOST_URL}/browser/shutdown" > /dev/null 2>&1 || true
    echo "Chrome shutdown complete"
  fi
  return $_rc
}

# 读取最新 snapshot .yml
_pw_snap() {
  local f
  f=$(ls -t "${_DUMATE_OUT}/"*.yml 2>/dev/null | head -1)
  if [ -z "$f" ]; then
    echo "[ERROR] No snapshot .yml found. Run 'playwright-cli snapshot' first." >&2
    return 1
  fi
  cat "$f"
}

# 登录/验证码等待（仅输出提示，由 Agent 暂停）
_pw_wait_login() {
  echo ""
  echo "[LOGIN_REQUIRED] 检测到页面需要登录/验证，自动化已暂停。"
  echo "[LOGIN_REQUIRED] 请用户在浏览器中完成登录/验证操作，完成后回复"已完成"。"
  echo "[LOGIN_REQUIRED] 等待用户操作中...（禁止继续任何自动化操作）"
  echo ""
}

# CDP 模式遇阻时检查是否可切换 Extension
_pw_check_extension_prompt() {
  [ "$_BROWSER_MODE" != "cdp" ] && return 0

  local enabled connected notice
  enabled=$(relay_get_enable_status)
  _diag "EXT_PROMPT_ENABLE | ${_RELAY_LAST_URL} | ${_RELAY_LAST_RAW}"
  [ "$enabled" = "false" ] && { _diag "EXT_PROMPT_CHECK | enabled=false | skip"; return 0; }

  connected=$(relay_get_connected_status)
  _diag "EXT_PROMPT_STATUS | ${_RELAY_LAST_URL} | ${_RELAY_LAST_RAW}"
  [ "$connected" = "true" ] && { _diag "EXT_PROMPT_CHECK | connected=true | skip"; return 0; }

  notice=$(relay_get_notice_status)
  _diag "EXT_PROMPT_NOTICE | ${_RELAY_LAST_URL} | ${_RELAY_LAST_RAW}"
  [ "$notice" = "false" ] && { _diag "EXT_PROMPT_CHECK | notice=false | skip"; return 0; }

  _diag "EXT_PROMPT_CHECK | show_prompt"
  prompt_extension "cdp_blocked"
  return 0
}

# 导航守卫
_pw_open() {
  local url="$1"
  if [ -z "$url" ]; then
    echo "[ERROR] _pw_open: url is required" >&2
    return 1
  fi
  local before_url=""
  before_url=$(playwright-cli eval "window.location.href" 2>/dev/null | tr -d '"' || true)
  echo "[NAVIGATE] $url (current: ${before_url:-unknown})"

  playwright-cli open "$url"
  local nav_rc=$?
  if [ $nav_rc -ne 0 ]; then
    echo "[ERROR] Navigation failed: playwright-cli open $url" >&2
    return $nav_rc
  fi

  sleep 1
  local after_url=""
  after_url=$(playwright-cli eval "window.location.href" 2>/dev/null | tr -d '"' || true)
  echo "[NAVIGATE] Result: ${after_url:-unknown}"

  playwright-cli snapshot && _pw_snap
  return 0
}