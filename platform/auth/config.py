"""
认证系统配置
"""

import os
from typing import Optional
from pydantic import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class AuthSettings(BaseSettings):
    """认证设置"""
    
    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/ai_plat_auth")
    
    # 密码策略
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_REQUIRE_UPPERCASE: bool = bool(os.getenv("PASSWORD_REQUIRE_UPPERCASE", "True"))
    PASSWORD_REQUIRE_LOWERCASE: bool = bool(os.getenv("PASSWORD_REQUIRE_LOWERCASE", "True"))
    PASSWORD_REQUIRE_NUMBERS: bool = bool(os.getenv("PASSWORD_REQUIRE_NUMBERS", "True"))
    PASSWORD_REQUIRE_SPECIAL_CHARS: bool = bool(os.getenv("PASSWORD_REQUIRE_SPECIAL_CHARS", "False"))
    
    # 安全配置
    RATE_LIMIT_ENABLED: bool = bool(os.getenv("RATE_LIMIT_ENABLED", "True"))
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_MINUTES: int = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "15"))
    
    # OAuth配置（可选）
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    
    # 邮件配置（用于验证邮件）
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@aiplat.com")
    
    # 应用配置
    APP_NAME: str = os.getenv("APP_NAME", "NexusMind OS - AI-Plat Platform")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # CORS配置
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建配置实例
settings = AuthSettings()

# 导出配置常量
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
DATABASE_URL = settings.DATABASE_URL


def get_auth_settings() -> AuthSettings:
    """获取认证设置"""
    return settings


def create_example_env_file():
    """创建示例.env文件"""
    env_content = """# AI-Plat认证系统环境变量配置

# JWT配置
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 数据库配置
DATABASE_URL=postgresql://postgres:password@localhost/ai_plat_auth

# 密码策略
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL_CHARS=false

# 安全配置
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=15

# OAuth配置（可选）
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-client-secret
# GITHUB_CLIENT_ID=your-github-client-id
# GITHUB_CLIENT_SECRET=your-github-client-secret

# 邮件配置（可选）
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-email-password
EMAIL_FROM=noreply@aiplat.com

# 应用配置
APP_NAME=NexusMind OS - AI-Plat Platform
APP_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# CORS配置
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
"""
    
    return env_content


if __name__ == "__main__":
    # 打印当前配置（不显示敏感信息）
    print("当前认证配置:")
    print(f"APP_NAME: {settings.APP_NAME}")
    print(f"APP_URL: {settings.APP_URL}")
    print(f"FRONTEND_URL: {settings.FRONTEND_URL}")
    print(f"ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    print(f"DATABASE_URL: {settings.DATABASE_URL.split('@')[0] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    
    # 询问是否创建.env示例文件
    if not os.path.exists(".env"):
        create_env = input("未找到.env文件，是否创建示例.env文件？(y/n): ")
        if create_env.lower() == 'y':
            with open(".env", "w") as f:
                f.write(create_example_env_file())
            print("示例.env文件已创建")
    else:
        print(".env文件已存在")