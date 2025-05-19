import csv
import argparse
import json
from datetime import datetime
import os

def validate_fake_companies(file_path, expected_num_companies=5, result_file=None):
    # 读取生成的 CSV 文件
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
    except Exception as e:
        print(f"错误：无法读取文件 {file_path}，原因：{str(e)}")
        if result_file:
            record_result(result_file, False, f"无法读取文件，原因：{str(e)}")
        return False
    
    # 验证行数是否符合预期
    if len(rows) != expected_num_companies:
        error_message = f"错误：文件中应该包含 {expected_num_companies} 条公司数据，但实际包含 {len(rows)} 条数据。"
        print(error_message)
        if result_file:
            record_result(result_file, False, error_message)
        return False
    
    # 验证每条数据是否包含 "公司名称"、"地址" 和 "电话"
    for row in rows:
        if not all(field in row for field in ['Company Name', 'Address', 'Phone']):
            error_message = f"错误：某条数据缺少必填字段（公司名称、地址或电话）"
            print(error_message)
            if result_file:
                record_result(result_file, False, error_message)
            return False

    success_message = f"所有 {expected_num_companies} 条公司数据验证通过！"
    print(success_message)
    if result_file:
        record_result(result_file, True, success_message)
    return True

def record_result(result_file, result, comments):
    # 获取当前时间戳
    time_point = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    # 构建结果字典
    result_data = {
        "Process": True,  # 这里可以设为 True，也可以根据需要动态调整
        "Result": result,  # 这里根据验证结果设置为布尔值
        "TimePoint": time_point,
        "comments": comments
    }
    
    # 写入 jsonl 文件
    try:
        # 如果文件不存在，创建一个新文件并写入
        with open(result_file, 'a', encoding='utf-8') as file:
            json.dump(result_data, file, ensure_ascii=False, default=str)
            file.write('\n')  # 每次写入新的一行
    except Exception as e:
        print(f"错误：无法写入结果文件 {result_file}，原因：{str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="验证生成的假公司数据")
    parser.add_argument('--output', type=str, required=True, help="生成的 CSV 文件路径")
    parser.add_argument('--result', type=str, required=False, help="结果保存的 jsonl 文件路径", default="test_results.jsonl")
    args = parser.parse_args()

    # 执行验证
    validate_fake_companies(args.output, result_file=args.result)