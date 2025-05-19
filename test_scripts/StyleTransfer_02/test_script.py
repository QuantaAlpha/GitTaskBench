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

def evaluate_psnr(input_img_path, output_img_path):
    """读取图像并计算 PSNR"""
    img1 = cv2.imread(input_img_path)
    img2 = cv2.imread(output_img_path)
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)

    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

    return psnr(img1, img2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSNR 图像质量评估")
    parser.add_argument('--groundtruth', required=True, help='原始图像路径')
    parser.add_argument('--output', required=True, help='重建图像路径')
    parser.add_argument('--result', required=True, help='结果保存为 JSONL 的路径')
    args = parser.parse_args()

    process = True
    comments = []

    # ——— 1. 校验图像有效性 ———
    for tag, path in [('input', args.groundtruth), ('output', args.output)]:
        ok, msg = verify_image(path)
        if not ok:
            process = False
            comments.append(f'[{tag}] {msg}')

    # ——— 2. 若可处理则计算 PSNR ———
    psnr_val = None
    if process:
        try:
            psnr_val = evaluate_psnr(args.groundtruth, args.output)
            result_flag = psnr_val > 10
            comments.append(f'PSNR={psnr_val:.2f} (>10 → {"成功" if result_flag else "失败"})')
        except Exception as e:
            process = False
            result_flag = False
            comments.append(f'PSNR 计算异常：{e}')
    else:
        result_flag = False

    # ——— 3. 写入 JSONL ———
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

    # ——— 4. 终端提示 ———
    print("\n测试完成 - 最终状态: " + ("成功" if result_flag else "失败"))
