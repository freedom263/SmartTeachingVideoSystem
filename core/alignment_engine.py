"""
【核心学术创新】跨模态时序对齐引擎 (Multimodal Alignment Engine)
功能：
1. 视觉流课件 OCR 文本与听觉流转写字幕的语义向量表征 (Embedding)
2. 融合语义相似度与时间邻域约束的跨模态代价矩阵构造
3. 动态时间规整 (Dynamic Time Warping, DTW) 求解最优对齐路径
4. 音画非刚性时序漂移量估计与校正 (Non-rigid Drift Estimation & Correction)
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import config.settings as settings


class AlignmentEngine:
    """跨模态音画义时对齐引擎"""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._embedder = None

    def _get_embedder(self):
        """延迟载入轻量化文本嵌入模型 (BGE / SentenceTransformer)"""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"[Alignment] 载入语义向量模型: {self.model_name}")
                self._embedder = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"[Alignment Warning] 向量模型载入失败或未安装 ({e})，启用语义降级比对")
                self._embedder = "FALLBACK"
        return self._embedder

    def compute_embeddings(self, texts: List[str]) -> np.ndarray:
        """计算一批文本的归一化向量表征"""
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)

        embedder = self._get_embedder()
        if embedder == "FALLBACK" or embedder is None:
            # 离线环境基于字符 n-gram 词袋构建模拟向量
            return self._compute_bow_embeddings(texts)

        try:
            embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return np.array(embeddings, dtype=np.float32)
        except Exception:
            return self._compute_bow_embeddings(texts)

    @staticmethod
    def _compute_bow_embeddings(texts: List[str], dim: int = 128) -> np.ndarray:
        """无大模型依赖下的伪嵌入 (基于字频哈希分布)，保证代码在任何环境均可跑通"""
        vectors = []
        for text in texts:
            vec = np.zeros(dim, dtype=np.float32)
            for ch in text:
                idx = hash(ch) % dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec /= norm
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)

    def align_audio_and_visual(
        self,
        frames: List[Dict[str, Any]],
        subtitles: List[Dict[str, Any]],
        window_sec: float = settings.ALIGNMENT_WINDOW_SECONDS,
        sim_threshold: float = settings.ALIGNMENT_SIMILARITY_THRESHOLD
    ) -> Dict[str, Any]:
        """
        跨模态对齐主算子
        输入：
        - frames: [{"id": 1, "time_seconds": 12.0, "ocr_text": "概念定义..."}, ...]
        - subtitles: [{"id": 10, "start_seconds": 10.5, "end_seconds": 15.0, "text": "讲师口述..."}, ...]

        输出：
        - aligned_frames: 包含更新后的 aligned_time 和 drift_offset
        - alignment_logs: 每对匹配的详细记录
        - average_drift: 平均漂移量
        """
        if not frames or not subtitles:
            return {
                "aligned_frames": frames,
                "alignment_logs": [],
                "average_drift": 0.0
            }

        # 1. 提取有效文本并计算语义嵌入
        frame_texts = [f.get("ocr_text") or "" for f in frames]
        sub_texts = [s.get("text") or "" for s in subtitles]

        frame_emb = self.compute_embeddings(frame_texts)
        sub_emb = self.compute_embeddings(sub_texts)

        # 2. 计算跨模态语义相似度矩阵 S (M x N)
        similarity_matrix = np.dot(frame_emb, sub_emb.T)  # 余弦相似度

        # 3. 构造融合时序惩罚的成本矩阵 C (Cost Matrix)
        n_frames = len(frames)
        n_subs = len(subtitles)
        cost_matrix = np.ones((n_frames, n_subs), dtype=np.float32) * 1e5

        time_weight = 0.02  # 时间差惩罚系数

        for i, f in enumerate(frames):
            f_time = f.get("time_seconds", 0.0)
            for j, s in enumerate(subtitles):
                s_time = (s.get("start_seconds", 0.0) + s.get("end_seconds", 0.0)) / 2.0
                dt = abs(f_time - s_time)
                # 处于时间邻域窗口内
                if dt <= window_sec:
                    sim = float(similarity_matrix[i, j])
                    # 代价 = (1 - 相似度) + 时间漂移惩罚
                    cost = (1.0 - sim) + (dt * time_weight)
                    cost_matrix[i, j] = cost

        # 4. 动态时间规整 (DTW) 最优路径搜索
        path = self._solve_constrained_dtw(cost_matrix)

        # 5. 生成对齐产物与非刚性漂移修正
        alignment_logs = []
        drift_records = []
        frame_aligned_map = {}

        for i, j in path:
            f = frames[i]
            s = subtitles[j]
            f_time = f.get("time_seconds", 0.0)
            s_time = (s.get("start_seconds", 0.0) + s.get("end_seconds", 0.0)) / 2.0
            sim = float(similarity_matrix[i, j])
            raw_diff = s_time - f_time

            is_matched = (sim >= sim_threshold) and (abs(raw_diff) <= settings.MAX_TIME_DRIFT_SECONDS)

            if is_matched:
                drift_records.append(raw_diff)
                if i not in frame_aligned_map:
                    frame_aligned_map[i] = []
                frame_aligned_map[i].append((s_time, raw_diff, sim))

            alignment_logs.append({
                "frame_id": f.get("id"),
                "subtitle_id": s.get("id"),
                "frame_time": f_time,
                "subtitle_time": s_time,
                "similarity_score": round(sim, 4),
                "raw_time_diff": round(raw_diff, 2),
                "aligned_time_diff": round(raw_diff if not is_matched else 0.0, 2),
                "is_matched": is_matched,
                "alignment_type": "dtw"
            })

        # 更新关键帧的校正时间
        aligned_frames = []
        for i, f in enumerate(frames):
            f_copy = dict(f)
            if i in frame_aligned_map and frame_aligned_map[i]:
                # 选取相似度最高的对齐点作为校准基准
                best_match = max(frame_aligned_map[i], key=lambda x: x[2])
                drift = best_match[1]
                f_copy["aligned_time"] = round(f_copy.get("time_seconds", 0.0) + drift, 2)
                f_copy["drift_offset"] = round(drift, 2)
            else:
                f_copy["aligned_time"] = f_copy.get("time_seconds", 0.0)
                f_copy["drift_offset"] = 0.0
            aligned_frames.append(f_copy)

        avg_drift = float(np.mean(np.abs(drift_records))) if drift_records else 0.0

        return {
            "aligned_frames": aligned_frames,
            "alignment_logs": alignment_logs,
            "average_drift": round(avg_drift, 3)
        }

    @staticmethod
    def _solve_constrained_dtw(cost_matrix: np.ndarray) -> List[Tuple[int, int]]:
        """求解带窗动态时间规整最优路径"""
        n, m = cost_matrix.shape
        dp = np.full((n, m), np.inf, dtype=np.float32)
        traceback = np.zeros((n, m, 2), dtype=np.int32)

        dp[0, 0] = cost_matrix[0, 0]

        for i in range(n):
            for j in range(m):
                if i == 0 and j == 0:
                    continue
                candidates = []
                if i > 0 and j > 0:
                    candidates.append((dp[i - 1, j - 1], (i - 1, j - 1)))
                if i > 0:
                    candidates.append((dp[i - 1, j], (i - 1, j)))
                if j > 0:
                    candidates.append((dp[i, j - 1], (i, j - 1)))

                if candidates:
                    min_val, min_idx = min(candidates, key=lambda x: x[0])
                    dp[i, j] = cost_matrix[i, j] + min_val
                    traceback[i, j] = min_idx

        # 回溯寻找路径
        path = []
        curr_i, curr_j = n - 1, m - 1
        while curr_i > 0 or curr_j > 0:
            path.append((curr_i, curr_j))
            prev_i, prev_j = traceback[curr_i, curr_j]
            curr_i, curr_j = prev_i, prev_j
        path.append((0, 0))
        path.reverse()
        return path
