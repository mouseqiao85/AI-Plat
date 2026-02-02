"""
AI-Plat 平台配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置"""
    # 项目基本信息
    PROJECT_NAME = os.getenv("PROJECT_NAME", "AI-Plat")
    PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.1.0")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # API配置
    API_V1_STR = "/api/v1"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # 数据库配置
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/aiplat")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # 大模型配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # 本体存储配置
    FUSEKI_URL = os.getenv("FUSEKI_URL", "http://localhost:3030")
    FUSEKI_DATASET = os.getenv("FUSEKI_DATASET", "aiplat")
    
    # 图数据库配置
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # 消息队列配置
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # 路径配置
    DATA_PATH = os.getenv("DATA_PATH", "./data")
    MODELS_PATH = os.getenv("MODELS_PATH", "./models")
    ONTOLOGY_PATH = os.getenv("ONTOLOGY_PATH", "./ontology")
    
    # 安全配置
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    DATABASE_URL = os.getenv("DEV_DATABASE_URL", "postgresql://user:password@localhost/aiplat_dev")


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    DATABASE_URL = os.getenv("PROD_DATABASE_URL", "postgresql://user:password@prod-server/aiplat_prod")


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost/aiplat_test")


# 根据环境变量选择配置
def get_config():
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()


# 获取当前配置实例
config = get_config()