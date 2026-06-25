#!/usr/bin/env bash
# fin-assistant 一键启动脚本 (Linux/macOS/Git Bash)
# 同时启动后端 (uvicorn :8000) 和前端 (vite :5173)

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  fin-assistant 启动中...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# ── Step 1: 检查 .env ──────────────────────────────────────────────────────
ENV_FILE="$BACKEND_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${YELLOW}[!] 未检测到 backend/.env 文件${NC}"
  if [ -f "$ROOT_DIR/.env.example" ]; then
    cp "$ROOT_DIR/.env.example" "$ENV_FILE"
    echo -e "${GREEN}[✓] 已从 .env.example 创建 backend/.env${NC}"
    echo -e "${YELLOW}    请编辑 backend/.env 填入实际密钥后重新启动${NC}"
    exit 1
  else
    echo -e "${RED}[✗] 未找到 .env.example 模板，请手动创建 backend/.env${NC}"
    exit 1
  fi
fi

# 验证关键配置
source_env() {
  # 简单解析 .env (跳过注释和空行)
  while IFS='=' read -r key value; do
    key=$(echo "$key" | xargs)
    [[ -z "$key" || "$key" == \#* ]] && continue
    value=$(echo "$value" | xargs | sed 's/^["'\'']//;s/["'\'']$//')
    export "$key=$value" 2>/dev/null || true
  done < "$ENV_FILE"
}
source_env

if [ -z "$LLM_API_KEY" ] || [ "$LLM_API_KEY" = "your-api-key-here" ]; then
  echo -e "${YELLOW}[!] 警告: LLM_API_KEY 未配置，聊天功能将不可用${NC}"
fi

# ── Step 2: 检查依赖 ──────────────────────────────────────────────────────
echo -e "${GREEN}[1/4]${NC} 检查 Python 依赖..."
cd "$BACKEND_DIR"
if [ -f "requirements.txt" ]; then
  pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt
fi

echo -e "${GREEN}[2/4]${NC} 检查 Node 依赖..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
  npm install
else
  # 如果 package.json 比 node_modules 新，重新安装
  if [ "package.json" -nt "node_modules/.package-lock.json" ] 2>/dev/null; then
    npm install
  fi
fi

# ── Step 3: 启动服务 ──────────────────────────────────────────────────────
cleanup() {
  echo -e "\n${CYAN}[fin-assistant] 正在停止服务...${NC}"
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  echo -e "${GREEN}[fin-assistant] 已停止${NC}"
}
trap cleanup EXIT INT TERM

echo -e "${GREEN}[3/4]${NC} 启动后端 uvicorn :8000 ..."
cd "$BACKEND_DIR"
python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!

sleep 2

echo -e "${GREEN}[4/4]${NC} 启动前端 vite :5173 ..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

sleep 2

echo
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  后端${NC}:   http://localhost:8000"
echo -e "${GREEN}  前端${NC}:   http://localhost:5173"
echo -e "${GREEN}  API文档${NC}: http://localhost:8000/docs"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止所有服务"
echo

wait
