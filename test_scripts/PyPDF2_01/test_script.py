import argparse
import json
import os
from datetime import datetime

def load_txt(file_path):
    """Read text file, return False if file doesn't exist or can't be read"""
    if not os.path.isfile(file_path):
        print(f"❌ Error: File does not exist or cannot be accessed: {file_path}")
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error: Exception occurred while opening file: {str(e)}")
        return False

def evaluate(pred_file, truth_file, result_file):
    """Compare accuracy between predicted text and standard text"""
    # Check if files can be opened successfully
    pred_text = load_txt(pred_file)
    truth_text = load_txt(truth_file)

    if not pred_text or not truth_text:
        process_status = False
        result_status = False
        comments = f"Cannot read file {pred_file if not pred_text else truth_file}"
        write_result(result_file, process_status, result_status, comments)
        return

    # Remove spaces and newlines for comparison
    pred_text = pred_text.replace("\n", "").replace(" ", "")
    truth_text = truth_text.replace("\n", "").replace(" ", "")

    total = len(truth_text)
    if total == 0:
        print("⚠️ Standard answer file has no text content!")
        process_status = False
        result_status = False
        comments = "Standard answer file is empty"
        write_result(result_file, process_status, result_status, comments)
        return

    correct = 0
    for i in range(min(len(pred_text), len(truth_text))):
        if pred_text[i] == truth_text[i]:
            correct += 1

    accuracy = (correct / total) * 100
    print(f"Extracted text accuracy: {accuracy:.2f}%")

    if accuracy >= 95:
        print("✅ Test passed!")
        process_status = True
        result_status = True
        comments = f"Extracted text accuracy {accuracy:.2f}%, meets requirements."
    else:
        print("❌ Test failed!")
        process_status = True
        result_status = False
        comments = f"Extracted text accuracy {accuracy:.2f}%, does not meet requirements."

    write_result(result_file, process_status, result_status, comments)

def write_result(result_file, process_status, result_status, comments):
    """Write test results to JSONL file"""
    result_data = {
        "Process": process_status,
        "Result": result_status,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": comments
    }

    # If file exists, append to it; if not, create new file
    with open(result_file, 'a', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False)
        f.write("\n")  # Add newline after each record

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="Path to extracted text file")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to standard text file")
    parser.add_argument("--result", type=str, required=True, help="Path to JSONL file for saving results")
    args = parser.parse_args()

    evaluate(args.output, args.groundtruth, args.result)