import argparse
import json
import os
import re
from datetime import datetime
from ast import literal_eval
import traceback


def normalize_json_item(item):
    """
    Normalize JSON objects to remove format differences
    """
    if isinstance(item, str):
        # Try parsing string as dictionary
        try:
            item = json.loads(item)
        except:
            try:
                # Try parsing non-standard JSON with ast.literal_eval
                item = literal_eval(item)
            except:
                # Return original string if parsing fails
                return item

    # Ensure all keys are strings
    result = {}
    for k, v in item.items():
        # Convert key to string and strip whitespace
        key = str(k).strip().lower()
        # Process value
        if isinstance(v, str):
            # Strip whitespace and lowercase string values (except for type field)
            if key == 'type':
                value = v.strip()  # Preserve case for type field
            else:
                value = v.strip().lower()
        else:
            value = v
        result[key] = value

    return result


def parse_gt_format(content):
    """
    Special parser for gt.txt format
    Features multi-line dictionaries separated by commas
    """
    items = []
    # Replace all newlines to make content single line
    content = content.replace('\n', ' ')

    # Try parsing as list
    try:
        # If content is wrapped in brackets, remove them
        if content.strip().startswith('[') and content.strip().endswith(']'):
            content = content.strip()[1:-1]

        # Split multiple dictionaries (each starts with { and ends with }, or })
        dict_pattern = r'\{[^{}]*\}'
        dict_matches = re.findall(dict_pattern, content)

        for dict_str in dict_matches:
            try:
                item = literal_eval(dict_str)
                items.append(normalize_json_item(item))
            except Exception as e:
                print(f"Failed to parse dictionary: {dict_str[:50]}... Error: {e}")
    except Exception as e:
        print(f"Failed to parse gt format: {e}")

    print(f"Parsed {len(items)} items from gt format")
    return items


def parse_json_line_format(content):
    """
    Parse format with one JSON object per line
    """
    items = []
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            # Try parsing as JSON object
            item = json.loads(line)
            items.append(normalize_json_item(item))
        except:
            try:
                # Try parsing non-standard JSON with ast.literal_eval
                item = literal_eval(line)
                items.append(normalize_json_item(item))
            except Exception as e:
                print(f"Unable to parse line: {line[:50]}... Error: {e}")

    print(f"Parsed {len(items)} items from JSON line format")
    return items


def load_json_items(file_path):
    """
    Read file containing JSON objects, return normalized list
    Supports multiple formats: JSON per line, single JSON array, list of dicts, multi-line dict format
    """
    print(f"Parsing file: {file_path}")
    items = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

            # Check if file is empty
            if not content:
                print("File is empty")
                return items

            # 1. First try gt.txt specific format
            if "{'c_header':" in content or '{"c_header":' in content or "'c_header':" in content:
                print("Detected gt.txt format, using specialized parser")
                items = parse_gt_format(content)
                if items:
                    return items

            # 2. Try parsing as JSON array
            if content.startswith('[') and content.endswith(']'):
                try:
                    array_items = json.loads(content)
                    for item in array_items:
                        items.append(normalize_json_item(item))
                    print(f"Parsed {len(items)} items from JSON array")
                    return items
                except Exception as e:
                    print(f"JSON array parsing failed: {e}")

                    # Try Python list literal
                    try:
                        array_items = literal_eval(content)
                        for item in array_items:
                            items.append(normalize_json_item(item))
                        print(f"Parsed {len(items)} items from Python list")
                        return items
                    except Exception as e:
                        print(f"Python list parsing failed: {e}")

            # 3. Try parsing JSON objects line by line
            items = parse_json_line_format(content)
            if items:
                return items

            # 4. Finally try extracting all possible dictionaries
            print("Attempting to extract all possible dictionaries...")
            dict_pattern = r'\{[^{}]*\}'
            dicts = re.findall(dict_pattern, content)
            for d in dicts:
                try:
                    item = literal_eval(d)
                    items.append(normalize_json_item(item))
                except Exception as e:
                    print(f"Dictionary extraction failed: {d[:30]}... Error: {e}")

            if items:
                print(f"Parsed {len(items)} items from dictionary extraction")
                return items

    except Exception as e:
        print(f"Error reading file: {e}")
        traceback.print_exc()

    return items


def compare_items(pred_items, gt_items):
    """
    Compare predicted items with ground truth items, calculate match rate for key fields
    """
    if not pred_items or not gt_items:
        return 0, "No valid items to compare"

    print(f"Comparing {len(pred_items)} predicted items with {len(gt_items)} ground truth items")

    # List of key fields we consider more important
    key_fields = ['value', 'row', 'column', 'excel_rc', 'c_header', 'r_header', 'sheet', 'f_name']

    total_matches = 0
    total_fields = 0
    missing_items = 0

    # Number of items to match (based on smaller set)
    expected_matches = min(len(pred_items), len(gt_items))

    # If predicted items are fewer than ground truth, record missing count
    if len(pred_items) < len(gt_items):
        missing_items = len(gt_items) - len(pred_items)

    # Print sample data for debugging
    print("Predicted items sample:")
    for i, item in enumerate(pred_items[:2]):
        print(f"  Item {i}: {item}")

    print("Ground truth items sample:")
    for i, item in enumerate(gt_items[:2]):
        print(f"  Item {i}: {item}")

    # Compare item by item
    for i in range(min(len(pred_items), len(gt_items))):
        pred_item = pred_items[i]
        gt_item = gt_items[i]

        item_matches = 0
        item_fields = 0

        # Compare key fields
        for field in key_fields:
            # For predicted item, try to match different case variations
            pred_fields = [f.lower() for f in pred_item.keys()]
            pred_field_key = None

            # Find matching field (case insensitive)
            if field in pred_item:
                pred_field_key = field
            else:
                for k in pred_item.keys():
                    if k.lower() == field.lower():
                        pred_field_key = k
                        break

            # For ground truth item, also try to match different case variations
            gt_field_key = None
            if field in gt_item:
                gt_field_key = field
            else:
                for k in gt_item.keys():
                    if k.lower() == field.lower():
                        gt_field_key = k
                        break

            # If both have the field, compare
            if pred_field_key is not None and gt_field_key is not None:
                item_fields += 1
                pred_value = pred_item[pred_field_key]
                gt_value = gt_item[gt_field_key]

                # Case insensitive comparison for excel_rc field
                if field.lower() == 'excel_rc':
                    if str(pred_value).upper() == str(gt_value).upper():
                        item_matches += 1
                # Numeric comparison for numeric fields
                elif field.lower() in ['row', 'column'] and isinstance(pred_value, (int, float)) and isinstance(
                        gt_value, (int, float)):
                    if pred_value == gt_value:
                        item_matches += 1
                # Special handling for type field
                elif field.lower() == 'type':
                    # Extract type name, ignoring quotes and class parts
                    pred_type = re.sub(r"[<>'\"]|class\s+", "", str(pred_value)).strip()
                    gt_type = re.sub(r"[<>'\"]|class\s+", "", str(gt_value)).strip()
                    if pred_type == gt_type:
                        item_matches += 1
                # Standardized comparison for other fields
                elif str(pred_value).lower() == str(gt_value).lower():
                    item_matches += 1

        # Add to total matches
        if item_fields > 0:
            total_matches += item_matches
            total_fields += item_fields

    # Calculate match rate
    if total_fields == 0:
        accuracy = 0
        details = "No valid fields found for comparison"
    else:
        accuracy = total_matches / total_fields
        details = f"Matched fields: {total_matches}/{total_fields}"

        # Apply penalty if missing items
        if missing_items > 0:
            penalty = min(0.2, missing_items / len(gt_items) * 0.5)  # Max 20% penalty
            accuracy = max(0, accuracy - penalty)
            details += f", Missing items: {missing_items}, applied {penalty:.2f} penalty"

    return accuracy, details


def evaluate(pred_path, gt_path):
    """Evaluate based on parsed content"""
    threshold = 0.70  # Fixed threshold

    # Load and normalize data
    pred_items = load_json_items(pred_path)
    gt_items = load_json_items(gt_path)

    # Initialize result dictionary
    result = {
        "Process": True,
        "Result": False,
        "TimePoint": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "comments": ""
    }

    # Check if input files are valid
    if not pred_items:
        result["Process"] = False
        result["comments"] = "Predicted file parsed as empty, cannot evaluate!"
        return result

    if not gt_items:
        result["Process"] = False
        result["comments"] = "❌ Ground truth parsed as empty!"
        result["Result"] = False
        return result

    # Compare items and calculate match rate
    accuracy, details = compare_items(pred_items, gt_items)

    # Determine result based on accuracy
    if accuracy >= threshold:
        result["Result"] = True
        result["comments"] = f"✅ Test passed! Content match rate={accuracy:.4f} ≥ {threshold}. {details}"
    else:
        result["Result"] = False
        result["comments"] = f"❌ Test failed. Content match rate={accuracy:.4f} < {threshold}. {details}"

    print(result["comments"])
    return result


def save_result(result, result_file):
    """Save results to jsonl file"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(result_file) or '.', exist_ok=True)

    # Write in append mode, ensuring each record is on separate line
    with open(result_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Excel cell parsing output by content similarity and save results")
    parser.add_argument("--output", required=True, help="Predicted output file path")
    parser.add_argument("--groundtruth", required=True, help="Ground truth file path")
    parser.add_argument("--result", required=True, help="Result output file path (JSONL format)")
    args = parser.parse_args()

    # Get evaluation result
    result = evaluate(args.output, args.groundtruth)

    # Save result to specified jsonl file
    save_result(result, args.result)
    print(f"Results saved to {args.result}")


if __name__ == "__main__":
    main()