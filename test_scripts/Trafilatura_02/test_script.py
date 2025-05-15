import os
import argparse
import numpy as np
import json
import datetime

# 引入Levenshtein距离的计算函数
from Levenshtein import distance as levenshtein_distance

def evaluate_extraction(pred_path, gt_path):
    # 固定阈值
    threshold = 0.5  # 编辑距离低于这个阈值即认为预测成功

    # 检查文件是否存在
    def check_file_exists(file_path):
        if not os.path.isfile(file_path):
            print(f"❌ 错误: 文件不存在: {file_path}")
            return False
        if os.path.getsize(file_path) == 0:
            print(f"❌ 错误: 文件为空: {file_path}")
            return False
        return True

    # 检查文件
    file_check = check_file_exists(pred_path) and check_file_exists(gt_path)
    if not file_check:
        return None, False

    # 读取预测结果
    with open(pred_path, 'r', encoding='utf-8') as f:
        pred_text = f.read()
    
    # 读取ground truth
    with open(gt_path, 'r', encoding='utf-8') as f:
        gt_text = f.read()
    
    # 计算编辑距离
    edit_distance = levenshtein_distance(pred_text, gt_text)
    max_len = max(len(pred_text), len(gt_text))
    
    # 计算编辑距离比率
    edit_distance_ratio = edit_distance / max_len if max_len > 0 else 0

    # 输出编辑距离比率
    print(f"编辑距离比率（Edit Distance Ratio）: {edit_distance_ratio:.4f}")

    # 判断是否达到阈值
    if edit_distance_ratio <= threshold:
        print("✅ 正确完成")
    else:
        print("❌ 提取有误")

    return edit_distance_ratio, True

def main():
    parser = argparse.ArgumentParser(description="Evaluate the edit distance between extracted and ground truth markdown content.")
    parser.add_argument('--output', type=str, required=True, help='Path to the extracted prediction markdown file')
    parser.add_argument('--groundtruth', type=str, required=True, help='Path to the ground truth markdown file')
    parser.add_argument('--result', type=str, required=True, help='Path to save the result in jsonl format')

    args = parser.parse_args()

    # 计算提取准确度（编辑距离比率）
    edit_distance_ratio, process_status = evaluate_extraction(pred_path=args.output, gt_path=args.groundtruth)

    # 保存结果
    result = {
        "Process": process_status,
        "Result": edit_distance_ratio <= 0.5 if process_status else False,  # 判断编辑距离比率是否低于阈值
        "TimePoint": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": f"编辑距离比率: {edit_distance_ratio:.4f} {'满足' if edit_distance_ratio <= 0.5 else '不满足'} 50% 精度要求" if process_status else "文件检查失败"
    }

    # 确保目录存在
    os.makedirs(os.path.dirname(args.result) or '.', exist_ok=True)
    
    # 写入结果
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    main()