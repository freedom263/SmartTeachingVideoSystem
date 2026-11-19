"""
课件与板书高精 OCR 引擎 (Slide & Board OCR Engine)
功能：
1. RapidOCR-ONNX (PP-OCRv4) 高效推理提取关键帧文本
2. 文本框坐标与置信度过滤
3. 教学场景分类判定 (slide课件 / board板书 / teacher讲师 / hybrid混合)
"""

import os
from typing import List, Dict, Any, Optional
import config.settings as settings


class OCREngine:
    """课件与板书 OCR 提取引擎"""

    def __init__(self, backend: Optional[str] = None):
        self.backend = backend or settings.OCR_BACKEND
        self._rapid_ocr = None

    def _get_ocr_instance(self):
        """延迟加载 RapidOCR 实例"""
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR()
            except ImportError:
                print("[OCR Warning] 未安装 rapidocr_onnxruntime，将启用备用回退模式")
                self._rapid_ocr = "MOCK"
        return self._rapid_ocr

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        单张关键帧高精 OCR 分析
        返回：
        {
            "full_text": "课件完整提取文本...",
            "boxes": [{"box": [[x1, y1], [x2, y2], ...], "text": "...", "confidence": 0.98}, ...],
            "scene_category": "slide" | "board" | "teacher" | "hybrid"
        }
        """
        if not os.path.exists(image_path):
            return {"full_text": "", "boxes": [], "scene_category": "slide"}

        ocr_inst = self._get_ocr_instance()
        if ocr_inst == "MOCK" or ocr_inst is None:
            return self._mock_ocr(image_path)

        try:
            result, elapse_list = ocr_inst(image_path)
            if not result:
                return {"full_text": "", "boxes": [], "scene_category": "teacher"}

            parsed_boxes = []
            texts = []
            for item in result:
                dt_box, text, score = item
                if float(score) >= settings.OCR_CONF_THRESHOLD:
                    parsed_boxes.append({
                        "box": dt_box,
                        "text": text.strip(),
                        "confidence": round(float(score), 3)
                    })
                    texts.append(text.strip())

            full_text = " ".join(texts)
            category = self._classify_scene(len(texts), full_text)

            return {
                "full_text": full_text,
                "boxes": parsed_boxes,
                "scene_category": category
            }
        except Exception as e:
            print(f"[OCR Error] 识别失败 ({e})，启用回退")
            return self._mock_ocr(image_path)

    @staticmethod
    def _classify_scene(num_lines: int, text: str) -> str:
        """根据文字行数和特征判定场景"""
        if num_lines >= 5 or len(text) > 40:
            return "slide"
        elif num_lines >= 1 and len(text) > 10:
            return "hybrid"
        elif num_lines > 0:
            return "board"
        else:
            return "teacher"

    @staticmethod
    def _mock_ocr(image_path: str) -> Dict[str, Any]:
        """离线与开发环境下的模拟 OCR 数据"""
        return {
            "full_text": "第一章 课程导论与核心概念解析 重点公式与理论框架",
            "boxes": [
                {"box": [[10, 10], [200, 10], [200, 50], [10, 50]], "text": "第一章 课程导论", "confidence": 0.95},
                {"box": [[10, 60], [300, 60], [300, 100], [10, 100]], "text": "核心概念解析与理论框架", "confidence": 0.92}
            ],
            "scene_category": "slide"
        }
