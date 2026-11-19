import os
import cv2
import numpy as np
import time
import json
import hashlib
from typing import List, Tuple, Dict

# ===================== Core Algorithms (Extracted from large_video.py) =====================

class TextDensityAnalyzer:
    def __init__(self):
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))

    def calculate_density(self, img: np.ndarray) -> float:
        if img is None: return 0.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gradX = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        gradY = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)
        gradient = cv2.subtract(gradX, gradY)
        gradient = cv2.convertScaleAbs(gradient)
        blurred = cv2.blur(gradient, (9, 9))
        _, thresh = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, self.kernel)
        closed = cv2.erode(closed, None, iterations=4)
        closed = cv2.dilate(closed, None, iterations=4)
        non_zero = cv2.countNonZero(closed)
        h, w = gray.shape
        return non_zero / (h * w)

class VisualSaliency:
    def __init__(self, size=64):
        self.size = size

    def get_saliency_map(self, img: np.ndarray) -> np.ndarray:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_resized = cv2.resize(img_gray, (self.size, self.size))
        my_fft = np.fft.fft2(img_resized)
        my_log_amplitude = np.log(np.abs(my_fft))
        my_phase = np.angle(my_fft)
        avg_log_amp = cv2.blur(my_log_amplitude, (3, 3))
        spectral_residual = my_log_amplitude - avg_log_amp
        saliency_map = np.abs(np.fft.ifft2(np.exp(spectral_residual + 1j * my_phase)))
        saliency_map = cv2.GaussianBlur(saliency_map, (3, 3), 0)
        saliency_map = cv2.resize(saliency_map, (img.shape[1], img.shape[0]))
        cv2.normalize(saliency_map, saliency_map, 0, 1, cv2.NORM_MINMAX)
        return saliency_map

def calculate_image_quality(image: np.ndarray) -> float:
    if image is None: return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.count_nonzero(edges) / edges.size
    clarity_score = min(laplacian_var / 500.0, 1.0)
    content_score = min(edge_density / 0.1, 1.0)
    return 0.7 * clarity_score + 0.3 * content_score

def detect_shot_boundaries(video_path: str, threshold: float = 0.7, step_time: float = 1.0) -> list:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return []
    key_timestamps = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps if fps > 0 else 0
    prev_hist = None
    current_time = 0.0
    while current_time < duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()
        if not ret: break
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        if prev_hist is not None:
            similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            if similarity < threshold:
                key_timestamps.append(current_time)
                current_time += 2.0
                prev_hist = None
                continue
        prev_hist = hist
        current_time += step_time
    cap.release()
    return key_timestamps

def calculate_dhash(image: np.ndarray) -> str:
    if image is None: return ""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    hash_str = ""
    for i in range(8):
        for j in range(8):
            hash_str += '1' if resized[i, j] > resized[i, j + 1] else '0'
    return hash_str

def hamming_distance(h1: str, h2: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))

# ===================== Experiment Implementations =====================

def run_baseline_keyframes(video_path: str, interval: float = 10.0) -> List[Dict]:
    """Baseline: Fixed interval frame extraction"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps if fps > 0 else 0
    
    keyframes = []
    current_time = 0.0
    while current_time < duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()
        if not ret: break
        
        quality = calculate_image_quality(frame)
        keyframes.append({
            "timestamp": current_time,
            "frame": frame.copy(),
            "quality": quality
        })
        current_time += interval
        
    cap.release()
    return keyframes

def run_ours_keyframes(video_path: str) -> List[Dict]:
    """Ours: Shot Boundary + Multi-feature filtering + dHash"""
    saliency_detector = VisualSaliency()
    density_analyzer = TextDensityAnalyzer()
    
    # 1. Shot boundary
    timestamps = detect_shot_boundaries(video_path)
    
    cap = cv2.VideoCapture(video_path)
    raw_keyframes = []
    
    # 2. Multi-feature selection within each shot
    for i, ts in enumerate(timestamps):
        search_window = 2.0
        search_steps = 5
        local_best = None
        local_best_score = -1.0
        
        for step in range(search_steps):
            offset = (step / search_steps) * search_window
            cap.set(cv2.CAP_PROP_POS_MSEC, (ts + offset) * 1000)
            ret, frame = cap.read()
            if not ret: break
            
            q = calculate_image_quality(frame)
            s = np.mean(saliency_detector.get_saliency_map(frame))
            d = density_analyzer.calculate_density(frame)
            
            # Integrated score
            integrated_score = 0.4 * q + 0.3 * s + 0.3 * d
            
            if integrated_score > local_best_score:
                local_best_score = integrated_score
                local_best = {
                    "timestamp": ts + offset,
                    "frame": frame.copy(),
                    "quality": q,
                    "saliency": s,
                    "density": d,
                    "score": integrated_score,
                    "hash": calculate_dhash(frame)
                }
        
        if local_best:
            raw_keyframes.append(local_best)
            
    cap.release()
    
    # 3. dHash De-duplication
    unique_keyframes = []
    if raw_keyframes:
        unique_keyframes.append(raw_keyframes[0])
        for k in raw_keyframes[1:]:
            is_dup = False
            for uk in unique_keyframes:
                dist = hamming_distance(k["hash"], uk["hash"])
                if dist < 10: # threshold 10/64 bits ~ 85%
                    is_dup = True
                    break
            if not is_dup:
                unique_keyframes.append(k)
                
    return unique_keyframes

def evaluate_keyframes(video_path: str):
    print(f"--- Keyframe Extraction Comparison Experiment ---")
    print(f"Video: {video_path}\n")
    
    # 1. Baseline
    start_time = time.time()
    baseline_frames = run_baseline_keyframes(video_path)
    baseline_duration = time.time() - start_time
    
    # 2. Ours
    start_time = time.time()
    ours_frames = run_ours_keyframes(video_path)
    ours_duration = time.time() - start_time
    
    # Calculate Metrics
    def calc_redundancy(frames):
        if not frames: return 0
        hashes = [calculate_dhash(f["frame"]) for f in frames]
        unique_hashes = set(hashes)
        return (len(hashes) - len(unique_hashes)) / len(hashes) if len(hashes) > 0 else 0

    def calc_representativeness(frames):
        # Using average integrated score as representativeness proxy
        if not frames: return 0
        scores = []
        for f in frames:
            q = f.get("quality", calculate_image_quality(f["frame"]))
            scores.append(q)
        return np.mean(scores)

    results = {
        "Baseline": {
            "Count": len(baseline_frames),
            "Redundancy Rate": f"{calc_redundancy(baseline_frames):.2%}",
            "Representativeness Score": f"{calc_representativeness(baseline_frames):.4f}",
            "Time": f"{baseline_duration:.2f}s"
        },
        "Ours": {
            "Count": len(ours_frames),
            "Redundancy Rate": f"{calc_redundancy(ours_frames):.2%}",
            "Representativeness Score": f"{calc_representativeness(ours_frames):.4f}",
            "Time": f"{ours_duration:.2f}s"
        }
    }
    
    import json
    print(json.dumps(results, indent=4, ensure_ascii=False))
    
    # Save results to file
    with open("results_keyframes.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"\nResults saved to results_keyframes.json")

if __name__ == "__main__":
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else ""
    if video and os.path.exists(video):
        evaluate_keyframes(video)
    else:
        print("Usage: python experiment_keyframes.py <video_path>")
