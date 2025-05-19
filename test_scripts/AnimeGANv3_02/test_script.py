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

def verify_image(path, exts=('.png','.jpg','.jpeg','.webp')):
    """检查文件存在、非空、扩展名合法，并能被 PIL 打开。"""
    if not os.path.isfile(path):
        return False, f'文件不存在：{path}'
    if os.path.getsize(path) == 0:
        return False, f'文件为空：{path}'
    if not path.lower().endswith(exts):
        return False, f'不支持的格式：{path}'
    try:
        img = Image.open(path)
        img.verify()
    except (UnidentifiedImageError, Exception) as e:
        return False, f'无法读取图像：{path} （{e}）'
    return True, ''

def load_tensor(path):
    """按原脚本方式载入并归一化到 [-1,1] 的 Tensor"""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f'cv2 读取失败：{path}')
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    t = transforms.ToTensor()(img) * 2 - 1
    return t.unsqueeze(0)

def main():
    p = argparse.ArgumentParser(description='自动化动漫化效果检测脚本')
    p.add_argument('--groundtruth',      required=True, help='原始图像路径')
    p.add_argument('--output',     required=True, help='动漫化后图像路径')
    p.add_argument('--lpips-thresh', type=float, default=0.30,
                   help='LPIPS 距离阈值 (>= 阈值 则通过)')
    p.add_argument('--result',     required=True, help='结果 JSONL 文件路径（追加模式）')
    args = p.parse_args()

    process = True
    comments = []

    # — 1. 检验输入和输出文件 —
    for tag, path in [('input', args.groundtruth), ('output', args.output)]:
        ok, msg = verify_image(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    # — 2. 计算 LPIPS（仅当 process==True）—
    lpips_val = None
    result_flag = False
    if process:
        try:
            img0 = load_tensor(args.groundtruth)
            img1 = load_tensor(args.output)
            # 对齐尺寸
            _, _, h0, w0 = img0.shape
            _, _, h1, w1 = img1.shape
            nh, nw = min(h0,h1), min(w0,w1)
            if (h0,w0) != (nh,nw):
                img0 = F.interpolate(img0, size=(nh,nw), mode='bilinear', align_corners=False)
            if (h1,w1) != (nh,nw):
                img1 = F.interpolate(img1, size=(nh,nw), mode='bilinear', align_corners=False)

            loss_fn = lpips.LPIPS(net='vgg').to(torch.device('cpu'))
            with torch.no_grad():
                lpips_val = float(loss_fn(img0, img1).item())

            passed = lpips_val >= args.lpips_thresh
            comments.append(f'LPIPS={lpips_val:.4f} (>= {args.lpips_thresh} → {"OK" if passed else "FAIL"})')
            result_flag = passed

        except Exception as e:
            process = False
            comments.append(f'指标计算出错：{e}')

    # — 3. 写入 JSONL —
    entry = {
        "Process": process,
        "Result":  result_flag,
        "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
        "comments": "; ".join(comments)
    }
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    main()
