import argparse
import csv
import os
import json
from datetime import datetime


def check_file_valid(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        print(f"❌ File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ File is empty: {file_path}")
        return False
    return True


def evaluate_scraping(pred_file: str, gt_file: str, threshold: float = 0.95, result_file: str = None):
    process_success = check_file_valid(pred_file) and check_file_valid(gt_file)

    if not process_success:
        result = {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"❌ File does not exist or is empty: pred={pred_file}, gt={gt_file}"
        }
        if result_file:
            with open(result_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
        return False

    # Read prediction file
    preds = []
    with open(pred_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            preds.append(row)

    # Read ground truth
    gts = []
    with open(gt_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gts.append(row)

    if len(preds) != len(gts):
        print(
            f"⚠️ Prediction and ground truth counts mismatch (predicted {len(preds)}, truth {len(gts)}), comparing minimum count.")

    num_samples = min(len(preds), len(gts))

    fields = preds[0].keys()  # Assume column names match
    correct_counts = {field: 0 for field in fields}

    # Calculate accuracy per column
    for i in range(num_samples):
        for field in fields:
            if preds[i][field] == gts[i][field]:
                correct_counts[field] += 1

    accuracies = {field: correct_counts[field] / num_samples for field in fields}

    # Print accuracy per column
    for field, acc in accuracies.items():
        print(f"Field '{field}' accuracy: {acc:.4f}")

    # Check if all fields meet threshold
    success = all(acc >= threshold for acc in accuracies.values())

    if success:
        print("✅ Validation passed: All columns accuracy >95%")
    else:
        print("❌ Validation failed: Some columns accuracy <95%")

    # Save results
    if result_file:
        result = {
            "Process": True,
            "Result": success,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"Field-level accuracy: {accuracies}, {'meets' if success else 'does not meet'} 95% threshold"
        }
        with open(result_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

    return accuracies, success


def main():
    parser = argparse.ArgumentParser(description="Evaluate field-level accuracy of Scrapy crawl results")
    parser.add_argument('--output', type=str, required=True, help="Prediction results (CSV) path")
    parser.add_argument('--groundtruth', type=str, required=True, help="Ground truth data (CSV) path")
    parser.add_argument('--threshold', type=float, default=0.95, help="Field accuracy threshold")
    parser.add_argument('--result', type=str, required=False, help="Output JSONL file path for results")

    args = parser.parse_args()

    evaluate_scraping(args.output, args.groundtruth, args.threshold, args.result)


if __name__ == "__main__":
    main()