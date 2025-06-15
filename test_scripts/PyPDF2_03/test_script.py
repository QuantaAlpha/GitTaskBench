import argparse
import json
import os
import sys
from datetime import datetime

TARGET_FIELDS = ["Author", "Title", "CreationDate"]


def load_truth_metadata(file_path):
    try:
        metadata = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if ': ' in line:
                    key, val = line.strip().split(': ', 1)
                    key = key.strip().lstrip('/')
                    metadata[key] = val.strip()
        return metadata
    except Exception as e:
        print(f"[load_truth_metadata] Error: {e}", file=sys.stderr)
        return None


def load_pred_metadata(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext not in ('.json', '.jsonl'):
        raise ValueError(f"Unsupported file format: {ext}. Only .json and .jsonl are allowed.")

    try:
        content = None
        for enc in ['utf-8', 'latin-1', 'gbk', 'utf-16']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except Exception:
                continue

        if content is None:
            raise ValueError('cannot read file')
        content = content.strip()

        # JSON object or array
        if content.startswith('{') or content.startswith('['):
            try:
                data = json.loads(content)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    data = data[0]
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        # try jsonl: parse last valid line
        for line in content.splitlines()[::-1]:
            try:
                doc = json.loads(line)
                if isinstance(doc, dict):
                    return doc
            except Exception:
                continue

        # fallback: parse key:value lines (shouldn't happen for json/jsonl)
        md = {}
        for line in content.splitlines():
            if ': ' in line:
                k, v = line.split(': ', 1)
                md[k.strip().lstrip('/')] = v.strip()
        return md

    except Exception as e:
        print(f"[load_pred_metadata] Error: {e}", file=sys.stderr)
        return None


def compute_recall(pred, truth):
    pred_chars = set(pred.lower())
    truth_chars = set(truth.lower())
    if not truth_chars:
        return 1.0
    return len(pred_chars & truth_chars) / len(truth_chars)


def evaluate(pred_file, truth_file, result_file):
    if not os.path.isfile(pred_file):
        msg = f"Error: Prediction file '{pred_file}' does not exist."
        print(msg)
        record_result(result_file, result=False, comments=msg, process_success=False)
        return False

    if not os.path.isfile(truth_file):
        msg = f"Error: Ground truth file '{truth_file}' does not exist."
        print(msg)
        record_result(result_file, result=False, comments=msg, process_success=False)
        return False

    _, ext = os.path.splitext(pred_file)
    ext = ext.lower()
    if ext not in ('.json', '.jsonl'):
        msg = f"Error: File {pred_file} must be .json or .jsonl format."
        print(msg)
        record_result(result_file, result=False, comments=msg, process_success=False)
        return False

    truth = load_truth_metadata(truth_file)
    if truth is None:
        record_result(result_file, result=False, comments="Failed to load truth metadata", process_success=False)
        return False

    pred = load_pred_metadata(pred_file)
    if pred is None:
        record_result(result_file, result=False, comments="Failed to load prediction metadata", process_success=False)
        return False

    passed = 0
    comments = []

    for field in TARGET_FIELDS:
        tval = truth.get(field, '')
        pval = str(pred.get(field, ''))
        recall = compute_recall(pval, tval)
        ok = recall >= 0.8
        comments.append({
            'field': field,
            'recall': recall,
            'pass': ok
        })
        if ok:
            passed += 1

    total = len(TARGET_FIELDS)
    overall = (passed / total) >= 0.8

    record_result(result_file, result=overall, comments=comments, process_success=True)
    print(f"Overall Result: {'PASS' if overall else 'FAIL'} ({passed}/{total})")
    return overall


def record_result(result_file, result, comments, process_success=True):
    time_point = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    result_data = {
        "Process": process_success,
        "Result": result,
        "TimePoint": time_point,
        "comments": comments
    }

    try:
        os.makedirs(os.path.dirname(result_file) or '.', exist_ok=True)
        with open(result_file, 'a', encoding='utf-8') as file:
            json.dump(result_data, file, ensure_ascii=False, default=str)
            file.write('\n')
    except Exception as e:
        print(f"Error: Unable to write to result file {result_file}, reason: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate PDF metadata recall')
    parser.add_argument('--output', required=True, help='Prediction file path')
    parser.add_argument('--groundtruth', required=True, help='Truth file path')
    parser.add_argument('--result', required=True, help='Output JSONL result file')
    args = parser.parse_args()

    try:
        success = evaluate(args.output, args.groundtruth, args.result)
    except Exception as e:
        error_msg = f"Critical error during execution: {str(e)}"
        print(error_msg)
        record_result(args.result, result=False, comments=error_msg, process_success=False)
        success = False
