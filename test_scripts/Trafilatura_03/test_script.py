import argparse
import sys
import os
import json
from datetime import datetime

def compute_precision_recall(extracted_content, ground_truth):
    """Function to calculate precision and recall"""
    extracted_chars = set(extracted_content.lower())
    ground_truth_chars = set(ground_truth.lower())

    intersection = extracted_chars & ground_truth_chars
    precision = len(intersection) / len(extracted_chars) if extracted_chars else 0
    recall = len(intersection) / len(ground_truth_chars) if ground_truth_chars else 0

    return precision, recall

def check_file_exists(file_path):
    """Check if file exists and is not empty"""
    if not os.path.isfile(file_path):
        print(f"❌ Error: File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ Error: File is empty: {file_path}")
        return False
    return True

def compare_txt_files(extracted_txt_path, ground_truth_txt_path, result_file):
    process_status = False
    results_status = False
    comments = ""
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    try:
        # Check if files exist and are not empty
        process_status = check_file_exists(extracted_txt_path) and check_file_exists(ground_truth_txt_path)

        if not process_status:
            comments = "Extracted or reference file missing/empty"
        else:
            # Read text content
            with open(extracted_txt_path, "r", encoding="utf-8") as f:
                extracted_message = f.read().strip()

            with open(ground_truth_txt_path, "r", encoding="utf-8") as f:
                ground_truth_message = f.read().strip()

            # Calculate precision and recall
            precision, recall = compute_precision_recall(extracted_message, ground_truth_message)
            passed = recall >= 0.5
            results_status = passed
            comments = f"🔍 Precision: {precision:.4f} | Recall: {recall:.4f} —— {'✅ Passed' if passed else '❌ Failed (recall < 50%)'}"
            print(comments)

    except Exception as e:
        comments = f"❌ Test exception: {e}"
        print(comments)

    # Write jsonl result
    result_data = {
        "Process": process_status,
        "Result": results_status,
        "TimePoint": time_point,
        "comments": comments
    }

    with open(result_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result_data, ensure_ascii=False, default=str) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Compare extracted text with ground truth file content")
    parser.add_argument("--output", required=True, help="Path to extracted txt file")
    parser.add_argument("--groundtruth", required=True, help="Path to ground truth txt file")
    parser.add_argument("--result", required=True, help="Path to jsonl file for storing test results")

    args = parser.parse_args()
    compare_txt_files(args.output, args.groundtruth, args.result)

if __name__ == "__main__":
    main()