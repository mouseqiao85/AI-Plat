# init-headed.sh — CDP 模式（显示浏览器窗口）
if ! command -v playwright-cli &>/dev/null; then
  npm install -g @playwright/cli@latest --registry https://registry.npmmirror.com -q 2>/dev/null
fi

_SKILL_DIR="${_SKILL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_LIB_DIR="${_SKILL_DIR}/scripts/lib"

. "${_LIB_DIR}/env.sh"
. "${_LIB_DIR}/log.sh"
. "${_LIB_DIR}/state.sh"
. "${_LIB_DIR}/relay-api.sh"
. "${_LIB_DIR}/pw-cli.sh"
. "${_LIB_DIR}/cdp-launch.sh"

_diag_session_start "init-headed"

cdp_launch_chrome "false" || return 1 2>/dev/null || exit 1
state_set_cdp_mode "$_CDP_ENDPOINT"
_BROWSER_MODE="cdp"
_diag "INIT_OK | mode=cdp | headless=false | cdp=${_CDP_ENDPOINT}"
