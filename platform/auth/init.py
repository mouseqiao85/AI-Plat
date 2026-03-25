"""
认证系统初始化脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.database import setup_database, db_manager
from auth.config import create_example_env_file, settings
from auth.service import AuthService
from auth.models import UserCreate, UserRole


def init_auth_system():
    """初始化认证系统"""
    print("=" * 60)
    print("AI-Plat平台认证系统初始化")
    print("=" * 60)
    
    # 检查配置
    print("\n1. 检查配置...")
    if settings.SECRET_KEY == "your-secret-key-change-in-production":
        print("⚠️  警告: 使用默认密钥，生产环境请修改SECRET_KEY")
    
    # 测试数据库连接
    print("\n2. 测试数据库连接...")
    if db_manager.test_connection():
        print("✓ 数据库连接成功")
    else:
        print("✗ 数据库连接失败")
        print("请检查DATABASE_URL配置")
        return False
    
    # 设置数据库
    print("\n3. 设置数据库...")
    try:
        setup_database()
        print("✓ 数据库设置完成")
    except Exception as e:
        print(f"✗ 数据库设置失败: {e}")
        return False
    
    # 创建默认管理员账户
    print("\n4. 创建默认管理员账户...")
    auth_service = AuthService()
    
    # 检查是否已有管理员账户
    admin_users = auth_service.get_user_by_username("admin")
    if admin_users:
        print("✓ 管理员账户已存在")
    else:
        try:
            admin_user = UserCreate(
                username="admin",
                email="admin@aiplat.com",
                password="Admin@123456",
                full_name="系统管理员"
            )
            
            user = auth_service.register_user(admin_user)
            
            # 更新为管理员角色
            auth_service.update_user(str(user.id), {"role": UserRole.ADMIN.value})
            print("✓ 管理员账户创建成功")
            print(f"   用户名: admin")
            print(f"   密码: Admin@123456")
            print("⚠️  注意: 请在生产环境中修改默认密码")
        except Exception as e:
            print(f"✗ 管理员账户创建失败: {e}")
    
    # 创建默认测试用户
    print("\n5. 创建默认测试用户...")
    test_users = [
        {
            "username": "developer",
            "email": "dev@aiplat.com",
            "password": "Dev@123456",
            "full_name": "开发人员",
            "role": UserRole.DEVELOPER.value
        },
        {
            "username": "analyst",
            "email": "analyst@aiplat.com",
            "password": "Analyst@123",
            "full_name": "业务分析师",
            "role": UserRole.ANALYST.value
        }
    ]
    
    for user_info in test_users:
        existing_user = auth_service.get_user_by_username(user_info["username"])
        if existing_user:
            print(f"✓ 测试用户 {user_info['username']} 已存在")
        else:
            try:
                user_create = UserCreate(
                    username=user_info["username"],
                    email=user_info["email"],
                    password=user_info["password"],
                    full_name=user_info["full_name"]
                )
                
                user = auth_service.register_user(user_create)
                auth_service.update_user(str(user.id), {"role": user_info["role"]})
                print(f"✓ 测试用户 {user_info['username']} 创建成功")
            except Exception as e:
                print(f"✗ 测试用户 {user_info['username']} 创建失败: {e}")
    
    print("\n" + "=" * 60)
    print("认证系统初始化完成")
    print("=" * 60)
    
    print("\n默认账户信息:")
    print("1. 管理员账户")
    print("   用户名: admin")
    print("   密码: Admin@123456")
    print("   角色: admin")
    
    print("\n2. 开发人员账户")
    print("   用户名: developer")
    print("   密码: Dev@123456")
    print("   角色: developer")
    
    print("\n3. 分析师账户")
    print("   用户名: analyst")
    print("   密码: Analyst@123")
    print("   角色: analyst")
    
    print("\nAPI端点:")
    print("   认证API: http://localhost:8000/auth")
    print("   文档: http://localhost:8000/docs")
    
    print("\n⚠️  重要提醒:")
    print("   1. 生产环境请修改默认密码")
    print("   2. 修改SECRET_KEY配置")
    print("   3. 配置数据库连接参数")
    
    return True


def check_environment():
    """检查环境"""
    print("\n检查环境依赖...")
    
    missing_modules = []
    
    try:
        import fastapi
        print("✓ FastAPI: " + fastapi.__version__)
    except ImportError:
        missing_modules.append("fastapi")
    
    try:
        import sqlalchemy
        print("✓ SQLAlchemy: " + sqlalchemy.__version__)
    except ImportError:
        missing_modules.append("sqlalchemy")
    
    try:
        import passlib
        print("✓ Passlib: " + passlib.__version__)
    except ImportError:
        missing_modules.append("passlib[bcrypt]")
    
    try:
        import jose
        print("✓ python-jose: " + jose.__version__)
    except ImportError:
        missing_modules.append("python-jose[cryptography]")
    
    try:
        import pydantic
        print("✓ Pydantic: " + pydantic.__version__)
    except ImportError:
        missing_modules.append("pydantic")
    
    if missing_modules:
        print("\n✗ 缺少依赖模块:")
        for module in missing_modules:
            print(f"   {module}")
        print("\n请安装依赖:")
        print(f"  pip install {' '.join(missing_modules)}")
        return False
    
    print("\n✓ 所有依赖检查通过")
    return True


def create_env_file_if_needed():
    """如果需要，创建.env文件"""
    if not os.path.exists(".env"):
        print("\n未找到.env文件，正在创建示例.env文件...")
        try:
            env_content = create_example_env_file()
            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
            print("✓ 示例.env文件已创建")
            print("请根据实际情况修改.env文件中的配置")
        except Exception as e:
            print(f"✗ 创建.env文件失败: {e}")
            return False
    else:
        print("\n✓ .env文件已存在")
    
    return True


def main():
    """主函数"""
    print("AI-Plat平台认证系统初始化工具")
    print("版本: 1.0.0")
    
    # 创建.env文件
    if not create_env_file_if_needed():
        return
    
    # 检查环境
    if not check_environment():
        return
    
    # 询问是否继续
    print("\n是否继续初始化认证系统？(y/n): ", end="")
    choice = input().strip().lower()
    
    if choice != 'y':
        print("初始化已取消")
        return
    
    # 初始化认证系统
    success = init_auth_system()
    
    if success:
        print("\n✅ 初始化完成！")
        print("\n下一步:")
        print("1. 启动平台: python app.py")
        print("2. 访问API文档: http://localhost:8000/docs")
        print("3. 使用默认账户登录测试")
    else:
        print("\n❌ 初始化失败，请检查错误信息")


if __name__ == "__main__":
    main()