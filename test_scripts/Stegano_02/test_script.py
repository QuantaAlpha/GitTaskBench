import argparse
import sys
import json
import os
from datetime import datetime

def compare_txt_files(extracted_txt_path, ground_truth_txt_path):
    """
    比较提取出来的txt文件与ground truth是否一致，返回结构化结果
    """
    comments = []
    process_status = True
    final_result_status = False
    time_point = datetime.now().isoformat()

    # === 输入文件检查 ===
    if not os.path.exists(extracted_txt_path) or os.path.getsize(extracted_txt_path) == 0:
        comments.append(f"❌ 错误：提取的TXT文件 '{extracted_txt_path}' 不存在或为空")
        process_status = False
    if not os.path.exists(ground_truth_txt_path) or os.path.getsize(ground_truth_txt_path) == 0:
        comments.append(f"❌ 错误：GT文件 '{ground_truth_txt_path}' 不存在或为空")
        process_status = False

    if process_status:
        try:
            with open(extracted_txt_path, "r", encoding="utf-8") as f:
                extracted_message = f.read().strip()
            with open(ground_truth_txt_path, "r", encoding="utf-8") as f:
                ground_truth_message = f.read().strip()

            if extracted_message == ground_truth_message:
                comments.append(f"✅ 测试通过：提取消息与ground truth一致 (match = 100%)")
                final_result_status = True
            else:
                comments.append(f"❌ 测试失败：内容不一致！\n提取到: {extracted_message}\n预期: {ground_truth_message}")
                final_result_status = False
        except Exception as e:
            comments.append(f"❌ 异常：读取或比较文件时出错: {e}")
            process_status = False

    return {
        "Process": process_status,
        "Result": final_result_status,
        "TimePoint": time_point,
        "comments": "\n".join(comments)
    }

def write_to_jsonl(file_path, data):
    """
    将单条结果以 JSONL 形式写入文件（追加模式）
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
        print(f"✅ 结果已追加到 JSONL 文件: {file_path}")
    except Exception as e:
        print(f"❌ 写入 JSONL 文件时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description="测试隐藏水印提取结果")
    parser.add_argument("--groundtruth", type=str, required=True, help="提取出的txt文件路径")
    parser.add_argument("--output", type=str, required=True, help="ground truth txt路径")
    parser.add_argument("--result", type=str, required=False, help="可选：输出 JSONL 结果的路径")

    args = parser.parse_args()

    result = compare_txt_files(args.groundtruth, args.output)

    # 打印提示
    print(result["comments"])

    # 写入结果文件
    if args.result:
        write_to_jsonl(args.result, result)

    # 输出最终状态（替代原退出逻辑）
    print("\n测试完成 - 最终状态: " + ("通过" if result["Process"] and result["Result"] else "未通过"))

if __name__ == "__main__":
    main()