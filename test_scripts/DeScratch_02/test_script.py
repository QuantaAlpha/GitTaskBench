import os
import numpy as np
from PIL import Image
from tqdm import tqdm
import argparse
import json
from datetime import datetime


def evaluate_mask(pred_mask, gt_mask):
    # Convert masks to boolean values, calculate IoU and Dice coefficient
    pred_mask = pred_mask.astype(bool)
    gt_mask = gt_mask.astype(bool)

    intersection = np.logical_and(pred_mask, gt_mask).sum()
    union = np.logical_or(pred_mask, gt_mask).sum()
    iou = intersection / union if union != 0 else 1.0

    dice = (2 * intersection) / (pred_mask.sum() + gt_mask.sum()) if (pred_mask.sum() + gt_mask.sum()) != 0 else 1.0

    return {"IoU": iou, "Dice": dice}


def main(pred_dir, gt_dir, iou_threshold=0.5, dice_threshold=0.6, result_file=None):
    all_metrics = []

    # Initialize Process with default status True (files exist and valid)
    process_result = {"Process": True, "Result": False, "TimePoint": "", "comments": ""}
    process_result["TimePoint"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print(f"\nStarting evaluation task:")
    print(f"Predicted masks path: {pred_dir}")
    print(f"Ground truth masks path: {gt_dir}\n")

    # Validate input paths
    if not os.path.exists(pred_dir) or not os.path.exists(gt_dir):
        process_result["Process"] = False
        process_result["comments"] = "Path does not exist"
        print("❌ Predicted or ground truth masks path does not exist")
        save_result(result_file, process_result)
        return

    # Check each file in directory
    for filename in tqdm(os.listdir(gt_dir)):
        # Check if file extension is valid image format
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        gt_path = os.path.join(gt_dir, filename)

        # Automatically find predicted filename matching output.*
        pred_filename = next((f for f in os.listdir(pred_dir) if
                              f.startswith('output.') and f.lower().endswith(('.png', '.jpg', '.jpeg'))), None)

        if not pred_filename:
            print(f"⚠️ Missing predicted file: {filename}")
            continue

        pred_path = os.path.join(pred_dir, pred_filename)

        # Read ground truth and predicted masks
        gt_mask = np.array(Image.open(gt_path).convert("L")) > 128
        pred_mask = np.array(Image.open(pred_path).convert("L")) > 128

        # Evaluate and calculate IoU and Dice
        metrics = evaluate_mask(pred_mask, gt_mask)

        # Check if passes evaluation thresholds
        passed = metrics["IoU"] >= iou_threshold and metrics["Dice"] >= dice_threshold
        status = "✅ Passed" if passed else "❌ Failed"

        print(f"{filename:20s} | IoU: {metrics['IoU']:.3f} | Dice: {metrics['Dice']:.3f} | {status}")
        all_metrics.append(metrics)

    # If no files were evaluated, notify user
    if not all_metrics:
        print("\n⚠️ No valid image pairs found for evaluation, please check folder paths.")
        process_result["Process"] = False
        process_result["comments"] = "No valid image pairs for evaluation"
        save_result(result_file, process_result)
        return

    # Calculate average results across all files
    avg_metrics = {k: np.mean([m[k] for m in all_metrics]) for k in all_metrics[0].keys()}
    print("\n📊 Overall average results:")
    print(f"Average IoU: {avg_metrics['IoU']:.3f}")
    print(f"Average Dice: {avg_metrics['Dice']:.3f}")

    # Determine final result
    if avg_metrics["IoU"] >= iou_threshold and avg_metrics["Dice"] >= dice_threshold:
        process_result["Result"] = True
        process_result[
            "comments"] = f"All images passed, average IoU: {avg_metrics['IoU']:.3f}, average Dice: {avg_metrics['Dice']:.3f}"
        print(f"✅ Test passed!")
    else:
        process_result["Result"] = False
        process_result[
            "comments"] = f"Test failed, average IoU: {avg_metrics['IoU']:.3f}, average Dice: {avg_metrics['Dice']:.3f}"
        print(f"❌ Test failed")

    save_result(result_file, process_result)


def save_result(result_file, result):
    # Save test results to jsonl file, append if file exists
    if result_file:
        try:
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, default=str) + "\n")
        except Exception as e:
            print(f"⚠️ Error writing result file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, required=True, help="Folder containing predicted mask images")
    parser.add_argument('--groundtruth', type=str, required=True, help="Folder containing ground truth mask images")
    parser.add_argument('--result', type=str, required=True, help="Path to jsonl file for storing test results")
    args = parser.parse_args()

    main(args.output, args.groundtruth, result_file=args.result)