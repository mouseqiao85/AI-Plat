# AI-Plat 平台部署指南

## 服务器信息
- **IP地址**: 8.215.63.182
- **用户**: root
- **密码**: q@851018

## 一键部署

### 方式1: 使用完整部署脚本

```bash
# 1. SSH连接到服务器
ssh root@8.215.63.182

# 2. 下载部署脚本
curl -o deploy-full.sh https://raw.githubusercontent.com/your-repo/ai-plat/main/deploy/scripts/deploy-full.sh

# 3. 添加执行权限
chmod +x deploy-full.sh

# 4. 执行部署
./deploy-full.sh
```

### 方式2: 手动部署

```bash
# 1. 连接服务器
ssh root@8.215.63.182

# 2. 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 3. 安装Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 4. 创建部署目录
mkdir -p /opt/ai-plat && cd /opt/ai-plat

# 5. 创建docker-compose.yml
# (复制 deploy/docker-compose.prod.yml 内容)

# 6. 启动服务
docker-compose up -d

# 7. 查看日志
docker-compose logs -f
```

## 访问地址

| 服务 | 地址 |
|------|------|
| Web界面 | http://8.215.63.182 |
| API文档 | http://8.215.63.182/docs |
| API接口 | http://8.215.63.182/api |
| Gateway | http://8.215.63.182:8080 |

## 默认账户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | Admin@123456 | 管理员 |
| developer | Dev@123456 | 开发者 |
| analyst | Analyst@123 | 分析师 |

## 管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api      # API日志
docker-compose logs -f gateway  # Gateway日志
docker-compose logs -f nginx    # Nginx日志

# 重启服务
docker-compose restart api
docker-compose restart gateway
docker-compose restart web

# 停止所有服务
docker-compose down

# 更新部署
git pull
docker-compose build
docker-compose up -d

# 进入容器
docker-compose exec api bash
docker-compose exec postgres psql -U postgres -d ai_plat
```

## 配置修改

### 环境变量
编辑 `/opt/ai-plat/platform/.env`

```bash
# 数据库
DATABASE_URL=postgresql://postgres:aiplat2024@postgres:5432/ai_plat

# Redis
REDIS_URL=redis://redis:6379/0

# JWT密钥
SECRET_KEY=your-secret-key

# 大模型API (可选)
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-xxx
```

### Nginx配置
编辑 `/opt/ai-plat/nginx/conf.d/ai-plat.conf`

修改后重启:
```bash
docker-compose restart nginx
```

## 数据备份

```bash
# 备份PostgreSQL
docker-compose exec postgres pg_dump -U postgres ai_plat > backup_$(date +%Y%m%d).sql

# 恢复
cat backup.sql | docker-compose exec -T postgres psql -U postgres ai_plat
```

## 监控

```bash
# 容器资源使用
docker stats

# 磁盘使用
df -h

# 内存使用
free -h
```

## 故障排查

### API无法启动
```bash
# 检查日志
docker-compose logs api

# 常见问题:
# 1. 数据库连接失败 - 确保postgres已启动
# 2. 依赖安装失败 - 重建镜像 docker-compose build api
```

### 数据库连接失败
```bash
# 检查postgres状态
docker-compose ps postgres

# 测试连接
docker-compose exec postgres pg_isready
```

### 端口被占用
```bash
# 查看端口占用
netstat -tlnp | grep -E "80|443|8000|8080"

# 停止占用进程
kill -9 <PID>
```

## 安全建议

1. 修改默认密码
2. 配置SSL证书
3. 启用防火墙
4. 定期备份数据
5. 更新系统补丁

## SSL配置

```bash
# 安装certbot
apt-get install certbot python3-certbot-nginx

# 获取证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```
