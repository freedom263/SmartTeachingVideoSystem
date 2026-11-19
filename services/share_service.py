"""
分享链接管理服务 (Share Management Service)
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from database.models import ShareLink


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
    """创建分享链接"""
    share_code = generate_share_code()

    expires_at = None
    if expires_in_days > 0:
        expires_at = datetime.now() + timedelta(days=expires_in_days)

    hashed_password = None
    if password:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

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
    """通过分享码获取分享信息"""
    return db.query(ShareLink).filter(ShareLink.share_code == share_code).first()


def verify_share_access(
    db: Session,
    share_code: str,
    password: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[ShareLink]]:
    """验证分享链接有效性及密码"""
    share_link = get_share_link(db, share_code)

    if not share_link:
        return False, "分享链接不存在", None

    if not share_link.is_active:
        return False, "分享链接已被禁用", None

    if share_link.expires_at and share_link.expires_at < datetime.now():
        return False, "分享链接已过期", None

    if share_link.password:
        if not password:
            return False, "需要访问密码", share_link
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if hashed != share_link.password:
            return False, "密码错误", share_link

    # 累加访问计数
    share_link.access_count += 1
    db.commit()

    return True, None, share_link
