"""
教学视频智能解析全流水线状态机调度服务 (Task Pipeline Service)
按序串联：音视频解耦 -> 视觉加权选帧 -> 语音识别 -> 课件OCR -> 跨模态时序对齐 -> 教学语义重构
"""

import os
import time
import traceback
import threading
from typing import Optional, Callable, Dict, Any
from sqlalchemy.orm import Session

import config.settings as settings
from database.connection import SessionLocal
from database.models import TaskStatus
import database.crud as crud
from core.audio_engine import AudioEngine
from core.visual_engine import VisualEngine
from core.ocr_engine import OCREngine
from core.alignment_engine import AlignmentEngine
from core.semantic_engine import SemanticEngine


class TaskPipelineService:
    """流水线编排服务单例"""

    def __init__(self):
        self.audio_engine = AudioEngine()
        self.visual_engine = VisualEngine()
        self.ocr_engine = OCREngine()
        self.alignment_engine = AlignmentEngine()
        self.semantic_engine = SemanticEngine()

    def run_pipeline_sync(
        self,
        task_id: str,
        video_path: str,
        progress_callback: Optional[Callable[[str, float, str], None]] = None
    ):
        """
        同步执行单个任务全流程，并在独立数据库会话中持续持久化状态
        """
        db: Session = SessionLocal()
        task_dir = os.path.join(settings.OUTPUT_ROOT, task_id)
        frames_dir = os.path.join(task_dir, "frames")
        audio_dir = os.path.join(task_dir, "audio")
        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)

        def report(stage_status: TaskStatus, pct: float, stage_desc: str):
            crud.update_task_progress(
                db, task_id=task_id,
                status=stage_status.value,
                progress_pct=pct,
                current_stage=stage_desc
            )
            if progress_callback:
                try:
                    progress_callback(task_id, pct, stage_desc)
                except Exception as cb_err:
                    print(f"[Callback Error] {cb_err}")

        try:
            print(f"[Pipeline] 任务启动: {task_id} | 视频路径: {video_path}")

            # ---------------- 阶段 1: 音视频解耦与音频抽取 ----------------
            report(TaskStatus.EXTRACTING_MEDIA, 10.0, "提取定点 16kHz WAV 音频")
            audio_path = os.path.join(audio_dir, "audio.wav")
            try:
                self.audio_engine.extract_audio(video_path, audio_path)
            except Exception as e:
                print(f"[Pipeline Warning] 外部 ffmpeg 抽取失败: {e}，将尝试以虚拟音频继续")

            # ---------------- 阶段 2: 视觉镜头检测与关键帧加权选优 ----------------
            report(TaskStatus.ANALYZING_VISUAL, 25.0, "执行 HSV 镜头检测与多特征(清晰度/显著性/文本)选帧")
            extracted_frames = self.visual_engine.extract_keyframes(
                video_path=video_path,
                output_frames_dir=frames_dir
            )

            # 持久化关键帧
            db_frames = []
            for item in extracted_frames:
                frame_obj = crud.create_frame(
                    db=db,
                    task_id=task_id,
                    filename=item["filename"],
                    time_seconds=item["time_seconds"],
                    url_path=item["url_path"],
                    saliency=item["saliency"],
                    density=item["density"],
                    quality=item["quality"],
                    composite=item["composite"],
                    is_unique=item["is_unique"]
                )
                db_frames.append(frame_obj)

            crud.update_task_counts(
                db, task_id=task_id,
                frames_count=len(extracted_frames),
                unique_frames_count=sum(1 for f in extracted_frames if f["is_unique"])
            )

            # ---------------- 阶段 3: 听觉流 VAD 语音切分与 ASR 转写 ----------------
            report(TaskStatus.TRANSCRIBING_AUDIO, 45.0, "执行语音活动检测(VAD)与语音识别(ASR)")
            subtitles_raw = self.audio_engine.transcribe(audio_path)

            db_subs = []
            for s in subtitles_raw:
                sub_obj = crud.create_subtitle(
                    db=db,
                    task_id=task_id,
                    sequence=s["sequence"],
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                    start_seconds=s["start_seconds"],
                    end_seconds=s["end_seconds"],
                    text=s["text"]
                )
                db_subs.append(sub_obj)

            crud.update_task_counts(db, task_id=task_id, subtitles_count=len(subtitles_raw))

            # ---------------- 阶段 4: 课件与板书高精 OCR 文本识别 ----------------
            report(TaskStatus.EXTRACTING_OCR, 65.0, "提取关键帧课件与板书 OCR 高精文字")
            unique_db_frames = [f for f in db_frames if f.is_unique]
            for f_obj in unique_db_frames:
                local_img_path = os.path.join(frames_dir, f_obj.filename)
                ocr_res = self.ocr_engine.extract_text(local_img_path)
                crud.update_frame_ocr(
                    db=db,
                    frame_id=f_obj.id,
                    ocr_text=ocr_res["full_text"],
                    ocr_boxes=ocr_res["boxes"],
                    scene_category=ocr_res["scene_category"]
                )

            # 重新加载更新了 OCR 的帧列表
            fresh_frames = crud.get_frames_by_task(db, task_id, unique_only=True)
            frames_dict_list = [f.to_dict() for f in fresh_frames]
            subs_dict_list = [s.to_dict() for s in db_subs]

            # ---------------- 阶段 5: 【核心学术创新】跨模态 DTW 时序对齐 ----------------
            report(TaskStatus.ALIGNING_MULTIMODAL, 80.0, "跨模态语义向量对齐与 DTW 非刚性漂移校正")
            alignment_result = self.alignment_engine.align_audio_and_visual(
                frames=frames_dict_list,
                subtitles=subs_dict_list
            )

            # 更新对齐时间戳并入库
            for af in alignment_result["aligned_frames"]:
                f_id = af.get("id")
                if f_id:
                    crud.update_frame_alignment(
                        db=db,
                        frame_id=f_id,
                        aligned_time=af.get("aligned_time", af.get("time_seconds", 0.0)),
                        drift_offset=af.get("drift_offset", 0.0)
                    )

            for log in alignment_result["alignment_logs"]:
                if log.get("frame_id") and log.get("subtitle_id"):
                    crud.create_alignment_log(
                        db=db,
                        task_id=task_id,
                        frame_id=log["frame_id"],
                        subtitle_id=log["subtitle_id"],
                        similarity_score=log["similarity_score"],
                        raw_time_diff=log["raw_time_diff"],
                        aligned_time_diff=log["aligned_time_diff"],
                        is_matched=log["is_matched"]
                    )

            crud.update_task_counts(db, task_id=task_id, alignment_count=len(alignment_result["alignment_logs"]))

            # ---------------- 阶段 6: 语义重构与知识图谱生成 ----------------
            report(TaskStatus.RESTRUCTURING_SEMANTICS, 92.0, "加涅九步教学事件分期与层次知识图谱重构")
            task_obj = crud.get_task_by_id(db, task_id)
            total_duration = task_obj.duration if task_obj else 0.0

            semantic_result = self.semantic_engine.analyze_pedagogy_and_graph(
                subtitles=subs_dict_list,
                frames=frames_dict_list,
                duration_sec=total_duration
            )

            crud.create_or_update_knowledge_graph(
                db=db,
                task_id=task_id,
                graph_data=semantic_result["graph_data"],
                pedagogical_stages=semantic_result["pedagogical_stages"],
                teaching_summary=semantic_result["teaching_summary"]
            )

            # ---------------- 阶段 7: 流水线全链路完成 ----------------
            report(TaskStatus.COMPLETED, 100.0, "解析已全部完成")
            print(f"[Pipeline] 任务执行完毕: {task_id}")

        except Exception as err:
            err_msg = f"{str(err)}\n{traceback.format_exc()}"
            print(f"[Pipeline Error] {err_msg}")
            crud.update_task_progress(
                db, task_id=task_id,
                status=TaskStatus.FAILED.value,
                error_message=err_msg,
                current_stage="处理异常中断"
            )
        finally:
            db.close()

    def run_pipeline_async(
        self,
        task_id: str,
        video_path: str,
        progress_callback: Optional[Callable[[str, float, str], None]] = None
    ) -> threading.Thread:
        """后台异步线程调度"""
        t = threading.Thread(
            target=self.run_pipeline_sync,
            args=(task_id, video_path, progress_callback),
            daemon=True
        )
        t.start()
        return t


# 单例实例
pipeline_service = TaskPipelineService()
