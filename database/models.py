"""
数据库模型定义 (SQLAlchemy Models)
基于音画义时关联的教学视频智能解析系统
"""

import enum
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, Index, Enum
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from database.connection import Base


class JSONType(TypeDecorator):
    """跨版本 SQLite/SQLAlchemy 兼容的 JSON 类型"""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value


class TaskStatus(str, enum.Enum):
    """任务全生命周期状态枚举"""
    QUEUED = "queued"                             # 排队中
    EXTRACTING_MEDIA = "extracting_media"         # ① 音视频解耦与音频提取
    ANALYZING_VISUAL = "analyzing_visual"         # ② 视觉镜头检测、关键帧加权选优与去重
    TRANSCRIBING_AUDIO = "transcribing_audio"     # ② 听觉流 VAD 语音切分与 ASR 转写
    EXTRACTING_OCR = "extracting_ocr"             # ③ 课件与板书高精 OCR 文本识别
    ALIGNING_MULTIMODAL = "aligning_multimodal"   # ③ 跨模态语义向量化与 DTW 时序非刚性对齐
    RESTRUCTURING_SEMANTICS = "restructuring_semantics" # ④ 加涅教学事件分期与层次知识图谱重构
    COMPLETED = "completed"                       # 流水线全流程顺利完成
    FAILED = "failed"                             # 执行异常中断


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

    # 关联
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    edits = relationship("UserEdit", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }


class Task(Base):
    """教学视频解析任务表"""
    __tablename__ = "tasks"

    id = Column(String(50), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    video_name = Column(String(255), nullable=False)
    status = Column(String(30), default=TaskStatus.QUEUED.value)
    progress_pct = Column(Float, default=0.0)      # 进度百分比 0.0 ~ 100.0
    current_stage = Column(String(50), default="排队中") # 当前展示状态文本
    duration = Column(Float, default=0.0)          # 视频总时长 (秒)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 产物指标
    frames_count = Column(Integer, default=0)
    unique_frames_count = Column(Integer, default=0)
    subtitles_count = Column(Integer, default=0)
    alignment_count = Column(Integer, default=0)   # 对齐对数

    error_message = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)

    # 关联
    user = relationship("User", back_populates="tasks")
    frames = relationship("Frame", back_populates="task", cascade="all, delete-orphan")
    subtitles = relationship("Subtitle", back_populates="task", cascade="all, delete-orphan")
    alignments = relationship("AlignmentLog", back_populates="task", cascade="all, delete-orphan")
    knowledge_graphs = relationship("KnowledgeGraph", back_populates="task", cascade="all, delete-orphan")
    edits = relationship("UserEdit", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.id,
            "user_id": self.user_id,
            "video_name": self.video_name,
            "status": self.status,
            "progress_pct": round(self.progress_pct, 1),
            "current_stage": self.current_stage,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "frames_count": self.frames_count,
            "unique_frames_count": self.unique_frames_count,
            "subtitles_count": self.subtitles_count,
            "alignment_count": self.alignment_count,
            "error_message": self.error_message,
            "is_favorite": self.is_favorite,
            "is_public": self.is_public
        }


class Frame(Base):
    """关键帧表 (扩展支持 OCR 课件文字与跨模态时序校正)"""
    __tablename__ = "frames"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    time_seconds = Column(Float, default=0.0)      # 物理抽取原始时间戳 (秒)
    url_path = Column(String(500), nullable=False)

    # 视觉特征评分
    saliency_score = Column(Float, default=0.0)    # 视觉显著性得分
    text_density = Column(Float, default=0.0)      # 文本密度得分
    quality_score = Column(Float, default=0.0)     # 清晰度得分
    composite_score = Column(Float, default=0.0)   # 三要素综合得分
    is_unique = Column(Boolean, default=True)

    # 扩展：课件与板书识别、时序校正
    ocr_text = Column(Text, nullable=True)         # 课件/板书高精识别文字
    ocr_boxes = Column(JSONType, nullable=True)    # 文本框坐标 [{box: [...], text: "...", conf: 0.9}]
    scene_category = Column(String(50), default="slide") # slide(课件), teacher(人像), board(纯板书), hybrid(混合)
    aligned_time = Column(Float, nullable=True)    # 经过 DTW 跨模态时序校正后的逻辑时间戳 (秒)
    drift_offset = Column(Float, default=0.0)      # 音画漂移差值 = aligned_time - time_seconds

    # 关联
    task = relationship("Task", back_populates="frames")
    alignments = relationship("AlignmentLog", back_populates="frame", cascade="all, delete-orphan")

    def format_time(self, seconds=None):
        s = self.time_seconds if seconds is None else seconds
        hours = int(s // 3600)
        minutes = int((s % 3600) // 60)
        secs = int(s % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "filename": self.filename,
            "time": self.format_time(self.time_seconds),
            "time_seconds": self.time_seconds,
            "aligned_time": self.format_time(self.aligned_time) if self.aligned_time is not None else None,
            "aligned_seconds": self.aligned_time,
            "drift_offset": round(self.drift_offset, 2),
            "url": self.url_path,
            "saliency": self.saliency_score,
            "density": self.text_density,
            "quality": self.quality_score,
            "composite": self.composite_score,
            "is_unique": self.is_unique,
            "ocr_text": self.ocr_text,
            "scene_category": self.scene_category
        }


class Subtitle(Base):
    """听觉流字幕表 (扩展支持时序绑定)"""
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    start_time = Column(String(50), nullable=False) # "00:01:23.400"
    end_time = Column(String(50), nullable=False)   # "00:01:28.100"
    start_seconds = Column(Float, default=0.0)
    end_seconds = Column(Float, default=0.0)
    text = Column(Text, nullable=False)

    # 关联
    task = relationship("Task", back_populates="subtitles")
    alignments = relationship("AlignmentLog", back_populates="subtitle", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "sequence": self.sequence,
            "time": f"{self.start_time} --> {self.end_time}",
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text
        }


class AlignmentLog(Base):
    """【核心学术创新】跨模态音画时序非刚性对齐记录表"""
    __tablename__ = "alignment_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True)
    frame_id = Column(Integer, ForeignKey("frames.id"), nullable=False, index=True)
    subtitle_id = Column(Integer, ForeignKey("subtitles.id"), nullable=False, index=True)

    similarity_score = Column(Float, default=0.0)  # 语义匹配相似度 (余弦相似度)
    raw_time_diff = Column(Float, default=0.0)     # 原始时间戳之差 (秒)
    aligned_time_diff = Column(Float, default=0.0) # DTW 校正后之差 (秒)
    is_matched = Column(Boolean, default=True)     # 是否判定为有效关联
    alignment_type = Column(String(20), default="dtw") # 'dtw', 'semantic_direct', 'anchor'
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    task = relationship("Task", back_populates="alignments")
    frame = relationship("Frame", back_populates="alignments")
    subtitle = relationship("Subtitle", back_populates="alignments")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "frame_id": self.frame_id,
            "subtitle_id": self.subtitle_id,
            "similarity_score": round(self.similarity_score, 4),
            "raw_time_diff": round(self.raw_time_diff, 2),
            "aligned_time_diff": round(self.aligned_time_diff, 2),
            "is_matched": self.is_matched,
            "alignment_type": self.alignment_type
        }


class KnowledgeGraph(Base):
    """语义层：知识图谱表 (扩展融合加涅九步教学事件)"""
    __tablename__ = "knowledge_graphs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False, index=True, unique=True)
    graph_data = Column(JSONType, nullable=False)  # {nodes: [...], links: [...]}
    pedagogical_stages = Column(JSONType, nullable=True) # 加涅事件分期结构 [{stage: "导入", start: 0, end: 180, concepts: [...]}]
    teaching_summary = Column(Text, nullable=True)   # 教学脉络与综合诊断报告

    # 关联
    task = relationship("Task", back_populates="knowledge_graphs")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "graph_data": self.graph_data,
            "pedagogical_stages": self.pedagogical_stages,
            "teaching_summary": self.teaching_summary
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

    # 关联
    task = relationship("Task", back_populates="edits")
    user = relationship("User", back_populates="edits")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "edit_type": self.edit_type,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ShareLink(Base):
    """分享链接表"""
    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False)
    share_code = Column(String(32), unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    access_count = Column(Integer, default=0)
    password = Column(String(128), nullable=True)


class Annotation(Base):
    """用户批注表"""
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(20), nullable=False)  # 'frame' or 'subtitle'
    target_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    position = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Favorite(Base):
    """收藏表"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_user_task', 'user_id', 'task_id', unique=True),
    )


class Tag(Base):
    """标签表"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#667eea")
    created_at = Column(DateTime, default=datetime.now)


class TaskTag(Base):
    """任务标签关联表"""
    __tablename__ = "task_tags"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_task_tag', 'task_id', 'tag_id', unique=True),
    )
