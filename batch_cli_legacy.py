# -*- coding: utf-8 -*-
"""
多视频解析：音频提取(+多格式)、（可选）人声分离、字幕（内嵌->ROI 智能 OCR 回退）、抽帧与关键帧、报告
Windows 友好：修复子进程 GBK 解码；统一“视频名-xxx”命名；自动探测 Tesseract/tessdata
"""

import os
import sys
import re
import json
import difflib
import platform
import subprocess
from typing import Tuple, List, Optional

import cv2
import numpy as np
from PIL import Image
import pytesseract
from shutil import which

# ========== 你可以按需修改 ==========
# VIDEO_PATH = r'E:\SchoolFiles\competetion\工坊校级项目\视频拆解\video\永远的番号.mp4'
VIDEO_PATH = r'E:\SchoolFiles\competetion\工坊校级项目\视频拆解\video\草船借箭.mp4'
OUTPUT_ROOT = r'E:\SchoolFiles\competetion\工坊校级项目\视频拆解\output_video'
SPLEETER_WORKDIR = None  # 可留 None
# ==================================


# ----------------- Tesseract 自动探测 -----------------
def _file_exists(p): return bool(p and os.path.exists(p))

def detect_tesseract() -> Tuple[Optional[str], Optional[str], List[str]]:
    candidates_exe = []
    if hasattr(pytesseract.pytesseract, "tesseract_cmd"):
        tc = pytesseract.pytesseract.tesseract_cmd
        if _file_exists(tc): candidates_exe.append(tc)

    w = which("tesseract")
    if _file_exists(w): candidates_exe.append(w)

    common_exe = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(sys.prefix, "Library", "bin", "tesseract.exe"),
        os.path.join(sys.prefix, "Scripts", "tesseract.exe"),
    ]
    for p in common_exe:
        if _file_exists(p): candidates_exe.append(p)

    tesseract_exe = None
    for p in candidates_exe:
        if _file_exists(p):
            tesseract_exe = p
            break

    candidates_tessdata = []
    if os.environ.get("TESSDATA_PREFIX"):
        candidates_tessdata.append(os.environ["TESSDATA_PREFIX"])
    if tesseract_exe:
        d = os.path.dirname(tesseract_exe)
        candidates_tessdata += [
            os.path.join(d, "tessdata"),
            os.path.join(d, "..", "share", "tessdata"),
            os.path.join(d, "..", "tessdata"),
        ]
    candidates_tessdata += [
        os.path.join(sys.prefix, "Library", "share", "tessdata"),
        os.path.join(sys.prefix, "share", "tessdata"),
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
    ]

    tessdata_dir = None
    for p in candidates_tessdata:
        if _file_exists(p) and os.path.isdir(p):
            tessdata_dir = os.path.abspath(p)
            break

    available_langs = []
    if tessdata_dir and os.path.isdir(tessdata_dir):
        try:
            for fn in os.listdir(tessdata_dir):
                if fn.endswith(".traineddata"):
                    available_langs.append(fn[:-12])
        except Exception:
            pass

    return tesseract_exe, tessdata_dir, sorted(set(available_langs))

def configure_tesseract_or_die():
    exe, data_dir, langs = detect_tesseract()
    if not exe:
        raise RuntimeError(
            "未找到 Tesseract 可执行文件。请安装后再试。\n"
            "Conda：conda install -c conda-forge tesseract\n"
            "Win 安装包：https://github.com/UB-Mannheim/tesseract/wiki"
        )
    pytesseract.pytesseract.tesseract_cmd = exe
    if data_dir and os.path.isdir(data_dir):
        os.environ["TESSDATA_PREFIX"] = data_dir

    lang_pair = None
    if "chi_sim" in langs and "eng" in langs:
        lang_pair = "chi_sim+eng"
    elif "eng" in langs:
        lang_pair = "eng"
    elif "chi_sim" in langs:
        lang_pair = "chi_sim"
    if not lang_pair:
        raise RuntimeError(
            "未找到所需语言数据（chi_sim/eng）。\n"
            f"当前 tessdata：{data_dir or '未知'}；已发现：{', '.join(langs) if langs else '无'}\n"
            "Conda：conda install -c conda-forge tesseract-data-chi-sim tesseract-data-eng"
        )
    return exe, data_dir, lang_pair

try:
    TESSERACT_EXE, TESSDATA_DIR, OCR_LANGS = configure_tesseract_or_die()
    print(f"[Tesseract] exe = {TESSERACT_EXE}")
    print(f"[Tesseract] tessdata = {TESSDATA_DIR}")
    print(f"[Tesseract] langs = {OCR_LANGS}")
except Exception as e:
    print("Tesseract 配置失败：", e)
    sys.exit(1)


# ----------------- 通用工具 -----------------
def run_cmd(args: List[str],
            cwd: Optional[str] = None,
            timeout: Optional[int] = None,
            env: Optional[dict] = None) -> Tuple[int, str, str]:
    startupinfo = None
    if platform.system().lower().startswith("win"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    proc = subprocess.run(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        startupinfo=startupinfo,
        env=env
    )

    def _safe_decode(b: bytes) -> str:
        if not b:
            return ""
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            try:
                return b.decode("gbk", errors="ignore")
            except Exception:
                return b.decode(errors="ignore")

    out = _safe_decode(proc.stdout)
    err = _safe_decode(proc.stderr)
    return proc.returncode, out, err

def slug_from_video(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r'[\\/:*?"<>|]+', '_', name)

def build_paths(video_path: str) -> dict:
    stem = slug_from_video(video_path)
    work_dir = os.path.join(OUTPUT_ROOT, stem)
    frames_dir = os.path.join(work_dir, f'{stem}-frames')
    audio_formats_dir = os.path.join(work_dir, 'audio_formats')
    paths = {
        "stem": stem,
        "work_dir": work_dir,
        "frames_dir": frames_dir,
        "audio_formats_dir": audio_formats_dir,
        "audio_wav": os.path.join(work_dir, f'{stem}-audio.wav'),
        "vocals": os.path.join(work_dir, f'{stem}-vocals.wav'),
        "acc": os.path.join(work_dir, f'{stem}-accompaniment.wav'),
        "srt": os.path.join(work_dir, f'{stem}-subtitles.srt'),
        "ocr_txt": os.path.join(work_dir, f'{stem}-ocr.txt'),
        "report": os.path.join(work_dir, f'{stem}-report.txt'),
        "keyframes_dir": os.path.join(work_dir, f'{stem}-keyframes'),
        "roi_preview": os.path.join(work_dir, f'{stem}-roi_preview.jpg'),
    }
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(paths["keyframes_dir"], exist_ok=True)
    os.makedirs(audio_formats_dir, exist_ok=True)
    return paths


# ----------------- 音频提取与多格式导出 -----------------
def extract_audio(video_path: str, output_audio_path: str) -> bool:
    if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 0:
        print("音频已存在，跳过提取")
        return True
    code, _, err = run_cmd([
        'ffmpeg', '-y', '-i', video_path, '-vn',
        '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
        output_audio_path
    ], timeout=600)
    if code != 0:
        print("音频提取失败：", err)
        return False
    print("音频提取完成：", output_audio_path)
    return True

def export_audio_formats(wav_path: str, out_dir: str, stem: str):
    """
    从主 WAV 生成多格式：mp3(192k)、m4a(aac 128k)、flac、ogg
    """
    targets = [
        (os.path.join(out_dir, f"{stem}.mp3"),  ['-codec:a', 'libmp3lame', '-b:a', '192k']),
        (os.path.join(out_dir, f"{stem}.m4a"),  ['-codec:a', 'aac',       '-b:a', '128k']),
        (os.path.join(out_dir, f"{stem}.flac"), ['-codec:a', 'flac']),
        (os.path.join(out_dir, f"{stem}.ogg"),  ['-codec:a', 'libvorbis', '-q:a', '5']),
    ]
    for out_path, opts in targets:
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            continue
        code, _, err = run_cmd(['ffmpeg', '-y', '-i', wav_path] + opts + [out_path], timeout=600)
        if code == 0:
            print("音频导出：", out_path)
        else:
            print("音频导出失败：", out_path, err)


# ----------------- 字幕：内嵌优先，失败回退“ROI+多策略 OCR” -----------------
def probe_subtitle_streams(video_path: str) -> list:
    rc, out, _ = run_cmd([
        'ffprobe', '-v', 'error',
        '-select_streams', 's',
        '-show_entries', 'stream=index,codec_name,codec_type:stream_tags=language,title',
        '-of', 'json',
        video_path
    ], timeout=30)
    if rc != 0:
        return []
    try:
        data = json.loads(out or "{}")
        return data.get("streams", []) or []
    except Exception:
        return []

def try_extract_text_subs(video_path: str, srt_path: str) -> bool:
    streams = probe_subtitle_streams(video_path)
    if not streams:
        return False
    sidx = streams[0].get("index", 0)
    rc, _, _ = run_cmd([
        'ffmpeg', '-y', '-i', video_path,
        '-map', f'0:s:{sidx}', '-c:s', 'srt',
        srt_path
    ], timeout=300)
    if rc == 0 and os.path.isfile(srt_path) and os.path.getsize(srt_path) > 0:
        return True
    rc2, _, _ = run_cmd([
        'ffmpeg', '-y', '-i', video_path,
        '-map', '0:s?', '-c:s', 'srt',
        srt_path
    ], timeout=300)
    return rc2 == 0 and os.path.isfile(srt_path) and os.path.getsize(srt_path) > 0

def fmt_ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hh = int(seconds // 3600)
    mm = int((seconds % 3600) // 60)
    ss = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

# —— 多种预处理（轮询尝试）——
def prep_variants(gray: np.ndarray) -> List[np.ndarray]:
    outs = []
    outs.append(gray)
    outs.append(cv2.equalizeHist(gray))  # 直方图均衡

    # 原阈值方法
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 31, 15)
    outs.append(thr)
    outs.append(cv2.bitwise_not(thr))

    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    outs.append(otsu)
    outs.append(cv2.bitwise_not(otsu))

    # 增加边缘强调
    k = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(gray, -1, k)
    outs.append(sharp)

    return outs


def tesseract_data_with_conf(img_bin: np.ndarray, psm_list=(6,7,11)) -> Tuple[str, float]:
    """
    返回 (最佳文本, 平均置信度)
    """
    best_txt, best_conf = "", -1.0
    for psm in psm_list:
        config = f'--oem 3 --psm {psm} -l {OCR_LANGS} --tessdata-dir "{os.environ.get("TESSDATA_PREFIX","")}"'
        try:
            data = pytesseract.image_to_data(img_bin, config=config, output_type=pytesseract.Output.DICT)
        except Exception:
            # 兜底
            data = pytesseract.image_to_data(img_bin, config=f'--oem 3 --psm {psm} -l {OCR_LANGS}', output_type=pytesseract.Output.DICT)
        words = []
        confs = []
        for w, c in zip(data.get('text', []), data.get('conf', [])):
            if w and w.strip() and str(c).isdigit():
                words.append(w.strip())
                confs.append(int(c))
        if words and confs:
            txt = ' '.join(words)
            conf = float(np.mean(confs))
            if conf > best_conf:
                best_conf, best_txt = conf, txt
    return best_txt.strip(), best_conf

def ocr_once_best_text(bgr: np.ndarray) -> Tuple[str, float]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    candidates = prep_variants(gray)
    best_txt, best_conf = "", -1.0
    for cand in candidates:
        txt, conf = tesseract_data_with_conf(cand)
        if conf > best_conf:
            best_txt, best_conf = txt, conf
    # 清洗（中文保留）
    txt = best_txt
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r'[\u200b-\u200f\u202a-\u202e]+', '', txt).strip()
    return txt, (best_conf if best_conf >= 0 else 0.0)

def find_best_subtitle_roi(video_path: str, save_preview: Optional[str] = None) -> Optional[tuple]:
    """
    在视频下半区域扫描多条水平带状 ROI，返回最优 ROI (x,y,w,h)
    评估指标：若干采样帧上，OCR 平均置信度*文本长度 最大
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if w == 0 or h == 0 or total == 0:
        cap.release()
        return None

    # 在下半屏（h*0.45~h*0.95）之间扫描多条带（高度约 h*0.12）
    band_h = max(40, int(h * 0.12))
    y_starts = list(range(int(h*0.45), int(h*0.95 - band_h), max(10, int(band_h * 0.25))))
    rois = [(int(w*0.05), y, int(w*0.90), band_h) for y in y_starts]  # 左右留边

    # 采样 20 帧：前中后各取若干
    sample_idx = []
    for p in [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]:
        i = int(total * p)
        if 0 <= i < total:
            sample_idx.append(i)
    sample_idx = sorted(set(sample_idx))[:20]

    best_score, best_roi = -1.0, None
    for (rx, ry, rw, rh) in rois:
        scores = []
        for i in sample_idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if not ok: continue
            roi = frame[ry:ry+rh, rx:rx+rw].copy()
            txt, conf = ocr_once_best_text(roi)
            if txt:
                # 分数：平均置信度 * 文本长度（中文不计空格）
                score = conf * max(1, len(re.sub(r'\s+', '', txt)))
                scores.append(score)
        if scores:
            avg = float(np.mean(scores))
            if avg > best_score:
                best_score, best_roi = avg, (rx, ry, rw, rh)
    cap.release()

    # 导出预览图（画出 ROI）
    if save_preview and best_roi:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_idx[len(sample_idx)//2] if sample_idx else 0)
        ok, frame = cap.read()
        cap.release()
        if ok:
            x,y,rw,rh = best_roi
            vis = frame.copy()
            cv2.rectangle(vis, (x,y), (x+rw,y+rh), (0,255,0), 2)
            cv2.imwrite(save_preview, vis)

    return best_roi

def sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def ocr_subtitles_to_srt(video_path: str, srt_path: str, ocr_txt_path: str,
                         sample_fps: float = 2.0, min_chars: int = 2, sim_thresh: float = 0.80,
                         roi_hint: Optional[tuple] = None) -> bool:
    """
    ROI + 多策略 OCR：默认 2fps；更宽松的过滤与相似度合并。
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("无法打开视频进行 OCR")
        return False

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(round(src_fps / max(sample_fps, 0.1))))

    if os.path.exists(srt_path):
        try: os.remove(srt_path)
        except Exception: pass

    idx = -1
    sub_idx = 0
    cur_text, cur_start_f = None, None
    ocr_lines = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        if idx % step != 0:
            continue

        # 先裁 ROI（如果有）
        if roi_hint:
            x,y,rw,rh = roi_hint
            roi = frame[y:y+rh, x:x+rw]
            if roi is None or roi.size == 0:
                roi = frame
        else:
            roi = frame

        txt, conf = ocr_once_best_text(roi)
        if txt:
            ocr_lines.append(f"[{fmt_ts(idx/src_fps)}] {txt} | conf≈{conf:.1f}")

        # 过滤非空 & 最短长度
        if not txt or len(re.sub(r'\s+', '', txt)) < min_chars:
            if cur_text is not None:
                start_ts = fmt_ts(cur_start_f / src_fps)
                end_ts = fmt_ts(idx / src_fps)
                sub_idx += 1
                with open(srt_path, 'a', encoding='utf-8') as srt:
                    srt.write(f"{sub_idx}\n{start_ts} --> {end_ts}\n{cur_text}\n\n")
                cur_text, cur_start_f = None, None
            continue

        if cur_text is None:
            cur_text, cur_start_f = txt, idx
        else:
            if sim(txt, cur_text) >= sim_thresh:
                # 同一句延长
                pass
            else:
                # 结束上一句
                start_ts = fmt_ts(cur_start_f / src_fps)
                end_ts = fmt_ts(idx / src_fps)
                sub_idx += 1
                with open(srt_path, 'a', encoding='utf-8') as srt:
                    srt.write(f"{sub_idx}\n{start_ts} --> {end_ts}\n{cur_text}\n\n")
                cur_text, cur_start_f = txt, idx

    if cur_text is not None:
        start_ts = fmt_ts(cur_start_f / src_fps)
        end_ts = fmt_ts((idx + 1) / src_fps)
        sub_idx += 1
        with open(srt_path, 'a', encoding='utf-8') as srt:
            srt.write(f"{sub_idx}\n{start_ts} --> {end_ts}\n{cur_text}\n\n")

    cap.release()

    if ocr_txt_path:
        with open(ocr_txt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(ocr_lines))

    ok = os.path.isfile(srt_path) and os.path.getsize(srt_path) > 0
    print("OCR 生成 SRT", "成功" if ok else "失败")
    return ok

def extract_subtitles(video_path: str, srt_path: str,
                      ocr_txt_path: Optional[str] = None,
                      roi_preview_path: Optional[str] = None) -> bool:
    """
    提取字幕：优先内嵌字幕 -> 失败则 ROI+OCR
    """
    # 1) 内嵌字幕
    if try_extract_text_subs(video_path, srt_path):
        print("字幕提取成功（内嵌）:", srt_path)
        return True

    print("未检测到可用内嵌字幕，转 OCR 回退...")

    # 2) OCR ROI 定位
    roi = find_best_subtitle_roi(video_path, save_preview=roi_preview_path)
    if roi:
        print("检测到最佳 ROI:", roi)
    else:
        print("未能检测到有效 ROI，将对整帧做 OCR")

    # 3) OCR 生成 SRT
    ok = ocr_subtitles_to_srt(video_path, srt_path, ocr_txt_path, roi_hint=roi)
    return ok



# ----------------- 抽帧/关键帧 -----------------
def extract_frames(video_path: str, frames_dir: str, stem: str, fps: float = 0.5) -> bool:
    save_pattern = os.path.join(frames_dir, f'{stem}-frame_%04d.jpg')
    rc, _, err = run_cmd([
        'ffmpeg', '-y', '-i', video_path,
        '-vf', f'fps={fps}',
        '-qscale:v', '2',
        save_pattern
    ], timeout=600)
    if rc != 0:
        print("帧提取失败：", err)
        return False
    print("帧提取完成：", frames_dir)
    return True

def analyze_frames_and_save_keyframes(video_path: str, keyframes_dir: str) -> int:
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("无法打开视频文件")
            return 0
        ret, prev_frame = cap.read()
        if not ret:
            return 0
        frame_count = 0
        keyframe_count = 0
        while True:
            ret, curr_frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if frame_count % 30 == 0 and prev_frame is not None and curr_frame is not None:
                prev_resized = cv2.resize(prev_frame, (320, 240))
                curr_resized = cv2.resize(curr_frame, (320, 240))
                prev_gray = cv2.cvtColor(prev_resized, cv2.COLOR_BGR2GRAY)
                curr_gray = cv2.cvtColor(curr_resized, cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(prev_gray, curr_gray)
                non_zero_count = cv2.countNonZero(diff)
                if non_zero_count > 5000:
                    keyframe_count += 1
                    path = os.path.join(keyframes_dir, f'keyframe_{keyframe_count:04d}.jpg')
                    cv2.imwrite(path, curr_frame)
                prev_frame = curr_frame
        cap.release()
        print(f"关键帧数：{keyframe_count}")
        return keyframe_count
    except Exception as e:
        print("关键帧分析失败：", e)
        return 0


# ----------------- 主流程 -----------------
def process_video(video_path: str) -> bool:
    print("\n开始处理视频：", video_path)
    P = build_paths(video_path)

    try:
        audio_ok = extract_audio(video_path, P["audio_wav"])

        # 音频多格式导出
        if audio_ok:
            export_audio_formats(P["audio_wav"], P["audio_formats_dir"], P["stem"])

        # （可选）人声分离，默认关闭
        # sep_ok = separate_audio_w_spleeter(P["audio_wav"], P["vocals"], P["acc"])
        sep_ok = False

        subs_ok = extract_subtitles(video_path, P["srt"], P["ocr_txt"], P["roi_preview"])

        frames_ok = extract_frames(video_path, P["frames_dir"], P["stem"], fps=0.5)

        keyframes_n = analyze_frames_and_save_keyframes(video_path, P["keyframes_dir"])

        # 报告
        with open(P["report"], 'w', encoding='utf-8') as f:
            f.write(f"视频：{os.path.basename(video_path)}\n")
            f.write("=" * 60 + "\n")
            f.write(f"音频提取：{'成功' if audio_ok else '失败'}\n")
            f.write(f"音频多格式：{P['audio_formats_dir']}\n")
            f.write(f"音频分离：{'成功' if sep_ok else '未执行/失败'}\n")
            f.write(f"字幕输出：{'成功' if subs_ok else '失败或无字幕'} —— {P['srt']}\n")
            if os.path.exists(P["roi_preview"]):
                f.write(f"字幕ROI预览：{P['roi_preview']}\n")
            f.write(f"抽帧输出：{'成功' if frames_ok else '失败'} —— {P['frames_dir']}\n")
            f.write(f"关键帧数量：{keyframes_n} —— {P['keyframes_dir']}\n")
            f.write("=" * 60 + "\n")

        print("处理完成，结果目录：", P["work_dir"])
        return True

    except Exception as e:
        print("处理过程中出现异常：", e)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = process_video(VIDEO_PATH)

    # 批量处理示例（取消注释）
    # INPUT_DIR = r'E:\SchoolFiles\competetion\工坊校级项目\视频拆解\video'
    # for name in os.listdir(INPUT_DIR):
    #     if name.lower().endswith(('.mp4', '.mkv', '.mov', '.avi')):
    #         process_video(os.path.join(INPUT_DIR, name))

    sys.exit(0 if ok else 1)
