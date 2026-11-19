"""
字幕导出工具
支持多种格式：SRT、VTT、TXT
"""
from typing import List
from models import Subtitle


def format_timestamp_srt(seconds: float) -> str:
    """格式化时间戳为SRT格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """格式化时间戳为VTT格式 (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def export_to_srt(subtitles: List[Subtitle]) -> str:
    """导出为SRT格式"""
    srt_content = []
    
    for i, subtitle in enumerate(subtitles, 1):
        # 序号
        srt_content.append(str(i))
        
        # 时间戳 handling: DB stores strings, but logic expects float
        if isinstance(subtitle.start_time, str):
            start_time = subtitle.start_time.replace('.', ',')
        else:
            start_time = format_timestamp_srt(subtitle.start_time)
            
        if isinstance(subtitle.end_time, str):
            end_time = subtitle.end_time.replace('.', ',')
        else:
            end_time = format_timestamp_srt(subtitle.end_time)
            
        srt_content.append(f"{start_time} --> {end_time}")
        
        # 字幕文本
        srt_content.append(subtitle.text)
        
        # 空行
        srt_content.append("")
    
    return "\n".join(srt_content)


def export_to_vtt(subtitles: List[Subtitle]) -> str:
    """导出为VTT格式"""
    vtt_content = ["WEBVTT", ""]
    
    for i, subtitle in enumerate(subtitles, 1):
        # 时间戳
        if isinstance(subtitle.start_time, str):
            start_time = subtitle.start_time.replace(',', '.')
        else:
            start_time = format_timestamp_vtt(subtitle.start_time)
            
        if isinstance(subtitle.end_time, str):
            end_time = subtitle.end_time.replace(',', '.')
        else:
            end_time = format_timestamp_vtt(subtitle.end_time)
            
        vtt_content.append(f"{start_time} --> {end_time}")
        
        # 字幕文本
        vtt_content.append(subtitle.text)
        
        # 空行
        vtt_content.append("")
    
    return "\n".join(vtt_content)


def export_to_txt(subtitles: List[Subtitle]) -> str:
    """导出为纯文本格式"""
    txt_content = []
    
    for subtitle in subtitles:
        # 时间戳 + 文本
        if isinstance(subtitle.start_time, str):
            start_time = subtitle.start_time.replace('.', ',')
        else:
            start_time = format_timestamp_srt(subtitle.start_time)
            
        txt_content.append(f"[{start_time}] {subtitle.text}")
    
    return "\n".join(txt_content)


def export_subtitles(subtitles: List[Subtitle], format: str = "srt") -> str:
    """
    导出字幕
    
    Args:
        subtitles: 字幕列表
        format: 导出格式 (srt, vtt, txt)
    
    Returns:
        格式化的字幕内容
    """
    format = format.lower()
    
    if format == "srt":
        return export_to_srt(subtitles)
    elif format == "vtt":
        return export_to_vtt(subtitles)
    elif format == "txt":
        return export_to_txt(subtitles)
    else:
        raise ValueError(f"不支持的格式: {format}")
