"""
多模态解析产物查询路由 (Result Query Routes)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
import database.crud as crud
from services.report_service import generate_markdown_report

router = APIRouter(prefix="/api/tasks", tags=["产物查询"])


@router.get("/{task_id}/frames")
async def get_task_frames(
    task_id: str,
    unique_only: bool = True,
    db: Session = Depends(get_db)
):
    """获取视频优选关键帧 (含 OCR 文字与时序校正参数)"""
    frames = crud.get_frames_by_task(db, task_id=task_id, unique_only=unique_only)
    return [f.to_dict() for f in frames]


@router.get("/{task_id}/subtitles")
async def get_task_subtitles(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取听觉流转写字幕"""
    subs = crud.get_subtitles_by_task(db, task_id=task_id)
    return [s.to_dict() for s in subs]


@router.get("/{task_id}/alignments")
async def get_task_alignments(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取跨模态音画 DTW 对齐明细与相似度日志"""
    logs = crud.get_alignments_by_task(db, task_id=task_id)
    return [l.to_dict() for l in logs]


@router.get("/{task_id}/knowledge_graph")
async def get_task_knowledge_graph(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取加涅教学事件分期与层次知识图谱"""
    kg = crud.get_knowledge_graph_by_task(db, task_id=task_id)
    if not kg:
        raise HTTPException(status_code=404, detail="知识图谱尚未生成")
    return kg.to_dict()


@router.get("/{task_id}/report", response_class=PlainTextResponse)
async def get_teaching_report(
    task_id: str,
    db: Session = Depends(get_db)
):
    """导出格式化教学智能诊断 Markdown 报告"""
    task = crud.get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    frames = crud.get_frames_by_task(db, task_id=task_id, unique_only=True)
    subtitles = crud.get_subtitles_by_task(db, task_id=task_id)
    kg = crud.get_knowledge_graph_by_task(db, task_id=task_id)

    report_md = generate_markdown_report(
        task=task,
        frames=frames,
        subtitles=subtitles,
        kg=kg
    )
    return report_md
