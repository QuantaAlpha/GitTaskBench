import argparse
import re
import json
from datetime import datetime
import os


def jaccard_similarity(str1, str2):
    # Calculate Jaccard similarity between two strings
    set1 = set(str1)
    set2 = set(str2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union


def validate_fake_text(input_file, output_file, result_file=None):
    # Read original file and generated fake text file contents
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            original_content = file.read()
    except Exception as e:
        print(f"Error: Unable to read original text file {input_file}, reason: {str(e)}")
        if result_file:
            record_result(result_file, False, f"Unable to read original text file, reason: {str(e)}")
        return False

    try:
        with open(output_file, 'r', encoding='utf-8') as file:
            fake_content = file.read()
    except Exception as e:
        print(f"Error: Unable to read fake text file {output_file}, reason: {str(e)}")
        if result_file:
            record_result(result_file, False, f"Unable to read fake text file, reason: {str(e)}")
        return False

    # Calculate Jaccard similarity between original and fake text
    similarity = jaccard_similarity(original_content, fake_content)
    print(f"Jaccard similarity between original and fake text: {similarity:.4f}")

    # Set a similarity threshold to determine test pass/fail
    threshold = 0.2  # Threshold can be adjusted as needed, 0.2 means fake text can differ up to 80%

    if similarity < threshold:
        result_message = f"❌ Fake text replacement effective, similarity: {similarity:.4f} below threshold!"
        print(result_message)
        if result_file:
            record_result(result_file, False, result_message)
        return False
    else:
        result_message = f"✅ Fake text validation passed, similarity: {similarity:.4f} above threshold!"
        print(result_message)
        if result_file:
            record_result(result_file, True, result_message)
        return True


def record_result(result_file, result, comments):
    # Get current timestamp
    time_point = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # Build result dictionary
    result_data = {
        "Process": True,
        "Result": result,
        "TimePoint": time_point,
        "comments": comments
    }

    # Write to jsonl file
    try:
        # Create file if it doesn't exist and write
        file_exists = os.path.exists(result_file)
        with open(result_file, 'a', encoding='utf-8') as file:
            if not file_exists:
                # Write empty json line if file doesn't exist (optional)
                file.write('\n')
            json.dump(result_data, file, ensure_ascii=False, default=str)
            file.write('\n')
    except Exception as e:
        print(f"Error: Unable to write to result file {result_file}, reason: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate effectiveness of fake text replacement")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to original text file")
    parser.add_argument("--output", type=str, required=True, help="Path to generated fake text file")
    parser.add_argument("--result", type=str, required=False, help="Path to save results in jsonl format",
                        default="test_results.jsonl")

    args = parser.parse_args()

    # Call test function
    validate_fake_text(args.groundtruth, args.output, result_file=args.result)