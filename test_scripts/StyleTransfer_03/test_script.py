#!/usr/bin/env python3
import os
import sys
import argparse
import json
import datetime
import cv2
import numpy as np
import torch
import lpips
from torchvision import transforms
import torch.nn.functional as F
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

def load_tensor(path):
    """Load and normalize image to [-1,1] range Tensor"""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f'cv2 read failed: {path}')
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t = transforms.ToTensor()(img) * 2 - 1
    return t.unsqueeze(0)

def histogram_intersection(a, b, bins=256):
    """Calculate average intersection ratio of RGB channel histograms between two images"""
    inters = []
    for ch in range(3):
        h1 = cv2.calcHist([a], [ch], None, [bins], [0,256]).ravel()
        h2 = cv2.calcHist([b], [ch], None, [bins], [0,256]).ravel()
        if h1.sum() > 0:
            h1 = h1 / h1.sum()
        if h2.sum() > 0:
            h2 = h2 / h2.sum()
        inters.append(np.minimum(h1, h2).sum())
    return float(np.mean(inters))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description='Automated style transfer evaluation script')
    p.add_argument('--groundtruth', required=True, help='Ground truth directory path')
    p.add_argument('--output', required=True, help='Path to stylized output image')
    p.add_argument('--lpips-thresh', type=float, default=0.5, help='LPIPS threshold (>= passes)')
    p.add_argument('--hi-thresh', type=float, default=0.7, help='HI (Histogram Intersection) threshold (>= passes)')
    p.add_argument('--result', required=True, help='Result JSONL file path (append mode)')
    args = p.parse_args()

    # Build content and style paths
    content_path = os.path.join(args.groundtruth, 'gt_01.jpg')
    style_path = os.path.join(args.groundtruth, 'gt_02.jpg')

    process = True
    comments = []

    # ——— 1. Validate all files ———
    for tag, path in [('content', content_path), ('style', style_path), ('output', args.output)]:
        ok, msg = verify_image(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    # ——— 2. Calculate metrics (only if process==True) ———
    lpips_pass = hi_pass = False
    lpips_val = hi_val = None
    if process:
        try:
            # LPIPS between content and output
            img_c = load_tensor(content_path)
            img_o = load_tensor(args.output)
            # Align dimensions
            _, _, h0, w0 = img_c.shape
            _, _, h1, w1 = img_o.shape
            nh, nw = min(h0,h1), min(w0,w1)
            if (h0,w0)!=(nh,nw):
                img_c = F.interpolate(img_c, size=(nh,nw), mode='bilinear', align_corners=False)
            if (h1,w1)!=(nh,nw):
                img_o = F.interpolate(img_o, size=(nh,nw), mode='bilinear', align_corners=False)

            loss_fn = lpips.LPIPS(net='vgg').to(torch.device('cpu'))
            with torch.no_grad():
                lpips_val = float(loss_fn(img_c, img_o).item())
            lpips_pass = lpips_val >= args.lpips_thresh

            # HI between style and output
            img_s = cv2.imread(style_path, cv2.IMREAD_COLOR)
            img_o_cv = cv2.imread(args.output, cv2.IMREAD_COLOR)
            hi_val = histogram_intersection(img_s, img_o_cv)
            hi_pass = hi_val >= args.hi_thresh

            comments.append(f'LPIPS={lpips_val:.4f} (>= {args.lpips_thresh} → {"OK" if lpips_pass else "FAIL"})')
            comments.append(f'HI={hi_val:.4f} (>= {args.hi_thresh} → {"OK" if hi_pass else "FAIL"})')

        except Exception as e:
            process = False
            comments.append(f'Metric calculation error: {e}')

    # ——— 3. Write to JSONL ———
    result_flag = (process and lpips_pass and hi_pass)
    entry = {
        "Process": process,
        "Result":  result_flag,
        "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments": "; ".join(comments)
    }
    print(entry["comments"])
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # ——— 4. Output final status ———
    print("\nEvaluation complete - Final status: " + ("PASSED" if result_flag else "FAILED"))