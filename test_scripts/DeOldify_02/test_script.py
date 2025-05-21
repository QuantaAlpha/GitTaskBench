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
    """Download or read local image, return PIL.Image in RGB mode."""
    if path_or_url.startswith(('http://', 'https://')):
        resp = requests.get(path_or_url, timeout=10)
        if resp.status_code != 200:
            raise ValueError(f"Failed to download image: {path_or_url} (status code {resp.status_code})")
        data = BytesIO(resp.content)
    else:
        if not os.path.isfile(path_or_url):
            raise ValueError(f"File does not exist: {path_or_url}")
        data = path_or_url
    try:
        return Image.open(data).convert('RGB')
    except Exception as e:
        raise ValueError(f"Failed to open image: {e}")

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
    """Append single result to file in JSONL format."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
    except Exception as e:
        print(f"❌ Error writing JSONL file: {e}", file=sys.stderr)

def main():
    p = argparse.ArgumentParser(
        description="Evaluate colorization/enhancement effect using CIEDE2000 and NIQE metrics, with JSONL output option")
    p.add_argument("--groundtruth", type=str, required=True, help="Reference image URL or local path")
    p.add_argument("--output", type=str, required=True, help="Reconstructed image URL or local path")
    p.add_argument("--ciede-thresh", type=float, required=True,
                   help="CIEDE2000 minimum acceptance threshold (higher is better)")
    p.add_argument("--niqe-thresh", type=float, required=True,
                   help="NIQE maximum acceptance threshold (lower is better)")
    p.add_argument("--result", help="File path to store JSONL results")
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

            comments.append(f"CIEDE2000 average color difference: {score_ciede:.4f} (threshold {args.ciede_thresh})")
            comments.append(f"Reconstructed image NIQE score: {score_niqe:.4f} (threshold {args.niqe_thresh})")

            ok_ciede = score_ciede >= args.ciede_thresh
            ok_niqe = score_niqe <= args.niqe_thresh

            if ok_ciede and ok_niqe:
                comments.append("✅ Processing effect meets requirements: CIEDE2000↑ and NIQE↓ both satisfy thresholds")
                result_ok = True
            else:
                fail_reasons = []
                if not ok_ciede:
                    fail_reasons.append("CIEDE2000 not met")
                if not ok_niqe:
                    fail_reasons.append("NIQE not met")
                comments.append("❌ Processing effect does not meet requirements: " + " ".join(fail_reasons))
        except Exception as e:
            comments.append(f"Exception during metric calculation: {e}")

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