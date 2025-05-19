import os
import numpy as np
from PIL import Image
from tqdm import tqdm
import argparse
import json
from datetime import datetime

def evaluate_mask(pred_mask, gt_mask):
    # 将掩码转换为布尔值，计算IoU和Dice系数
    pred_mask = pred_mask.astype(bool)
    gt_mask = gt_mask.astype(bool)

    intersection = np.logical_and(pred_mask, gt_mask).sum()
    union = np.logical_or(pred_mask, gt_mask).sum()
    iou = intersection / union if union != 0 else 1.0

    dice = (2 * intersection) / (pred_mask.sum() + gt_mask.sum()) if (pred_mask.sum() + gt_mask.sum()) != 0 else 1.0

    return {"IoU": iou, "Dice": dice}

def main(pred_dir, gt_dir, iou_threshold=0.5, dice_threshold=0.6, result_file=None):
    all_metrics = []

    # 初始化Process的默认状态为True，表示文件存在且有效
    process_result = {"Process": True, "Result": False, "TimePoint": "", "comments": ""}
    process_result["TimePoint"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print(f"\n开始评估任务：")
    print(f"预测掩码路径：{pred_dir}")
    print(f"真实掩码路径：{gt_dir}\n")

    # 检查输入路径的有效性
    if not os.path.exists(pred_dir) or not os.path.exists(gt_dir):
        process_result["Process"] = False
        process_result["comments"] = "路径不存在"
        print("❌ 预测或真实掩码路径不存在")
        save_result(result_file, process_result)
        return

    # 检查文件夹中的每个文件
    for filename in tqdm(os.listdir(gt_dir)):
        # 检查文件扩展名是否是图像格式
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        gt_path = os.path.join(gt_dir, filename)
        
        # 自动查找预测文件名，匹配 output.*
        pred_filename = next((f for f in os.listdir(pred_dir) if f.startswith('output.') and f.lower().endswith(('.png', '.jpg', '.jpeg'))), None)

        if not pred_filename:
            print(f"⚠️ 预测文件缺失：{filename}")
            continue

        pred_path = os.path.join(pred_dir, pred_filename)

        # 读取真实掩码和预测掩码
        gt_mask = np.array(Image.open(gt_path).convert("L")) > 128
        pred_mask = np.array(Image.open(pred_path).convert("L")) > 128

        # 评估并计算IoU和Dice
        metrics = evaluate_mask(pred_mask, gt_mask)

        # 判断是否通过评估阈值
        passed = metrics["IoU"] >= iou_threshold and metrics["Dice"] >= dice_threshold
        status = "✅ 通过" if passed else "❌ 未通过"

        print(f"{filename:20s} | IoU: {metrics['IoU']:.3f} | Dice: {metrics['Dice']:.3f} | {status}")
        all_metrics.append(metrics)

    # 如果没有评估的文件，提示用户
    if not all_metrics:
        print("\n⚠️ 没有找到可评估的图像对，请检查文件夹路径。")
        process_result["Process"] = False
        process_result["comments"] = "没有可评估的图像对"
        save_result(result_file, process_result)
        return

    # 计算所有文件的平均结果
    avg_metrics = {k: np.mean([m[k] for m in all_metrics]) for k in all_metrics[0].keys()}
    print("\n📊 总体平均结果：")
    print(f"平均 IoU ：{avg_metrics['IoU']:.3f}")
    print(f"平均 Dice：{avg_metrics['Dice']:.3f}")

    # 判断最终的结果
    if avg_metrics["IoU"] >= iou_threshold and avg_metrics["Dice"] >= dice_threshold:
        process_result["Result"] = True
        process_result["comments"] = f"所有图像通过，平均IoU: {avg_metrics['IoU']:.3f}, 平均Dice: {avg_metrics['Dice']:.3f}"
        print(f"✅ 测试通过！")
    else:
        process_result["Result"] = False
        process_result["comments"] = f"测试未通过，平均IoU: {avg_metrics['IoU']:.3f}, 平均Dice: {avg_metrics['Dice']:.3f}"
        print(f"❌ 测试未通过")

    save_result(result_file, process_result)

def save_result(result_file, result):
    # 保存测试结果到jsonl文件，若文件存在则追加
    if result_file:
        try:
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, default=str) + "\n")
        except Exception as e:
            print(f"⚠️ 写入结果文件时发生错误：{e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, required=True, help="预测掩码图像所在文件夹")
    parser.add_argument('--groundtruth', type=str, required=True, help="真实掩码图像所在文件夹")
    parser.add_argument('--result', type=str, required=True, help="测试结果存储的jsonl文件路径")
    args = parser.parse_args()

    main(args.output, args.groundtruth, result_file=args.result)

