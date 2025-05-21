# -*- coding: utf-8 -*-
import argparse
import sys
import os
import json
from datetime import datetime
from charset_normalizer import detect

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

def read_file_with_encoding(file_path):
    """Read file with automatic encoding detection"""
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
        # Detect encoding
        detected = detect(raw_data)
        encoding = detected["encoding"] if detected["encoding"] else "utf-8"
        print(f"📄 Detected file {file_path} encoding: {encoding}")
        return raw_data.decode(encoding).strip()
    except Exception as e:
        print(f"❌ Failed to read file {file_path}: {e}")
        raise

def compare_txt_files(extracted_txt_path, ground_truth_txt_path, result_file):
    try:
        # Check if files exist and are not empty
        process_status = check_file_exists(extracted_txt_path) and check_file_exists(ground_truth_txt_path)
        if not process_status:
            raise ValueError("File check failed")

        # Record current time
        time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Read file contents
        extracted_message = read_file_with_encoding(extracted_txt_path)
        ground_truth_message = read_file_with_encoding(ground_truth_txt_path)

        # Calculate precision and recall
        precision, recall = compute_precision_recall(extracted_message, ground_truth_message)
        passed = precision >= 0.92
        match_result = ":white_check_mark:" if passed else ":x:"

        # Output results
        print(f"🔍 Precision: {precision:.4f} | Recall: {recall:.4f}")
        print(f"Result: {match_result} Precision {precision:.4f} {'meets' if passed else 'does not meet'} 92%")

        results_status = passed
        comments = f"Precision {precision:.4f} {'meets' if passed else 'does not meet'} 92%"

        # Write to jsonl result
        result_data = {
            "Process": process_status,
            "Result": results_status,
            "TimePoint": time_point,
            "comments": comments
        }

        # Append if file exists, create new if not
        with open(result_file, 'a', encoding="utf-8") as f:
            f.write(json.dumps(result_data, ensure_ascii=False, default=str) + "\n")

        # Output final status
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