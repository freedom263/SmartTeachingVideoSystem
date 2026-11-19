"""
教学报告生成器
支持Markdown、PDF、Word格式
"""
import os
from typing import List
from datetime import datetime
from models import Task, Frame, Subtitle, KnowledgeGraph


def generate_markdown_report(task: Task, frames: List[Frame], subtitles: List[Subtitle], kg: KnowledgeGraph = None,
                             custom_class_summary: str = "", custom_user_reflection: str = "") -> str:
    """生成Markdown格式报告"""
    
    report = []
    
    # 标题
    report.append(f"# 微格教学视频分析报告")
    report.append(f"\n## 视频信息\n")
    report.append(f"- **视频名称**: {task.video_name}")
    report.append(f"- **任务ID**: {task.id}")
    report.append(f"- **视频时长**: {format_duration(task.duration)}")
    report.append(f"- **分析时间**: {task.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    # 统计信息
    report.append(f"\n## 分析统计\n")
    report.append(f"- **字幕条数**: {len(subtitles)} 条")
    report.append(f"- **总字数**: {sum(len(s.text) for s in subtitles)} 字")
    
    # 1. 课堂实录 (字幕)
    report.append(f"\n## 一、课堂实录\n")
    if subtitles:
        for subtitle in subtitles:
            # Check if start_time is already a string
            if isinstance(subtitle.start_time, str):
                start = subtitle.start_time
            else:
                start = format_duration(subtitle.start_time)
            report.append(f"**[{start}]** {subtitle.text}\n")
    else:
        report.append("*本节课未识别到有效语内容*\n")

    # 2. 课堂小结 (优先使用用户编辑的，否则使用AI生成的)
    report.append(f"\n## 二、课堂小结\n")
    
    # 获取AI Summary作为默认值 (如果custom_class_summary为空)
    ai_summary = ""
    if kg and kg.graph_data:
        if isinstance(kg.graph_data, dict):
             ai_summary = kg.graph_data.get('summary') or kg.graph_data.get('ai_summary') or ""
    
    # Fallback: 从文件系统读取 summary.txt (与 main logic 保持一致)
    if not ai_summary and task:
         try:
            # 假设 output_root 在上级目录或通过环境变量
            # 简单起见，尝试构建路径
            task_dir = os.path.join(os.environ.get("OUTPUT_ROOT", "outputs"), task.id)
            summary_path = os.path.join(task_dir, "ai_results", "summary.txt")
            if os.path.exists(summary_path):
                with open(summary_path, 'r', encoding='utf-8') as f:
                    ai_summary = f.read()
         except:
             pass

    final_class_summary = custom_class_summary if custom_class_summary else ai_summary
    
    if final_class_summary:
        report.append(str(final_class_summary))
    else:
        report.append("*暂无课堂小结*")
        
    # 3. 教学反思 (完全由用户填写)
    report.append(f"\n\n## 三、教学反思\n")
    if custom_user_reflection and custom_user_reflection.strip():
        report.append(custom_user_reflection)
    else:
        report.append("*暂无教学反思*")

    # 4. 知识图谱 (保留)
    if kg and kg.graph_data:
        report.append(f"\n\n## 四、知识图谱分析\n")
        # 简单展示节点信息，详细的可视化图表无法在纯Markdown中展示，只能列出要点
        # 这里复用之前的逻辑或者重新组织
        # 之前的逻辑在 large_video.py 里写了一遍，这里 report_generator.py 也要统一
        # 之前的 report_generator.py 只显示了 summary
        # 现在我们把详细的知识点列出来
        
        if isinstance(kg.graph_data, dict):
            nodes = kg.graph_data.get('nodes', [])
            if nodes:
                 report.append(f"### 核心知识点\n")
                 for node in nodes:
                     name = node.get("name", "")
                     report.append(f"- {name}\n")
    
    # 页脚
    report.append(f"\n---\n")
    report.append(f"*本报告由微格教学视频智能分析系统自动生成*")
    
    return "\n".join(report)


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if not seconds:
        return "00:00"
    
    try:
        seconds = float(seconds)
    except:
        return str(seconds)
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def save_report(content: str, task_id: str, format: str, output_dir: str) -> str:
    """
    保存报告到文件
    
    Args:
        content: 报告内容
        task_id: 任务ID
        format: 格式(md/pdf/docx)
        output_dir: 输出目录
    
    Returns:
        文件路径
    """
    # 创建输出目录
    report_dir = os.path.join(output_dir, task_id)
    os.makedirs(report_dir, exist_ok=True)
    
    # 保存文件
    filename = f"report.{format}"
    filepath = os.path.join(report_dir, filename)
    
    if format == 'md':
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    elif format == 'pdf':
        # TODO: 使用reportlab生成PDF
        # 目前先保存为文本
        with open(filepath.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
            f.write("PDF生成功能待实现\n\n")
            f.write(content)
    elif format == 'docx':
        # TODO: 使用python-docx生成Word
        # 目前先保存为文本
        with open(filepath.replace('.docx', '.txt'), 'w', encoding='utf-8') as f:
            f.write("Word生成功能待实现\n\n")
            f.write(content)
    
    return filepath
