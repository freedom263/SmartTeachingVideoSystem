"""
文件打包工具
用于批量下载关键帧等文件
"""
import os
import zipfile
from typing import List
from pathlib import Path


def create_frames_zip(task_id: str, frame_paths: List[str], output_dir: str = "./outputs") -> str:
    """
    将关键帧打包为ZIP文件
    
    Args:
        task_id: 任务ID
        frame_paths: 关键帧文件路径列表
        output_dir: 输出目录
    
    Returns:
        ZIP文件路径
    """
    # 创建ZIP文件路径
    zip_filename = f"{task_id}_frames.zip"
    zip_path = os.path.join(output_dir, task_id, zip_filename)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    
    # 创建ZIP文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, frame_path in enumerate(frame_paths, 1):
            if os.path.exists(frame_path):
                # 在ZIP中使用简化的文件名
                arcname = f"frame_{i:04d}{Path(frame_path).suffix}"
                zipf.write(frame_path, arcname)
    
    return zip_path


def create_subtitles_zip(task_id: str, subtitle_files: dict, output_dir: str = "./outputs") -> str:
    """
    将多格式字幕打包为ZIP文件
    
    Args:
        task_id: 任务ID
        subtitle_files: 字幕文件字典 {'srt': path, 'vtt': path, 'txt': path}
        output_dir: 输出目录
    
    Returns:
        ZIP文件路径
    """
    # 创建ZIP文件路径
    zip_filename = f"{task_id}_subtitles.zip"
    zip_path = os.path.join(output_dir, task_id, zip_filename)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    
    # 创建ZIP文件
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for format_name, file_path in subtitle_files.items():
            if file_path and os.path.exists(file_path):
                arcname = f"subtitles.{format_name}"
                zipf.write(file_path, arcname)
    
    return zip_path


def get_zip_size(zip_path: str) -> int:
    """获取ZIP文件大小（字节）"""
    if os.path.exists(zip_path):
        return os.path.getsize(zip_path)
    return 0
