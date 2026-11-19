"""
分享管理器
用于生成和管理任务分享链接
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models import ShareLink  # 从models导入ShareLink，不要重复定义


def generate_share_code() -> str:
    """生成唯一的分享码"""
    return secrets.token_urlsafe(16)


def create_share_link(
    db: Session,
    task_id: str,
    user_id: int,
    expires_in_days: int = 7,
    password: Optional[str] = None
) -> ShareLink:
    """
    创建分享链接
    
    Args:
        db: 数据库会话
        task_id: 任务ID
        user_id: 创建者ID
        expires_in_days: 有效天数（0表示永久）
        password: 可选密码
    
    Returns:
        ShareLink对象
    """
    share_code = generate_share_code()
    
    # 计算过期时间
    expires_at = None
    if expires_in_days > 0:
        expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    # 如果有密码，进行哈希
    hashed_password = None
    if password:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    # 创建分享链接
    share_link = ShareLink(
        task_id=task_id,
        share_code=share_code,
        created_by=user_id,
        expires_at=expires_at,
        password=hashed_password
    )
    
    db.add(share_link)
    db.commit()
    db.refresh(share_link)
    
    return share_link


def get_share_link(db: Session, share_code: str) -> Optional[ShareLink]:
    """获取分享链接"""
    return db.query(ShareLink).filter(
        ShareLink.share_code == share_code,
        ShareLink.is_active == True
    ).first()


def verify_share_link(share_link: ShareLink, password: Optional[str] = None) -> bool:
    """
    验证分享链接是否有效
    
    Args:
        share_link: 分享链接对象
        password: 用户提供的密码
    
    Returns:
        是否有效
    """
    # 检查是否过期
    if share_link.expires_at and share_link.expires_at < datetime.now():
        return False
    
    # 检查密码
    if share_link.password:
        if not password:
            return False
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if hashed != share_link.password:
            return False
    
    return True


def increment_access_count(db: Session, share_link: ShareLink):
    """增加访问计数"""
    share_link.access_count += 1
    db.commit()


def deactivate_share_link(db: Session, share_code: str) -> bool:
    """停用分享链接"""
    share_link = get_share_link(db, share_code)
    if share_link:
        share_link.is_active = False
        db.commit()
        return True
    return False
