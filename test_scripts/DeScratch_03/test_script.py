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
    """在指定目录中根据通配符匹配单个图像文件。"""
    files = glob.glob(os.path.join(directory, pattern))
    if len(files) == 1:
        return files[0]
    elif len(files) == 0:
        print(f"⚠️ 在 {directory} 中未找到匹配 {pattern} 的图像文件")
    else:
        print(f"⚠️ 在 {directory} 中找到多个匹配 {pattern} 的图像文件")
    return None

def evaluate_quality(pred_dir, gt_dir, threshold_ssim=0.65, threshold_psnr=15, result_file=None):
    result = {
        "Process": True,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    print(f"\n开始评估任务：")
    print(f"预测图像路径：{pred_dir}")
    print(f"真实图像路径：{gt_dir}\n")

    if not os.path.exists(pred_dir) or not os.path.exists(gt_dir):
        result["Process"] = False
        result["comments"] = "路径不存在"
        print("❌ 路径不存在")
        save_result(result_file, result)
        return

    pred_path = find_single_image(pred_dir, "output.*")
    gt_path = find_single_image(gt_dir, "gt.*")

    if not pred_path or not gt_path:
        result["Process"] = False
        result["comments"] = "预测图像或GT图像缺失或匹配不唯一"
        save_result(result_file, result)
        return

    pred_img = cv2.imread(pred_path)
    gt_img = cv2.imread(gt_path)

    if pred_img is None or gt_img is None:
        result["Process"] = False
        result["comments"] = "图像读取失败"
        print("⚠️ 图像读取失败")
        save_result(result_file, result)
        return

    pred_img = cv2.resize(pred_img, (gt_img.shape[1], gt_img.shape[0]))
    pred_gray = cv2.cvtColor(pred_img, cv2.COLOR_BGR2GRAY)
    gt_gray = cv2.cvtColor(gt_img, cv2.COLOR_BGR2GRAY)

    ssim_val = ssim(gt_gray, pred_gray)
    psnr_val = psnr(gt_gray, pred_gray)

    print(f"平均结构相似性（SSIM）：{ssim_val:.4f}")
    print(f"平均峰值信噪比（PSNR）：{psnr_val:.2f}")

    if ssim_val >= threshold_ssim and psnr_val >= threshold_psnr:
        result["Result"] = True
        result["comments"] = f"测试通过，SSIM={ssim_val:.4f}, PSNR={psnr_val:.2f}"
        print("✅ 恢复效果达标")
    else:
        result["Result"] = False
        result["comments"] = f"测试未通过，SSIM={ssim_val:.4f}, PSNR={psnr_val:.2f}"
        print("❌ 恢复效果未达标")

    save_result(result_file, result)

def save_result(result_file, result):
    if result_file:
        try:
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(f"[成功] 输出文件: {result_file}")
        except Exception as e:
            print(f"⚠️ 写入结果文件失败：{e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, required=True, help='预测结果文件夹')
    parser.add_argument('--groundtruth', type=str, required=True, help='原始GT文件夹')
    parser.add_argument('--result', type=str, required=True, help='结果输出JSONL文件')
    args = parser.parse_args()

    evaluate_quality(args.output, args.groundtruth, result_file=args.result)
