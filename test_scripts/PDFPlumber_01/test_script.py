import argparse
import difflib
import os
import json
from datetime import datetime

def check_file_exists(file_path):
    """检查文件是否存在且非空"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    if os.path.getsize(file_path) == 0:
        print(f"❌ 文件为空: {file_path}")
        return False
    return True

def compute_similarity(pred_text, truth_text):
    """
    计算两个文本的整体相似度，返回百分比
    """
    seq = difflib.SequenceMatcher(None, pred_text, truth_text)
    return seq.ratio() * 100

def evaluate(pred_file, truth_file, result_file):
    """
    测试函数，传入预测文件路径和真实文件路径，输出相似度
    """
    process_status = True
    comments = ""

    # 检查文件存在性
    if not check_file_exists(pred_file):
        process_status = False
        comments = f"预测文件 {pred_file} 不存在或为空。"
    if not check_file_exists(truth_file):
        process_status = False
        comments = f"真实文件 {truth_file} 不存在或为空。"

    # 处理文件和计算相似度
    if process_status:
        with open(pred_file, 'r', encoding='utf-8') as f_pred, open(truth_file, 'r', encoding='utf-8') as f_truth:
            pred_text = f_pred.read().strip()
            truth_text = f_truth.read().strip()

        similarity = compute_similarity(pred_text, truth_text)
        print(f"文本整体相似度：{similarity:.2f}%")

        result_status = similarity >= 98
        if result_status:
            print("✅ 测试通过！整体文本相似度达到要求。")
        else:
            print("❌ 测试未通过，相似度低于98%。")
    else:
        result_status = False
        print("❌ 测试未通过，文件检查失败。")

    # 获取当前时间
    time_point = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 生成结果数据
    result_data = {
        "Process": process_status,
        "Results": result_status,
        "TimePoint": time_point,
        "comments": comments
    }

    # 写入结果到 JSONL 文件
    if os.path.exists(result_file):
        with open(result_file, 'a', encoding='utf-8') as f_result:
            f_result.write(json.dumps(result_data, default=str) + '\n')
    else:
        with open(result_file, 'w', encoding='utf-8') as f_result:
            f_result.write(json.dumps(result_data, default=str) + '\n')

    print(f"结果已保存到: {result_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="提取出的文本文件路径")
    parser.add_argument("--groundtruth", type=str, required=True, help="真实标准文本文件路径")
    parser.add_argument("--result", type=str, required=True, help="结果输出文件路径")
    args = parser.parse_args()

    evaluate(args.output, args.groundtruth, args.result)
