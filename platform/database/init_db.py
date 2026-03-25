"""
数据库初始化脚本
创建表、初始化数据
"""

import sys
import os
import logging
from datetime import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseManager, get_db_session
from database.models import (
    Base, User, Ontology, Agent, Workflow,
    MCPServer, Dataset, Model, UserRoleEnum
)
from database.cache import get_cache
from passlib.context import CryptContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_tables():
    """创建所有表"""
    logger.info("创建数据库表...")
    db_manager = DatabaseManager()
    db_manager.create_all_tables()
    logger.info("数据库表创建完成")


def create_default_users():
    """创建默认用户"""
    logger.info("创建默认用户...")
    db = get_db_session()
    
    default_users = [
        {
            "username": "admin",
            "email": "admin@aiplat.com",
            "password": "Admin@123456",
            "full_name": "系统管理员",
            "role": UserRoleEnum.ADMIN.value,
            "is_superuser": True
        },
        {
            "username": "developer",
            "email": "dev@aiplat.com",
            "password": "Dev@123456",
            "full_name": "开发人员",
            "role": UserRoleEnum.DEVELOPER.value
        },
        {
            "username": "analyst",
            "email": "analyst@aiplat.com",
            "password": "Analyst@123",
            "full_name": "业务分析师",
            "role": UserRoleEnum.ANALYST.value
        },
        {
            "username": "guest",
            "email": "guest@aiplat.com",
            "password": "Guest@123",
            "full_name": "访客用户",
            "role": UserRoleEnum.GUEST.value
        }
    ]
    
    for user_data in default_users:
        existing = db.query(User).filter(
            User.username == user_data["username"]
        ).first()
        
        if not existing:
            password = user_data.pop("password")
            hashed_password = pwd_context.hash(password)
            
            user = User(
                id=uuid.uuid4(),
                hashed_password=hashed_password,
                is_active=True,
                is_verified=True,
                **user_data
            )
            db.add(user)
            logger.info(f"创建用户: {user_data['username']}")
        else:
            logger.info(f"用户已存在: {user_data['username']}")
    
    db.commit()
    logger.info("默认用户创建完成")


def create_sample_ontologies():
    """创建示例本体"""
    logger.info("创建示例本体...")
    db = get_db_session()
    
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        logger.warning("未找到admin用户，跳过本体创建")
        return
    
    sample_ontologies = [
        {
            "name": "企业组织架构本体",
            "description": "描述企业组织结构、部门和人员的本体",
            "domain": "organization",
            "entity_count": 15,
            "relation_count": 23,
            "is_public": True,
            "tags": ["企业", "组织", "人员"]
        },
        {
            "name": "客户关系本体",
            "description": "描述客户信息和关系的本体",
            "domain": "crm",
            "entity_count": 12,
            "relation_count": 18,
            "is_public": True,
            "tags": ["客户", "CRM", "销售"]
        },
        {
            "name": "产品知识本体",
            "description": "描述产品信息和分类的本体",
            "domain": "product",
            "entity_count": 20,
            "relation_count": 30,
            "is_public": True,
            "tags": ["产品", "知识库", "分类"]
        }
    ]
    
    for ont_data in sample_ontologies:
        existing = db.query(Ontology).filter(
            Ontology.name == ont_data["name"]
        ).first()
        
        if not existing:
            ontology = Ontology(
                id=uuid.uuid4(),
                owner_id=admin_user.id,
                **ont_data
            )
            db.add(ontology)
            logger.info(f"创建本体: {ont_data['name']}")
    
    db.commit()
    logger.info("示例本体创建完成")


def create_sample_agents():
    """创建示例代理"""
    logger.info("创建示例代理...")
    db = get_db_session()
    
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        return
    
    sample_agents = [
        {
            "name": "客服智能代理",
            "description": "处理客户咨询和服务请求的智能代理",
            "agent_type": "service",
            "status": "running",
            "skills": ["nlp", "qa", "sentiment"],
            "is_public": True
        },
        {
            "name": "销售助手代理",
            "description": "辅助销售人员进行客户跟进和产品推荐",
            "agent_type": "sales",
            "status": "running",
            "skills": ["recommendation", "analysis"],
            "is_public": True
        },
        {
            "name": "数据分析代理",
            "description": "执行数据分析和报表生成的代理",
            "agent_type": "analysis",
            "status": "stopped",
            "skills": ["visualization", "statistics", "ml"],
            "is_public": True
        }
    ]
    
    for agent_data in sample_agents:
        existing = db.query(Agent).filter(
            Agent.name == agent_data["name"]
        ).first()
        
        if not existing:
            agent = Agent(
                id=uuid.uuid4(),
                owner_id=admin_user.id,
                **agent_data
            )
            db.add(agent)
            logger.info(f"创建代理: {agent_data['name']}")
    
    db.commit()
    logger.info("示例代理创建完成")


def create_sample_mcp_servers():
    """创建示例MCP服务器"""
    logger.info("创建示例MCP服务器...")
    db = get_db_session()
    
    sample_servers = [
        {
            "name": "GPT-4 主连接",
            "description": "OpenAI GPT-4模型连接",
            "endpoint": "https://api.openai.com",
            "server_type": "model",
            "status": "healthy",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        },
        {
            "name": "Claude-3 连接",
            "description": "Anthropic Claude-3模型连接",
            "endpoint": "https://api.anthropic.com",
            "server_type": "model",
            "status": "healthy",
            "models": ["claude-3-opus", "claude-3-sonnet"]
        },
        {
            "name": "本地模型服务",
            "description": "本地部署的模型服务",
            "endpoint": "http://localhost:8001",
            "server_type": "model",
            "status": "offline",
            "models": ["local-llm"]
        }
    ]
    
    for server_data in sample_servers:
        existing = db.query(MCPServer).filter(
            MCPServer.name == server_data["name"]
        ).first()
        
        if not existing:
            server = MCPServer(
                id=uuid.uuid4(),
                **server_data
            )
            db.add(server)
            logger.info(f"创建MCP服务器: {server_data['name']}")
    
    db.commit()
    logger.info("示例MCP服务器创建完成")


def verify_database():
    """验证数据库"""
    logger.info("验证数据库...")
    db = get_db_session()
    
    counts = {
        "users": db.query(User).count(),
        "ontologies": db.query(Ontology).count(),
        "agents": db.query(Agent).count(),
        "mcp_servers": db.query(MCPServer).count()
    }
    
    logger.info("数据库统计:")
    for table, count in counts.items():
        logger.info(f"  {table}: {count}")
    
    return counts


def init_database():
    """初始化数据库"""
    logger.info("=" * 60)
    logger.info("AI-Plat 数据库初始化")
    logger.info("=" * 60)
    
    try:
        create_tables()
        create_default_users()
        create_sample_ontologies()
        create_sample_agents()
        create_sample_mcp_servers()
        
        counts = verify_database()
        
        logger.info("=" * 60)
        logger.info("数据库初始化完成!")
        logger.info("=" * 60)
        
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


if __name__ == "__main__":
    init_database()
