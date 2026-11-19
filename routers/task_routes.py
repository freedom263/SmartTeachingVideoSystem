"""
任务调度与视频上传路由 (Task & Upload Routes)
"""

import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

import config.settings as settings
from database.connection import get_db
from database.models import User, Task, TaskStatus
import database.crud as crud
from auth import get_current_user
from services.task_pipeline import pipeline_service
from routers.websocket_routes import ws_manager

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])


@router.get("", response_model=List[dict])
async def list_tasks(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的解析任务列表"""
    if current_user.role == "admin":
        tasks = crud.get_all_tasks(db, skip=skip, limit=limit)
    else:
        tasks = crud.get_tasks_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return [t.to_dict() for t in tasks]


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传教学视频并初始化任务"""
    filename = file.filename
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    # 保存视频到磁盘
    save_dir = os.path.join(settings.UPLOAD_ROOT, task_id)
    os.makedirs(save_dir, exist_ok=True)
    video_path = os.path.join(save_dir, filename)

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 创建数据库任务
    task = crud.create_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
        video_name=filename
    )

    return {
        "status": "success",
        "task_id": task.id,
        "video_name": task.video_name,
        "video_path": video_path,
        "message": "视频上传成功，可调用 /process 触发全流水线解析"
    }


@router.post("/{task_id}/process")
async def start_processing(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """触发全套音画义时多模态流水线异步解析"""
    task = crud.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作此任务")

    # 寻找视频物理路径
    upload_task_dir = os.path.join(settings.UPLOAD_ROOT, task_id)
    video_path = os.path.join(upload_task_dir, task.video_name)
    if not os.path.exists(video_path):
        # 兼容旧路径
        video_path = os.path.join(settings.OUTPUT_ROOT, task_id, task.video_name)

    # 定义 WebSocket 进度广播回调
    def on_progress(tid: str, pct: float, stage: str):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_progress(tid, pct, stage),
                    loop
                )
        except Exception:
            pass

    # 异步启动调度服务
    pipeline_service.run_pipeline_async(
        task_id=task_id,
        video_path=video_path,
        progress_callback=on_progress
    )

    return {
        "status": "started",
        "task_id": task_id,
        "message": "流水线已在后台启动，可通过 WebSocket 监听进度"
    }


@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """查询任务当前生命周期状态与执行进度"""
    task = crud.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除任务及级联产物"""
    task = crud.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除此任务")

    crud.delete_task(db, task_id)
    # 清理磁盘文件
    task_dir = os.path.join(settings.OUTPUT_ROOT, task_id)
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)

    return {"status": "success", "message": "任务已安全删除"}
