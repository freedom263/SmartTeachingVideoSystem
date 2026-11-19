"""
教学诊断与多模态分析报告生成服务 (Report Generation Service)
支持生成融合加涅九步事件、音画时序校正与知识图谱的 Markdown / HTML 报告
"""

import os
from typing import List, Optional
from datetime import datetime
from database.models import Task, Frame, Subtitle, KnowledgeGraph


def format_duration(seconds: float) -> str:
    """格式化秒数为时分秒"""
    s = int(seconds or 0)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def generate_markdown_report(
    task: Task,
    frames: List[Frame],
    subtitles: List[Subtitle],
    kg: Optional[KnowledgeGraph] = None,
    custom_class_summary: str = "",
    custom_user_reflection: str = ""
) -> str:
    """生成增强版微格教学视频多模态分析报告 (Markdown)"""
    report = []

    # 1. 标题与基本信息
    report.append("# 教学视频多模态智能分析与诊断报告\n")
    report.append("## 一、视频基础档案\n")
    report.append(f"- **视频名称**: {task.video_name}")
    report.append(f"- **任务标识**: `{task.id}`")
    report.append(f"- **视频总时长**: {format_duration(task.duration)}")
    report.append(f"- **分析生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- **分析状态**: {task.current_stage} ({task.status})")

    # 2. 统计指标概览
    report.append("\n## 二、音画义时多模态统计概览\n")
    report.append(f"- **优选关键帧**: {len(frames)} 帧 (课件/板书高精识别)")
    report.append(f"- **语音转写句数**: {len(subtitles)} 句")
    total_words = sum(len(s.text) for s in subtitles)
    report.append(f"- **课堂讲授总字数**: {total_words} 字")
    avg_speed = (total_words / (task.duration / 60.0)) if task.duration > 0 else 0
    report.append(f"- **平均语速**: {avg_speed:.1f} 字/分钟")

    # 3. 加涅九步教学事件时序分期
    report.append("\n## 三、加涅教学事件时序结构分期\n")
    if kg and kg.pedagogical_stages:
        for idx, stage in enumerate(kg.pedagogical_stages, start=1):
            s_name = stage.get("stage", f"阶段 {idx}")
            s_start = stage.get("start_time", "00:00:00")
            s_end = stage.get("end_time", "00:00:00")
            s_desc = stage.get("description", "")
            s_concepts = "、".join(stage.get("concepts", []))
            report.append(f"### {idx}. {s_name} (`{s_start}` ~ `{s_end}`)")
            report.append(f"- **教学特征**: {s_desc}")
            if s_concepts:
                report.append(f"- **核心概念**: {s_concepts}")
            report.append("")
    else:
        report.append("*暂未检测到明确的教学事件分期结构*\n")

    # 4. 关键帧与板书时序对齐表
    report.append("\n## 四、课件关键帧与跨模态对齐明细\n")
    if frames:
        report.append("| 序号 | 物理时间 | 对齐逻辑时间 | 音画漂移 | 场景类别 | 课件/板书文本识别摘要 |")
        report.append("| :---: | :---: | :---: | :---: | :---: | :--- |")
        for idx, f in enumerate(frames, start=1):
            raw_t = f.format_time(f.time_seconds)
            aligned_t = f.format_time(f.aligned_time) if f.aligned_time is not None else raw_t
            drift = f"{f.drift_offset:+.2f}s" if f.drift_offset is not None else "0.00s"
            cat = f.scene_category or "slide"
            ocr_brief = (f.ocr_text or "无显著文字").replace("\n", " ")[:35]
            report.append(f"| {idx} | `{raw_t}` | `{aligned_t}` | `{drift}` | {cat} | {ocr_brief}... |")
    else:
        report.append("*未抽取到有效关键帧*\n")

    # 5. 课堂知识图谱拓扑
    report.append("\n## 五、核心知识图谱概念拓扑\n")
    if kg and kg.graph_data and isinstance(kg.graph_data, dict):
        nodes = kg.graph_data.get("nodes", [])
        links = kg.graph_data.get("links", [])
        report.append(f"- **知识概念节点数**: {len(nodes)} 个")
        report.append(f"- **概念关联边数**: {len(links)} 条")
        report.append("\n**知识概念清单**：")
        for node in nodes:
            tier_str = f"[层级 {node.get('tier', 1)}]" if 'tier' in node else ""
            report.append(f"- {tier_str} **{node.get('name', node.get('id'))}** ({node.get('category', '概念')})")
    else:
        report.append("*暂无关联知识图谱数据*\n")

    # 6. 教学综合诊断与反思建议
    report.append("\n## 六、教学综合诊断与反思\n")
    summary_text = custom_class_summary or (kg.teaching_summary if kg else "") or "教学节奏合理，知识脉络清晰。"
    report.append(f"### 教学脉络总结\n{summary_text}\n")

    if custom_user_reflection:
        report.append(f"### 教师个人反思与评注\n{custom_user_reflection}\n")

    return "\n".join(report)
