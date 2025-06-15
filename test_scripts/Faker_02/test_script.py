import csv
import argparse
import json
from datetime import datetime
import os


def validate_fake_companies(file_path, expected_num_companies=5, result_file=None):
    if not file_path.lower().endswith('.csv'):
        msg = f"Error: File {file_path} is not a CSV file."
        print(msg)
        if result_file:
            record_result(result_file, False, msg, process_success=False)
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
    except Exception as e:
        msg = f"Error: Unable to read file {file_path}, reason: {str(e)}"
        print(msg)
        if result_file:
            record_result(result_file, False, msg, process_success=False)
        return False

    if not rows:
        msg = "Error: CSV file is empty or contains no valid data rows."
        print(msg)
        if result_file:
            record_result(result_file, False, msg, process_success=True)
        return False

    if len(rows) != expected_num_companies:
        msg = f"Error: Expected {expected_num_companies} records, but got {len(rows)}."
        print(msg)
        if result_file:
            record_result(result_file, False, msg, process_success=True)
        return False

    required_fields = ['company name', 'address', 'phone']
    for idx, row in enumerate(rows, 1):
        normalized_row = {k.lower().strip(): v.strip() for k, v in row.items()}

        for field in required_fields:
            if field not in normalized_row:
                msg = f"Error: Row {idx} is missing field '{field}'."
                print(msg)
                if result_file:
                    record_result(result_file, False, msg, process_success=True)
                return False

            value = normalized_row[field]
            if not value:
                msg = f"Error: Row {idx} has empty value for field '{field}'."
                print(msg)
                if result_file:
                    record_result(result_file, False, msg, process_success=True)
                return False

            # Basic content checks
            if field == "phone" and not any(char.isdigit() for char in value):
                msg = f"Error: Row {idx} field 'Phone' should contain digits."
                print(msg)
                if result_file:
                    record_result(result_file, False, msg, process_success=True)
                return False
            if field == "company name" and value.isdigit():
                msg = f"Error: Row {idx} field 'Company Name' should not be all digits."
                print(msg)
                if result_file:
                    record_result(result_file, False, msg, process_success=True)
                return False
            if field == "address" and len(value) < 5:
                msg = f"Error: Row {idx} field 'Address' seems too short to be valid."
                print(msg)
                if result_file:
                    record_result(result_file, False, msg, process_success=True)
                return False

    success_msg = f"All {expected_num_companies} company records passed structural and content checks."
    print(success_msg)
    if result_file:
        record_result(result_file, True, success_msg, process_success=True)
    return True


def record_result(result_file, result, comments, process_success=True):
    # Get current timestamp
    time_point = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # Build result dictionary
    result_data = {
        "Process": process_success,
        "Result": result,
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