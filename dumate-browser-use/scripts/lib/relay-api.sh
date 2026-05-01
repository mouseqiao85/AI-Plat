# lib/relay-api.sh — Relay HTTP API 封装
# 所有返回值统一归一化为 "true" / "false" / ""（失败/不可达）。
# 对外函数：
#   relay_http_base           返回 Relay HTTP base，如 http://127.0.0.1:19228
#   relay_get_enable_status   → "true" | "false" | ""
#   relay_get_connected_status→ "true" | "false" | ""
#   relay_get_notice_status   → "true" | "false" | ""
#   relay_post_notice_ttl     POST /extension/notice/ttl

if [ -n "$_LIB_RELAY_API_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_RELAY_API_LOADED=1

relay_http_base() {
  local base="${BROWSER_USE_RELAY_URL:-ws://127.0.0.1:19228/cdp}"
  base="${base%%/cdp*}"
  echo "${base/ws:/http:}"
}

# 内部：从响应中解析布尔字段
# $1: json 字符串  $2: 字段名
_relay_parse_bool() {
  local resp="$1" field="$2"
  if echo "$resp" | grep -q "\"${field}\":\s*true"; then
    echo "true"
  elif echo "$resp" | grep -q "\"${field}\":\s*false"; then
    echo "false"
  else
    echo ""
  fi
}

relay_get_enable_status() {
  local base resp
  base=$(relay_http_base)
  resp=$(curl -s --max-time 2 "${base}/extension/enable_status" 2>/dev/null || echo '')
  _RELAY_LAST_RAW="$resp"
  _RELAY_LAST_URL="${base}/extension/enable_status"
  _relay_parse_bool "$resp" "enabled"
}

relay_get_connected_status() {
  local base resp
  base=$(relay_http_base)
  resp=$(curl -s --max-time 2 "${base}/extension/status" 2>/dev/null || echo '')
  _RELAY_LAST_RAW="$resp"
  _RELAY_LAST_URL="${base}/extension/status"
  _relay_parse_bool "$resp" "connected"
}

relay_get_notice_status() {
  local base resp
  base=$(relay_http_base)
  resp=$(curl -s --max-time 2 "${base}/extension/notice" 2>/dev/null || echo '')
  _RELAY_LAST_RAW="$resp"
  _RELAY_LAST_URL="${base}/extension/notice"
  _relay_parse_bool "$resp" "notice"
}

# $1: ttl 值（如 20260423）
relay_post_notice_ttl() {
  local ttl="$1" base
  base=$(relay_http_base)
  curl -s --max-time 2 -X POST -H 'Content-Type: application/json' \
    -d "{\"ttl\": \"${ttl}\"}" "${base}/extension/notice/ttl" 2>/dev/null || true
}
