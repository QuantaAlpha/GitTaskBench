import argparse
import json
import os
from datetime import datetime

def load_txt(file_path):
    try:
        emails = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                emails.append(line.strip())  # Remove newline characters
        return emails, None
    except Exception as e:
        return [], str(e)

def evaluate(pred_file, truth_file):
    pred_emails, pred_err = load_txt(pred_file)
    truth_emails, truth_err = load_txt(truth_file)

    process_ok = True
    comments = ""

    if pred_err:
        comments += f"[Prediction file read failed] {pred_err}\n"
        process_ok = False
    if truth_err:
        comments += f"[GT file read failed] {truth_err}\n"
        process_ok = False

    if not process_ok:
        return {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": comments.strip()
        }

    total = len(truth_emails)
    if total == 0:
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "⚠️ Standard answer file has no email addresses!"
        }

    correct = 0
    for pred_email in pred_emails:
        if pred_email in truth_emails:
            correct += 1

    accuracy = (correct / total) * 100
    passed = accuracy >= 98
    result_msg = (
        f"Extracted email address accuracy: {accuracy:.2f}%\n"
        + ("✅ Test passed!" if passed else "❌ Test failed!")
    )

    return {
        "Process": True,
        "Result": passed,
        "TimePoint": datetime.now().isoformat(),
        "comments": result_msg
    }

def append_result_to_jsonl(result_path, result_dict):
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, default=str)
        f.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="Path to extracted email addresses file")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to standard email addresses file")
    parser.add_argument("--result", type=str, required=True, help="Path to output JSONL result file")
    args = parser.parse_args()

    result_dict = evaluate(args.output, args.groundtruth)
    append_result_to_jsonl(args.result, result_dict)