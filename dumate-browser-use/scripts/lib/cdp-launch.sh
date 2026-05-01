# lib/cdp-launch.sh — Chrome CDP 启动模块
# 依赖：env.sh, log.sh
# 提供 cdp_launch_chrome 统一处理 headed/headless 启动。

if [ -n "$_LIB_CDP_LAUNCH_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_CDP_LAUNCH_LOADED=1

# $1: headless ("true" | "false")
# 成功：导出 _CDP_ENDPOINT 并返回 0
# 失败：_diag LAUNCH_FAIL 并返回 1
cdp_launch_chrome() {
  local headless="${1:-true}"
  _CDP_ENDPOINT="${BROWSER_USE_CDP_URL:-http://127.0.0.1:19222}"

  # 先关闭旧实例，避免端口冲突
  curl -s --max-time 30 -X POST "${DUMATE_HOST_URL}/browser/shutdown" > /dev/null 2>&1 || true

  _diag "LAUNCH | mode=$([ "$headless" = "true" ] && echo headless || echo headed) | cdp=${_CDP_ENDPOINT} | host=${DUMATE_HOST_URL}"
  local _R
  _R=$(curl -s --max-time 60 -X POST "${DUMATE_HOST_URL}/browser/launch" \
    -H "Content-Type: application/json" \
    -d "{\"cdpUrl\":\"${_CDP_ENDPOINT}\",\"headless\":${headless}}")
  _diag "LAUNCH_RESP | $_R"

  if echo "$_R" | grep -q '"success":true'; then
    _diag "LAUNCH_OK | headless=${headless}"
    return 0
  else
    _diag "LAUNCH_FAIL | $_R"
    return 1
  fi
}
