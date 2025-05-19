import argparse
import re
import json
from datetime import datetime
import os

def jaccard_similarity(str1, str2):
    # 计算两个字符串的 Jaccard 相似度
    set1 = set(str1)
    set2 = set(str2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

def validate_fake_text(input_file, output_file, result_file=None):
    # 读取原始文件和生成的假文本文件内容
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            original_content = file.read()
    except Exception as e:
        print(f"错误：无法读取原始文本文件 {input_file}，原因：{str(e)}")
        if result_file:
            record_result(result_file, False, f"无法读取原始文本文件，原因：{str(e)}")
        return False

    try:
        with open(output_file, 'r', encoding='utf-8') as file:
            fake_content = file.read()
    except Exception as e:
        print(f"错误：无法读取假文本文件 {output_file}，原因：{str(e)}")
        if result_file:
            record_result(result_file, False, f"无法读取假文本文件，原因：{str(e)}")
        return False

    # 计算原始文本与假文本之间的 Jaccard 相似度
    similarity = jaccard_similarity(original_content, fake_content)
    print(f"原始文本与假文本的Jaccard相似度：{similarity:.4f}")

    # 设置一个相似度阈值来判断是否通过测试
    threshold = 0.2  # 阈值可以根据需要调整，0.2 表示假文本和原始文本之间的差异最大可以为 80%
    
    if similarity < threshold:
        result_message = f"❌ 假文本文件替换效果较好，相似度：{similarity:.4f} 低于阈值！"
        print(result_message)
        if result_file:
            record_result(result_file, False, result_message)
        return False
    else:
        result_message = f"✅ 假文本文件验证通过，相似度：{similarity:.4f} 超过阈值！"
        print(result_message)
        if result_file:
            record_result(result_file, True, result_message)
        return True

def record_result(result_file, result, comments):
    # 获取当前时间戳
    time_point = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    # 构建结果字典
    result_data = {
        "Process": True,
        "Result": result,
        "TimePoint": time_point,
        "comments": comments
    }
    
    # 写入 jsonl 文件
    try:
        # 如果文件不存在，创建一个新文件并写入
        file_exists = os.path.exists(result_file)
        with open(result_file, 'a', encoding='utf-8') as file:
            if not file_exists:
                # 如果文件不存在，先写入一个空的 json 行（可选）
                file.write('\n')
            json.dump(result_data, file, ensure_ascii=False, default=str)
            file.write('\n')
    except Exception as e:
        print(f"错误：无法写入结果文件 {result_file}，原因：{str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="验证假文本文件的替换效果")
    parser.add_argument("--groundtruth", type=str, required=True, help="原始文本文件路径")
    parser.add_argument("--output", type=str, required=True, help="生成的假文本文件路径")
    parser.add_argument("--result", type=str, required=False, help="结果保存的 jsonl 文件路径", default="test_results.jsonl")
    
    args = parser.parse_args()
    
    # 调用测试函数
    validate_fake_text(args.groundtruth, args.output, result_file=args.result)