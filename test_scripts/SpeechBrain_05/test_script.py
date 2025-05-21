import json
import argparse
import os
import datetime


def evaluate_accuracy(output_file, gt_file, result_file):
    # Initialize result dictionary
    process_result = False
    result = False
    comments = ""

    # 1. Check if output file exists, is not empty, and has correct format
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, "r") as f:
                output_data = json.load(f)
            if 'prediction' not in output_data:
                comments += "Error: Output JSON file does not contain 'prediction' key.\n"
            else:
                process_result = True  # File check passed
        except Exception as e:
            comments += f"Error: Could not read output file - {str(e)}\n"
    else:
        comments += "Error: Output file does not exist or is empty.\n"

    # 2. Check if ground truth file exists, is not empty, and has correct format
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

    # 3. Compare predictions between output and ground truth
    if process_result:
        correct = output_data['prediction'] == gt_data['prediction']
        result = correct
        comments += f"Comparison result: {'Match' if correct else 'Mismatch'}\n"

    # 4. Get current timestamp
    time_point = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 5. Prepare output dictionary
    result_dict = {
        "Process": process_result,
        "Result": result,
        "TimePoint": time_point,
        "comments": comments
    }

    # 6. Write results to jsonl file
    with open(result_file, "a", encoding="utf-8") as result_f:
        result_f.write(json.dumps(result_dict, default=str) + "\n")

    # Print to terminal
    print(f"Process: {process_result}")
    print(f"Result: {result}")
    print(f"Comments: {comments}")


if __name__ == "__main__":
    # Parse command line arguments using argparse
    parser = argparse.ArgumentParser(description="Evaluate the accuracy of speaker recognition task.")
    parser.add_argument("--output", type=str, help="Path to the output.json file")
    parser.add_argument("--groundtruth", type=str, help="Path to the ground truth (gt.json) file")
    parser.add_argument("--result", type=str, default="evaluation_result.jsonl",
                        help="Path to store the evaluation results in JSONL format")

    # Parse command line arguments
    args = parser.parse_args()

    # Call evaluation function
    evaluate_accuracy(args.output, args.groundtruth, args.result)