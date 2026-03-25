#!/bin/bash
# AI-Plat 完整部署脚本
# 用于服务器 8.215.63.182

set -e

SERVER_IP="8.215.63.182"
DEPLOY_DIR="/opt/ai-plat"

echo "=========================================="
echo "AI-Plat Platform - 完整部署"
echo "服务器: $SERVER_IP"
echo "部署目录: $DEPLOY_DIR"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 步骤1: 环境准备
prepare_environment() {
    log_step "步骤1: 准备环境"
    
    # 安装必要工具
    apt-get update
    apt-get install -y curl wget git vim htop net-tools
    
    # 安装Docker
    if ! command -v docker &> /dev/null; then
        log_info "安装Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl start docker
        systemctl enable docker
    fi
    
    # 安装Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_info "安装Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    log_info "环境准备完成"
}

# 步骤2: 创建目录
create_directories() {
    log_step "步骤2: 创建目录结构"
    
    mkdir -p $DEPLOY_DIR/{platform/{web,gateway},nginx/conf.d,ssl,scripts,logs,data}
    
    log_info "目录创建完成: $DEPLOY_DIR"
}

# 步骤3: 克隆代码
clone_code() {
    log_step "步骤3: 获取代码"
    
    cd $DEPLOY_DIR
    
    # 如果已有代码，更新；否则克隆
    if [ -d "platform/.git" ]; then
        log_info "更新代码..."
        cd platform && git pull
    else
        log_info "代码已存在，跳过克隆"
    fi
}

# 步骤4: 配置环境变量
configure_env() {
    log_step "步骤4: 配置环境变量"
    
    cd $DEPLOY_DIR/platform
    
    if [ ! -f ".env" ]; then
        log_info "创建.env文件..."
        cat > .env << EOF
# 数据库配置
DATABASE_URL=postgresql://postgres:aiplat2024@postgres:5432/ai_plat
REDIS_URL=redis://redis:6379/0

# JWT配置
SECRET_KEY=ai-plat-secret-key-2024-production-$(date +%s)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用配置
APP_NAME=NexusMind OS - AI-Plat Platform
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# CORS配置
CORS_ORIGINS=http://$SERVER_IP,http://localhost:3000,http://localhost:8080

# 服务器配置
HOST=0.0.0.0
PORT=8000

# OAuth配置 (可选)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# 大模型配置 (可选)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EOF
        log_info ".env文件创建完成"
    else
        log_info ".env文件已存在"
    fi
}

# 步骤5: 创建Nginx配置
setup_nginx() {
    log_step "步骤5: 配置Nginx"
    
    # 主配置
    cat > $DEPLOY_DIR/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    
    client_max_body_size 100M;
    
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    upstream api {
        server api:8000;
        keepalive 32;
    }
    
    upstream gateway {
        server gateway:8080;
        keepalive 32;
    }
    
    upstream web {
        server web:80;
        keepalive 16;
    }
    
    include /etc/nginx/conf.d/*.conf;
}
EOF

    # 站点配置
    cat > $DEPLOY_DIR/nginx/conf.d/ai-plat.conf << EOF
server {
    listen 80;
    server_name $SERVER_IP localhost;
    
    client_max_body_size 100M;
    
    location /health {
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /auth/ {
        proxy_pass http://api/auth/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Connection "";
    }
    
    location /docs {
        proxy_pass http://api/docs;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
    
    location /redoc {
        proxy_pass http://api/redoc;
        proxy_http_version 1.1;
    }
    
    location /openapi.json {
        proxy_pass http://api/openapi.json;
    }
    
    location /ws/ {
        proxy_pass http://gateway/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
    
    location / {
        proxy_pass http://web;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

    log_info "Nginx配置完成"
}

# 步骤6: 创建Docker Compose文件
create_docker_compose() {
    log_step "步骤6: 创建Docker Compose配置"
    
    cat > $DEPLOY_DIR/docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: ai-plat-postgres
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: aiplat2024
      POSTGRES_DB: ai_plat
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ai-plat-net

  redis:
    image: redis:7-alpine
    container_name: ai-plat-redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ai-plat-net

  api:
    build:
      context: ./platform
      dockerfile: Dockerfile
    container_name: ai-plat-api
    restart: always
    env_file:
      - ./platform/.env
    ports:
      - "8000:8000"
    volumes:
      - ./platform:/app
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - ai-plat-net

  gateway:
    build:
      context: ./platform/gateway
      dockerfile: Dockerfile
    container_name: ai-plat-gateway
    restart: always
    ports:
      - "8080:8080"
    environment:
      - API_UPSTREAM=http://api:8000
    depends_on:
      - api
    networks:
      - ai-plat-net

  web:
    build:
      context: ./platform/web
      dockerfile: Dockerfile
    container_name: ai-plat-web
    restart: always
    ports:
      - "3000:80"
    networks:
      - ai-plat-net

  nginx:
    image: nginx:alpine
    container_name: ai-plat-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
    depends_on:
      - api
      - gateway
      - web
    networks:
      - ai-plat-net

volumes:
  postgres_data:
  redis_data:

networks:
  ai-plat-net:
    driver: bridge
EOF

    log_info "Docker Compose配置完成"
}

# 步骤7: 创建Dockerfile
create_dockerfiles() {
    log_step "步骤7: 创建Dockerfile"
    
    # API Dockerfile
    cat > $DEPLOY_DIR/platform/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

    # Gateway Dockerfile
    mkdir -p $DEPLOY_DIR/platform/gateway
    cat > $DEPLOY_DIR/platform/gateway/Dockerfile << 'EOF'
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY . .
RUN go mod download
RUN go build -o gateway ./cmd/gateway

FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/gateway .
COPY --from=builder /app/config ./config

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -q --spider http://localhost:8080/health || exit 1

CMD ["./gateway"]
EOF

    # Web Dockerfile
    mkdir -p $DEPLOY_DIR/platform/web
    cat > $DEPLOY_DIR/platform/web/Dockerfile << 'EOF'
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

    log_info "Dockerfile创建完成"
}

# 步骤8: 构建和启动服务
deploy_services() {
    log_step "步骤8: 构建和启动服务"
    
    cd $DEPLOY_DIR
    
    log_info "构建镜像..."
    docker-compose build
    
    log_info "启动服务..."
    docker-compose up -d
    
    log_info "等待服务启动..."
    sleep 30
    
    log_info "服务状态:"
    docker-compose ps
}

# 步骤9: 初始化数据库
init_database() {
    log_step "步骤9: 初始化数据库"
    
    log_info "运行数据库迁移..."
    docker-compose exec api python -m database.init_db || true
    
    log_info "数据库初始化完成"
}

# 步骤10: 验证部署
verify_deployment() {
    log_step "步骤10: 验证部署"
    
    log_info "检查服务健康状态..."
    
    # 检查API
    if curl -sf http://localhost:8000/health > /dev/null; then
        log_info "✓ API服务正常"
    else
        log_warn "✗ API服务异常"
    fi
    
    # 检查Gateway
    if curl -sf http://localhost:8080/health > /dev/null; then
        log_info "✓ Gateway服务正常"
    else
        log_warn "✗ Gateway服务异常"
    fi
    
    # 检查Web
    if curl -sf http://localhost:3000 > /dev/null; then
        log_info "✓ Web服务正常"
    else
        log_warn "✗ Web服务异常"
    fi
    
    # 检查Nginx
    if curl -sf http://localhost/health > /dev/null; then
        log_info "✓ Nginx服务正常"
    else
        log_warn "✗ Nginx服务异常"
    fi
}

# 显示访问信息
show_info() {
    echo ""
    echo "=========================================="
    echo "部署完成！"
    echo "=========================================="
    echo ""
    echo "访问地址:"
    echo "  Web界面:    http://$SERVER_IP"
    echo "  API文档:    http://$SERVER_IP/docs"
    echo "  API地址:    http://$SERVER_IP/api"
    echo ""
    echo "默认账户:"
    echo "  用户名: admin"
    echo "  密码:   Admin@123456"
    echo ""
    echo "管理命令:"
    echo "  查看日志:   docker-compose logs -f"
    echo "  重启服务:   docker-compose restart"
    echo "  停止服务:   docker-compose down"
    echo "  更新部署:   docker-compose pull && docker-compose up -d"
    echo ""
    echo "配置文件:"
    echo "  环境变量:   $DEPLOY_DIR/platform/.env"
    echo "  Nginx:      $DEPLOY_DIR/nginx/conf.d/ai-plat.conf"
    echo ""
    echo "=========================================="
}

# 主函数
main() {
    log_info "开始部署 AI-Plat 平台..."
    
    prepare_environment
    create_directories
    # clone_code  # 如果需要从Git克隆
    configure_env
    setup_nginx
    create_dockerfiles
    create_docker_compose
    deploy_services
    init_database
    verify_deployment
    show_info
    
    log_info "部署完成！"
}

# 运行主函数
main "$@"
