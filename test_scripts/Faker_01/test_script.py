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
        comments.append(f"[Error] File does not exist: {file_path}")
        process_ok = False
    elif os.path.getsize(file_path) == 0:
        comments.append(f"[Error] File is empty: {file_path}")
        process_ok = False

    if process_ok:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for idx, row in enumerate(reader):
                    email = row.get('Email', '')
                    if not re.match(email_pattern, email):
                        comments.append(f"[Row {idx+2}] Invalid email: {email}")
                        break
                else:
                    comments.append("All user data validated successfully!")
                    result_ok = True
        except Exception as e:
            comments.append(f"[Exception] File parsing error: {str(e)}")
            process_ok = False

    return {
        "Process": process_ok,
        "Result": result_ok,
        "TimePoint": datetime.now().isoformat(),
        "comments": " | ".join(comments)
    }

def main():
    parser = argparse.ArgumentParser(description="Validate generated fake user data")
    parser.add_argument('--output', type=str, required=True, help="CSV file path")
    parser.add_argument('--result', type=str, required=True, help="Result output JSONL path")
    args = parser.parse_args()

    result_record = validate_fake_users(args.output)

    os.makedirs(os.path.dirname(args.result), exist_ok=True)
    with open(args.result, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result_record, ensure_ascii=False, default=str) + '\n')

if __name__ == "__main__":
    main()