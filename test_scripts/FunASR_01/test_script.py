import os
import json
import argparse
import datetime
import numpy as np


def check_file_exists(file_path):
    """Check if file exists and is not empty"""
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"File is empty: {file_path}"
    return True, ""


def cer(ref, hyp):
    """Character Error Rate using Levenshtein distance"""
    r = ref
    h = hyp
    d = np.zeros((len(r)+1)*(len(h)+1), dtype=np.uint8).reshape((len(r)+1, len(h)+1))

    for i in range(len(r)+1):
        d[i][0] = i
    for j in range(len(h)+1):
        d[0][j] = j

    for i in range(1, len(r)+1):
        for j in range(1, len(h)+1):
            cost = 0 if r[i-1] == h[j-1] else 1
            d[i][j] = min(d[i-1][j] + 1,     # deletion
                          d[i][j-1] + 1,     # insertion
                          d[i-1][j-1] + cost)  # substitution

    return d[len(r)][len(h)] / max(len(r), 1)


def load_text(file_path):
    """Load full text content from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().replace('\n', '').strip(), ""
    except Exception as e:
        return None, str(e)


def evaluate(system_output_file, ground_truth_file, cer_threshold=0.05):
    """Evaluate CER between system output and ground truth"""
    # Check files
    process_ok, process_msg = check_file_exists(system_output_file)
    if not process_ok:
        return False, False, process_msg

    process_ok, process_msg = check_file_exists(ground_truth_file)
    if not process_ok:
        return False, False, process_msg

    # Load content
    sys_text, msg1 = load_text(system_output_file)
    gt_text, msg2 = load_text(ground_truth_file)

    if sys_text is None:
        return True, False, f"Failed to load system output: {msg1}"
    if gt_text is None:
        return True, False, f"Failed to load ground truth: {msg2}"

    score = cer(gt_text, sys_text)
    comment = f"CER = {score:.4f}"
    if score > cer_threshold:
        comment += f" ❌ Exceeds threshold {cer_threshold}"
        return True, False, comment
    else:
        comment += f" ✅ Within threshold {cer_threshold}"
        return True, True, comment


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
    parser = argparse.ArgumentParser(description='Evaluate speech recognition results (no speaker separation)')
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
    elif not result_ok:
        print(f"Results do not meet requirements: {comments}")
    else:
        print("✅ Test passed")
        print(comments)


if __name__ == "__main__":
    main()
