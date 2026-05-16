#!/bin/bash

# ============================================
# 在服务器上安装 Hermes 和配置多Agent系统
# ============================================

set -e

echo "========================================"
echo "  安装 Hermes Agent"
echo "========================================"
echo ""

# 检查是否已安装
if command -v hermes &> /dev/null; then
    echo "[OK] Hermes 已安装"
    hermes --version
else
    echo "[i] 正在安装 Hermes..."
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

    # 重新加载环境
    source ~/.bashrc

    echo "[OK] Hermes 安装完成"
fi

echo ""
echo "========================================"
echo "  配置 Claude Code"
echo "========================================"
echo ""

# 配置 Claude Code API
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your_api_key_here}"
export CLAUDE_CODE_MODEL="${CLAUDE_CODE_MODEL:-claude-sonnet-4.5}"

echo "[OK] Claude Code 环境变量已设置"

echo ""
echo "========================================"
echo "  安装完成"
echo "========================================"
echo ""
echo "下一步:"
echo "  1. 运行: hermes setup"
echo "  2. 测试: hermes --help"
echo "  3. 使用Agent: hermes skill requirement-analyst --task '分析项目'"
