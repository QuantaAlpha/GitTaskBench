import argparse
import json
import os
import re
from datetime import datetime

def load_txt(file_path):
    """Load emails from a text file, one email per line, convert to lowercase."""
    try:
        emails = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                email = line.strip()
                if email:
                    emails.append(email.lower())  # Normalize to lowercase
        return emails, None
    except Exception as e:
        return [], str(e)

def is_valid_email(email):
    """Simple regex check to validate email format."""
    pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
    return re.match(pattern, email) is not None

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

    # Filter out invalid emails using regex
    pred_emails = set(e for e in pred_emails if is_valid_email(e))
    truth_emails = set(e for e in truth_emails if is_valid_email(e))

    if not truth_emails:
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "⚠️ Standard answer file has no valid email addresses!"
        }

    # Calculate true positives, false positives, false negatives
    true_positives = pred_emails.intersection(truth_emails)
    false_positives = pred_emails.difference(truth_emails)
    false_negatives = truth_emails.difference(pred_emails)

    precision = len(true_positives) / len(pred_emails) if pred_emails else 0
    recall = len(true_positives) / len(truth_emails)
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Pass criterion can be adjusted; here recall >= 98%
    passed = recall >= 0.98

    comments += (
        f"Precision: {precision:.2%}, Recall: {recall:.2%}, F1: {f1_score:.2%}\n"
        f"True Positives: {len(true_positives)}, False Positives: {len(false_positives)}, False Negatives: {len(false_negatives)}\n"
        f"False Positives: {sorted(false_positives)}\n"
        f"False Negatives: {sorted(false_negatives)}\n"
        + ("✅ Test passed!" if passed else "❌ Test failed!")
    )

    return {
        "Process": True,
        "Result": passed,
        "TimePoint": datetime.now().isoformat(),
        "comments": comments
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
