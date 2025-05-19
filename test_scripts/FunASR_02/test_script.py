import os
import sys
import json
import argparse
from difflib import SequenceMatcher
import datetime

def check_file_exists(file_path):
    """检查文件是否存在且非空"""
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"文件为空: {file_path}"
    return True, ""

def cer(ref, hyp):
    """计算字符错误率 CER（Character Error Rate）"""
    matcher = SequenceMatcher(None, ref, hyp)
    edit_ops = sum(
        [max(triple[2] - triple[1], triple[2] - triple[1]) 
         for triple in matcher.get_opcodes() if triple[0] != 'equal']
    )
    return edit_ops / max(len(ref), 1)

def load_transcripts(file_path):
    """从文本文件加载转录文本"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().replace("\n", ""), ""
    except Exception as e:
        return None, str(e)

def evaluate(system_output_file, ground_truth_file, cer_threshold=0.05):
    """主评估函数：直接计算系统输出与标准答案的 CER"""
    # 检查文件
    process_ok, process_msg = check_file_exists(system_output_file)
    if not process_ok:
        return False, False, process_msg
    
    process_ok, process_msg = check_file_exists(ground_truth_file)
    if not process_ok:
        return False, False, process_msg
    
    # 加载转录文本
    system_trans, msg = load_transcripts(system_output_file)
    if system_trans is None:
        return True, False, f"加载系统输出失败: {msg}"
    
    ground_truth, msg = load_transcripts(ground_truth_file)
    if ground_truth is None:
        return True, False, f"加载标准答案失败: {msg}"

    # 计算 CER
    score = cer(ground_truth, system_trans)
    comments = [f"CER = {score:.4f}"]

    result_ok = score <= cer_threshold
    if not result_ok:
        comments.append(f"CER ({score:.4f}) 超过阈值 {cer_threshold}")
    
    return True, result_ok, "\n".join(comments)

def save_results_to_jsonl(process_ok, result_ok, comments, jsonl_file):
    """保存测试结果到JSONL文件"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    result_data = {
        "Process": bool(process_ok),
        "Result": bool(result_ok),
        "TimePoint": current_time,
        "comments": comments
    }
    
    os.makedirs(os.path.dirname(jsonl_file), exist_ok=True)
    
    with open(jsonl_file, 'a', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, default=str)
        f.write('\n')

def main():
    parser = argparse.ArgumentParser(description='评估语音识别结果')
    parser.add_argument('--output', required=True, help='系统输出文件路径')
    parser.add_argument('--groundtruth', required=True, help='标准答案文件路径')
    parser.add_argument('--cer_threshold', type=float, default=0.10, help='CER阈值')
    parser.add_argument('--result', required=True, help='结果JSONL文件路径')
    
    args = parser.parse_args()
    
    process_ok, result_ok, comments = evaluate(
        args.output,
        args.groundtruth,
        args.cer_threshold
    )
    
    save_results_to_jsonl(process_ok, result_ok, comments, args.result)
    
    if not process_ok:
        print(f"处理失败: {comments}")
    if not result_ok:
        print(f"结果不满足要求: {comments}")
    print("测试完成")  # 修改为中性提示

if __name__ == "__main__":
    main()