import argparse
import sys
import json
import os
from datetime import datetime

def compare_txt_files(extracted_txt_path, ground_truth_txt_path):
    """
    Compare extracted txt file with ground truth and return structured results
    """
    comments = []
    process_status = True
    final_result_status = False
    time_point = datetime.now().isoformat()

    # === Input file validation ===
    if not os.path.exists(extracted_txt_path) or os.path.getsize(extracted_txt_path) == 0:
        comments.append(f"❌ Error: Extracted TXT file '{extracted_txt_path}' missing or empty")
        process_status = False
    if not os.path.exists(ground_truth_txt_path) or os.path.getsize(ground_truth_txt_path) == 0:
        comments.append(f"❌ Error: GT file '{ground_truth_txt_path}' missing or empty")
        process_status = False

    if process_status:
        try:
            with open(extracted_txt_path, "r", encoding="utf-8") as f:
                extracted_message = f.read().strip()
            with open(ground_truth_txt_path, "r", encoding="utf-8") as f:
                ground_truth_message = f.read().strip()

            if extracted_message == ground_truth_message:
                comments.append(f"✅ Test passed: Extracted message matches ground truth (match = 100%)")
                final_result_status = True
            else:
                comments.append(f"❌ Test failed: Content mismatch!\nExtracted: {extracted_message}\nExpected: {ground_truth_message}")
                final_result_status = False
        except Exception as e:
            comments.append(f"❌ Exception: Error reading or comparing files: {e}")
            process_status = False

    return {
        "Process": process_status,
        "Result": final_result_status,
        "TimePoint": time_point,
        "comments": "\n".join(comments)
    }

def write_to_jsonl(file_path, data):
    """
    Write single result to JSONL file (append mode)
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
        print(f"✅ Results appended to JSONL file: {file_path}")
    except Exception as e:
        print(f"❌ Error writing to JSONL file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Test hidden watermark extraction results")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to extracted txt file")
    parser.add_argument("--output", type=str, required=True, help="Path to ground truth txt file")
    parser.add_argument("--result", type=str, required=False, help="Optional: Path to output JSONL results")

    args = parser.parse_args()

    result = compare_txt_files(args.groundtruth, args.output)

    # Print results
    print(result["comments"])

    # Write to result file
    if args.result:
        write_to_jsonl(args.result, result)

    # Output final status (replaces original exit logic)
    print("\nTest complete - Final status: " + ("PASSED" if result["Process"] and result["Result"] else "FAILED"))

if __name__ == "__main__":
    main()