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

def histogram_intersection(a, b, bins=256):
    """计算两张图 RGB 通道直方图的平均交集比率"""
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
    p = argparse.ArgumentParser(description='自动化风格迁移效果检测脚本')
    p.add_argument('--content',    required=True, help='原始内容图像路径')
    p.add_argument('--style',      required=True, help='参考风格图像路径')
    p.add_argument('--output',     required=True, help='风格化后图像路径')
    p.add_argument('--lpips-thresh', type=float, default=0.5, help='LPIPS 阈值 (>= 通过)')
    p.add_argument('--hi-thresh',    type=float, default=0.7, help='HI(直方图交集) 阈值 (>= 通过)')
    p.add_argument('--result',      required=True, help='结果 JSONL 文件路径，追加模式')
    args = p.parse_args()

    process = True
    comments = []

    # ——— 1. 检验所有文件 —
    for tag, path in [('content', args.content), ('style', args.style), ('output', args.output)]:
        ok, msg = verify_image(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    # ——— 2. 计算指标（仅当 process==True） —
    lpips_pass = hi_pass = False
    lpips_val = hi_val = None
    if process:
        try:
            # LPIPS between content 与 output
            img_c = load_tensor(args.content)
            img_o = load_tensor(args.output)
            # 对齐尺寸
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

            # HI between style 与 output
            img_s = cv2.imread(args.style, cv2.IMREAD_COLOR)
            img_o_cv = cv2.imread(args.output, cv2.IMREAD_COLOR)
            hi_val = histogram_intersection(img_s, img_o_cv)
            hi_pass = hi_val >= args.hi_thresh

            comments.append(f'LPIPS={lpips_val:.4f} (>= {args.lpips_thresh} → {"OK" if lpips_pass else "FAIL"})')
            comments.append(f'HI={hi_val:.4f} (>= {args.hi_thresh} → {"OK" if hi_pass else "FAIL"})')

        except Exception as e:
            process = False
            comments.append(f'指标计算出错：{e}')

    # ——— 3. 写入 JSONL —
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

    # ——— 4. 输出最终状态（替代原退出逻辑）———
    print("\n测试完成 - 最终状态: " + ("通过" if result_flag else "未通过"))