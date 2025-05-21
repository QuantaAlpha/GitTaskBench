import csv
import argparse
import json
from datetime import datetime
import os


def validate_fake_companies(file_path, expected_num_companies=5, result_file=None):
    # Read generated CSV file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
    except Exception as e:
        print(f"Error: Unable to read file {file_path}, reason: {str(e)}")
        if result_file:
            record_result(result_file, False, f"Unable to read file, reason: {str(e)}")
        return False

    # Validate row count matches expected number
    if len(rows) != expected_num_companies:
        error_message = f"Error: File should contain {expected_num_companies} company records, but actually contains {len(rows)} records."
        print(error_message)
        if result_file:
            record_result(result_file, False, error_message)
        return False

    # Validate each record contains required fields
    for row in rows:
        if not all(field in row for field in ['Company Name', 'Address', 'Phone']):
            error_message = "Error: A record is missing required fields (Company Name, Address, or Phone)"
            print(error_message)
            if result_file:
                record_result(result_file, False, error_message)
            return False

    success_message = f"All {expected_num_companies} company records validated successfully!"
    print(success_message)
    if result_file:
        record_result(result_file, True, success_message)
    return True


def record_result(result_file, result, comments):
    # Get current timestamp
    time_point = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # Build result dictionary
    result_data = {
        "Process": True,  # Can be set to True or adjusted as needed
        "Result": result,  # Boolean based on validation result
        "TimePoint": time_point,
        "comments": comments
    }

    # Write to jsonl file
    try:
        # Create file if it doesn't exist and append result
        with open(result_file, 'a', encoding='utf-8') as file:
            json.dump(result_data, file, ensure_ascii=False, default=str)
            file.write('\n')  # Write each result on new line
    except Exception as e:
        print(f"Error: Unable to write to result file {result_file}, reason: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate generated fake company data")
    parser.add_argument('--output', type=str, required=True, help="Path to generated CSV file")
    parser.add_argument('--result', type=str, required=False, help="Path to save results in jsonl format",
                        default="test_results.jsonl")
    args = parser.parse_args()

    # Execute validation
    validate_fake_companies(args.output, result_file=args.result)