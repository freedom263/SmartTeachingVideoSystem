"""
数据库连接与会话工厂
Database Connection and Session Factory
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config.settings as settings

# 数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()


def get_db():
    """
    FastAPI 依赖注入：获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据表 (自动探测模型并建表)
    """
    import database.models  # 确保所有模型被导入
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表结构初始化/验证成功")


def drop_all_tables():
    """
    清空所有表 (慎用)
    """
    import database.models
    Base.metadata.drop_all(bind=engine)
    print("⚠️ 所有数据库表已删除")
