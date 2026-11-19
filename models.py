"""
数据库模型定义
SQLAlchemy Models for Teaching Video System
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="student")  # student, teacher, admin
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    # 关联关系
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    edits = relationship("UserEdit", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self):
        """转换为字典（不包含密码）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }


class Task(Base):
    """任务表"""
    __tablename__ = "tasks"
    
    id = Column(String(50), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    video_name = Column(String(255), nullable=False)
    status = Column(String(20), default="uploading")  # uploading, processing, completed, failed
    duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    frames_count = Column(Integer, default=0)
    unique_frames_count = Column(Integer, default=0)
    subtitles_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    
    # 关联关系
    user = relationship("User", back_populates="tasks")
    frames = relationship("Frame", back_populates="task", cascade="all, delete-orphan")
    subtitles = relationship("Subtitle", back_populates="task", cascade="all, delete-orphan")
    knowledge_graphs = relationship("KnowledgeGraph", back_populates="task", cascade="all, delete-orphan")
    edits = relationship("UserEdit", back_populates="task", cascade="all, delete-orphan")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.id, # Alias for frontend compatibility
            "user_id": self.user_id,
            "video_name": self.video_name,
            "status": self.status,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "frames_count": self.frames_count,
            "unique_frames_count": self.unique_frames_count,
            "subtitles_count": self.subtitles_count,
            "error_message": self.error_message,
            "is_favorite": self.is_favorite,
            "is_public": self.is_public
        }


class Frame(Base):
    """关键帧表"""
    __tablename__ = "frames"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    time_seconds = Column(Float, default=0.0)
    url_path = Column(String(500), nullable=False)
    saliency_score = Column(Float, default=0.0)
    text_density = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    is_unique = Column(Boolean, default=True)
    
    # 关联关系
    task = relationship("Task", back_populates="frames")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "filename": self.filename,
            "time": self.format_time(),
            "url": self.url_path,
            "saliency": self.saliency_score,
            "density": self.text_density,
            "quality": self.quality_score,
            "is_unique": self.is_unique
        }
    
    def format_time(self):
        """格式化时间"""
        seconds = self.time_seconds
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class Subtitle(Base):
    """字幕表"""
    __tablename__ = "subtitles"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    start_time = Column(String(50), nullable=False)
    end_time = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    
    # 关联关系
    task = relationship("Task", back_populates="subtitles")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "sequence": self.sequence,
            "time": f"{self.start_time} --> {self.end_time}",
            "text": self.text
        }


class KnowledgeGraph(Base):
    """知识图谱表"""
    __tablename__ = "knowledge_graphs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True, unique=True)
    graph_data = Column(JSON, nullable=False)  # 存储 {nodes: [...], links: [...]}
    
    # 关联关系
    task = relationship("Task", back_populates="knowledge_graphs")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "graph_data": self.graph_data
        }


class UserEdit(Base):
    """用户编辑表"""
    __tablename__ = "user_edits"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    edit_type = Column(String(50), nullable=False)  # summary, annotation, tag
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联关系
    task = relationship("Task", back_populates="edits")
    user = relationship("User", back_populates="edits")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "edit_type": self.edit_type,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ==================== 扩展功能模型 ====================

from sqlalchemy import Index

class ShareLink(Base):
    """分享链接"""
    __tablename__ = "share_links"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    share_code = Column(String(32), unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    access_count = Column(Integer, default=0)
    password = Column(String(128), nullable=True)


class Annotation(Base):
    """用户标注"""
    __tablename__ = "annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(20), nullable=False)  # 'frame' or 'subtitle'
    target_id = Column(Integer, nullable=False)  # Frame.id or Subtitle.id
    content = Column(Text, nullable=False)
    position = Column(String(100), nullable=True)  # JSON格式的位置信息
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Favorite(Base):
    """收藏"""
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 联合唯一索引
    __table_args__ = (
        Index('idx_user_task', 'user_id', 'task_id', unique=True),
    )


class Tag(Base):
    """标签"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#667eea")  # 十六进制颜色
    created_at = Column(DateTime, default=datetime.now)


class TaskTag(Base):
    """任务-标签关联"""
    __tablename__ = "task_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 联合唯一索引
    __table_args__ = (
        Index('idx_task_tag', 'task_id', 'tag_id', unique=True),
    )
