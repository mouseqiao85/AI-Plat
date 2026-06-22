#!/bin/bash
# AI-Plat Platform Update Script
# 用于更新服务器上的AI-Plat平台

set -e

echo "=========================================="
echo "AI-Plat Platform Update Script"
echo "=========================================="

cd /opt/ai-plat

# 拉取最新代码
echo "1. Pulling latest code..."
git fetch origin
git reset --hard origin/master

# 检查版本
echo ""
echo "2. Current version:"
git log -1 --oneline

# 停止现有容器
echo ""
echo "3. Stopping existing containers..."
docker-compose -f deploy/docker-compose.yml down || true

# 重新构建并启动
echo ""
echo "4. Rebuilding and starting services..."
docker-compose -f deploy/docker-compose.yml build --no-cache
docker-compose -f deploy/docker-compose.yml up -d

# 等待服务启动
echo ""
echo "5. Waiting for services to start..."
sleep 10

# 检查服务状态
echo ""
echo "6. Service status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 健康检查
echo ""
echo "7. Health check..."
sleep 5
curl -s http://localhost:8000/health && echo " - API OK"
curl -s http://localhost:8080/health && echo " - Gateway OK"

echo ""
echo "=========================================="
echo "Update completed!"
echo "=========================================="
echo ""
echo "Access the platform:"
echo "  Web: http://8.215.63.182:3000"
echo "  API: http://8.215.63.182:8000"
echo "  Gateway: http://8.215.63.182:8080"
echo "  API Docs: http://8.215.63.182:8000/docs"
