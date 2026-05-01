# lib/log.sh — 诊断日志模块
# 依赖：env.sh (提供 _LOG_DIR)
# 对外暴露：
#   变量  _DIAG_LOG
#   函数  _diag  _diag_session_start

if [ -n "$_LIB_LOG_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_LOG_LOADED=1

_DIAG_LOG="${_LOG_DIR:-/tmp}/browser-use.log"

_diag() {
  echo "[DIAG $(date '+%H:%M:%S.%3N' 2>/dev/null || date '+%H:%M:%S')] $*" | tee -a "$_DIAG_LOG"
}

_diag_session_start() {
  local tag="${1:-session}"
  _diag "${tag} sourced | SID=${SANDBOX_SESSION_ID:-default} | PID=$$ | PWD=$(pwd) | epoch=$(date +%s)"
}
