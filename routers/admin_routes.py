"""
管理员后台 API 路由 (Admin Dashboard Routes)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil

from database.connection import get_db
from database.models import User, Task, Frame, Subtitle, KnowledgeGraph
import database.crud as crud
from auth import get_current_user, require_role
from admin_stats import (
    get_system_stats,
    get_task_trend,
    get_task_distribution,
    get_user_activity,
    get_recent_activities,
    get_user_stats_by_id
)

router = APIRouter(prefix="/api/admin", tags=["管理员后台"])


class UpdateUserRoleRequest(BaseModel):
    new_role: str


class BatchDeleteRequest(BaseModel):
    ids: List[int]


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """获取系统总体统计数据"""
    return get_system_stats(db)


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """获取用户列表（支持搜索和筛选）"""
    query = db.query(User)
    if search:
        query = query.filter((User.username.contains(search)) | (User.email.contains(search)))
    if role and role != "all":
        query = query.filter(User.role == role)

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [u.to_dict() for u in users]
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """修改用户角色"""
    if request.new_role not in ["student", "teacher", "admin"]:
        raise HTTPException(status_code=400, detail="无效的角色类型")

    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    user.role = request.new_role
    db.commit()
    return {"status": "success", "message": f"用户角色已更新为 {request.new_role}"}


@router.delete("/users/{user_id}")
async def delete_user_api(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """删除用户"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    crud.delete_user(db, user_id)
    return {"status": "success", "message": "用户已删除"}
