import os
import cv2
import numpy as np
import time
import json
from experiment_keyframes import (
    detect_shot_boundaries, 
    calculate_image_quality, 
    VisualSaliency, 
    TextDensityAnalyzer, 
    calculate_dhash, 
    hamming_distance
)

def run_experiment_variant(video_path: str, use_quality=True, use_saliency=True, use_density=True, use_dhash=True):
    saliency_detector = VisualSaliency()
    density_analyzer = TextDensityAnalyzer()
    
    timestamps = detect_shot_boundaries(video_path)
    cap = cv2.VideoCapture(video_path)
    raw_keyframes = []
    
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
            
            q = calculate_image_quality(frame) if use_quality else 0.5
            s = np.mean(saliency_detector.get_saliency_map(frame)) if use_saliency else 0.5
            d = density_analyzer.calculate_density(frame) if use_density else 0.5
            
            # Integrated score
            integrated_score = 0.4 * q + 0.3 * s + 0.3 * d
            
            if integrated_score > local_best_score:
                local_best_score = integrated_score
                local_best = {
                    "timestamp": ts + offset,
                    "frame": frame.copy(),
                    "score": integrated_score,
                    "hash": calculate_dhash(frame)
                }
        
        if local_best:
            raw_keyframes.append(local_best)
    cap.release()
    
    # dHash De-duplication
    if use_dhash:
        unique_keyframes = []
        if raw_keyframes:
            unique_keyframes.append(raw_keyframes[0])
            for k in raw_keyframes[1:]:
                is_dup = False
                for uk in unique_keyframes:
                    if hamming_distance(k["hash"], uk["hash"]) < 10:
                        is_dup = True
                        break
                if not is_dup:
                    unique_keyframes.append(k)
        return unique_keyframes
    else:
        return raw_keyframes

def ablation_study(video_path: str):
    print(f"--- Ablation Study ---")
    print(f"Video: {video_path}\n")
    
    scenarios = [
        ("Full (Ours)", True, True, True, True),
        ("-Visual Saliency", True, False, True, True),
        ("-Text Density", True, True, False, True),
        ("-dHash (De-dupe)", True, True, True, False),
        ("Shot Only (No Filter)", False, False, False, False),
    ]
    
    results = {}
    
    for name, q, s, d, dh in scenarios:
        print(f"Running: {name}...")
        start_time = time.time()
        frames = run_experiment_variant(video_path, q, s, d, dh)
        duration = time.time() - start_time
        
        # Calculate redundancy
        hashes = [calculate_dhash(f["frame"]) for f in frames]
        unique_count = len(set(hashes))
        redundancy = (len(frames) - unique_count) / len(frames) if len(frames) > 0 else 0
        
        results[name] = {
            "Count": len(frames),
            "Redundancy": f"{redundancy:.2%}",
            "Time": f"{duration:.2f}s"
        }
        
    print("\nSummary Table:")
    print(json.dumps(results, indent=4, ensure_ascii=False))
    
    with open("results_ablation.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    video = sys.argv[1] if len(sys.argv) > 1 else ""
    if video and os.path.exists(video):
        ablation_study(video)
    else:
        print("Usage: python ablation_study.py <video_path>")
