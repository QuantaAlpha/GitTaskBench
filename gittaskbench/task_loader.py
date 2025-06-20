# gittaskbench/task_loader.py
import os
import yaml
import glob
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union

from gittaskbench.utils import logger, find_project_root, ensure_dir


@dataclass
class TaskTest:
    """Class for holding task test information."""
    taskid: str
    result: str
    output_dir: str
    multi_output: bool
    test_script: str
    groundtruth: Optional[str] = None
    output: Optional[Union[str, List[str]]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


def find_task_config(taskid: str) -> Optional[Path]:
    """
    Find the configuration file for a specific task ID.

    Args:
        taskid: Task ID to look for

    Returns:
        Path to the task configuration file or None if not found
    """
    project_root = find_project_root()
    task_config_path = project_root / "config" / taskid / "task_info.yaml"

    if not task_config_path.exists():
        logger.error(f"Task config not found for {taskid} at {task_config_path}")
        return None

    return task_config_path

'''
def load_output(output_dir: str, multi_output: bool) -> Optional[Union[str, List[str]]]:
    """
    Find output files in the specified directory.

    Args:
        output_dir: Directory to search for output files
        multi_output: Whether to expect multiple output files

    Returns:
        Path(s) to output file(s) or None if not found
    """
    output_dir_path = Path(output_dir)

    if not output_dir_path.exists():
        logger.warning(f"Output directory not found: {output_dir}")
        return None

    # First, look for output.* files in the output directory
    output_files = list(output_dir_path.glob("output.*"))

    # If not found, search in subdirectories named "output*"
    if not output_files:
        for subdir in output_dir_path.glob("output*"):
            if subdir.is_dir():
                output_files.extend(list(subdir.glob("*")))

    if not output_files:
        logger.warning(f"No output files found in {output_dir}")
        return None

    if multi_output:
        logger.info(f"Found {len(output_files)} output files in {output_dir}")
        return str(output_dir_path)  # Return the directory for multi-output
    else:
        logger.info(f"Using output file: {output_files[0]}")
        return str(output_files[0])  # Return the first file for single output
'''
def load_output(output_dir: str, multi_output: bool) -> Optional[Union[str, List[str]]]:
    output_dir_path = Path(output_dir)

    if not output_dir_path.exists():
        logger.warning(f"Output directory not found: {output_dir}")
        return None

    # First, look for output.* files in the output directory
    output_files = [f for f in output_dir_path.glob("output.*") if f.is_file()]

    # If not found, look for output* file with no format
    if not output_files:
        output_files = [f for f in output_dir_path.glob("output*") if f.is_file()]

    # If not found, look for output_*. files
    if not output_files:
        output_files = [f for f in output_dir_path.glob("output_*") if f.is_file()]

    # If still not found, search in subdirectories named "output*"
    if not output_files:
        for subdir in output_dir_path.glob("output*"):
            if subdir.is_dir():
                output_files.extend(list(subdir.glob("*")))

    if not output_files:
        logger.warning(f"No output files found in {output_dir}")
        return None

    if multi_output:
        logger.info(f"Found {len(output_files)} output files in {output_dir}")
        return str(output_dir_path)  # Return the directory for multi-output
    else:
        logger.info(f"Using output file: {output_files[0]}")
        output_files = [f for f in output_files if f.is_file()]
        return str(output_files[0])  # Return the first file for single output

def load_task(taskid: str, override_output_dir: Optional[str] = None, override_result_dir: Optional[str] = None) -> Optional[TaskTest]:
    """
    Load task information from configuration file.

    Args:
        taskid: Task ID to load
        override_output_dir: Optional output directory to override the one in config
        override_result_dir: Optional result directory to override the one in config

    Returns:
        TaskTest object or None if loading failed
    """
    config_path = find_task_config(taskid)
    if not config_path:
        return None

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        logger.debug(f"Loaded config for task {taskid}: {config}")

        # Validate required fields
        required_fields = ['taskid', 'result', 'output_dir', 'multi_output', 'test_script']
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required field '{field}' in task config for {taskid}")
                return None

        # Create task test object
        task_test = TaskTest(
            taskid=config['taskid'],
            result=config['result'],
            output_dir=override_output_dir or config['output_dir'],
            multi_output=config['multi_output'],
            test_script=config['test_script'],
            groundtruth=config.get('groundtruth'),
            parameters=config.get('parameters', {})
        )

        # Make paths absolute relative to project root
        project_root = find_project_root()
        task_test.output_dir = str(project_root / task_test.output_dir)
        task_test.test_script = str(project_root / task_test.test_script)

        if task_test.groundtruth:
            task_test.groundtruth = str(project_root / task_test.groundtruth)

        # Handle override result directory
        if override_result_dir:
            result_dir = Path(override_result_dir)
            if not result_dir.is_dir():
                logger.error(f"Provided result path is not a directory: {override_result_dir}")
                return None
            ensure_dir(result_dir)
            task_test.result = str(result_dir / taskid / "result.jsonl")
        else:
            task_test.result = str(project_root / task_test.result)

        # Find output file(s)
        task_test.output = load_output(task_test.output_dir, task_test.multi_output)

        return task_test

    except Exception as e:
        logger.error(f"Error loading task config for {taskid}: {str(e)}")
        return None