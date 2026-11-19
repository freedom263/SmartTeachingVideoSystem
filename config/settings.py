"""
全局系统配置 (Global System Settings)
基于音画义时关联的教学视频智能解析系统
"""

import os
from pathlib import Path

# ==================== 基础路径配置 ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# 输出与媒体根目录
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", BASE_DIR / "outputs"))
UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", OUTPUT_ROOT / "uploads"))
TEMP_FRAMES_ROOT = Path(os.environ.get("TEMP_FRAMES_ROOT", BASE_DIR / "temp_frames"))
STATIC_ROOT = BASE_DIR / "static"

# 自动创建目录
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
TEMP_FRAMES_ROOT.mkdir(parents=True, exist_ok=True)

# ==================== 数据库与安全 ====================
DATABASE_FILE = OUTPUT_ROOT / "teaching_video_system.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATABASE_FILE.as_posix()}")

SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# ==================== ①+② 听觉流 (Audio & ASR) ====================
# ASR后端选择: 'faster-whisper' (推荐, RTX 5060本地) 或 'baidu' (备用)
ASR_BACKEND = os.environ.get("ASR_BACKEND", "faster-whisper")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")  # 或 'medium'
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")           # 'cuda' 或 'cpu'
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "float16") # 'float16' 或 'int8_float16'

# 百度 ASR 凭证 (备用)
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")

# VAD 语音活动检测参数
VAD_FRAME_DURATION_MS = 30
VAD_ENERGY_THRESHOLD = 0.015
VAD_MIN_SPEECH_DURATION_MS = 250
VAD_MIN_SILENCE_DURATION_MS = 300

# ==================== ①+② 视觉流 (Visual & Keyframes) ====================
DEFAULT_FRAMES_FPS = float(os.environ.get("FRAMES_FPS", "1.0"))
SHOT_HSV_THRESHOLD = float(os.environ.get("SHOT_HSV_THRESHOLD", "0.35"))
DHASH_SIMILARITY_THRESHOLD = float(os.environ.get("DHASH_SIMILARITY_THRESHOLD", "0.85"))

# 关键帧三要素加权评分权重: 清晰度 + 视觉显著性 + 文本密度 = 1.0
WEIGHT_SHARPNESS = float(os.environ.get("WEIGHT_SHARPNESS", "0.40"))
WEIGHT_SALIENCY = float(os.environ.get("WEIGHT_SALIENCY", "0.30"))
WEIGHT_TEXT_DENSITY = float(os.environ.get("WEIGHT_TEXT_DENSITY", "0.30"))

# ==================== ③ 课件与板书 OCR (RapidOCR) ====================
OCR_BACKEND = os.environ.get("OCR_BACKEND", "rapidocr")
OCR_USE_GPU = os.environ.get("OCR_USE_GPU", "false").lower() in ("true", "1")
OCR_CONF_THRESHOLD = float(os.environ.get("OCR_CONF_THRESHOLD", "0.60"))

# ==================== ③ 跨模态时序对齐 (Alignment & DTW) ====================
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
ALIGNMENT_WINDOW_SECONDS = float(os.environ.get("ALIGNMENT_WINDOW_SECONDS", "30.0"))  # DTW搜索邻域
ALIGNMENT_SIMILARITY_THRESHOLD = float(os.environ.get("ALIGNMENT_SIMILARITY_THRESHOLD", "0.45"))
MAX_TIME_DRIFT_SECONDS = float(os.environ.get("MAX_TIME_DRIFT_SECONDS", "15.0"))

# ==================== ④ 语义重构与知识图谱 (Semantic & LLM) ====================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
MAX_CONTEXT_TOKENS = int(os.environ.get("MAX_CONTEXT_TOKENS", "32000"))
