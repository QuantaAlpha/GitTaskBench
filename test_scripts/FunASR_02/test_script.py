import os
import sys
import json
import argparse
from difflib import SequenceMatcher
import datetime
import re

def check_file_exists(file_path):
    """Check if file exists and is not empty"""
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    return True, ""


def cer(ref, hyp):
    """Character Error Rate = Edit Distance / Length of Reference"""
    import numpy as np
    ref = list(ref)
    hyp = list(hyp)
    d = np.zeros((len(ref)+1, len(hyp)+1), dtype=int)
    for i in range(len(ref)+1):
        d[i][0] = i
    for j in range(len(hyp)+1):
        d[0][j] = j
    for i in range(1, len(ref)+1):
        for j in range(1, len(hyp)+1):
            cost = 0 if ref[i-1] == hyp[j-1] else 1
            d[i][j] = min(
                d[i-1][j] + 1,      # deletion
                d[i][j-1] + 1,      # insertion
                d[i-1][j-1] + cost  # substitution
            )
    return d[len(ref)][len(hyp)] / max(len(ref), 1)


def is_likely_english(text):
    english_letters = re.findall(r'[a-zA-Z]', text)
    if not english_letters:
        return False
    ratio = len(english_letters) / max(len(text), 1)
    return ratio > 0.5 and len(english_letters) >= 10  # at least 10 letters, >50% are English



def load_transcripts(file_path):
    """Load transcript text from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().replace("\n", ""), ""
    except Exception as e:
        return None, str(e)


def evaluate(system_output_file, ground_truth_file, cer_threshold=0.05):
    """Main evaluation function: Calculate CER between system output and ground truth"""
    # Check files
    process_ok, process_msg = check_file_exists(system_output_file)
    if not process_ok:
        return False, False, process_msg

    process_ok, process_msg = check_file_exists(ground_truth_file)
    if not process_ok:
        return False, False, process_msg

    # Load transcripts
    system_trans, msg = load_transcripts(system_output_file)
    if system_trans is None:
        return True, False, f"Failed to load system output: {msg}"

    ground_truth, msg = load_transcripts(ground_truth_file)
    if ground_truth is None:
        return True, False, f"Failed to load ground truth: {msg}"

    if not is_likely_english(system_trans):
        return True, False, "Output text does not appear to be valid English transcription"

    # Calculate CER
    score = cer(ground_truth, system_trans)
    comments = [f"CER = {score:.4f}"]

    result_ok = score <= cer_threshold
    if not result_ok:
        comments.append(f"CER ({score:.4f}) exceeds threshold {cer_threshold}")

    return True, result_ok, "\n".join(comments)


def save_results_to_jsonl(process_ok, result_ok, comments, jsonl_file):
    """Save test results to JSONL file"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    result_data = {
        "Process": bool(process_ok),
        "Result": bool(result_ok),
        "TimePoint": current_time,
        "comments": comments
    }

    os.makedirs(os.path.dirname(jsonl_file), exist_ok=True)

    with open(jsonl_file, 'a', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, default=str)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description='Evaluate speech recognition results')
    parser.add_argument('--output', required=True, help='System output file path')
    parser.add_argument('--groundtruth', required=True, help='Ground truth file path')
    parser.add_argument('--cer_threshold', type=float, default=0.10, help='CER threshold')
    parser.add_argument('--result', required=True, help='Result JSONL file path')

    args = parser.parse_args()

    process_ok, result_ok, comments = evaluate(
        args.output,
        args.groundtruth,
        args.cer_threshold
    )

    save_results_to_jsonl(process_ok, result_ok, comments, args.result)

    if not process_ok:
        print(f"Processing failed: {comments}")
    if not result_ok:
        print(f"Results do not meet requirements: {comments}")
    print("Test completed")  # Changed to neutral prompt


if __name__ == "__main__":
    main()