import os
import argparse
import numpy as np
import json
import datetime

# Import Levenshtein distance calculation function
from Levenshtein import distance as levenshtein_distance


def evaluate_extraction(pred_path, gt_path):
    # Fixed threshold
    threshold = 0.5  # Prediction is considered successful if edit distance is below this threshold

    # Check if file exists
    def check_file_exists(file_path):
        if not os.path.isfile(file_path):
            print(f"❌ Error: File does not exist: {file_path}")
            return False
        if os.path.getsize(file_path) == 0:
            print(f"❌ Error: File is empty: {file_path}")
            return False
        return True

    # Check files
    file_check = check_file_exists(pred_path) and check_file_exists(gt_path)
    if not file_check:
        return None, False

    # Read prediction result
    with open(pred_path, 'r', encoding='utf-8') as f:
        pred_text = f.read()

    # Read ground truth
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_text = f.read()

    # Calculate edit distance
    edit_distance = levenshtein_distance(pred_text, gt_text)
    max_len = max(len(pred_text), len(gt_text))

    # Calculate edit distance ratio
    edit_distance_ratio = edit_distance / max_len if max_len > 0 else 0

    # Output edit distance ratio
    print(f"Edit Distance Ratio: {edit_distance_ratio:.4f}")

    # Check if threshold is met
    if edit_distance_ratio <= threshold:
        print("✅ Correctly completed")
    else:
        print("❌ Extraction error")

    return edit_distance_ratio, True


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the edit distance between extracted and ground truth markdown content.")
    parser.add_argument('--output', type=str, required=True, help='Path to the extracted prediction markdown file')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to the ground truth markdown file')
    parser.add_argument('--result', type=str, required=True, help='Path to save the result in jsonl format')

    args = parser.parse_args()

    # Calculate extraction accuracy (edit distance ratio)
    edit_distance_ratio, process_status = evaluate_extraction(pred_path=args.output, gt_path=args.groundtruth)

    # Save results
    result = {
        "Process": process_status,
        "Result": edit_distance_ratio <= 0.5 if process_status else False,
        # Check if edit distance ratio is below threshold
        "TimePoint": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": f"Edit Distance Ratio: {edit_distance_ratio:.4f} {'meets' if edit_distance_ratio <= 0.5 else 'does not meet'} 50% accuracy requirement" if process_status else "File check failed"
    }

    # Ensure directory exists
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)

    # Write results
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    main()