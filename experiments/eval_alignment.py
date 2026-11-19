"""
毕业论文量化评测实验：跨模态时序对齐精度评测 (Alignment Precision Evaluation)
指标：
1. 平均绝对误差 (Mean Absolute Error, MAE): 对齐后时间戳与人工真值时间戳的误差 (秒)
2. 误差在 ±2秒 内的对齐命中率 (Hit Rate @ 2s)
3. 误差在 ±5秒 内的对齐命中率 (Hit Rate @ 5s)
4. 对齐前后漂移抑制比
"""

import numpy as np
from typing import List, Dict, Any
from core.alignment_engine import AlignmentEngine


def evaluate_alignment_accuracy(
    predicted_alignments: List[Dict[str, Any]],
    ground_truth_alignments: List[Dict[str, float]]
) -> Dict[str, float]:
    """
    计算对齐精度指标
    predicted_alignments: [{"frame_id": 1, "subtitle_id": 10, "aligned_time_diff": 0.5, "is_matched": True}, ...]
    ground_truth_alignments: [{"frame_id": 1, "true_time_drift": 0.4}, ...]
    """
    errors = []
    hits_2s = 0
    hits_5s = 0

    gt_map = {item["frame_id"]: item["true_time_drift"] for item in ground_truth_alignments}

    for pred in predicted_alignments:
        fid = pred.get("frame_id")
        if fid in gt_map:
            true_drift = gt_map[fid]
            pred_drift = pred.get("aligned_time_diff", 0.0)
            err = abs(pred_drift - true_drift)
            errors.append(err)
            if err <= 2.0:
                hits_2s += 1
            if err <= 5.0:
                hits_5s += 1

    total = max(len(errors), 1)
    mae = float(np.mean(errors)) if errors else 0.0
    rmse = float(np.sqrt(np.mean(np.array(errors) ** 2))) if errors else 0.0

    return {
        "sample_count": len(errors),
        "MAE_seconds": round(mae, 3),
        "RMSE_seconds": round(rmse, 3),
        "HitRate_2s_pct": round((hits_2s / total) * 100.0, 2),
        "HitRate_5s_pct": round((hits_5s / total) * 100.0, 2)
    }


if __name__ == "__main__":
    print("=== 跨模态时序对齐精度消融基准测试 ===")
    mock_preds = [
        {"frame_id": 1, "aligned_time_diff": 0.8},
        {"frame_id": 2, "aligned_time_diff": 1.2},
        {"frame_id": 3, "aligned_time_diff": 0.3},
        {"frame_id": 4, "aligned_time_diff": 4.1},
    ]
    mock_gts = [
        {"frame_id": 1, "true_time_drift": 0.5},
        {"frame_id": 2, "true_time_drift": 1.0},
        {"frame_id": 3, "true_time_drift": 0.2},
        {"frame_id": 4, "true_time_drift": 3.8},
    ]
    metrics = evaluate_alignment_accuracy(mock_preds, mock_gts)
    print(f"评测结果: {metrics}")
