import os
import json
import logging
from pathlib import Path
from gittaskbench.utils import logger

def analyze_results(result_dir: Path):
    if not result_dir.exists():
        logger.error(f"Result directory not found: {result_dir}")
        return

    process_true_count = 0
    process_false_count = 0
    result_true_count = 0
    result_false_count = 0
    process_false_tasks = []
    result_false_tasks = []
    skipped_files = []

    logger.info(f"Starting to analyze results in {result_dir}")

    for root, dirs, files in os.walk(result_dir):
        logger.debug(f"Checking directory: {root}")
        for file in files:
            if file == "results.jsonl":
                file_path = Path(root) / file
                logger.info(f"Found result file: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            last_line = lines[-1].strip()
                            data = json.loads(last_line)
                            process_status = data.get("Process")
                            result_status = data.get("Result")

                            if isinstance(process_status, bool):
                                if process_status:
                                    process_true_count += 1
                                else:
                                    process_false_count += 1
                                    task_name = Path(root).name
                                    process_false_tasks.append(task_name)
                            elif isinstance(process_status, str):
                                if process_status.lower() == "true":
                                    process_true_count += 1
                                elif process_status.lower() == "false":
                                    process_false_count += 1
                                    task_name = Path(root).name
                                    process_false_tasks.append(task_name)
                                else:
                                    skipped_files.append((str(file_path), f"Invalid Process value: {process_status}"))
                            else:
                                skipped_files.append((str(file_path), f"Invalid Process value type: {type(process_status).__name__}"))

                            # 处理 Result 状态
                            if isinstance(result_status, bool):
                                if result_status:
                                    result_true_count += 1
                                else:
                                    result_false_count += 1
                                    task_name = Path(root).name
                                    result_false_tasks.append(task_name)
                            elif isinstance(result_status, str):
                                if result_status.lower() == "true":
                                    result_true_count += 1
                                elif result_status.lower() == "false":
                                    result_false_count += 1
                                    task_name = Path(root).name
                                    result_false_tasks.append(task_name)
                                else:
                                    skipped_files.append((str(file_path), f"Invalid Result value: {result_status}"))
                            else:
                                skipped_files.append((str(file_path), f"Invalid Result value type: {type(result_status).__name__}"))

                except json.JSONDecodeError:
                    skipped_files.append((str(file_path), "JSON decode error"))
                    logger.warning(f"Failed to decode JSON from {file_path}")
                except Exception as e:
                    skipped_files.append((str(file_path), str(e)))
                    logger.error(f"Error reading {file_path}: {e}")

    logger.info(f"Process - True: {process_true_count}, False: {process_false_count}")
    logger.info(f"Result - True: {result_true_count}, False: {result_false_count}")
    if process_false_tasks:
        logger.info(f"Process False tasks: {', '.join(process_false_tasks)}")
    if result_false_tasks:
        logger.info(f"Result False tasks: {', '.join(result_false_tasks)}")
    if skipped_files:
        logger.warning("Skipped files:")
        for file, reason in skipped_files:
            logger.warning(f"  {file}: {reason}")