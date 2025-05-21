import os
import argparse
import cv2
import numpy as np
import json
from datetime import datetime
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim
import glob

def find_single_image(directory, pattern):
    """Find single image file in specified directory using glob pattern."""
    files = glob.glob(os.path.join(directory, pattern))
    if len(files) == 1:
        return files[0]
    elif len(files) == 0:
        print(f"⚠️ No matching {pattern} image found in {directory}")
    else:
        print(f"⚠️ Multiple matching {pattern} images found in {directory}")
    return None

def evaluate_quality(pred_dir, gt_dir, threshold_ssim=0.65, threshold_psnr=15, result_file=None):
    result = {
        "Process": True,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    print(f"\nStarting evaluation task:")
    print(f"Predicted images path: {pred_dir}")
    print(f"Ground truth images path: {gt_dir}\n")

    if not os.path.exists(pred_dir) or not os.path.exists(gt_dir):
        result["Process"] = False
        result["comments"] = "Path does not exist"
        print("❌ Path does not exist")
        save_result(result_file, result)
        return

    pred_path = find_single_image(pred_dir, "output.*")
    gt_path = find_single_image(gt_dir, "gt.*")

    if not pred_path or not gt_path:
        result["Process"] = False
        result["comments"] = "Predicted or GT image missing or multiple matches"
        save_result(result_file, result)
        return

    pred_img = cv2.imread(pred_path)
    gt_img = cv2.imread(gt_path)

    if pred_img is None or gt_img is None:
        result["Process"] = False
        result["comments"] = "Failed to read images"
        print("⚠️ Failed to read images")
        save_result(result_file, result)
        return

    pred_img = cv2.resize(pred_img, (gt_img.shape[1], gt_img.shape[0]))
    pred_gray = cv2.cvtColor(pred_img, cv2.COLOR_BGR2GRAY)
    gt_gray = cv2.cvtColor(gt_img, cv2.COLOR_BGR2GRAY)

    ssim_val = ssim(gt_gray, pred_gray)
    psnr_val = psnr(gt_gray, pred_gray)

    print(f"Structural Similarity (SSIM): {ssim_val:.4f}")
    print(f"Peak Signal-to-Noise Ratio (PSNR): {psnr_val:.2f}")

    if ssim_val >= threshold_ssim and psnr_val >= threshold_psnr:
        result["Result"] = True
        result["comments"] = f"Test passed, SSIM={ssim_val:.4f}, PSNR={psnr_val:.2f}"
        print("✅ Restoration quality meets requirements")
    else:
        result["Result"] = False
        result["comments"] = f"Test failed, SSIM={ssim_val:.4f}, PSNR={psnr_val:.2f}"
        print("❌ Restoration quality does not meet requirements")

    save_result(result_file, result)

def save_result(result_file, result):
    if result_file:
        try:
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(f"[Success] Output file: {result_file}")
        except Exception as e:
            print(f"⚠️ Failed to write result file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, required=True, help='Predicted results folder')
    parser.add_argument('--groundtruth', type=str, required=True, help='Original GT folder')
    parser.add_argument('--result', type=str, required=True, help='Output JSONL file for results')
    args = parser.parse_args()

    evaluate_quality(args.output, args.groundtruth, result_file=args.result)