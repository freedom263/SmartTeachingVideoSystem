"""
毕业论文加涅教学事件分期与知识图谱评估实验 (Pedagogical & Knowledge Graph Evaluation)
指标：
1. 加涅九步事件覆盖度 (Gagné Events Coverage)
2. 知识概念抽取 Precision / Recall / F1
3. 拓扑层级深度 (Hierarchy Depth)
"""

from typing import Dict, Any, List


def evaluate_pedagogical_stages(stages: List[Dict[str, Any]]) -> Dict[str, float]:
    """评估加涅事件阶段完整度"""
    standard_events = [
        "引起注意", "告知目标", "回忆旧知", "呈现内容",
        "学习指导", "引发行为", "提供反馈", "评估表现", "强化迁移"
    ]

    matched = 0
    stage_names = " ".join([s.get("stage", "") + s.get("description", "") for s in stages])

    for ev in standard_events:
        if ev in stage_names:
            matched += 1

    coverage = (matched / len(standard_events)) * 100.0
    return {
        "detected_stages_count": len(stages),
        "standard_events_matched": matched,
        "gagne_coverage_pct": round(coverage, 2)
    }


def evaluate_graph_topology(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """评估知识图谱结构特征"""
    nodes = graph_data.get("nodes", [])
    links = graph_data.get("links", [])

    tiers = set(n.get("tier", 1) for n in nodes)
    avg_degree = (2.0 * len(links) / max(len(nodes), 1))

    return {
        "nodes_count": len(nodes),
        "edges_count": len(links),
        "hierarchy_depth": len(tiers),
        "average_node_degree": round(avg_degree, 2)
    }


if __name__ == "__main__":
    print("=== 教学语义图谱结构评测 ===")
    mock_stages = [
        {"stage": "导入与激发旧知引起注意", "description": "告知学习目标"},
        {"stage": "核心概念呈现内容与学习指导", "description": "展开理论"},
        {"stage": "强化迁移复习与评估表现", "description": "课堂小测"}
    ]
    mock_graph = {
        "nodes": [{"id": 1, "tier": 1}, {"id": 2, "tier": 2}, {"id": 3, "tier": 3}],
        "links": [{"source": 1, "target": 2}, {"source": 2, "target": 3}]
    }
    print("加涅事件分期指标:", evaluate_pedagogical_stages(mock_stages))
    print("图谱拓扑指标:", evaluate_graph_topology(mock_graph))
