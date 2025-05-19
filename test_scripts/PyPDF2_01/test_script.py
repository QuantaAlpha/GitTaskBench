import argparse
import json
import os
from datetime import datetime

def load_txt(file_path):
    """读取文本文件，若文件不存在或不可读取，则返回 False"""
    if not os.path.isfile(file_path):
        print(f"❌ 错误: 文件不存在或无法访问: {file_path}")
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ 错误: 打开文件时发生异常: {str(e)}")
        return False

def evaluate(pred_file, truth_file, result_file):
    """比较预测文本和标准文本的准确率"""
    # 检查文件是否能成功打开
    pred_text = load_txt(pred_file)
    truth_text = load_txt(truth_file)

    if not pred_text or not truth_text:
        process_status = False
        result_status = False
        comments = f"无法读取文件 {pred_file if not pred_text else truth_file}"
        write_result(result_file, process_status, result_status, comments)
        return

    # 去掉空格和换行符进行比对
    pred_text = pred_text.replace("\n", "").replace(" ", "")
    truth_text = truth_text.replace("\n", "").replace(" ", "")

    total = len(truth_text)
    if total == 0:
        print("⚠️ 标准答案文件没有文本内容！")
        process_status = False
        result_status = False
        comments = "标准答案文件为空"
        write_result(result_file, process_status, result_status, comments)
        return

    correct = 0
    for i in range(min(len(pred_text), len(truth_text))):
        if pred_text[i] == truth_text[i]:
            correct += 1

    accuracy = (correct / total) * 100
    print(f"提取的文本内容准确率：{accuracy:.2f}%")

    if accuracy >= 95:
        print("✅ 测试通过！")
        process_status = True
        result_status = True
        comments = f"提取的文本准确率 {accuracy:.2f}%，满足要求。"
    else:
        print("❌ 测试未通过！")
        process_status = True
        result_status = False
        comments = f"提取的文本准确率 {accuracy:.2f}%，未达到要求。"

    write_result(result_file, process_status, result_status, comments)

def write_result(result_file, process_status, result_status, comments):
    """将测试结果写入到 JSONL 文件"""
    result_data = {
        "Process": process_status,
        "Result": result_status,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": comments
    }

    # 如果文件存在，则追加到文件；如果文件不存在，则创建新文件
    with open(result_file, 'a', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False)
        f.write("\n")  # 每条记录写完后换行

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="提取出的文本文件")
    parser.add_argument("--groundtruth", type=str, required=True, help="标准文本文件")
    parser.add_argument("--result", type=str, required=True, help="保存结果的 JSONL 文件")
    args = parser.parse_args()

    evaluate(args.output, args.groundtruth, args.result)