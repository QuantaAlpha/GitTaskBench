import argparse
import json
import os
from datetime import datetime
from difflib import SequenceMatcher


def check_file_valid(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ 文件为空: {file_path}")
        return False
    return True


def load_json_or_jsonl(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []

        # 尝试解析为 JSON array
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # 否则按 JSONL 处理
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
                print(f"❌ 第 {i} 行 JSON 解析失败: {line}")
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
            "comments": f"❌ 文件不存在或为空: pred={pred_path}, truth={truth_path}"
        }
        if result_path:
            with open(result_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        return False

    try:
        pred_lines = load_json_or_jsonl(pred_path)
        true_lines = load_json_or_jsonl(truth_path)

        if len(pred_lines) != len(true_lines):
            print(f"⚠️ 抓取结果与标注数量不一致（预测 {len(pred_lines)} 条，真实 {len(true_lines)} 条）")

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

        print(f"📊 平均字段相似度 (编辑距离相似度): {avg_similarity:.2%}")
        print("✅ 提取有效，相似度 >= 95%" if result_passed else "❌ 提取失败")

        if result_path:
            result = {
                "Process": True,
                "Result": result_passed,
                "TimePoint": datetime.now().isoformat(),
                "comments": f"平均字段相似度: {avg_similarity:.4f}，{'满足' if result_passed else '不满足'} 95% 阈值"
            }
            with open(result_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

        return result_passed

    except Exception as e:
        print(f"❌ 运行异常: {e}")
        if result_path:
            result = {
                "Process": True,
                "Result": False,
                "TimePoint": datetime.now().isoformat(),
                "comments": f"运行异常: {str(e)}"
            }
            with open(result_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评估 Scrapy 抓取结果的字段级相似度")
    parser.add_argument("--output", type=str, required=True, help="预测结果（JSON/JSONL）路径")
    parser.add_argument("--groundtruth", type=str, required=True, help="标注数据（JSON/JSONL）路径")
    parser.add_argument("--result", type=str, required=False, help="保存结果的JSONL文件路径")

    args = parser.parse_args()
    success = evaluate_scrapy_output(args.output, args.groundtruth, args.result)

