"""
创建初始管理员账户
Create Initial Admin Account
"""

from database import SessionLocal
from crud import create_user, get_user_by_username

def create_initial_admin():
    """创建初始管理员账户"""
    db = SessionLocal()
    try:
        # 检查是否已存在管理员
        existing_admin = get_user_by_username(db, "admin")
        if existing_admin:
            print("✅ 管理员账户已存在")
            return
        
        # 创建管理员
        admin = create_user(
            db=db,
            username="admin",
            email="admin@system.com",
            password="admin123",  # 生产环境请修改此密码
            role="admin"
        )
        print(f"✅ 管理员账户创建成功:")
        print(f"   用户名: admin")
        print(f"   密码: admin123")
        print(f"   角色: {admin.role}")
        print(f"⚠️  请尽快修改默认密码！")
        
    except Exception as e:
        print(f"❌ 创建管理员失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()
