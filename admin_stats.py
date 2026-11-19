"""
管理后台统计数据计算模块
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from models import User, Task, Frame, Subtitle
from typing import Dict, List


def get_system_stats(db: Session) -> Dict:
    """获取系统整体统计数据"""
    
    # 用户统计
    total_users = db.query(User).count()
    teacher_count = db.query(User).filter(User.role == "teacher").count()
    admin_count = db.query(User).filter(User.role == "admin").count()
    
    # 任务统计
    total_tasks = db.query(Task).count()
    done_tasks = db.query(Task).filter(Task.status == "done").count()
    processing_tasks = db.query(Task).filter(Task.status.in_(["processing", "uploaded", "extracting_frames", "extracting_audio", "generating_subtitles", "ai_analysis"])).count()
    failed_tasks = db.query(Task).filter(Task.status == "failed").count()
    
    # 资源统计
    total_frames = db.query(Frame).count()
    total_subtitles = db.query(Subtitle).count()
    
    # 存储统计（假设每个任务平均占用空间）
    avg_task_size = 50  # MB
    estimated_storage = total_tasks * avg_task_size
    
    return {
        "users": {
            "total": total_users,
            "teachers": teacher_count,
            "admins": admin_count
        },
        "tasks": {
            "total": total_tasks,
            "done": done_tasks,
            "processing": processing_tasks,
            "failed": failed_tasks
        },
        "resources": {
            "frames": total_frames,
            "subtitles": total_subtitles
        },
        "storage": {
            "estimated_mb": estimated_storage,
            "estimated_gb": round(estimated_storage / 1024, 2)
        }
    }


def get_task_trend(db: Session, days: int = 7) -> List[Dict]:
    """获取任务趋势数据（最近N天）"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 按天统计任务数
    trend_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        next_date = date + timedelta(days=1)
        
        count = db.query(Task).filter(
            and_(
                Task.created_at >= date,
                Task.created_at < next_date
            )
        ).count()
        
        trend_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "count": count
        })
    
    return trend_data


def get_task_distribution(db: Session) -> Dict:
    """获取任务状态分布"""
    
    status_map = {
        "done": "已完成",
        "processing": "处理中",
        "failed": "失败",
        "uploaded": "已上传"
    }
    
    # 统计各状态任务数
    distribution = {}
    for status, label in status_map.items():
        if status == "processing":
            # 处理中包含多个状态
            count = db.query(Task).filter(
                Task.status.in_(["processing", "extracting_frames", "extracting_audio", "generating_subtitles", "ai_analysis"])
            ).count()
        else:
            count = db.query(Task).filter(Task.status == status).count()
        
        if count > 0:
            distribution[label] = count
    
    return distribution


def get_user_activity(db: Session, days: int = 7) -> List[Dict]:
    """获取用户活跃度数据"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 获取活跃用户（有任务创建的用户）
    active_users = db.query(
        User.username,
        func.count(Task.id).label('task_count')
    ).join(Task, User.id == Task.user_id).filter(
        Task.created_at >= start_date
    ).group_by(User.id, User.username).order_by(
        func.count(Task.id).desc()
    ).limit(10).all()
    
    return [
        {"username": user.username, "task_count": user.task_count}
        for user in active_users
    ]


def get_recent_activities(db: Session, limit: int = 10) -> Dict:
    """获取最近活动"""
    
    # 最新注册用户
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    
    # 最新任务
    recent_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(limit).all()
    
    return {
        "recent_users": [
            {
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in recent_users
        ],
        "recent_tasks": [
            {
                "task_id": task.task_id,
                "video_name": task.video_name,
                "status": task.status,
                "user_id": task.user_id,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
            for task in recent_tasks
        ]
    }


def get_user_stats_by_id(db: Session, user_id: int) -> Dict:
    """获取指定用户的统计信息"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    total_tasks = db.query(Task).filter(Task.user_id == user_id).count()
    done_tasks = db.query(Task).filter(
        and_(Task.user_id == user_id, Task.status == "done")
    ).count()
    
    # 该用户的总关键帧数和字幕数
    total_frames = db.query(Frame).join(Task).filter(Task.user_id == user_id).count()
    total_subtitles = db.query(Subtitle).join(Task).filter(Task.user_id == user_id).count()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "tasks": {
            "total": total_tasks,
            "done": done_tasks
        },
        "resources": {
            "frames": total_frames,
            "subtitles": total_subtitles
        }
    }
