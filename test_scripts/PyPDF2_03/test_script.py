import argparse
import json
import os
import sys
from datetime import datetime

TARGET_FIELDS = ["Author", "Title", "CreationDate"]


def load_truth_metadata(file_path):
    metadata = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ': ' in line:
                key, val = line.strip().split(': ', 1)
                key = key.strip().lstrip('/')
                metadata[key] = val.strip()
    return metadata


def load_pred_metadata(file_path):
    # support json, jsonl, txt key:value
    try:
        content = None
        # try text read
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
                # try jsonl: parse last valid line
                for line in content.splitlines()[::-1]:
                    try:
                        doc = json.loads(line)
                        if isinstance(doc, dict):
                            return doc
                    except Exception:
                        continue
        # fallback: parse key:value lines
        md = {}
        for line in content.splitlines():
            if ': ' in line:
                k, v = line.split(': ', 1)
                md[k.strip().lstrip('/')] = v.strip()
        return md
    except Exception as e:
        print(f"Error loading pred metadata: {e}", file=sys.stderr)
        return {}


def compute_recall(pred, truth):
    pred_chars = set(pred.lower())
    truth_chars = set(truth.lower())
    if not truth_chars:
        return 1.0
    return len(pred_chars & truth_chars) / len(truth_chars)


def evaluate(pred_file, truth_file, result_file):
    truth = load_truth_metadata(truth_file)
    pred = load_pred_metadata(pred_file)

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

    # prepare result
    entry = {
        'Process': True,
        'Result': overall,
        'TimePoint': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'comments': comments
    }
    # write
    os.makedirs(os.path.dirname(result_file) or '.', exist_ok=True)
    with open(result_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + '\n')

    # print simple
    print(f"Overall Result: {'PASS' if overall else 'FAIL'} ({passed}/{total})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate PDF metadata recall')
    parser.add_argument('--output', required=True, help='Prediction file path')
    parser.add_argument('--groundtruth', required=True, help='Truth file path')
    parser.add_argument('--result', required=True, help='Output JSONL result file')
    args = parser.parse_args()
    evaluate(args.output, args.groundtruth, args.result)