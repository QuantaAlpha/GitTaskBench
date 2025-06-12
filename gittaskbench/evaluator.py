"""
Evaluator module for GitTaskBench.

This module handles executing test scripts and recording evaluation results.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from gittaskbench.utils import logger, ensure_dir
from gittaskbench.task_loader import TaskTest
import datetime

def run_evaluation(task: TaskTest) -> bool:
    logger.info(f"Evaluating task: {task.taskid}")
    logger.debug(f"Task parameters type: {type(task.parameters)}, value: {task.parameters}")  # 添加调试信息

    # Check if required files exist
    if task.groundtruth and not Path(task.groundtruth).exists():
        logger.warning(f"Groundtruth file not found: {task.groundtruth}")

    if not task.output:
        logger.warning(f"No output found for task {task.taskid}")
        output_dir_path = Path(task.output_dir)
        if not output_dir_path.exists():
            logger.error(f"Output directory not found: {task.output_dir} for task {task.taskid}")
            return False

        output_files = list(output_dir_path.glob("*"))
        if not output_files:
            logger.error(f"No files found in output directory {task.output_dir} for task {task.taskid}")
            return False
        else:
            # output is not valid, write to jsonl
            result_path = Path(task.result)
            ensure_dir(result_path.parent)
            result_data = {
                "Process": False,
                "Result": False,
                "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
                "comments": "No valid output found."
            }
            with open(result_path, 'a', encoding="utf-8") as f:
                f.write(json.dumps(result_data, ensure_ascii=False, default=str) + "\n")
            logger.warning("No valid output found, specific information written to jsonl.")
            return False

    if not Path(task.test_script).exists():
        logger.error(f"Test script not found: {task.test_script}")
        return False

    # Ensure result directory exists
    result_path = Path(task.result)
    ensure_dir(result_path.parent)

    # Prepare command line arguments for test script
    cmd = ["python", str(task.test_script)]

    # Add required arguments
    cmd.extend(["--output", str(task.output)])
    cmd.extend(["--result", str(task.result)])

    # Add groundtruth if available
    if task.groundtruth:
        cmd.extend(["--groundtruth", str(task.groundtruth)])

    # Add any additional parameters
    for key, value in task.parameters.items():
        cmd.extend([f"--{key}", str(value)])

    # Run the test script
    logger.info(f"Running test script: {' '.join(cmd)}")
    try:
        # Execute the script in a subprocess
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False
        )

        # Log stdout/stderr
        if process.stdout:
            logger.info(f"Script output: {process.stdout}")
        if process.stderr:
            logger.warning(f"Script errors: {process.stderr}")

        if process.returncode != 0:
            logger.error(f"Test script failed with return code: {process.returncode}")
            raise Exception(f"Test script failed with return code: {process.returncode}")

    except Exception as e:
        logger.error(f"Error running test script: {str(e)}")
        # Write error information to result.jsonl
        error_result = {
            "Process": False,
            "Result": False,
            "TimePoint": datetime.datetime.now().isoformat(sep='T', timespec='seconds'),
            "comments": str(e)
        }
        with open(result_path, 'a', encoding="utf-8") as f:
            f.write(json.dumps(error_result, ensure_ascii=False, default=str) + "\n")
        return False

    # Check if result file was created
    if not Path(task.result).exists():
        logger.warning(f"Test completed but no result file was created at {task.result}")
        return False

    logger.info(f"Evaluation completed successfully. Results saved to {task.result}")

    # Print summary of results if file exists and is JSON or JSONL
    try:
        if task.result.endswith('.json') or task.result.endswith('.jsonl'):
            with open(task.result, 'r') as f:
                if task.result.endswith('.json'):
                    results = json.load(f)
                    print_result_summary(results)
                else:  # JSONL file
                    lines = f.readlines()
                    if lines:
                        last_result = json.loads(lines[-1])
                        print_result_summary(last_result)
    except Exception as e:
        logger.warning(f"Could not parse results file: {str(e)}")

    return True
'''
def run_evaluation(task: TaskTest) -> bool:
    """
    Run the evaluation for a task.

    Args:
        task: TaskTest object containing task information

    Returns:
        True if evaluation was successful, False otherwise
    """
    logger.info(f"Evaluating task: {task.taskid}")

    # Check if required files exist
    if task.groundtruth and not Path(task.groundtruth).exists():
        logger.warning(f"Groundtruth file not found: {task.groundtruth}")

    if not task.output:
        logger.error(f"No output found for task {task.taskid}")
        return False

    if not Path(task.test_script).exists():
        logger.error(f"Test script not found: {task.test_script}")
        return False

    # Ensure result directory exists
    result_path = Path(task.result)
    ensure_dir(result_path.parent)

    # Prepare command line arguments for test script
    cmd = ["python", str(task.test_script)]

    # Add required arguments
    cmd.extend(["--output", str(task.output)])
    cmd.extend(["--result", str(task.result)])

    # Add groundtruth if available
    if task.groundtruth:
        cmd.extend(["--groundtruth", str(task.groundtruth)])

    # Add any additional parameters
    for key, value in task.parameters.items():
        cmd.extend([f"--{key}", str(value)])

    # Run the test script
    logger.info(f"Running test script: {' '.join(cmd)}")
    try:
        # Execute the script in a subprocess
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False
        )

        # Log stdout/stderr
        if process.stdout:
            logger.info(f"Script output: {process.stdout}")
        if process.stderr:
            logger.warning(f"Script errors: {process.stderr}")

        if process.returncode != 0:
            logger.error(f"Test script failed with return code: {process.returncode}")
            return False

    except Exception as e:
        logger.error(f"Error running test script: {str(e)}")
        return False

    # Check if result file was created
    if not Path(task.result).exists():
        logger.warning(f"Test completed but no result file was created at {task.result}")
        return False

    logger.info(f"Evaluation completed successfully. Results saved to {task.result}")

    # Print summary of results if file exists and is JSON or JSONL
    try:
        if task.result.endswith('.json') or task.result.endswith('.jsonl'):
            with open(task.result, 'r') as f:
                if task.result.endswith('.json'):
                    results = json.load(f)
                    print_result_summary(results)
                else:  # JSONL file
                    lines = f.readlines()
                    if lines:
                        last_result = json.loads(lines[-1])
                        print_result_summary(last_result)
    except Exception as e:
        logger.warning(f"Could not parse results file: {str(e)}")

    return True
'''



def print_result_summary(results: Dict[str, Any]) -> None:
    """
    Print a summary of evaluation results.

    Args:
        results: Dictionary containing evaluation results
    """
    logger.info("Evaluation Summary:")

    # Look for common result fields
    for key in ['Process', 'Result', 'TimePoint', 'comments']:
        if key in results:
            logger.info(f"  {key.capitalize()}: {results[key]}")

    # Print overall status if available
    if 'Result' in results:
        status = results['Result']
        if isinstance(status, bool):
            status_str = "PASSED" if status else "FAILED"
        else:
            status_str = str(status)
        logger.info(f"  Status: {status_str}")