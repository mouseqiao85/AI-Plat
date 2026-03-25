#!/usr/bin/env python3
"""
AI-Plat 自动部署脚本
自动推送代码到服务器并执行部署
"""

import paramiko
import os
import sys
import time
import tarfile
from io import BytesIO

# 服务器配置
SERVER_HOST = "8.215.63.182"
SERVER_USER = "root"
SERVER_PASS = "q@851018"
SERVER_PATH = "/opt/ai-plat"

# 本地路径
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))

def create_deployment_package():
    """创建部署包"""
    print("=" * 50)
    print("1. Creating deployment package...")
    print("=" * 50)
    
    package_path = os.path.join(LOCAL_PATH, "ai-plat-deploy.tar.gz")
    
    files_to_include = [
        "platform/web/src",
        "platform/api",
        "platform/mlops",
        "platform/auth",
        "platform/database",
        "platform/agents",
        "platform/ontology",
        "platform/vibecoding",
        "platform/workflow",
        "platform/gateway",
        "platform/app.py",
        "platform/main.py",
        "platform/requirements.txt",
        "deploy",
    ]
    
    with tarfile.open(package_path, "w:gz") as tar:
        for item in files_to_include:
            full_path = os.path.join(LOCAL_PATH, item)
            if os.path.exists(full_path):
                print(f"  Adding: {item}")
                tar.add(full_path, arcname=item)
            else:
                print(f"  Skipping (not found): {item}")
        
        # 添加更新脚本
        update_script = os.path.join(LOCAL_PATH, "deploy_update_v2.sh")
        if os.path.exists(update_script):
            tar.add(update_script, arcname="deploy_update_v2.sh")
    
    size_mb = os.path.getsize(package_path) / (1024 * 1024)
    print(f"\nPackage created: {package_path} ({size_mb:.2f} MB)")
    return package_path

def connect_server():
    """连接到服务器"""
    print("\n" + "=" * 50)
    print("2. Connecting to server...")
    print("=" * 50)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print(f"  Connected to {SERVER_HOST}")
        return client
    except Exception as e:
        print(f"  Connection failed: {e}")
        sys.exit(1)

def upload_file(client, local_path):
    """上传文件到服务器"""
    print("\n" + "=" * 50)
    print("3. Uploading deployment package...")
    print("=" * 50)
    
    sftp = client.open_sftp()
    
    try:
        remote_file = "/tmp/ai-plat-deploy.tar.gz"
        print(f"  Uploading to {remote_file}...")
        sftp.put(local_path, remote_file)
        print(f"  Upload completed")
        return remote_file
    except Exception as e:
        print(f"  Upload failed: {e}")
        sys.exit(1)
    finally:
        sftp.close()

def run_command(client, command, show_output=True):
    """执行远程命令"""
    stdin, stdout, stderr = client.exec_command(command)
    
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    exit_code = stdout.channel.recv_exit_status()
    
    if show_output:
        if output:
            print(output.rstrip())
        if error and exit_code != 0:
            print(f"Error: {error.rstrip()}")
    
    return exit_code, output, error

def deploy(client, package_path):
    """执行部署"""
    print("\n" + "=" * 50)
    print("4. Deploying to server...")
    print("=" * 50)
    
    commands = [
        # 检查目录
        f"mkdir -p {SERVER_PATH}",
        
        # 备份当前版本
        f"if [ -d {SERVER_PATH}/platform ]; then cd {SERVER_PATH} && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz platform 2>/dev/null || true; fi",
        
        # 解压新版本
        f"cd {SERVER_PATH} && tar -xzf /tmp/ai-plat-deploy.tar.gz",
        
        # 设置权限
        f"chmod +x {SERVER_PATH}/deploy_update_v2.sh 2>/dev/null || true",
        
        # 显示当前状态
        f"echo 'Current git status:' && cd {SERVER_PATH} && git log -1 --oneline 2>/dev/null || echo 'Not a git repo'",
        
        # 检查Docker状态
        "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' 2>/dev/null || echo 'Docker not running'",
    ]
    
    for cmd in commands:
        print(f"\n> {cmd}")
        run_command(client, cmd)
    
    # 检查docker-compose是否存在
    print("\n" + "=" * 50)
    print("5. Checking Docker Compose...")
    print("=" * 50)
    
    exit_code, output, _ = run_command(client, f"test -f {SERVER_PATH}/deploy/docker-compose.yml && echo 'exists' || echo 'not_found'", False)
    
    if "exists" in output:
        print("  Docker Compose file found. Rebuilding services...")
        
        deploy_commands = [
            f"cd {SERVER_PATH} && docker-compose -f deploy/docker-compose.yml down || true",
            f"cd {SERVER_PATH} && docker-compose -f deploy/docker-compose.yml build --no-cache",
            f"cd {SERVER_PATH} && docker-compose -f deploy/docker-compose.yml up -d",
        ]
        
        for cmd in deploy_commands:
            print(f"\n> {cmd}")
            exit_code, output, error = run_command(client, cmd)
            if exit_code != 0:
                print(f"  Warning: Command exited with code {exit_code}")
    else:
        print("  Docker Compose file not found. Skipping container rebuild.")
        print("  You may need to run: ./deploy_update_v2.sh manually")

def verify_deployment(client):
    """验证部署"""
    print("\n" + "=" * 50)
    print("6. Verifying deployment...")
    print("=" * 50)
    
    time.sleep(5)  # 等待服务启动
    
    # 检查容器状态
    print("\n  Container status:")
    run_command(client, "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    
    # 检查API健康
    print("\n  API health check:")
    exit_code, output, _ = run_command(client, "curl -s http://localhost:8000/health || echo 'API not responding'", False)
    print(f"  {output.strip()}")
    
    # 检查Web服务
    print("\n  Web service check:")
    exit_code, output, _ = run_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 || echo 'Web not responding'", False)
    print(f"  HTTP Status: {output.strip()}")

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  AI-Plat Platform - Auto Deployment Script")
    print("=" * 60)
    
    try:
        # 1. 创建部署包
        package_path = create_deployment_package()
        
        # 2. 连接服务器
        client = connect_server()
        
        try:
            # 3. 上传文件
            remote_file = upload_file(client, package_path)
            
            # 4. 执行部署
            deploy(client, package_path)
            
            # 5. 验证部署
            verify_deployment(client)
            
            print("\n" + "=" * 60)
            print("  Deployment completed successfully!")
            print("=" * 60)
            print(f"\n  Access URLs:")
            print(f"    Web:   http://{SERVER_HOST}:3000")
            print(f"    API:   http://{SERVER_HOST}:8000")
            print(f"    Docs:  http://{SERVER_HOST}:8000/docs")
            print()
            
        finally:
            client.close()
            
    except Exception as e:
        print(f"\nDeployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
