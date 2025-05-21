import argparse
import json
import os
from datetime import datetime
from difflib import SequenceMatcher


def check_file_valid(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        print(f"❌ File does not exist: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ File is empty: {file_path}")
        return False
    return True


def load_json_or_jsonl(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []

        # Try to parse as JSON array
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Otherwise process as JSONL
    lines = []
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, list):
                    lines.extend(item)
                else:
                    lines.append(item)
            except Exception as e:
                print(f"❌ Line {i} JSON parse failed: {line}")
                raise e
    return lines


def normalized_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def evaluate_scrapy_output(pred_path: str, truth_path: str, result_path: str = None) -> bool:
    threshold = 0.95
    process_success = check_file_valid(pred_path) and check_file_valid(truth_path)

    if not process_success:
        result = {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": f"❌ File does not exist or is empty: pred={pred_path}, truth={truth_path}"
        }
        if result_path:
            with open(result_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        return False

    try:
        pred_lines = load_json_or_jsonl(pred_path)
        true_lines = load_json_or_jsonl(truth_path)

        if len(pred_lines) != len(true_lines):
            print(f"⚠️ Crawl results count mismatch (predicted {len(pred_lines)}, truth {len(true_lines)})")

        total_fields = 0
        total_similarity = 0

        for pred, true in zip(pred_lines, true_lines):
            for field in ["author", "text"]:
                pred_val = str(pred.get(field, ""))
                true_val = str(true.get(field, ""))
                sim = normalized_similarity(pred_val, true_val)
                total_similarity += sim
                total_fields += 1

        avg_similarity = total_similarity / total_fields if total_fields else 0
        result_passed = avg_similarity >= threshold

        print(f"📊 Average field similarity (edit distance): {avg_similarity:.2%}")
        print("✅ Extraction valid, similarity >= 95%" if result_passed else "❌ Extraction failed")

        if result_path:
            result = {
                "Process": True,
                "Result": result_passed,
                "TimePoint": datetime.now().isoformat(),
                "comments": f"Average field similarity: {avg_similarity:.4f}, {'meets' if result_passed else 'does not meet'} 95% threshold"
            }
            with open(result_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

        return result_passed

    except Exception as e:
        print(f"❌ Runtime error: {e}")
        if result_path:
            result = {
                "Process": True,
                "Result": False,
                "TimePoint": datetime.now().isoformat(),
                "comments": f"Runtime error: {str(e)}"
            }
            with open(result_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate field-level similarity of Scrapy crawl results")
    parser.add_argument("--output", type=str, required=True, help="Prediction results (JSON/JSONL) path")
    parser.add_argument("--groundtruth", type=str, required=True, help="Ground truth (JSON/JSONL) path")
    parser.add_argument("--result", type=str, required=False, help="Output JSONL file path for results")

    args = parser.parse_args()
    success = evaluate_scrapy_output(args.output, args.groundtruth, args.result)