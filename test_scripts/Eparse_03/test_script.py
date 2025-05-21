import argparse
import json
import os
import datetime
import re
from collections import defaultdict


def normalize_value(value):
    """Standardize values to handle consistency between numbers and strings"""
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def extract_cell_data(json_data):
    """Extract cell data from different JSON structures, returning standardized cell collections"""
    cells = []

    # Handle GT format
    if isinstance(json_data, dict) and "sheets" in json_data:
        for sheet_name, sheet_data in json_data["sheets"].items():
            for row in sheet_data.get("rows", []):
                row_index = row.get("row_index", 0)
                for cell in row.get("cells", []):
                    cells.append({
                        "row": row_index,
                        "column": cell.get("column_index"),
                        "value": normalize_value(cell.get("value")),
                        "excel_RC": cell.get("excel_RC"),
                        "c_header": cell.get("c_header"),
                        "r_header": cell.get("r_header"),
                        "type": cell.get("type")
                    })

    # Handle Agent output format
    elif isinstance(json_data, list):
        for table in json_data:
            for cell in table.get("data", []):
                cells.append({
                    "row": cell.get("row"),
                    "column": cell.get("column"),
                    "value": normalize_value(cell.get("value")),
                    "excel_RC": cell.get("excel_RC"),
                    "c_header": cell.get("c_header"),
                    "r_header": cell.get("r_header"),
                    "type": cell.get("type")
                })

    # Handle other possible formats
    else:
        try:
            # Attempt recursive search for all cell-like data structures
            def find_cells(obj, path=""):
                if isinstance(obj, dict):
                    # Check if it's a cell structure
                    if all(k in obj for k in ["row", "column", "value"]) or \
                            all(k in obj for k in ["row_index", "column_index", "value"]):
                        row = obj.get("row", obj.get("row_index", 0))
                        column = obj.get("column", obj.get("column_index", 0))
                        cells.append({
                            "row": row,
                            "column": column,
                            "value": normalize_value(obj.get("value")),
                            "excel_RC": obj.get("excel_RC", f"{chr(65 + column)}{row + 1}"),
                            "c_header": obj.get("c_header", str(column + 1)),
                            "r_header": obj.get("r_header", str(row + 1)),
                            "type": obj.get("type", "")
                        })
                    else:
                        for k, v in obj.items():
                            find_cells(v, f"{path}.{k}" if path else k)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_cells(item, f"{path}[{i}]")

            find_cells(json_data)
        except Exception as e:
            print(f"Failed to parse JSON structure: {str(e)}")

    return cells


def compute_cell_similarity(cells1, cells2):
    """Calculate similarity between two cell collections"""
    if not cells1 and not cells2:
        return 1.0  # Both empty, consider perfect match

    if not cells1 or not cells2:
        return 0.0  # One empty, the other not

    # Create position-to-cell mappings
    cells1_dict = {(cell["row"], cell["column"]): cell for cell in cells1}
    cells2_dict = {(cell["row"], cell["column"]): cell for cell in cells2}

    # Get all unique cell positions
    all_positions = set(cells1_dict.keys()) | set(cells2_dict.keys())

    # Calculate matched cell count
    matches = 0
    total_weight = 0

    for pos in all_positions:
        weight = 1  # Cell weight
        total_weight += weight

        if pos in cells1_dict and pos in cells2_dict:
            cell1 = cells1_dict[pos]
            cell2 = cells2_dict[pos]

            # Compare values
            if normalize_value(cell1["value"]) == normalize_value(cell2["value"]):
                matches += 0.6 * weight  # Value match contributes 60% weight

            # Compare other metadata (10% weight each)
            for key in ["excel_RC", "c_header", "r_header", "type"]:
                if key in cell1 and key in cell2 and normalize_value(cell1[key]) == normalize_value(cell2[key]):
                    matches += 0.1 * weight

    similarity = matches / total_weight if total_weight > 0 else 0
    return similarity


def is_valid_file(file_path):
    """Check if file exists and is not empty"""
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0


def evaluate(pred_file, gt_file):
    """Read files and calculate similarity"""
    try:
        with open(pred_file, 'r', encoding='utf-8') as f_pred:
            pred_text = f_pred.read()
        with open(gt_file, 'r', encoding='utf-8') as f_gt:
            gt_text = f_gt.read()
    except Exception as e:
        return None, f"❌ File read error: {str(e)}"

    try:
        # Parse JSON
        pred_json = json.loads(pred_text)
        gt_json = json.loads(gt_text)

        # Extract cell data
        pred_cells = extract_cell_data(pred_json)
        gt_cells = extract_cell_data(gt_json)

        # Calculate cell content similarity
        similarity = compute_cell_similarity(pred_cells, gt_cells)

        return similarity, f"✅ Similarity calculation complete: {similarity:.4f} ({len(gt_cells)} GT cells, {len(pred_cells)} predicted cells)"
    except json.JSONDecodeError:
        # Fallback to Levenshtein similarity if JSON parsing fails
        try:
            import Levenshtein
            levenshtein_distance = Levenshtein.distance(pred_text, gt_text)
            similarity = 1 - levenshtein_distance / max(len(pred_text), len(gt_text))
            return similarity, f"⚠️ JSON parsing failed, using Levenshtein similarity: {similarity:.4f}"
        except ImportError:
            return 0.0, "❌ JSON parsing failed and Levenshtein library unavailable"
    except Exception as e:
        return 0.0, f"❌ Evaluation process error: {str(e)}"


def save_result(result_path, data):
    """Save results to jsonl file"""
    os.makedirs(os.path.dirname(result_path) or '.', exist_ok=True)
    with open(result_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare similarity between predicted and ground truth Excel JSON data.")
    parser.add_argument('--output', required=True, help="Path to predicted JSON file.")
    parser.add_argument('--groundtruth', required=True, help="Path to ground truth JSON file.")
    parser.add_argument('--result', required=True, help="Path to save evaluation results (.jsonl).")
    args = parser.parse_args()

    result_dict = {
        "Process": False,
        "Result": False,
        "TimePoint": datetime.datetime.now().isoformat(),
        "comments": ""
    }

    # Step 1: Check if files exist and are not empty
    if not is_valid_file(args.output):
        result_dict["comments"] = "❌ Prediction file does not exist or is empty"
        save_result(args.result, result_dict)
        print(result_dict["comments"])
        return

    if not is_valid_file(args.groundtruth):
        result_dict["comments"] = "❌ GT file does not exist or is empty"
        save_result(args.result, result_dict)
        print(result_dict["comments"])
        return

    result_dict["Process"] = True

    # Step 2: Evaluate similarity
    similarity, msg = evaluate(args.output, args.groundtruth)
    if similarity is None:
        result_dict["comments"] = msg
        save_result(args.result, result_dict)
        print(msg)
        return

    result_dict["comments"] = msg
    result_dict["Result"] = similarity >= 0.8
    save_result(args.result, result_dict)

    print(msg)
    if result_dict["Result"]:
        print("✅ Passed: Similarity ≥ 0.8")
    else:
        print("❌ Failed: Similarity < 0.8")


if __name__ == "__main__":
    main()