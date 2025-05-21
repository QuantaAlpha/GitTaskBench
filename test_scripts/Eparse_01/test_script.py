import argparse
import csv
import json
import os
import re
from datetime import datetime
from collections import defaultdict


def load_txt_file(file_path):
    """Load TXT file content"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None
    except Exception as e:
        return "", str(e)


def extract_file_blocks(content):
    """Extract filename and corresponding table data blocks from TXT content"""
    file_blocks = {}
    current_file = None
    current_block = []

    # Attempt to split content using filename markers
    lines = content.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect filename line - supports multiple possible formats
        file_name_match = None
        if line.startswith("文件名:") or line.startswith("File name:"):
            file_name_match = re.search(r'(?:文件名|File name):?\s*(.+?)(?:\s|$)', line)
        elif "文件名" in line:
            file_name_match = re.search(r'.*文件名:?\s*(.+?)(?:\s|$)', line)
        elif re.match(r'^[^:]*\.xlsx?\s*$', line):  # Case of direct filename.xls(x)
            file_name_match = re.match(r'^([^:]*\.xlsx?)$', line)

        if file_name_match:
            # If we have a current file, save its data block
            if current_file and current_block:
                file_blocks[current_file] = '\n'.join(current_block)

            # Extract new filename
            current_file = file_name_match.group(1).strip()
            current_block = []
        elif current_file is not None:
            # Add to current block
            current_block.append(line)

        i += 1

    # Process last file block
    if current_file and current_block:
        file_blocks[current_file] = '\n'.join(current_block)

    return file_blocks


def parse_table_content(block_content):
    """Parse table block content to extract data structure"""
    sheets_data = []
    current_sheet = []

    lines = block_content.split('\n')
    i = 0
    in_sheet = False

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Detect Sheet marker
        sheet_match = re.search(r'Sheet:?', line)
        if sheet_match:
            # If new Sheet found, save previous sheet data
            if in_sheet and current_sheet:
                sheets_data.append(current_sheet)
                current_sheet = []

            in_sheet = True
            i += 1
            continue

        # Process data rows
        if in_sheet or not sheets_data:  # Also try parsing if no explicit Sheet markers
            # Clean line numbers
            cleaned_line = re.sub(r'^\d+\s+', '', line)

            # Split cell data
            # First try tab or multiple spaces
            cells = re.split(r'\s{2,}|\t', cleaned_line)

            # If only one element after split, try single space
            if len(cells) <= 1:
                cells = re.split(r'\s+', cleaned_line)

            if cells:
                current_sheet.append(cells)

        i += 1

    # Save last sheet
    if current_sheet:
        sheets_data.append(current_sheet)

    # If no explicit sheet separation but has data, treat as single sheet
    if not sheets_data and lines:
        # Re-parse as single sheet
        current_sheet = []
        for line in lines:
            if line.strip():
                # Clean line numbers
                cleaned_line = re.sub(r'^\d+\s+', '', line)
                # Split cells
                cells = re.split(r'\s{2,}|\t', cleaned_line)
                if len(cells) <= 1:
                    cells = re.split(r'\s+', cleaned_line)
                if cells:
                    current_sheet.append(cells)

        if current_sheet:
            sheets_data.append(current_sheet)

    return sheets_data


def normalize_value(value):
    """Normalize cell value, handling various format differences"""
    # Convert to string and strip whitespace
    value_str = str(value).strip()

    # Standardize date formats
    date_match = re.match(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})(?:\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)?', value_str)
    if date_match:
        # Extract date part
        date_part = date_match.group(1)
        # Unify separator to -
        date_part = date_part.replace('/', '-')
        # Ensure yyyy-mm-dd format
        date_parts = date_part.split('-')
        if len(date_parts) == 3:
            year = date_parts[0]
            month = date_parts[1].zfill(2)
            day = date_parts[2].zfill(2)
            value_str = f"{year}-{month}-{day}"

    # Standardize number formats
    number_match = re.match(r'^[-+]?\d+(?:\.\d+)?$', value_str)
    if number_match:
        try:
            # Try converting to float, then remove trailing zeros
            num_value = float(value_str)
            # If integer, remove decimal point
            if num_value.is_integer():
                value_str = str(int(num_value))
            else:
                value_str = str(num_value).rstrip('0').rstrip('.')
        except:
            pass

    return value_str


def calculate_sheet_similarity(pred_sheet, truth_sheet):
    """Calculate content similarity between two sheets"""
    # Normalize all cell values
    pred_values = set()
    truth_values = set()

    # Process prediction data
    for row in pred_sheet:
        for cell in row:
            normalized = normalize_value(cell)
            if normalized:  # Ignore empty cells
                pred_values.add(normalized)

    # Process ground truth data
    for row in truth_sheet:
        for cell in row:
            normalized = normalize_value(cell)
            if normalized:  # Ignore empty cells
                truth_values.add(normalized)

    # Calculate intersection and union
    intersection = pred_values.intersection(truth_values)
    union = pred_values.union(truth_values)

    # Jaccard similarity
    if not union:
        return 0.0

    similarity = len(intersection) / len(union) * 100
    return similarity


def evaluate_file_similarity(pred_sheets, truth_sheets):
    """Evaluate file similarity"""
    if not pred_sheets or not truth_sheets:
        return 0.0

    # Calculate similarity for each sheet
    total_similarity = 0.0
    sheet_count = min(len(pred_sheets), len(truth_sheets))

    for i in range(sheet_count):
        sheet_similarity = calculate_sheet_similarity(
            pred_sheets[i],
            truth_sheets[i]
        )
        total_similarity += sheet_similarity

    # Average similarity
    avg_similarity = total_similarity / sheet_count if sheet_count > 0 else 0.0

    # Reduce similarity if sheet counts differ
    sheet_diff_penalty = abs(len(pred_sheets) - len(truth_sheets)) * 5  # 5% reduction per extra/missing sheet
    final_similarity = max(0, avg_similarity - sheet_diff_penalty)

    return final_similarity


def evaluate(pred_file, truth_file):
    """Evaluation function"""
    pred_content, pred_err = load_txt_file(pred_file)
    truth_content, truth_err = load_txt_file(truth_file)

    process_ok = True
    comments = []

    # Read error checking
    if pred_err:
        comments.append(f"[Prediction file read error] {pred_err}")
        process_ok = False
    if truth_err:
        comments.append(f"[GT file read error] {truth_err}")
        process_ok = False
    if not process_ok:
        return {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # Extract file blocks
    pred_file_blocks = extract_file_blocks(pred_content)
    truth_file_blocks = extract_file_blocks(truth_content)

    # Filename comparison
    pred_files = set(pred_file_blocks.keys())
    truth_files = set(truth_file_blocks.keys())

    comments.append(f"Prediction file contains {len(pred_files)} Excel data blocks")
    comments.append(f"GT file contains {len(truth_files)} Excel data blocks")

    if len(pred_files) == 0:
        comments.append("⚠️ No Excel data blocks found in prediction file!")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    if len(truth_files) == 0:
        comments.append("⚠️ No Excel data blocks found in GT file!")
        return {
            "Process": True,
            "Result": False,
            "TimePoint": datetime.now().isoformat(),
            "comments": "\n".join(comments)
        }

    # Calculate file matching
    common_files = pred_files.intersection(truth_files)
    missing_files = truth_files - pred_files
    extra_files = pred_files - truth_files

    # Filename match rate
    file_match_rate = len(common_files) / len(truth_files) * 100 if truth_files else 0
    comments.append(f"Filename match rate: {file_match_rate:.2f}%")

    if missing_files:
        comments.append(f"Missing files: {', '.join(missing_files)}")
    if extra_files:
        comments.append(f"Extra files: {', '.join(extra_files)}")

    # Content similarity scoring
    total_similarity = 0.0
    file_count = 0

    # Process exactly matched filenames
    for file_name in common_files:
        pred_content_block = pred_file_blocks[file_name]
        truth_content_block = truth_file_blocks[file_name]

        # Parse table content
        pred_sheets = parse_table_content(pred_content_block)
        truth_sheets = parse_table_content(truth_content_block)

        # Calculate file similarity
        file_similarity = evaluate_file_similarity(pred_sheets, truth_sheets)

        comments.append(f"File '{file_name}' content similarity: {file_similarity:.2f}%")
        total_similarity += file_similarity
        file_count += 1

    # Attempt to match files with slightly different names by content
    if missing_files and extra_files:
        for missing_file in list(missing_files):
            best_match = None
            best_similarity = 0

            truth_content_block = truth_file_blocks[missing_file]
            truth_sheets = parse_table_content(truth_content_block)

            for extra_file in list(extra_files):
                pred_content_block = pred_file_blocks[extra_file]
                pred_sheets = parse_table_content(pred_content_block)

                similarity = evaluate_file_similarity(pred_sheets, truth_sheets)
                if similarity > best_similarity and similarity > 60:  # Require at least 60% similarity
                    best_similarity = similarity
                    best_match = extra_file

            if best_match:
                comments.append(
                    f"Different filenames but similar content: '{missing_file}' and '{best_match}', similarity: {best_similarity:.2f}%")
                total_similarity += best_similarity
                file_count += 1
                missing_files.remove(missing_file)
                extra_files.remove(best_match)

    # Calculate average file similarity
    avg_similarity = total_similarity / len(truth_files) if truth_files else 0

    # Penalize for missing files
    if missing_files:
        missing_penalty = len(missing_files) / len(truth_files) * 100
        comments.append(f"Score reduction for missing files: -{missing_penalty:.2f}%")
        avg_similarity = max(0, avg_similarity - missing_penalty)

    comments.append(f"Average content similarity across all files: {avg_similarity:.2f}%")

    # File match and content similarity weights
    file_match_weight = 0.3
    content_similarity_weight = 0.7

    # Final score
    final_score = (file_match_rate * file_match_weight + avg_similarity * content_similarity_weight)
    passed = final_score >= 75

    comments.append(
        f"Final score (filename match {file_match_weight * 100}% + content similarity {content_similarity_weight * 100}%): {final_score:.2f}% (threshold=75%)")

    if passed:
        comments.append("✅ Test passed!")
    else:
        comments.append("❌ Test failed!")

    # If structured parsing fails, try basic content comparison
    if file_count == 0:
        comments.append("Note: No matches found in structured parsing, attempting basic content comparison")

        # Calculate word overlap in full content
        pred_words = set(re.findall(r'\b\w+\b', pred_content.lower()))
        truth_words = set(re.findall(r'\b\w+\b', truth_content.lower()))

        common_words = pred_words.intersection(truth_words)
        all_words = pred_words.union(truth_words)

        if all_words:
            word_overlap = len(common_words) / len(all_words) * 100
            comments.append(f"Content word overlap: {word_overlap:.2f}%")

            # Pass if high word overlap
            if word_overlap >= 75:
                comments.append("Based on word overlap: ✅ Test passed!")
                return {
                    "Process": True,
                    "Result": True,
                    "TimePoint": datetime.now().isoformat(),
                    "comments": "\n".join(comments)
                }

    return {
        "Process": True,
        "Result": passed,
        "TimePoint": datetime.now().isoformat(),
        "comments": "\n".join(comments)
    }


def append_result_to_jsonl(result_path, result_dict):
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, default=str)
        f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, required=True, help="Path to extracted tables")
    parser.add_argument("--groundtruth", type=str, required=True, help="Path to standard tables")
    parser.add_argument("--result", type=str, required=True, help="Output JSONL file path for results")
    args = parser.parse_args()

    result_dict = evaluate(args.output, args.groundtruth)
    append_result_to_jsonl(args.result, result_dict)
    print("[Evaluation complete] Result summary:")
    print(json.dumps(result_dict, ensure_ascii=False, indent=2, default=str))