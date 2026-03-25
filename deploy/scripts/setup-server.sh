#!/bin/bash
# AI-Plat 平台一键部署脚本
# 服务器: 8.215.63.182

set -e

echo "=========================================="
echo "AI-Plat Platform Deployment"
echo "Server: 8.215.63.182"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    log_info "检测到操作系统: $OS $VER"
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        apt-get update -y
        apt-get upgrade -y
    elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
        yum update -y
    else
        log_warn "未知操作系统，跳过更新"
    fi
}

# 安装Docker
install_docker() {
    log_info "检查Docker..."
    
    if command -v docker &> /dev/null; then
        log_info "Docker已安装: $(docker --version)"
        return
    fi
    
    log_info "安装Docker..."
    
    # 安装依赖
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common
    
    # 添加Docker官方GPG密钥
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # 添加Docker仓库
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # 启动Docker
    systemctl start docker
    systemctl enable docker
    
    log_info "Docker安装完成: $(docker --version)"
}

# 安装Docker Compose
install_docker_compose() {
    log_info "检查Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose已安装: $(docker-compose --version)"
        return
    fi
    
    log_info "安装Docker Compose..."
    
    curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    
    chmod +x /usr/local/bin/docker-compose
    
    log_info "Docker Compose安装完成: $(docker-compose --version)"
}

# 安装其他依赖
install_dependencies() {
    log_info "安装其他依赖..."
    
    apt-get install -y \
        git \
        wget \
        curl \
        vim \
        htop \
        net-tools \
        nginx \
        certbot \
        python3-certbot-nginx
    
    log_info "依赖安装完成"
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    mkdir -p /opt/ai-plat/{data,logs,config,ssl}
    mkdir -p /opt/ai-plat/platform/{web,gateway}
    
    log_info "目录创建完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        ufw --force reset
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 3000/tcp
        ufw allow 8000/tcp
        ufw allow 8080/tcp
        ufw --force enable
        log_info "UFW防火墙配置完成"
    else
        log_warn "UFW未安装，跳过防火墙配置"
    fi
}

# 配置系统参数
configure_system() {
    log_info "配置系统参数..."
    
    # 增加文件描述符限制
    cat >> /etc/security/limits.conf << EOF
* soft nofile 65535
* hard nofile 65535
EOF
    
    # 内核参数优化
    cat >> /etc/sysctl.conf << EOF
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
EOF
    
    sysctl -p
    
    log_info "系统参数配置完成"
}

# 创建swap文件
create_swap() {
    log_info "检查swap..."
    
    if [ -f /swapfile ]; then
        log_info "Swap已存在"
        return
    fi
    
    log_info "创建swap文件 (4GB)..."
    
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    
    log_info "Swap创建完成"
}

# 显示系统信息
show_info() {
    echo ""
    echo "=========================================="
    echo "系统信息"
    echo "=========================================="
    echo ""
    echo "主机名: $(hostname)"
    echo "IP地址: $(hostname -I | awk '{print $1}')"
    echo "操作系统: $OS $VER"
    echo "内核版本: $(uname -r)"
    echo ""
    echo "CPU: $(nproc) 核"
    echo "内存: $(free -h | awk '/^Mem:/{print $2}')"
    echo "磁盘: $(df -h / | awk 'NR==2{print $4}') 可用"
    echo ""
    echo "Docker: $(docker --version)"
    echo "Docker Compose: $(docker-compose --version)"
    echo ""
    echo "=========================================="
    echo "部署准备完成"
    echo "=========================================="
}

# 主函数
main() {
    log_info "开始部署准备..."
    
    detect_os
    update_system
    install_docker
    install_docker_compose
    install_dependencies
    create_directories
    configure_firewall
    configure_system
    create_swap
    show_info
    
    log_info "环境准备完成！"
}

main
