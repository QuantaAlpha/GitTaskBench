#!/usr/bin/env python3
import sys
import argparse
import cv2   # pip install opencv-python
import numpy as np   # pip install numpy
import json
import os
from datetime import datetime

def image_colorfulness(image):
    """
    Calculate image colorfulness:
    Formula defined by Hasler & Süsstrunk (2003)
    """
    if image.shape[-1] == 4:
        image = image[:, :, :3]
    if len(image.shape) != 3 or image.shape[-1] != 3:
        raise ValueError("Input image must be 3-channel (BGR) or 4-channel (BGRA) format")
    (B, G, R) = cv2.split(image.astype("float"))
    rg = np.abs(R - G)
    yb = np.abs(0.5 * (R + G) - B)
    rbMean, rbStd = np.mean(rg), np.std(rg)
    ybMean, ybStd = np.mean(yb), np.std(yb)
    return np.sqrt(rbStd**2 + ybStd**2) + 0.3 * np.sqrt(rbMean**2 + ybMean**2)

def save_result_jsonl(process, results, comments, result_file):
    """
    Append a single record in JSONL format to file,
    Record fields: Process, Results, TimePoint, comments
    """
    entry = {
        "Process": bool(process),
        "Result": bool(results),
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": comments
    }
    # Ensure directory exists
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    # Append one JSONL line
    with open(result_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate colorfulness difference between original and matted images, determine pass/fail based on threshold, output JSONL format results"
    )
    parser.add_argument('--groundtruth', help="Original image path (supports .jpg/.png)")
    parser.add_argument('--output', help="Matting result image path (supports .png)")
    parser.add_argument(
        '--colorfulness-diff-thresh', type=float, default=20.0,
        help="Colorfulness difference threshold: pass when orig - pred ≥ thresh"
    )
    parser.add_argument('--result', required=True,
                        help="JSONL result file path")
    args = parser.parse_args()

    process = os.path.exists(args.output)
    if not process:
        comments = f"Prediction file does not exist: {args.output}"
        save_result_jsonl(process, False, comments, args.result)
        print(f"Test complete - Final status: Failed (file not found)")
        return

    try:
        orig = cv2.imread(args.groundtruth, cv2.IMREAD_UNCHANGED)
        pred = cv2.imread(args.output, cv2.IMREAD_UNCHANGED)
        if orig is None:
            raise FileNotFoundError(f"Failed to load original image: {args.groundtruth}")
        if pred is None:
            raise FileNotFoundError(f"Failed to load result image: {args.output}")

        cf_orig = image_colorfulness(orig)
        cf_pred = image_colorfulness(pred)
        diff = cf_orig - cf_pred
        results = diff >= args.colorfulness_diff_thresh

        comments = (
            f"Original image colorfulness: {cf_orig:.2f}, "
            f"Result image colorfulness: {cf_pred:.2f}, "
            f"Difference: {diff:.2f}, "
            f"Threshold: {args.colorfulness_diff_thresh}"
        )

        save_result_jsonl(process, results, comments, args.result)
        print(f"Test complete - Final status: {'Passed' if results else 'Failed'}")

    except Exception as e:
        comments = f"Error during processing: {str(e)}"
        save_result_jsonl(False, False, comments, args.result)
        print(f"Test complete - Final status: Error ({str(e)})")

if __name__ == "__main__":
    main()