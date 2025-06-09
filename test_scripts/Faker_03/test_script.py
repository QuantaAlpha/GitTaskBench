import argparse
import re
import json
from datetime import datetime
import os


def jaccard_similarity_tokens(str1, str2):
    # Token-based Jaccard similarity
    tokens1 = set(re.findall(r'\w+', str1.lower()))
    tokens2 = set(re.findall(r'\w+', str2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union


def validate_fake_text(input_file, output_file, result_file=None):
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            original_content = file.read()
    except Exception as e:
        msg = f"Error: Unable to read original text file {input_file}, reason: {str(e)}"
        print(msg)
        if result_file:
            record_result(result_file, False, msg)
        return False

    try:
        with open(output_file, 'r', encoding='utf-8') as file:
            fake_content = file.read()
    except Exception as e:
        msg = f"Error: Unable to read fake text file {output_file}, reason: {str(e)}"
        print(msg)
        if result_file:
            record_result(result_file, False, msg)
        return False

    # Early checks
    if original_content.strip() == fake_content.strip():
        msg = "Error: Output text is identical to input text. No replacement performed."
        print(msg)
        if result_file:
            record_result(result_file, False, msg)
        return False

    if len(fake_content.strip()) < 20:
        msg = "Error: Output fake text is too short to be valid replacement."
        print(msg)
        if result_file:
            record_result(result_file, False, msg)
        return False

    # Token-based similarity
    similarity = jaccard_similarity_tokens(original_content, fake_content)
    print(f"Token-based Jaccard similarity: {similarity:.4f}")

    threshold = 0.3  # Token-level threshold

    if similarity < threshold:
        result_message = f"✅ Fake text replacement successful. Similarity {similarity:.4f} below threshold."
        print(result_message)
        if result_file:
            record_result(result_file, True, result_message)
        return True
    else:
        result_message = f"❌ Fake text too similar to original. Similarity {similarity:.4f} above threshold."
        print(result_message)
        if result_file:
            record_result(result_file, False, result_message)
        return False



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