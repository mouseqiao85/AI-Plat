# lib/decision.sh — 决策纯函数模块
# 纯函数：仅处理字符串输入输出，无 HTTP/IO 副作用，可直接单元测试。
#
# 输入契约：三个字段均使用 "true" / "false" / "" 三值：
#   enabled   extension 是否被用户启用（enable_status）
#   connected extension 是否已连接（status）
#   notice    是否应提示安装（notice）
#
# 输出契约（stdout）：以下之一
#   extension              → 使用 Extension 模式
#   mode_prompt:disabled   → enable=false，提示选择 CDP
#   mode_prompt:declined   → notice=false，提示选择 CDP
#   extension_prompt       → 提示安装 Extension + 提供 CDP 选择

if [ -n "$_LIB_DECISION_LOADED" ]; then return 0 2>/dev/null || exit 0; fi
_LIB_DECISION_LOADED=1

# $1 enabled  $2 connected  $3 notice
decide_mode() {
  local enabled="$1" connected="$2" notice="$3"

  # 第 1 步：enable_status
  if [ "$enabled" = "false" ]; then
    echo "mode_prompt:disabled"
    return 0
  fi

  # 第 2 步：connected
  if [ "$connected" = "true" ]; then
    echo "extension"
    return 0
  fi

  # 第 3 步：notice（仅在未连接时）
  if [ "$notice" = "false" ]; then
    echo "mode_prompt:declined"
    return 0
  fi

  # 默认：notice=true 或未知 → 提示安装
  echo "extension_prompt"
}

# 是否需要查询 connected/notice（仅当 enabled != "false"）
decision_need_status() {
  [ "$1" != "false" ]
}

# 是否需要查询 notice（enabled != "false" 且 connected != "true"）
decision_need_notice() {
  [ "$1" != "false" ] && [ "$2" != "true" ]
}
