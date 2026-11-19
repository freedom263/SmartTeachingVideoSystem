"""
数据库 CRUD 操作
Database CRUD Operations with Multimodal Alignment & OCR Support
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.models import (
    User, Task, Frame, Subtitle, AlignmentLog, KnowledgeGraph,
    UserEdit, TaskStatus, ShareLink, Annotation, Favorite, Tag, TaskTag
)
from auth import get_password_hash


# ==================== User CRUD ====================

def create_user(db: Session, username: str, email: str, password: str, role: str = "student") -> User:
    """创建用户"""
    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """通过用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """通过邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """通过ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()


def get_user(db: Session, user_id: int) -> Optional[User]:
    """兼容别名"""
    return get_user_by_id(db, user_id)


def update_user_last_login(db: Session, user_id: int):
    """更新用户最后登录时间"""
    user = get_user_by_id(db, user_id)
    if user:
        user.last_login = datetime.now()
        db.commit()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """获取所有用户（分页）"""
    return db.query(User).offset(skip).limit(limit).all()


def delete_user(db: Session, user_id: int) -> bool:
    """删除用户"""
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


# ==================== Task CRUD ====================

def create_task(db: Session, task_id: str, user_id: int, video_name: str) -> Task:
    """创建任务"""
    task = Task(
        id=task_id,
        user_id=user_id,
        video_name=video_name,
        status=TaskStatus.QUEUED.value,
        progress_pct=0.0,
        current_stage="排队中"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task_by_id(db: Session, task_id: str) -> Optional[Task]:
    """获取任务"""
    return db.query(Task).filter(Task.id == task_id).first()


def get_task(db: Session, task_id: str) -> Optional[Task]:
    """兼容别名"""
    return get_task_by_id(db, task_id)


def get_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[Task]:
    """获取用户的所有任务"""
    return db.query(Task).filter(Task.user_id == user_id).order_by(desc(Task.created_at)).offset(skip).limit(limit).all()


def get_all_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[Task]:
    """获取全站所有任务（管理员）"""
    return db.query(Task).order_by(desc(Task.created_at)).offset(skip).limit(limit).all()


def update_task_progress(
    db: Session,
    task_id: str,
    status: Optional[str] = None,
    progress_pct: Optional[float] = None,
    current_stage: Optional[str] = None,
    error_message: Optional[str] = None,
    duration: Optional[float] = None
) -> Optional[Task]:
    """更新任务流水线进度与阶段"""
    task = get_task_by_id(db, task_id)
    if task:
        if status is not None:
            task.status = status
        if progress_pct is not None:
            task.progress_pct = max(0.0, min(100.0, progress_pct))
        if current_stage is not None:
            task.current_stage = current_stage
        if error_message is not None:
            task.error_message = error_message
        if duration is not None:
            task.duration = duration
        task.updated_at = datetime.now()
        db.commit()
        db.refresh(task)
    return task


def update_task_status(db: Session, task_id: str, status: str, error_message: str = None, duration: float = None):
    """兼容旧接口更新状态"""
    return update_task_progress(db, task_id, status=status, error_message=error_message, duration=duration)


def update_task_counts(
    db: Session,
    task_id: str,
    frames_count: int = None,
    unique_frames_count: int = None,
    subtitles_count: int = None,
    alignment_count: int = None
):
    """更新任务各模块产出计数"""
    task = get_task_by_id(db, task_id)
    if task:
        if frames_count is not None:
            task.frames_count = frames_count
        if unique_frames_count is not None:
            task.unique_frames_count = unique_frames_count
        if subtitles_count is not None:
            task.subtitles_count = subtitles_count
        if alignment_count is not None:
            task.alignment_count = alignment_count
        task.updated_at = datetime.now()
        db.commit()
        db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> bool:
    """删除任务及级联产物"""
    task = get_task_by_id(db, task_id)
    if task:
        db.delete(task)
        db.commit()
        return True
    return False


# ==================== Frame CRUD ====================

def create_frame(
    db: Session,
    task_id: str,
    filename: str,
    time_seconds: float,
    url_path: str,
    saliency: float = 0.0,
    density: float = 0.0,
    quality: float = 0.0,
    composite: float = 0.0,
    is_unique: bool = True,
    ocr_text: Optional[str] = None,
    ocr_boxes: Optional[Any] = None,
    scene_category: str = "slide"
) -> Frame:
    """创建关键帧"""
    frame = Frame(
        task_id=task_id,
        filename=filename,
        time_seconds=time_seconds,
        url_path=url_path,
        saliency_score=saliency,
        text_density=density,
        quality_score=quality,
        composite_score=composite,
        is_unique=is_unique,
        ocr_text=ocr_text,
        ocr_boxes=ocr_boxes,
        scene_category=scene_category
    )
    db.add(frame)
    db.commit()
    db.refresh(frame)
    return frame


def update_frame_ocr(db: Session, frame_id: int, ocr_text: str, ocr_boxes: Any = None, scene_category: str = "slide"):
    """更新关键帧的 OCR 识别内容"""
    frame = db.query(Frame).filter(Frame.id == frame_id).first()
    if frame:
        frame.ocr_text = ocr_text
        if ocr_boxes is not None:
            frame.ocr_boxes = ocr_boxes
        frame.scene_category = scene_category
        db.commit()
        db.refresh(frame)
    return frame


def update_frame_alignment(db: Session, frame_id: int, aligned_time: float, drift_offset: float):
    """更新关键帧的跨模态对齐时间与漂移量"""
    frame = db.query(Frame).filter(Frame.id == frame_id).first()
    if frame:
        frame.aligned_time = aligned_time
        frame.drift_offset = drift_offset
        db.commit()
        db.refresh(frame)
    return frame


def get_frames_by_task(db: Session, task_id: str, unique_only: bool = False) -> List[Frame]:
    """获取任务的所有关键帧"""
    query = db.query(Frame).filter(Frame.task_id == task_id)
    if unique_only:
        query = query.filter(Frame.is_unique == True)
    return query.order_by(Frame.time_seconds).all()


# ==================== Subtitle CRUD ====================

def create_subtitle(
    db: Session,
    task_id: str,
    sequence: int,
    start_time: str,
    end_time: str,
    text: str,
    start_seconds: float = 0.0,
    end_seconds: float = 0.0
) -> Subtitle:
    """创建字幕"""
    subtitle = Subtitle(
        task_id=task_id,
        sequence=sequence,
        start_time=start_time,
        end_time=end_time,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        text=text
    )
    db.add(subtitle)
    db.commit()
    db.refresh(subtitle)
    return subtitle


def get_subtitles_by_task(db: Session, task_id: str) -> List[Subtitle]:
    """获取任务的所有字幕"""
    return db.query(Subtitle).filter(Subtitle.task_id == task_id).order_by(Subtitle.sequence).all()


# ==================== Alignment Log CRUD ====================

def create_alignment_log(
    db: Session,
    task_id: str,
    frame_id: int,
    subtitle_id: int,
    similarity_score: float,
    raw_time_diff: float,
    aligned_time_diff: float,
    is_matched: bool = True,
    alignment_type: str = "dtw"
) -> AlignmentLog:
    """创建一条跨模态时序对齐记录"""
    log = AlignmentLog(
        task_id=task_id,
        frame_id=frame_id,
        subtitle_id=subtitle_id,
        similarity_score=similarity_score,
        raw_time_diff=raw_time_diff,
        aligned_time_diff=aligned_time_diff,
        is_matched=is_matched,
        alignment_type=alignment_type
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_alignments_by_task(db: Session, task_id: str) -> List[AlignmentLog]:
    """获取任务的所有对齐记录"""
    return db.query(AlignmentLog).filter(AlignmentLog.task_id == task_id).order_by(AlignmentLog.id).all()


# ==================== KnowledgeGraph CRUD ====================

def create_or_update_knowledge_graph(
    db: Session,
    task_id: str,
    graph_data: dict,
    pedagogical_stages: Optional[list] = None,
    teaching_summary: Optional[str] = None
) -> KnowledgeGraph:
    """创建或更新知识图谱与教学事件分期"""
    kg = db.query(KnowledgeGraph).filter(KnowledgeGraph.task_id == task_id).first()
    if kg:
        kg.graph_data = graph_data
        if pedagogical_stages is not None:
            kg.pedagogical_stages = pedagogical_stages
        if teaching_summary is not None:
            kg.teaching_summary = teaching_summary
    else:
        kg = KnowledgeGraph(
            task_id=task_id,
            graph_data=graph_data,
            pedagogical_stages=pedagogical_stages,
            teaching_summary=teaching_summary
        )
        db.add(kg)
    db.commit()
    db.refresh(kg)
    return kg


def get_knowledge_graph_by_task(db: Session, task_id: str) -> Optional[KnowledgeGraph]:
    """获取任务的知识图谱"""
    return db.query(KnowledgeGraph).filter(KnowledgeGraph.task_id == task_id).first()


# ==================== UserEdit CRUD ====================

def create_user_edit(db: Session, task_id: str, user_id: int, edit_type: str, content: str) -> UserEdit:
    """创建用户编辑记录"""
    edit = UserEdit(
        task_id=task_id,
        user_id=user_id,
        edit_type=edit_type,
        content=content
    )
    db.add(edit)
    db.commit()
    db.refresh(edit)
    return edit


def get_user_edits_by_task(db: Session, task_id: str, edit_type: str = None) -> List[UserEdit]:
    """获取任务的用户编辑记录"""
    query = db.query(UserEdit).filter(UserEdit.task_id == task_id)
    if edit_type:
        query = query.filter(UserEdit.edit_type == edit_type)
    return query.order_by(desc(UserEdit.created_at), desc(UserEdit.id)).all()
