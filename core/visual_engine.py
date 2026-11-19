"""
视觉流核心解析引擎 (Visual Analysis Engine)
功能：
1. HSV 色彩直方图镜头边界切分 (Shot Boundary Detection)
2. 多特征融合加权选优 (清晰度 + 视觉显著性 + 文本密度)
3. dHash 感知哈希与汉明距离去重 (Perceptual Hash Deduplication)
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import config.settings as settings


class VisualEngine:
    """视觉关键帧提取与多特征评分引擎"""

    def __init__(
        self,
        weight_sharpness: float = settings.WEIGHT_SHARPNESS,
        weight_saliency: float = settings.WEIGHT_SALIENCY,
        weight_text_density: float = settings.WEIGHT_TEXT_DENSITY,
        dhash_threshold: float = settings.DHASH_SIMILARITY_THRESHOLD
    ):
        self.w_sharp = weight_sharpness
        self.w_sal = weight_saliency
        self.w_text = weight_text_density
        self.dhash_thresh = dhash_threshold

    # ==================== 特征提取核心算子 ====================

    @staticmethod
    def calculate_sharpness(img_gray: np.ndarray) -> float:
        """清晰度评分：拉普拉斯算子方差"""
        if img_gray is None or img_gray.size == 0:
            return 0.0
        return float(cv2.Laplacian(img_gray, cv2.CV_64F).var())

    @staticmethod
    def calculate_saliency(img_bgr: np.ndarray) -> float:
        """视觉显著性评分：基于频谱残差 (Spectral Residual) 算法"""
        if img_bgr is None or img_bgr.size == 0:
            return 0.0
        try:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (64, 64))
            dft = np.fft.fft2(resized)
            amplitude = np.abs(dft)
            log_amplitude = np.log(amplitude + 1e-6)
            phase = np.angle(dft)

            # 均值滤波获取谱残差
            avg_log_amp = cv2.blur(log_amplitude, (3, 3))
            spectral_residual = log_amplitude - avg_log_amp

            # 傅里叶逆变换
            combined = np.exp(spectral_residual + 1j * phase)
            saliency_map = np.abs(np.fft.ifft2(combined)) ** 2
            saliency_map = cv2.GaussianBlur(saliency_map, (9, 9), 2.5)

            # 归一化与能量值计算
            score = float(np.sum(saliency_map) / (saliency_map.size + 1e-6))
            return min(1.0, score * 10.0)
        except Exception:
            return 0.5

    @staticmethod
    def calculate_text_density(img_gray: np.ndarray) -> float:
        """文本密度评分：课件/板书高频边缘梯度密度分析"""
        if img_gray is None or img_gray.size == 0:
            return 0.0
        try:
            # Sobel 突出水平与垂直字符笔画
            grad_x = cv2.Sobel(img_gray, cv2.CV_16S, 1, 0, ksize=3)
            grad_y = cv2.Sobel(img_gray, cv2.CV_16S, 0, 1, ksize=3)
            abs_grad_x = cv2.convertScaleAbs(grad_x)
            abs_grad_y = cv2.convertScaleAbs(grad_y)
            grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)

            # 二值化统计边缘像素比例
            _, thresh = cv2.threshold(grad, 50, 255, cv2.THRESH_BINARY)
            edge_ratio = np.count_nonzero(thresh) / float(thresh.size)
            # 教学课件通常边缘比例在 0.02 ~ 0.25 之间
            score = min(1.0, edge_ratio * 5.0)
            return float(score)
        except Exception:
            return 0.0

    @staticmethod
    def compute_dhash(image: np.ndarray, hash_size: int = 8) -> str:
        """计算差异哈希 (dHash)"""
        resized = cv2.resize(image, (hash_size + 1, hash_size))
        if len(resized.shape) == 3:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        diff = resized[:, 1:] > resized[:, :-1]
        return "".join(["1" if b else "0" for b in diff.flatten()])

    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """计算两段二进制哈希的汉明距离"""
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

    # ==================== 镜头检测与多特征加权提取流水线 ====================

    def extract_keyframes(
        self,
        video_path: str,
        output_frames_dir: str,
        target_fps: float = settings.DEFAULT_FRAMES_FPS
    ) -> List[Dict[str, Any]]:
        """
        全量关键帧抽取、评分与去重主流程
        """
        os.makedirs(output_frames_dir, exist_ok=True)
        unique_dir = os.path.join(output_frames_dir, "unique")
        os.makedirs(unique_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int(video_fps / max(target_fps, 0.1)))

        raw_candidates = []
        frame_idx = 0
        extracted_count = 0

        prev_hist = None
        current_shot_frames = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                current_time = frame_idx / video_fps
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # 计算 HSV 直方图用于镜头切点检测
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [12, 12], [0, 180, 0, 256])
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                is_cut = False
                if prev_hist is not None:
                    similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    if similarity < settings.SHOT_HSV_THRESHOLD:
                        is_cut = True
                prev_hist = hist

                # 计算特征得分
                sharp = self.calculate_sharpness(gray)
                sal = self.calculate_saliency(frame)
                text_den = self.calculate_text_density(gray)

                frame_info = {
                    "time_seconds": current_time,
                    "frame_bgr": frame,
                    "gray": gray,
                    "sharpness": sharp,
                    "saliency": sal,
                    "text_density": text_den
                }
                current_shot_frames.append(frame_info)

                # 镜头切换或累计达到上限时，在当前镜头内优选 1 张最佳帧
                if is_cut and len(current_shot_frames) > 1:
                    best = self._select_best_frame(current_shot_frames[:-1])
                    if best:
                        raw_candidates.append(best)
                    current_shot_frames = [current_shot_frames[-1]]

            frame_idx += 1

        # 收尾镜头
        if current_shot_frames:
            best = self._select_best_frame(current_shot_frames)
            if best:
                raw_candidates.append(best)

        cap.release()

        # 对优选候选帧执行 dHash 去重并持久化到磁盘
        results = self._deduplicate_and_save(raw_candidates, output_frames_dir, unique_dir)
        return results

    def _select_best_frame(self, frame_candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """在单镜头所有采样帧中，依据三要素加权评分挑选最佳帧"""
        if not frame_candidates:
            return None

        # 归一化清晰度
        sharp_vals = [f["sharpness"] for f in frame_candidates]
        max_s = max(sharp_vals) if sharp_vals else 1.0
        min_s = min(sharp_vals) if sharp_vals else 0.0
        range_s = max_s - min_s if max_s > min_s else 1.0

        for f in frame_candidates:
            s_norm = (f["sharpness"] - min_s) / range_s
            comp = (
                self.w_sharp * s_norm +
                self.w_sal * f["saliency"] +
                self.w_text * f["text_density"]
            )
            f["composite"] = comp

        # 选出最高综合分者
        frame_candidates.sort(key=lambda x: x["composite"], reverse=True)
        return frame_candidates[0]

    def _deduplicate_and_save(
        self,
        candidates: List[Dict[str, Any]],
        frames_dir: str,
        unique_dir: str
    ) -> List[Dict[str, Any]]:
        """dHash 去重与磁盘落盘"""
        results = []
        unique_hashes = []

        for idx, item in enumerate(candidates, start=1):
            frame = item["frame_bgr"]
            t_sec = item["time_seconds"]
            filename = f"frame_{idx:04d}_{int(t_sec)}s.jpg"
            file_path = os.path.join(frames_dir, filename)

            # 保存图片
            cv2.imwrite(file_path, frame)

            # 计算 dHash
            cur_hash = self.compute_dhash(frame)
            is_unique = True
            for u_h in unique_hashes:
                dist = self.hamming_distance(cur_hash, u_h)
                sim = 1.0 - (dist / 64.0)
                if sim >= self.dhash_thresh:
                    is_unique = False
                    break

            if is_unique:
                unique_hashes.append(cur_hash)
                unique_path = os.path.join(unique_dir, filename)
                cv2.imwrite(unique_path, frame)

            results.append({
                "filename": filename,
                "time_seconds": round(t_sec, 2),
                "url_path": f"/outputs/{os.path.basename(os.path.dirname(frames_dir))}/frames/{filename}",
                "saliency": round(item["saliency"], 3),
                "density": round(item["text_density"], 3),
                "quality": round(item["sharpness"], 1),
                "composite": round(item.get("composite", 0.0), 3),
                "is_unique": is_unique
            })

        return results
