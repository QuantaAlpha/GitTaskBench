import csv
import re
import argparse
import os
import json
from datetime import datetime

def validate_fake_users(file_path):
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    comments = []
    process_ok = True
    result_ok = False

    if not os.path.isfile(file_path):
        comments.append(f"[错误] 文件不存在: {file_path}")
        process_ok = False
    elif os.path.getsize(file_path) == 0:
        comments.append(f"[错误] 文件为空: {file_path}")
        process_ok = False

    if process_ok:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for idx, row in enumerate(reader):
                    email = row.get('Email', '')
                    if not re.match(email_pattern, email):
                        comments.append(f"[行 {idx+2}] 无效的电子邮件：{email}")
                        break
                else:
                    comments.append("所有用户数据验证通过！")
                    result_ok = True
        except Exception as e:
            comments.append(f"[异常] 文件解析错误: {str(e)}")
            process_ok = False

    return {
        "Process": process_ok,
        "Result": result_ok,
        "TimePoint": datetime.now().isoformat(),
        "comments": " | ".join(comments)
    }

def main():
    parser = argparse.ArgumentParser(description="验证生成的假用户数据")
    parser.add_argument('--output', type=str, required=True, help="CSV文件路径")
    parser.add_argument('--result', type=str, required=True, help="结果输出JSONL路径")
    args = parser.parse_args()

    result_record = validate_fake_users(args.output)

    os.makedirs(os.path.dirname(args.result), exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result_record, ensure_ascii=False, default=str) + '\n')

if __name__ == "__main__":
    main()
