import argparse
import sys
import os
import json
from datetime import datetime

def compute_precision_recall(extracted_content, ground_truth):
    """计算precision和recall的函数"""
    extracted_chars = set(extracted_content.lower())
    ground_truth_chars = set(ground_truth.lower())

    intersection = extracted_chars & ground_truth_chars
    precision = len(intersection) / len(extracted_chars) if extracted_chars else 0
    recall = len(intersection) / len(ground_truth_chars) if ground_truth_chars else 0

    return precision, recall

def check_file_exists(file_path):
    """检查文件是否存在，并且不为空"""
    if not os.path.isfile(file_path):
        print(f"❌ 错误: 文件不存在: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ 错误: 文件为空: {file_path}")
        return False
    return True

def compare_txt_files(extracted_txt_path, ground_truth_txt_path, result_file):
    process_status = False
    results_status = False
    comments = ""
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    try:
        # 检查文件是否存在且不为空
        process_status = check_file_exists(extracted_txt_path) and check_file_exists(ground_truth_txt_path)

        if not process_status:
            comments = "提取或标准文件缺失/为空"
        else:
            # 读取文本内容
            with open(extracted_txt_path, "r", encoding="utf-8") as f:
                extracted_message = f.read().strip()

            with open(ground_truth_txt_path, "r", encoding="utf-8") as f:
                ground_truth_message = f.read().strip()

            # 计算精度和召回率
            precision, recall = compute_precision_recall(extracted_message, ground_truth_message)
            passed = recall >= 0.5
            results_status = passed
            comments = f"🔍 精度: {precision:.4f} | 召回率: {recall:.4f} —— {'✅ 通过' if passed else '❌ 未通过（召回 < 50%）'}"
            print(comments)

    except Exception as e:
        comments = f"❌ 测试异常: {e}"
        print(comments)

    # 写入 jsonl 结果
    result_data = {
        "Process": process_status,
        "Result": results_status,
        "TimePoint": time_point,
        "comments": comments
    }

    with open(result_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result_data, ensure_ascii=False, default=str) + "\n")

def main():
    parser = argparse.ArgumentParser(description="比较提取文本与ground truth文件内容")
    parser.add_argument("--output", required=True, help="提取的txt文件路径")
    parser.add_argument("--groundtruth", required=True, help="ground truth txt文件路径")
    parser.add_argument("--result", required=True, help="存储测试结果的jsonl文件路径")

    args = parser.parse_args()
    compare_txt_files(args.output, args.groundtruth, args.result)

if __name__ == "__main__":
    main()
