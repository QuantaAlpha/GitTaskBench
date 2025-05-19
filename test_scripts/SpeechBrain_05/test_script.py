import json
import argparse
import os
import datetime

def evaluate_accuracy(output_file, gt_file, result_file):
    # 初始化返回的结果字典
    process_result = False
    result = False
    comments = ""
    
    # 1. 检查 output 文件是否存在、非空、格式正确
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, "r") as f:
                output_data = json.load(f)
            if 'prediction' not in output_data:
                comments += "Error: Output JSON file does not contain 'prediction' key.\n"
            else:
                process_result = True  # 文件检查通过
        except Exception as e:
            comments += f"Error: Could not read output file - {str(e)}\n"
    else:
        comments += "Error: Output file does not exist or is empty.\n"

    # 2. 检查 gt 文件是否存在、非空、格式正确
    if os.path.exists(gt_file) and os.path.getsize(gt_file) > 0:
        try:
            with open(gt_file, "r") as f:
                gt_data = json.load(f)
            if 'prediction' not in gt_data:
                comments += "Error: Ground truth JSON file does not contain 'prediction' key.\n"
        except Exception as e:
            comments += f"Error: Could not read ground truth file - {str(e)}\n"
    else:
        comments += "Error: Ground truth file does not exist or is empty.\n"
    
    # 3. 比较 output 和 gt 的 prediction 是否一致
    if process_result:
        correct = output_data['prediction'] == gt_data['prediction']
        result = correct
        comments += f"Comparison result: {'Match' if correct else 'Mismatch'}\n"
    
    # 4. 获取当前时间戳
    time_point = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    # 5. 准备输出的字典
    result_dict = {
        "Process": process_result,
        "Result": result,
        "TimePoint": time_point,
        "comments": comments
    }
    
    # 6. 将结果写入 jsonl 文件
    with open(result_file, "a", encoding="utf-8") as result_f:
        result_f.write(json.dumps(result_dict, default=str) + "\n")

    # 输出到终端
    print(f"Process: {process_result}")
    print(f"Result: {result}")
    print(f"Comments: {comments}")

if __name__ == "__main__":
    # 使用 argparse 解析命令行输入
    parser = argparse.ArgumentParser(description="Evaluate the accuracy of speaker recognition task.")
    parser.add_argument("--output", type=str, help="Path to the output.json file")
    parser.add_argument("--groundtruth", type=str, help="Path to the ground truth (gt.json) file")
    parser.add_argument("--result", type=str, default="evaluation_result.jsonl", help="Path to store the evaluation results in JSONL format")

    # 解析命令行参数
    args = parser.parse_args()

    # 调用评估函数
    evaluate_accuracy(args.output, args.groundtruth, args.result)