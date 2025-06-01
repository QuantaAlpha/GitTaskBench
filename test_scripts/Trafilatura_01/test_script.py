# -*- coding: utf-8 -*-
import argparse
import sys
import os
import json
import re
from datetime import datetime
from charset_normalizer import detect
from difflib import SequenceMatcher

def preprocess_text(text):
    """
    Preprocess text by removing HTML tags, extra whitespace, and converting to lowercase.
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace and convert to lowercase
    return text.strip().lower()

def compute_precision_recall(extracted_content, ground_truth):
    """
    Compute approximate precision and recall using SequenceMatcher ratio,
    treating the ratio as both precision and recall estimates.
    """
    extracted = preprocess_text(extracted_content)
    ground = preprocess_text(ground_truth)

    matcher = SequenceMatcher(None, extracted, ground)
    match_ratio = matcher.ratio()

    # Use match_ratio as estimate for precision and recall
    precision = recall = match_ratio
    return precision, recall

def check_file_exists(file_path):
    """
    Check if the file exists and is not empty.
    """
    if not os.path.isfile(file_path):
        print(f"❌ Error: File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ Error: File is empty: {file_path}")
        return False
    return True

def read_file_with_encoding(file_path):
    """
    Read file content with automatic encoding detection.
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
        detected = detect(raw_data)
        encoding = detected["encoding"] if detected["encoding"] else "utf-8"
        print(f"📄 Detected file {file_path} encoding: {encoding}")
        return raw_data.decode(encoding).strip()
    except Exception as e:
        print(f"❌ Failed to read file {file_path}: {e}")
        raise

def compare_txt_files(extracted_txt_path, ground_truth_txt_path, result_file):
    try:
        # Check files existence and non-empty status
        process_status = check_file_exists(extracted_txt_path) and check_file_exists(ground_truth_txt_path)
        if not process_status:
            raise ValueError("File check failed")

        time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Read file contents
        extracted_message = read_file_with_encoding(extracted_txt_path)
        ground_truth_message = read_file_with_encoding(ground_truth_txt_path)

        # Compute precision, recall, and F1 score
        precision, recall = compute_precision_recall(extracted_message, ground_truth_message)
        f1 = 2 * precision * recall / (precision + recall + 1e-10)

        # Threshold for passing the test (adjustable)
        threshold = 0.90
        passed = f1 >= threshold
        match_result = "✅" if passed else "❌"

        print(f"🔍 Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
        print(f"Result: {match_result} F1 {f1:.4f} {'meets' if passed else 'does not meet'} threshold {threshold}")

        comments = f"F1 {f1:.4f} {'meets' if passed else 'does not meet'} threshold {threshold}"

        # Write results to jsonl file
        result_data = {
            "Process": process_status,
            "Result": passed,
            "TimePoint": time_point,
            "comments": comments
        }

        with open(result_file, 'a', encoding="utf-8") as f:
            f.write(json.dumps(result_data, ensure_ascii=False, default=str) + "\n")

        print("\nTest complete - Final status: " + ("PASS" if passed else "FAIL"))

    except Exception as e:
        print(f"❌ Test exception: {e}")
        print("\nTest complete - Final status: ERROR")
        raise

def main():
    parser = argparse.ArgumentParser(description="Compare extracted text with ground truth file content")
    parser.add_argument("--output", required=True, help="Path to extracted output txt file")
    parser.add_argument("--groundtruth", required=True, help="Path to ground truth txt file")
    parser.add_argument("--result", required=True, help="Path to jsonl file for storing test results")
    args = parser.parse_args()

    compare_txt_files(args.output, args.groundtruth, args.result)

if __name__ == "__main__":
    main()
