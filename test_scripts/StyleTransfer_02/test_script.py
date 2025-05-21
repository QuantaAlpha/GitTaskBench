#!/usr/bin/env python3
import os
import argparse
import json
from datetime import datetime
import cv2
import numpy as np
from skimage.metrics import peak_signal_noise_ratio as psnr
from PIL import Image, UnidentifiedImageError

def verify_image(path, exts=('.png', '.jpg', '.jpeg', '.webp')):
    """Verify file exists, is non-empty, has valid extension, and can be opened by PIL."""
    if not os.path.isfile(path):
        return False, f'File not found: {path}'
    if os.path.getsize(path) == 0:
        return False, f'File is empty: {path}'
    if not path.lower().endswith(exts):
        return False, f'Unsupported format: {path}'
    try:
        img = Image.open(path)
        img.verify()
    except (UnidentifiedImageError, Exception) as e:
        return False, f'Cannot read image: {path} ({e})'
    return True, ''

def evaluate_psnr(input_img_path, output_img_path):
    """Read images and calculate PSNR"""
    img1 = cv2.imread(input_img_path)
    img2 = cv2.imread(output_img_path)
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)

    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    return psnr(img1, img2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSNR image quality evaluation")
    parser.add_argument('--groundtruth', required=True, help='Original image path')
    parser.add_argument('--output', required=True, help='Reconstructed image path')
    parser.add_argument('--result', required=True, help='Path to save results as JSONL')
    args = parser.parse_args()

    process = True
    comments = []

    # ——— 1. Validate image files ———
    for tag, path in [('input', args.groundtruth), ('output', args.output)]:
        ok, msg = verify_image(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    # ——— 2. Calculate PSNR if processable ———
    psnr_val = None
    if process:
        try:
            psnr_val = evaluate_psnr(args.groundtruth, args.output)
            result_flag = psnr_val > 10
            comments.append(f'PSNR={psnr_val:.2f} (>10 → {"PASS" if result_flag else "FAIL"})')
        except Exception as e:
            process = False
            result_flag = False
            comments.append(f'PSNR calculation error: {e}')
    else:
        result_flag = False

    # ——— 3. Write to JSONL ———
    entry = {
        "Process": process,
        "Result": result_flag,
        "TimePoint": datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments": "; ".join(comments)
    }
    print(entry["comments"])
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # ——— 4. Terminal notification ———
    print("\nTest complete - Final status: " + ("PASS" if result_flag else "FAIL"))