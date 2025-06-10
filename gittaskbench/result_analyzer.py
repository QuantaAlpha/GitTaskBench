import os
import json
from pathlib import Path
import datetime
from typing import Optional, List, Tuple, Dict, Any, Union
from gittaskbench.utils import logger

def analyze_results(result_dir: Path, output_file: Optional[Path] = None):
    """
    Analyze result files in the specified directory and generate a report.

    Args:
        result_dir: Directory containing result files to analyze
        output_file: Optional file path to write the report to (default: None)
    """
    if not result_dir.exists():
        logger.error(f"Result directory not found: {result_dir}")
        return

    logger.info(f"Starting to analyze results in {result_dir}")

    # Step 1: Collect and parse results
    results_data = collect_results(result_dir)

    # Step 2: Generate statistics
    stats = calculate_statistics(results_data)

    # Step 3: Print statistics to console
    print_statistics(stats)

    # Step 4: Write report to file if specified
    if output_file:
        write_report(output_file, result_dir, stats)


def collect_results(result_dir: Path) -> Dict[str, Any]:
    """
    Collect and parse all result files in the given directory.

    Args:
        result_dir: Directory containing result files

    Returns:
        Dictionary containing parsed results and metadata
    """
    results_data = {
        "process_true": 0,
        "process_false": 0,
        "result_true": 0,
        "result_false": 0,
        "process_false_tasks": [],
        "result_false_tasks": [],
        "skipped_files": [],
        "ambiguous_files": []
    }

    for root, _, files in os.walk(result_dir):
        for file in files:
            if file == "results.jsonl":
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            last_line = lines[-1].strip()
                            data = json.loads(last_line)

                            # Process 'Process' status
                            process_status = parse_boolean_value(data.get("Process"))
                            if process_status is not None:
                                if process_status:
                                    results_data["process_true"] += 1
                                else:
                                    results_data["process_false"] += 1
                                    results_data["process_false_tasks"].append(Path(root).name)
                            else:
                                results_data["skipped_files"].append((str(file_path),
                                                                      f"Invalid Process value: {data.get('Process')}"))

                            # Process 'Result' or 'Results' status
                            result_status = parse_result_status(data)
                            if result_status is not None:
                                if result_status:
                                    results_data["result_true"] += 1
                                else:
                                    results_data["result_false"] += 1
                                    results_data["result_false_tasks"].append(Path(root).name)
                            else:
                                results_data["skipped_files"].append((str(file_path),
                                                                      f"Invalid Result value: {data.get('Result', data.get('Results'))}"))

                except json.JSONDecodeError:
                    results_data["skipped_files"].append((str(file_path), "JSON decode error"))
                    logger.warning(f"Failed to decode JSON from {file_path}")
                except Exception as e:
                    results_data["skipped_files"].append((str(file_path), str(e)))
                    logger.error(f"Error reading {file_path}: {e}")

    return results_data


def parse_boolean_value(value: Any) -> Optional[bool]:
    """
    Parse a value as a boolean, handling both boolean and string representations.

    Args:
        value: The value to parse

    Returns:
        Boolean value if valid, None otherwise
    """
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        lower_val = value.lower()
        if lower_val == "true":
            return True
        elif lower_val == "false":
            return False
    return None


def parse_result_status(data: Dict[str, Any]) -> Optional[bool]:
    """
    Parse the result status from the data, handling both 'Result' and 'Results' fields.

    Args:
        data: Dictionary containing result data

    Returns:
        Boolean result status if valid, None otherwise
    """
    # Check for both 'Result' and 'Results' fields (case-insensitive)
    result_fields = [k for k in data if k.lower() in ["result", "results"]]

    if not result_fields:
        return None  # No result field found

    if len(result_fields) > 1:
        # Both fields exist - log ambiguity and use first field
        logger.warning(f"Both Result and Results fields exist: {result_fields}")

    result_status = data.get(result_fields[0])
    return parse_boolean_value(result_status)


def calculate_statistics(results_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate additional statistics based on the collected results.

    Args:
        results_data: Dictionary containing parsed results

    Returns:
        Dictionary with calculated statistics
    """
    # Copy base results
    stats = results_data.copy()

    # Calculate success rates
    total_process = total_result = 54


    stats["process_success_rate"] = (stats["process_true"] / total_process * 100) if total_process > 0 else 0
    stats["result_success_rate"] = (stats["result_true"] / total_result * 100) if total_result > 0 else 0

    return stats


def print_statistics(stats: Dict[str, Any]) -> None:
    """
    Print statistics to the console.

    Args:
        stats: Dictionary containing calculated statistics
    """
    logger.info(f"Process - True: {stats['process_true']}, False: {stats['process_false']}")
    logger.info(f"Result - True: {stats['result_true']}, False: {stats['result_false']}")

    if stats["process_false_tasks"]:
        logger.info(f"Process False tasks: {', '.join(stats['process_false_tasks'])}")

    if stats["result_false_tasks"]:
        logger.info(f"Result False tasks: {', '.join(stats['result_false_tasks'])}")

    if stats["ambiguous_files"]:
        logger.warning("Ambiguous files with both Result and Results fields:")
        for file, reason in stats["ambiguous_files"]:
            logger.warning(f"  {file}: {reason}")

    if stats["skipped_files"]:
        logger.warning("Skipped files:")
        for file, reason in stats["skipped_files"]:
            logger.warning(f"  {file}: {reason}")


def write_report(output_file: Path, result_dir: Path, stats: Dict[str, Any]) -> None:
    """
    Write evaluation report to a text file.

    Args:
        output_file: Path to the output file
        result_dir: Directory containing analyzed results
        stats: Dictionary containing calculated statistics
    """
    try:
        # Create parent directories if they don't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"# GitTaskBench Evaluation Report\n")
            f.write(f"Generated on: {timestamp}\n")
            f.write(f"Results directory: {result_dir}\n\n")

            # Write summary statistics
            f.write(f"## Summary Statistics\n")
            f.write(f"Process - True: {stats['process_true']}, False: {stats['process_false']}\n")
            f.write(f"Result - True: {stats['result_true']}, False: {stats['result_false']}\n\n")

            # Write success rates
            f.write(f"## Success Rates\n")
            f.write(f"Process Success Rate: {stats['process_success_rate']:.2f}%\n")
            f.write(f"Result Success Rate: {stats['result_success_rate']:.2f}%\n\n")

            # Write details for failed tasks
            if stats["process_false_tasks"]:
                f.write(f"## Process Failed Tasks ({len(stats['process_false_tasks'])})\n")
                for task in stats["process_false_tasks"]:
                    f.write(f"- {task}\n")
                f.write("\n")

            if stats["result_false_tasks"]:
                f.write(f"## Result Failed Tasks ({len(stats['result_false_tasks'])})\n")
                for task in stats["result_false_tasks"]:
                    f.write(f"- {task}\n")
                f.write("\n")

            # Write ambiguous files
            if stats["ambiguous_files"]:
                f.write(f"## Ambiguous Files with Both Result and Results Fields ({len(stats['ambiguous_files'])})\n")
                for file, reason in stats["ambiguous_files"]:
                    f.write(f"- {file}: {reason}\n")
                f.write("\n")

            # Write skipped files
            if stats["skipped_files"]:
                f.write(f"## Skipped Files ({len(stats['skipped_files'])})\n")
                for file, reason in stats["skipped_files"]:
                    f.write(f"- {file}: {reason}\n")

        logger.info(f"Report successfully written to: {output_file}")
    except Exception as e:
        logger.error(f"Failed to write report to {output_file}: {e}")
