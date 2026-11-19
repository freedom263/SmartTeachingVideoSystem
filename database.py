"""
数据库连接和会话管理
Database Connection and Session Management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库文件路径
DATABASE_FILE = os.path.join(os.path.dirname(__file__), "teaching_video_system.db")
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite需要
    echo=False  # 设置为True可以看到SQL语句
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（依赖注入）
    用法: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库（创建所有表）
    """
    from models import User, Task, Frame, Subtitle, KnowledgeGraph, UserEdit
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功")


def drop_all_tables():
    """
    删除所有表（谨慎使用！）
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  所有数据库表已删除")
