#!/usr/bin/env python3
import argparse
import os
import sys
import cv2
import numpy as np
import json
from datetime import datetime

def compute_colorfulness(frame):
    # Convert to float for computation
    b, g, r = cv2.split(frame.astype('float'))
    # Compute RG and YB components
    rg = r - g
    yb = 0.5 * (r + g) - b
    # Compute statistics
    std_rg, std_yb = np.std(rg), np.std(yb)
    mean_rg, mean_yb = np.mean(rg), np.mean(yb)
    # Colorfulness metric
    return np.sqrt(std_rg**2 + std_yb**2) + 0.3 * np.sqrt(mean_rg**2 + mean_yb**2)

def sample_frames(video_path, max_frames=30):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total_frames // max_frames)
    frames = []
    for idx in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        # Resize frame to width=256, keep aspect ratio
        h, w = frame.shape[:2]
        new_w = 256
        new_h = int(h * (256 / w))
        frame = cv2.resize(frame, (new_w, new_h))
        frames.append(frame)
    cap.release()
    return frames

def main():
    parser = argparse.ArgumentParser(description="Evaluate video colorfulness (detect non-BW video).")
    parser.add_argument("--output", type=str, required=True,
                        help="Path to the input video file.")
    parser.add_argument("--threshold", type=float, default=10.0,
                        help="Colorfulness threshold for pass/fail (default: 10.0).")
    parser.add_argument("--result", help="Path to append the jsonl result.")
    args = parser.parse_args()

    input_path = args.output
    process_ok = False
    results_ok = False
    comments = []

    # Check file existence and basic validity
    if not os.path.exists(input_path):
        comments.append(f"Input file not found: {input_path}")
    elif os.path.getsize(input_path) == 0:
        comments.append(f"Input file is empty: {input_path}")
    else:
        ext = os.path.splitext(input_path)[1].lower()
        if ext not in ['.mp4', '.avi', '.mov', '.mkv']:
            comments.append(f"Unsupported file format: {ext}")
        else:
            process_ok = True

    if process_ok:
        frames = sample_frames(input_path)
        if not frames:
            comments.append("Failed to read any frames from video.")
        else:
            scores = [compute_colorfulness(f) for f in frames]
            avg_score = float(np.mean(scores))
            comments.append(f"Average colorfulness: {avg_score:.2f}")
            results_ok = avg_score > args.threshold
            comments.append("Pass" if results_ok else "Fail")

    # Print result
    print("=== Evaluation ===")
    print("Process OK: ", process_ok)
    if process_ok:
        print("Result OK:  ", results_ok)
    for c in comments:
        print(c)

    # Append to jsonl
    if args.result:
        record = {
            "Process": process_ok,
            "Result": results_ok,
            "TimePoint": datetime.now().isoformat(),
            "comments": "; ".join(comments)
        }
        os.makedirs(os.path.dirname(args.result), exist_ok=True)
        with open(args.result, 'a', encoding='utf-8') as f:
            json_line = json.dumps(record, default=str, ensure_ascii=False)
            f.write(json_line + "\n")

if __name__ == "__main__":
    main()