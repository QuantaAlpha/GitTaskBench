import argparse
import difflib
import os
import json
from datetime import datetime

def check_file_exists(file_path):
    """Check if file exists and is not empty"""
    if not os.path.exists(file_path):
        print(f"❌ File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ File is empty: {file_path}")
        return False
    return True

def compute_similarity(pred_text, truth_text):
    """
    Calculate overall similarity between two texts, return percentage
    """
    seq = difflib.SequenceMatcher(None, pred_text, truth_text)
    return seq.ratio() * 100

def evaluate(pred_file, truth_file, result_file):
    """
    Test function, takes prediction file path and truth file path, outputs similarity
    """
    process_status = True
    comments = ""

    # Check file existence
    if not check_file_exists(pred_file):
        process_status = False
        comments = f"Prediction file {pred_file} does not exist or is empty."
    if not check_file_exists(truth_file):
        process_status = False
        comments = f"Truth file {truth_file} does not exist or is empty."

    # Process files and calculate similarity
    if process_status:
        with open(pred_file, 'r', encoding='utf-8') as f_pred, open(truth_file, 'r', encoding='utf-8') as f_truth:
            pred_text = f_pred.read().strip()
            truth_text = f_truth.read().strip()

        similarity = compute_similarity(pred_text, truth_text)
        print(f"Text similarity score: {similarity:.2f}%")

        result_status = similarity >= 98
        if result_status:
            print("✅ Test passed! Text similarity meets requirements.")
        else:
            print("❌ Test failed, similarity below 98%.")
    else:
        result_status = False
        print("❌ Test failed, file check failed.")

    # Get current time
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Generate result data
    result_data = {
        "Process": process_status,
        "Result": result_status,
        "TimePoint": time_point,
        "comments": comments
    }

    # Write results to JSONL file
    if os.path.exists(result_file):
        with open(result_file, 'a', encoding='utf-8') as f_result:
            f_result.write(json.dumps(result_data, default=str) + '\n')
    else:
        with open(result_file, 'w', encoding='utf-8') as f_result:
            f_result.write(json.dumps(result_data, default=str) + '\n')

    print(f"Results saved to: {result_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="Path to extracted text file")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to ground truth text file")
    parser.add_argument("--result", type=str, required=True, help="Path to output result file")
    args = parser.parse_args()

    evaluate(args.output, args.groundtruth, args.result)