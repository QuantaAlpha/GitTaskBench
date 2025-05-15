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

    # 读取错误检查
    if pred_err:
        comments.append(f"[预测文件读取失败] {pred_err}")
        process_ok = False
    if truth_err:
        comments.append(f"[GT文件读取失败] {truth_err}")
        process_ok = False

    if not process_ok:
        return {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # 至少要有一行作为header
    if not pred_rows or not truth_rows:
        comments.append("⚠️ 没有找到任何数据行！")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # 提取列名
    pred_header = pred_rows[0]
    truth_header = truth_rows[0]

    # 比较列名顺序
    if pred_header != truth_header:
        comments.append(f"⚠️ 列名或顺序不一致！预测列: {pred_header}，GT列: {truth_header}")
    else:
        comments.append("✅ 列名和顺序一致。")

    # 构造纯列表内容，跳过header行
    pred_data = pred_rows[1:]
    truth_data = truth_rows[1:]

    total_rows = min(len(pred_data), len(truth_data))
    if total_rows == 0:
        comments.append("⚠️ 没有数据行进行比较！")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # 逐行逐列按顺序比较
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
        # 若列数不一致，也需计入未匹配
        total_cells += abs(len(pr) - len(tr))

    # 计算匹配率
    match_rate = (match_count / total_cells) * 100 if total_cells else 0
    passed = match_rate >= 75
    comments.append(f"整体按列顺序比较内容匹配率：{match_rate:.2f}% (阈值=75%)")
    if passed:
        comments.append("✅ 测试通过！")
    else:
        comments.append("❌ 测试未通过！")

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
    parser.add_argument("--output", type=str, required=True, help="提取出的整体表格路径")
    parser.add_argument("--groundtruth", type=str, required=True, help="标准整体表格路径")
    parser.add_argument("--result", type=str, required=True, help="结果输出 JSONL 文件路径")
    args = parser.parse_args()

    result_dict = evaluate(args.output, args.groundtruth)
    append_result_to_jsonl(args.result, result_dict)

