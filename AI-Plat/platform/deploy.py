"""
AI-Plat 平台部署脚本
用于简化平台的部署和启动过程
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import shutil


def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要 Python 3.8 或更高版本")
        sys.exit(1)
    print(f"✅ Python 版本检查通过: {sys.version}")


def install_dependencies():
    """安装依赖"""
    print("📦 安装依赖...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True, check=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False


def create_env_file():
    """创建环境配置文件"""
    env_file = ".env"
    if not os.path.exists(env_file):
        print("📄 创建环境配置文件...")
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write("""# AI-Plat 平台环境配置

# 项目配置
PROJECT_NAME=AI-Plat
PROJECT_VERSION=0.1.0
ENVIRONMENT=development

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=True

# 数据库配置
DATABASE_URL=sqlite:///./aiplat.db

# 大模型配置
# OPENAI_API_KEY=your-openai-api-key-here
OLLAMA_BASE_URL=http://localhost:11434

# 本体存储配置
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=aiplat

# 图数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 消息队列配置
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# 路径配置
DATA_PATH=./data
MODELS_PATH=./models
ONTOLOGY_PATH=./ontology/definitions

# 安全配置
SECRET_KEY=change-this-to-a-random-secret-key-for-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 日志级别
LOG_LEVEL=INFO
""")
        print("✅ 环境配置文件创建完成")


def setup_directories():
    """设置必要目录"""
    print("📁 创建必要目录...")
    dirs_to_create = [
        "data/raw",
        "data/processed", 
        "data/external",
        "models",
        "ontology/definitions",
        "ontology/instances", 
        "ontology/inference",
        "notebooks",
        "docs"
    ]
    
    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)
    
    print("✅ 目录创建完成")


def run_tests():
    """运行测试"""
    print("🧪 运行测试...")
    try:
        # 这里可以添加具体的测试命令
        # 例如: subprocess.run(["python", "-m", "pytest"], check=True)
        print("⚠️  测试部分 - 当前无测试文件")
        return True
    except Exception as e:
        print(f"❌ 测试运行失败: {e}")
        return False


def start_server():
    """启动服务器"""
    print("🚀 启动 AI-Plat 服务器...")
    try:
        # 启动FastAPI服务器
        subprocess.run([sys.executable, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\\n🛑 服务器已停止")
        return True


def docker_build():
    """构建Docker镜像"""
    print("🐳 构建 Docker 镜像...")
    try:
        result = subprocess.run([
            "docker", "build", "-t", "ai-plat:latest", "."
        ], check=True, capture_output=True, text=True)
        print("✅ Docker 镜像构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker 镜像构建失败: {e}")
        print(f"Docker 输出: {e.stdout}\\n{e.stderr}")
        return False


def docker_run():
    """运行Docker容器"""
    print("🐳 运行 Docker 容器...")
    try:
        subprocess.run([
            "docker", "run", "-p", "8000:8000", "-d", "ai-plat:latest"
        ], check=True)
        print("✅ Docker 容器运行中，访问 http://localhost:8000")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker 容器运行失败: {e}")
        return False


def run_demo():
    """运行演示"""
    print("🎬 运行 AI-Plat 演示...")
    try:
        subprocess.run([sys.executable, "ai_plat_platform.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 演示运行失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="AI-Plat 平台部署工具")
    parser.add_argument("--setup", action="store_true", help="完整设置（检查依赖、创建目录、配置环境）")
    parser.add_argument("--install", action="store_true", help="仅安装依赖")
    parser.add_argument("--start", action="store_true", help="启动服务器")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--docker-build", action="store_true", help="构建 Docker 镜像")
    parser.add_argument("--docker-run", action="store_true", help="运行 Docker 容器")
    parser.add_argument("--all", action="store_true", help="执行所有步骤")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # 检查Python版本
    check_python_version()
    
    if args.setup or args.all:
        setup_directories()
        create_env_file()
        install_dependencies()
    
    if args.install:
        install_dependencies()
    
    if args.test:
        run_tests()
    
    if args.demo:
        run_demo()
    
    if args.docker_build:
        docker_build()
    
    if args.docker_run:
        docker_run()
    
    if args.start:
        start_server()


if __name__ == "__main__":
    main()