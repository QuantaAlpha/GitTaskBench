import argparse
import json
import os
from datetime import datetime

def load_txt(file_path):
    try:
        emails = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                emails.append(line.strip())  # 去掉换行符
        return emails, None
    except Exception as e:
        return [], str(e)

def evaluate(pred_file, truth_file):
    pred_emails, pred_err = load_txt(pred_file)
    truth_emails, truth_err = load_txt(truth_file)

    process_ok = True
    comments = ""

    if pred_err:
        comments += f"[预测文件读取失败] {pred_err}\n"
        process_ok = False
    if truth_err:
        comments += f"[GT文件读取失败] {truth_err}\n"
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
            "comments": "⚠️ 标准答案文件没有邮箱！"
        }

    correct = 0
    for pred_email in pred_emails:
        if pred_email in truth_emails:
            correct += 1

    accuracy = (correct / total) * 100
    passed = accuracy >= 98
    result_msg = (
        f"提取的邮箱地址准确率：{accuracy:.2f}%\n"
        + ("✅ 测试通过！" if passed else "❌ 测试未通过！")
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
    parser.add_argument("--output", type=str, required=True, help="提取出的邮箱地址文件")
    parser.add_argument("--groundtruth", type=str, required=True, help="标准邮箱地址文件")
    parser.add_argument("--result", type=str, required=True, help="结果输出 JSONL 文件路径")
    args = parser.parse_args()

    result_dict = evaluate(args.output, args.groundtruth)
    append_result_to_jsonl(args.result, result_dict)

