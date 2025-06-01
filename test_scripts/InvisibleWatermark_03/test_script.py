import argparse
import os
import json
from datetime import datetime
import cv2

def evaluate_watermark(groundtruth_path, watermark_text, output_txt_path):
    process_status = True
    final_result_status = False
    comments = []

    time_point = datetime.now().isoformat()

    if not os.path.exists(groundtruth_path) or os.path.getsize(groundtruth_path) == 0:
        comments.append(f"Error: Original image file '{groundtruth_path}' does not exist or is empty.")
        process_status = False
    else:
        img = cv2.imread(groundtruth_path)
        if img is None:
            comments.append("Error: Failed to read original image. Check file integrity/format.")
            process_status = False

    if not os.path.exists(output_txt_path) or os.path.getsize(output_txt_path) == 0:
        comments.append(f"Error: Output text file '{output_txt_path}' does not exist or is empty.")
        process_status = False

    if process_status:
        try:
            with open(output_txt_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read().strip()

            is_match = (extracted_text == watermark_text)
            comments.append(f"{'✅' if is_match else '❌'} Extracted watermark: '{extracted_text}' | Expected: '{watermark_text}'")

            final_result_status = is_match
            comments.append(f"Final evaluation: Watermark match={is_match}")

        except Exception as e:
            comments.append(f"Exception during reading output file: {e}")
            final_result_status = False

    output_data = {
        "Process": process_status,
        "Result": final_result_status,
        "TimePoint": time_point,
        "Comments": "\n".join(comments)
    }

    return output_data

def write_to_jsonl(file_path, data):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
        print(f"✅ Results appended to JSONL file: {file_path}")
    except Exception as e:
        print(f"❌ Error writing to JSONL file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate blind watermark decoding result (text file) against expected watermark string")
    parser.add_argument("--groundtruth", required=True, help="Path to original image (PNG)")
    parser.add_argument("--output", required=True, help="Path to decoded watermark text file (txt)")
    parser.add_argument("--watermark", required=True, help="Expected watermark string")
    parser.add_argument("--result", help="Output path for JSONL results")

    args = parser.parse_args()

    evaluation_result = evaluate_watermark(args.groundtruth, args.watermark, args.output)

    if args.result:
        write_to_jsonl(args.result, evaluation_result)
