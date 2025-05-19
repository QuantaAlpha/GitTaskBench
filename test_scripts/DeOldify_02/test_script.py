import os
import sys
import argparse
import json
from datetime import datetime
import requests
from io import BytesIO

import numpy as np
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from basicsr.metrics.niqe import calculate_niqe

def download_image(path_or_url: str) -> Image.Image:
    """下载或读取本地图片，返回 RGB 模式的 PIL.Image。"""
    if path_or_url.startswith(('http://', 'https://')):
        resp = requests.get(path_or_url, timeout=10)
        if resp.status_code != 200:
            raise ValueError(f"无法下载图片：{path_or_url} (状态码 {resp.status_code})")
        data = BytesIO(resp.content)
    else:
        if not os.path.isfile(path_or_url):
            raise ValueError(f"文件不存在：{path_or_url}")
        data = path_or_url
    try:
        return Image.open(data).convert('RGB')
    except Exception as e:
        raise ValueError(f"打开图像失败：{e}")

def compute_ciede2000(ref_img: Image.Image, test_img: Image.Image) -> float:
    arr_ref  = np.asarray(ref_img, dtype=np.float32) / 255.0
    arr_test = np.asarray(test_img, dtype=np.float32) / 255.0
    lab_ref  = rgb2lab(arr_ref)
    lab_test = rgb2lab(arr_test)
    delta    = deltaE_ciede2000(lab_ref, lab_test)
    return float(np.mean(delta))

def compute_niqe(img: Image.Image) -> float:
    arr = np.asarray(img).astype(np.float32)
    return float(calculate_niqe(arr, crop_border=0))

def write_result_jsonl(file_path: str, data: dict):
    """将单条结果以 JSONL 形式追加到文件末尾。"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
    except Exception as e:
        print(f"❌ 写入 JSONL 文件时发生错误: {e}", file=sys.stderr)

def main():
    p = argparse.ArgumentParser(
        description="以 CIEDE2000 与 NIQE 两指标评测上色/增强效果，并可输出 JSONL 结果")
    p.add_argument("--groundtruth", type=str, required=True, help="参考图像 URL 或本地路径")
    p.add_argument("--output", type=str, required=True, help="重建图像 URL 或本地路径")
    p.add_argument("--ciede-thresh", type=float, required=True,
                   help="CIEDE2000 最低接受阈值（越大越好）")
    p.add_argument("--niqe-thresh", type=float, required=True,
                   help="NIQE 最高接受阈值（越小越好）")
    p.add_argument("--result", help="用于存储 JSONL 结果的文件路径")
    args = p.parse_args()

    process_ok = True
    result_ok = False
    comments = []

    time_point = datetime.now().isoformat()

    try:
        img_ref = download_image(args.groundtruth)
        img_recon = download_image(args.output)
    except ValueError as err:
        comments.append(str(err))
        process_ok = False

    if process_ok:
        try:
            score_ciede = compute_ciede2000(img_ref, img_recon)
            score_niqe = compute_niqe(img_recon)

            comments.append(f"CIEDE2000 平均色差：{score_ciede:.4f} (阈值 {args.ciede_thresh})")
            comments.append(f"重建图像 NIQE 分数：{score_niqe:.4f} (阈值 {args.niqe_thresh})")

            ok_ciede = score_ciede >= args.ciede_thresh
            ok_niqe = score_niqe <= args.niqe_thresh

            if ok_ciede and ok_niqe:
                comments.append("✅ 处理效果符合要求：CIEDE2000↑ 且 NIQE↓ 均满足阈值")
                result_ok = True
            else:
                fail_reasons = []
                if not ok_ciede:
                    fail_reasons.append("CIEDE2000 未达标")
                if not ok_niqe:
                    fail_reasons.append("NIQE 未达标")
                comments.append("❌ 处理效果不符合要求：" + " ".join(fail_reasons))
        except Exception as e:
            comments.append(f"指标计算时发生异常：{e}")

    if args.result:
        record = {
            "Process": process_ok,
            "Result": result_ok,
            "TimePoint": time_point,
            "comments": "\n".join(comments)
        }
        write_result_jsonl(args.result, record)

    for line in comments:
        print(line, file=(sys.stderr if not process_ok or not result_ok else sys.stdout))

if __name__ == "__main__":
    main()
