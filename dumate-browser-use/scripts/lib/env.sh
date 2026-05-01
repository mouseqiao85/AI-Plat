# lib/env.sh — 环境初始化模块（Windows / Git Bash）
# 负责：skill 目录自定位、daemon/config/log 目录创建、connId 生成
# 对外暴露：
#   变量  _SKILL_DIR _DUMATE_OUT _DATA_DIR _LOG_DIR _CONN_ID _PW_SESSION _PW_CLI_BIN
#   环境  PLAYWRIGHT_DAEMON_SESSION_DIR PLAYWRIGHT_MCP_OUTPUT_DIR

if [ -n "$_LIB_ENV_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_ENV_LOADED=1

# ── Self-locate skill directory (lib/ 的上两级) ──
if [ -z "$_SKILL_DIR" ]; then
  _SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

# daemon-sessions 必须在短路径（Unix Socket 路径长度限制 108 字符）
# Windows: 优先使用 $TEMP，fallback 到 /tmp
export PLAYWRIGHT_DAEMON_SESSION_DIR="${TEMP:-/tmp}/playwright-cli-${SANDBOX_SESSION_ID:-session}/daemon-sessions"
mkdir -p "$PLAYWRIGHT_DAEMON_SESSION_DIR"

_DUMATE_OUT="$(pwd)/.dumate/${SANDBOX_SESSION_ID:-default}"
mkdir -p "$_DUMATE_OUT"

# 统一的会话状态目录：config.json 存放 browser / mode / connId
_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dumate-browser/${SANDBOX_SESSION_ID:-default}"
mkdir -p "$_DATA_DIR"

# 诊断日志目录（全局共享，不按 SID 分目录）
_LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/logs/dialog"
mkdir -p "$_LOG_DIR"

export PLAYWRIGHT_MCP_OUTPUT_DIR="${_DUMATE_OUT}"
_PW_CLI_BIN="$(command -v playwright-cli)"

# ── 基于 SANDBOX_SESSION_ID 生成稳定 connId ──
_CONN_ID="session-${SANDBOX_SESSION_ID:-default}"
_PW_SESSION="${_CONN_ID}"
