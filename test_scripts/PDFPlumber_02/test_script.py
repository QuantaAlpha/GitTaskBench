import argparse
import csv
import json
import os
from datetime import datetime

def load_csv(file_path):
    try:
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
        return rows, None
    except Exception as e:
        return [], str(e)


def evaluate(pred_file, truth_file):
    pred_rows, pred_err = load_csv(pred_file)
    truth_rows, truth_err = load_csv(truth_file)

    process_ok = True
    comments = []

    # Check for read errors
    if pred_err:
        comments.append(f"[Prediction file read failed] {pred_err}")
        process_ok = False
    if truth_err:
        comments.append(f"[GT file read failed] {truth_err}")
        process_ok = False

    if not process_ok:
        return {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # Need at least one row as header
    if not pred_rows or not truth_rows:
        comments.append("⚠️ No data rows found!")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # Extract column names
    pred_header = pred_rows[0]
    truth_header = truth_rows[0]

    # Compare column name order
    if pred_header != truth_header:
        comments.append(f"⚠️ Column names or order mismatch! Prediction columns: {pred_header}, GT columns: {truth_header}")
    else:
        comments.append("✅ Column names and order match.")

    # Construct pure list content, skip header row
    pred_data = pred_rows[1:]
    truth_data = truth_rows[1:]

    total_rows = min(len(pred_data), len(truth_data))
    if total_rows == 0:
        comments.append("⚠️ No data rows for comparison!")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # Compare cell by cell in order
    match_count = 0
    total_cells = 0
    for i in range(total_rows):
        pr = pred_data[i]
        tr = truth_data[i]
        min_cols = min(len(pr), len(tr))
        for j in range(min_cols):
            total_cells += 1
            if pr[j] == tr[j]:
                match_count += 1
        # Count mismatches for unequal column counts
        total_cells += abs(len(pr) - len(tr))

    # Calculate match rate
    match_rate = (match_count / total_cells) * 100 if total_cells else 0
    passed = match_rate >= 75
    comments.append(f"Overall cell-by-cell match rate: {match_rate:.2f}% (threshold=75%)")
    if passed:
        comments.append("✅ Test passed!")
    else:
        comments.append("❌ Test failed!")

    return {
        "Process": True,
        "Result": passed,
        "TimePoint": datetime.now().isoformat(),
        "comments": "\n".join(comments)
    }


def append_result_to_jsonl(result_path, result_dict):
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, default=str)
        f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="Path to extracted complete table")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to standard complete table")
    parser.add_argument("--result", type=str, required=True, help="Path to output JSONL result file")
    args = parser.parse_args()

    result_dict = evaluate(args.output, args.groundtruth)
    append_result_to_jsonl(args.result, result_dict)