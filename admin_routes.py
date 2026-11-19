"""
管理后台API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil

from database import get_db
from auth import get_current_user, require_role
from models import User, Task, Frame, Subtitle, KnowledgeGraph
from crud import get_user, delete_user, get_task, delete_task
from admin_stats import (
    get_system_stats,
    get_task_trend,
    get_task_distribution,
    get_user_activity,
    get_recent_activities,
    get_user_stats_by_id
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ===================== 数据模型 =====================

class UpdateUserRoleRequest(BaseModel):
    new_role: str


class BatchDeleteRequest(BaseModel):
    ids: List[int]


# ===================== 统计相关API =====================

@router.get("/stats")
async def get_stats(
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取系统整体统计数据"""
    return get_system_stats(db)


@router.get("/stats/trend")
async def get_trend(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取任务趋势数据"""
    return get_task_trend(db, days)


@router.get("/stats/distribution")
async def get_distribution(
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取任务状态分布"""
    return get_task_distribution(db)


@router.get("/stats/activity")
async def get_activity(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取用户活跃度"""
    return get_user_activity(db, days)


@router.get("/stats/recent")
async def get_recent(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取最近活动"""
    return get_recent_activities(db, limit)


# ===================== 用户管理API =====================

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取用户列表（分页）"""
    
    query = db.query(User)
    
    # 角色筛选
    if role and role in ["teacher", "admin"]:
        query = query.filter(User.role == role)
    
    # 搜索
    if search:
        query = query.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * limit
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    # 获取每个用户的统计信息
    user_list = []
    for user in users:
        user_stats = get_user_stats_by_id(db, user.id)
        user_list.append(user_stats)
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "users": user_list
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取用户详细信息"""
    
    user_stats = get_user_stats_by_id(db, user_id)
    if not user_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user_stats


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """修改用户角色"""
    
    # 验证新角色
    if request.new_role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的角色类型"
        )
    
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 不能修改自己的角色
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改自己的角色"
        )
    
    user.role = request.new_role
    db.commit()
    
    return {"message": "角色修改成功", "user_id": user_id, "new_role": request.new_role}


@router.delete("/users/{user_id}")
async def delete_user_by_admin(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """删除用户（级联删除所有任务和文件）"""
    
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除自己的账号"
        )
    
    # 获取用户所有任务
    user_tasks = db.query(Task).filter(Task.user_id == user_id).all()
    
    # 删除任务相关文件
    output_root = os.getenv("OUTPUT_ROOT", "./outputs")
    for task in user_tasks:
        task_dir = os.path.join(output_root, task.id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
    
    # 删除用户（会级联删除任务）
    success = delete_user(db, user_id)
    
    if success:
        return {"message": "用户及其所有数据已删除", "user_id": user_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )


# ===================== 任务管理API =====================

@router.get("/tasks")
async def list_all_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取所有任务列表（全局视图）"""
    
    query = db.query(Task).join(User)
    
    # 状态筛选
    if status:
        if status == "processing":
            query = query.filter(Task.status.in_(["processing", "extracting_frames", "extracting_audio", "generating_subtitles", "ai_analysis"]))
        else:
            query = query.filter(Task.status == status)
    
    # 用户筛选
    if user_id:
        query = query.filter(Task.user_id == user_id)
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * limit
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    
    # 组装任务信息
    task_list = []
    for task in tasks:
        user = db.query(User).filter(User.id == task.user_id).first()
        
        # 统计资源
        frames_count = db.query(Frame).filter(Frame.task_id == task.id).count()
        subtitles_count = db.query(Subtitle).filter(Subtitle.task_id == task.id).count()
        
        task_list.append({
            "id": task.id,
            "task_id": task.id,
            "video_name": task.video_name,
            "status": task.status,
            "duration": task.duration,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "user": {
                "id": user.id if user else None,
                "username": user.username if user else "未知用户",
                "email": user.email if user else None
            },
            "resources": {
                "frames": frames_count,
                "subtitles": subtitles_count
            }
        })
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "tasks": task_list
    }


@router.get("/tasks/{task_id}/archive")
async def get_task_archive(
    task_id: str,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取任务完整档案（管理员专用）"""
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 获取用户信息
    user = db.query(User).filter(User.id == task.user_id).first()
    
    # 获取关键帧
    frames = db.query(Frame).filter(Frame.task_id == task.id).order_by(Frame.time_seconds).all()
    
    # 获取字幕
    subtitles = db.query(Subtitle).filter(Subtitle.task_id == task.id).order_by(Subtitle.start_time).all()
    
    # 获取知识图谱
    kg = db.query(KnowledgeGraph).filter(KnowledgeGraph.task_id == task.id).first()
    
    return {
        "task": {
            "task_id": task.id,
            "video_name": task.video_name,
            "video_path": "",
            "duration": task.duration,
            "fps": 0,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.updated_at.isoformat() if task.updated_at else None
        },
        "user": {
            "id": user.id if user else None,
            "username": user.username if user else "未知用户",
            "email": user.email if user else None,
            "role": user.role if user else None
        },
        "frames": [
            {
                "id": frame.id,
                "frame_path": frame.url_path,
                "timestamp": frame.time_seconds,
                "frame_number": 0
            }
            for frame in frames
        ],
        "subtitles": [
            {
                "id": sub.id,
                "text": sub.text,
                "start_time": sub.start_time,
                "end_time": sub.end_time
            }
            for sub in subtitles
        ],
        "knowledge_graph": {
            "summary": None,
            "user_summary": None,
            "graph_data": kg.graph_data if kg else None
        } if kg else None
    }


@router.delete("/tasks/batch")
async def batch_delete_tasks(
    request: BatchDeleteRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """批量删除任务"""
    
    deleted_count = 0
    output_root = os.getenv("OUTPUT_ROOT", "./outputs")
    
    for task_id in request.ids:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            # 删除文件
            task_dir = os.path.join(output_root, task.id)
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)
            
            # 删除数据库记录
            if delete_task(db, task.id):
                deleted_count += 1
    
    return {
        "message": f"成功删除 {deleted_count} 个任务",
        "deleted_count": deleted_count,
        "total_requested": len(request.ids)
    }


@router.post("/tasks/cleanup")
async def cleanup_failed_tasks(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """清理失败的任务"""
    
    failed_tasks = db.query(Task).filter(Task.status == "failed").all()
    deleted_count = 0
    output_root = os.getenv("OUTPUT_ROOT", "./outputs")
    
    for task in failed_tasks:
        # 删除文件
        task_dir = os.path.join(output_root, task.id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        
        # 删除数据库记录
        if delete_task(db, task.id):
            deleted_count += 1
    
    return {
        "message": f"成功清理 {deleted_count} 个失败任务",
        "deleted_count": deleted_count
    }


# ===================== 系统设置API (简化版) =====================

@router.get("/storage")
async def get_storage_info(
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """获取存储使用情况"""
    
    output_root = os.getenv("OUTPUT_ROOT", "./outputs")
    
    if not os.path.exists(output_root):
        return {
            "total_size_mb": 0,
            "total_size_gb": 0,
            "task_count": 0
        }
    
    # 计算目录大小
    total_size = 0
    task_count = 0
    
    for dirpath, dirnames, filenames in os.walk(output_root):
        task_count = len(dirnames) if dirpath == output_root else task_count
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    
    total_size_mb = total_size / (1024 * 1024)
    total_size_gb = total_size_mb / 1024
    
    return {
        "total_size_mb": round(total_size_mb, 2),
        "total_size_gb": round(total_size_gb, 2),
        "task_count": task_count
    }
