# lib/state.sh — 状态读写模块
# 依赖：env.sh (提供 _DATA_DIR)
# 统一用 config.json 管理 browser / mode / connId

if [ -n "$_LIB_STATE_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_STATE_LOADED=1

_STATE_USER_AGENT='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
_STATE_FILE="${_DATA_DIR}/config.json"

# 内部：写入完整 config.json
_state_write() {
  local endpoint="$1" mode="$2" conn="$3"
  mkdir -p "$_DATA_DIR"
  cat > "$_STATE_FILE" <<INEOF
{"browser":{"cdpEndpoint":"${endpoint}","isolated":false,"userAgent":"${_STATE_USER_AGENT}"},"mode":"${mode}","connId":"${conn}"}
INEOF
}

# 读取字段（无 jq 时用 grep）
state_get_mode() {
  [ -f "$_STATE_FILE" ] || { echo ""; return; }
  if command -v jq &>/dev/null; then
    jq -r '.mode // empty' "$_STATE_FILE" 2>/dev/null
  else
    grep -o '"mode":"[^"]*"' "$_STATE_FILE" 2>/dev/null | sed 's/"mode":"//;s/"$//'
  fi
}

state_get_connid() {
  [ -f "$_STATE_FILE" ] || { echo ""; return; }
  if command -v jq &>/dev/null; then
    jq -r '.connId // empty' "$_STATE_FILE" 2>/dev/null
  else
    grep -o '"connId":"[^"]*"' "$_STATE_FILE" 2>/dev/null | sed 's/"connId":"//;s/"$//'
  fi
}

state_get_endpoint() {
  [ -f "$_STATE_FILE" ] || { echo ""; return; }
  if command -v jq &>/dev/null; then
    jq -r '.browser.cdpEndpoint // empty' "$_STATE_FILE" 2>/dev/null
  else
    grep -o '"cdpEndpoint":"[^"]*"' "$_STATE_FILE" 2>/dev/null | sed 's/"cdpEndpoint":"//;s/"$//'
  fi
}

# Extension 模式：设置 mode + connId + endpoint
# $1: connId
state_set_extension_mode() {
  local conn="$1"
  local relay="${BROWSER_USE_RELAY_URL:-ws://127.0.0.1:19228/cdp}"
  _state_write "${relay}?connId=${conn}" "extension" "$conn"
}

# CDP 模式：设置 mode + 清空 connId + endpoint
# $1: cdpEndpoint
state_set_cdp_mode() {
  local cdp="$1"
  _state_write "$cdp" "cdp" ""
}

# Pending 模式
state_set_pending_mode() {
  local cdp="${BROWSER_USE_CDP_URL:-http://127.0.0.1:19222}"
  _state_write "$cdp" "pending" ""
}

# 确保默认状态文件存在
state_ensure_defaults() {
  if [ ! -f "$_STATE_FILE" ]; then
    local cdp="${BROWSER_USE_CDP_URL:-http://127.0.0.1:19222}"
    _state_write "$cdp" "cdp" ""
  fi
}

# Extension 模式下确保 endpoint 含 connId
state_ensure_extension_config() {
  local conn="$1"
  [ -z "$conn" ] && return 0
  local current
  current=$(state_get_endpoint)
  if [ -n "$current" ] && ! echo "$current" | grep -q "connId="; then
    local relay="${BROWSER_USE_RELAY_URL:-ws://127.0.0.1:19228/cdp}"
    _state_write "${relay}?connId=${conn}" "extension" "$conn"
  fi
}

state_dump() {
  echo "mode=$(state_get_mode) connId=$(state_get_connid) cfg=$_STATE_FILE"
}