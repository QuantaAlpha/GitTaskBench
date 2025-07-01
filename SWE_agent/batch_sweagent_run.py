#!/usr/bin/env python3
import argparse
import os
import subprocess
import logging
import time # Added for sleep
import shlex # Added for command splitting
import json
# No need for platform module anymore, removed platform import
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Configure logging for the script itself
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - [BatchScript] %(message)s' # Added prefix
)
logger = logging.getLogger(__name__)

def run_subprocess_cmd(command: List[str], task_name: str, step_name: str) -> bool:
    """
    Runs a command as a subprocess and logs its output/errors.

    Args:
        command: The command to run as a list of strings.
        task_name: The name of the parent task for logging context.
        step_name: The name of the specific step being executed (e.g., "Docker Prune").

    Returns:
        True if the command executed successfully (return code 0), False otherwise.
    """
    try:
        # For commands involving shell expansion like $(docker ps -aq), use shell=True
        # and pass the command as a string. Be cautious with shell=True.
        is_shell_cmd = isinstance(command, str) or any("$" in str(arg) or "*" in str(arg) for arg in command)
        cmd_str = ' '.join(command) if not isinstance(command, str) else command
        logger.info(f"[{task_name}] Running {step_name}: {cmd_str}")

        result = subprocess.run(
            cmd_str if is_shell_cmd else command,
            capture_output=True,
            text=True,
            check=False,
            shell=is_shell_cmd # Enable shell if needed (e.g., for $(...))
        )

        if result.stdout:
            stdout_msg = f"[{task_name}] {step_name} stdout:\n{result.stdout.strip()}"
            logger.info(stdout_msg)
        if result.stderr:
            stderr_msg = f"[{task_name}] {step_name} stderr:\n{result.stderr.strip()}"
            logger.warning(stderr_msg)

        if result.returncode == 0:
            logger.info(f"[{task_name}] {step_name} completed successfully.")
            return True
        else:
            logger.error(f"[{task_name}] {step_name} failed (RC: {result.returncode}).")
            return False
    except FileNotFoundError:
        cmd_name = command[0] if isinstance(command, list) and command else str(command)
        logger.error(f"[{task_name}] {step_name} failed: Command not found ('{cmd_name}'). Ensure it's in PATH.")
        return False
    except Exception as e:
        logger.error(f"[{task_name}] {step_name} failed due to script exception: {e}")
        return False


def run_sweagent_task(
        base_cmd: List[str],
        problem_statement_path: str,
        task_name: str,
        custom_output_dir: Path  # New parameter: Custom output directory
) -> Tuple[str, bool, str]:
    """
    Runs a single SWE-agent task, letting its output go directly to the terminal.

    Args:
        base_cmd: The base list of command arguments for sweagent run.
        problem_statement_path: The path to the specific .md problem statement.
        task_name: A descriptive name for the task (e.g., the .md filename).
        custom_output_dir: The custom base directory for this specific task's output.

    Returns:
        A tuple containing:
        - task_name (str): The name of the task.
        - success (bool): True if the command executed successfully (return code 0), False otherwise.
        - output (str): An empty string, as output is not captured directly here.
    """
    # Ensure the custom output directory exists
    custom_output_dir.mkdir(parents=True, exist_ok=True)

    # Add --output_dir to the command, pointing to our custom, task-specific directory
    # SWE-agent will create its own subdirectory structure (usually problem_id) within this directory
    full_cmd = base_cmd + [
        '--problem_statement.path', problem_statement_path,
        '--output_dir', str(custom_output_dir)  # Use the entire custom directory as SWE-agent's output root directory
    ]
    logger.info(f"Starting task: {task_name} | Command: {' '.join(full_cmd)}")
    logger.info(f"Output for this task will be in: {custom_output_dir}")
    logger.info(f"--- Output for {task_name} will appear below (interleaved if workers > 1) ---")
    try:
        # Let the subprocess inherit stdout/stderr from the parent for live output
        process = subprocess.Popen(full_cmd)
        returncode = process.wait()
        output = ""  # Output is inherited, not captured

        if returncode == 0:
            logger.info(f"--- Task {task_name} completed successfully (RC: {returncode}) ---")
            return task_name, True, output
        else:
            logger.error(f"--- Task {task_name} failed (RC: {returncode}) ---")
            return task_name, False, output

    except Exception as e:
        logger.error(f"--- Task {task_name} failed to run due to script exception: {e} ---")
        rc = -1
        return task_name, False, f"Exception: {str(e)}\nReturn Code: {rc}"

def post_task_actions(
    task_name: str,
    host_repo_path: str,
    sleep_duration: int,
    skip_docker_prune: bool,
    skip_git_commit: bool
) -> None:
    """
    Performs cleanup and Git operations after a task finishes.
    Args are the same as before.
    """
    logger.info(f"--- Starting post-task actions for {task_name} ---")

    if not skip_docker_prune:
        logger.info(f"[{task_name}] Cleaning up Docker containers...")
        # Use shell=True for command substitution $()
        stop_cmd = "docker stop $(docker ps -aq)"
        rm_cmd = "docker rm $(docker ps -aq)"
        run_subprocess_cmd(stop_cmd, task_name, "Docker Stop")
        run_subprocess_cmd(rm_cmd, task_name, "Docker Remove")
        logger.info(f"[{task_name}] Docker cleanup finished.")
    else:
        logger.info(f"[{task_name}] Skipping Docker prune step.")

    if sleep_duration > 0:
        logger.info(f"[{task_name}] Sleeping for {sleep_duration} seconds...")
        time.sleep(sleep_duration)
        logger.info(f"[{task_name}] Sleep finished.")

    if not skip_git_commit:
        if not os.path.isdir(host_repo_path):
            logger.error(f"[{task_name}] Git repo path not found or not a directory: {host_repo_path}. Skipping Git actions.")
            return

        logger.info(f"[{task_name}] Performing Git actions in {host_repo_path}...")
        add_cmd = ['git', '-C', host_repo_path, 'add', '.']
        run_subprocess_cmd(add_cmd, task_name, "Git Add")

        commit_msg = f"SWE-agent task {task_name}: Post-run commit"
        commit_cmd = ['git', '-C', host_repo_path, 'commit', '--allow-empty', '--no-verify', '-m', commit_msg]
        run_subprocess_cmd(commit_cmd, task_name, "Git Commit")
    else:
         logger.info(f"[{task_name}] Skipping Git commit step.")

    logger.info(f"--- Finished post-task actions for {task_name} ---")

def find_trajectory_file(task_specific_output_dir: str, user_name_arg: str, model_name_arg: str, task_name: str) -> Optional[str]:
    """
    Finds the trajectory file in the specified task-specific output directory.
    SWE-agent creates a subdirectory named after the problem_id under the provided --output_dir (i.e., task_specific_output_dir).

    Args:
        task_specific_output_dir: The --output_dir created by the batch script for this task and passed to sweagent.
                                (e.g., trajectories/your_user/model-task/)
        user_name_arg: The user_name passed from the command line, mainly for logging or debugging here; path construction already relies on task_specific_output_dir.
        model_name_arg: The model_name passed from the command line, mainly for logging or debugging here.
        task_name: The original task name (e.g., "Scrapy_02.md")

    Returns:
        The path to the trajectory file, or None if not found.
    """
    # task_specific_output_dir is already .../trajectories/USER_NAME/MODEL_NAME-TASK_NAME_NO_EXT/
    base_search_dir = Path(task_specific_output_dir)

    logger.debug(f"[find_trajectory_file] Searching in base directory for task '{task_name}': {base_search_dir}")

    if not base_search_dir.is_dir():
        logger.warning(f"[find_trajectory_file] Base search directory not found: {base_search_dir}")
        return None

    # SWE-agent creates a subdirectory named after problem_statement.id under base_search_dir.
    # We need to iterate through the subdirectories of base_search_dir to find the trajectory file.
    try:
        for potential_problem_id_dir in base_search_dir.iterdir():
            if potential_problem_id_dir.is_dir():
                logger.debug(f"[find_trajectory_file] Checking subdir for .traj: {potential_problem_id_dir}")
                for file_in_subdir in potential_problem_id_dir.iterdir():
                    if file_in_subdir.is_file() and file_in_subdir.name.endswith('.traj'):
                        logger.info(f"[find_trajectory_file] Found trajectory file: {file_in_subdir}")
                        return str(file_in_subdir)
                logger.debug(f"[find_trajectory_file] No .traj file in {potential_problem_id_dir}")
            # Also check if base_search_dir itself directly contains a .traj file (in case SWE-agent behavior changes or simple tasks don't have a problem_id subdirectory)
            elif potential_problem_id_dir.is_file() and potential_problem_id_dir.name.endswith('.traj'):
                 logger.info(f"[find_trajectory_file] Found trajectory file directly in task output dir: {potential_problem_id_dir}")
                 return str(potential_problem_id_dir)

    except OSError as e:
        logger.error(f"[find_trajectory_file] Error listing directories in {base_search_dir}: {e}")
        return None

    logger.warning(f"[find_trajectory_file] No .traj file found for task '{task_name}' in {base_search_dir} or its direct subdirectories.")
    return None

def parse_trajectory_stats(trajectory_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses model_stats information from a trajectory file.

    Args:
        trajectory_path: The path to the trajectory file.

    Returns:
        A dictionary containing model_stats information, or None if parsing fails.
    """
    try:
        if not os.path.exists(trajectory_path):
            logger.warning(f"Trajectory file not found: {trajectory_path}")
            return None

        # Attempt to load the entire file directly as a JSON object
        # This works if the trajectory file is a single large JSON object
        try:
            with open(trajectory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check for info.model_stats or direct model_stats
            if isinstance(data, dict):
                if 'info' in data and isinstance(data['info'], dict) and \
                   'model_stats' in data['info'] and isinstance(data['info']['model_stats'], dict):
                    return data['info']['model_stats']

                if 'model_stats' in data and isinstance(data['model_stats'], dict):
                    return data['model_stats']
        except (json.JSONDecodeError, MemoryError) as e:
            logger.debug(f"Failed to load trajectory as single JSON object ({trajectory_path}): {e}. Trying line-by-line parsing.")
            # If loading as a single JSON object fails, try line-by-line parsing (for JSON Lines format or appended stats)
            pass # Continue to try the method below

        # If the above method fails, try to find model_stats from the end of the file
        with open(trajectory_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # Move to the end of the file
            file_size = f.tell()

            chunk_size = 100000  # Read the last 100KB (can be adjusted based on where model_stats usually appear)
            position = file_size

            buffer = ""
            while position > 0:
                read_size = min(chunk_size, position)
                position -= read_size
                f.seek(position)

                # Read the chunk and concatenate with the unparsed part of the previous chunk
                current_chunk = f.read(read_size)
                content_to_search = current_chunk + buffer

                # Find the "model_stats": { ... } structure
                # Search from the end to get the latest model_stats (if there are multiple in the file)
                last_match_pos = -1
                search_start_pos = 0
                while True:
                    match_pos = content_to_search.find('"model_stats":', search_start_pos)
                    if match_pos != -1:
                        last_match_pos = match_pos
                        search_start_pos = match_pos + 1
                    else:
                        break

                if last_match_pos != -1:
                    # Found "model_stats":, try to extract the JSON object that follows
                    json_text_start = content_to_search.find('{', last_match_pos + len('"model_stats":'))
                    if json_text_start != -1:
                        brace_count = 0
                        json_obj_str = ""
                        for i in range(json_text_start, len(content_to_search)):
                            char = content_to_search[i]
                            json_obj_str += char
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    try:
                                        model_stats = json.loads(json_obj_str)
                                        logger.debug(f"Successfully parsed model_stats from chunk in {trajectory_path}")
                                        return model_stats
                                    except json.JSONDecodeError:
                                        # Parsing failed, possibly incomplete or malformed JSON object
                                        logger.debug(f"JSONDecodeError for model_stats chunk in {trajectory_path}: {json_obj_str}")
                                        # Continue in the outer loop to find the next occurrence of model_stats or read more content
                                        break # Exit inner for loop, continue while loop to read more chunks
                        # If brace_count is not zero when the inner loop ends, it means the JSON object might span across chunks
                        # Store the beginning of the current chunk (which might contain incomplete JSON) in the buffer to concatenate with the next chunk
                        if brace_count != 0:
                             buffer = content_to_search[json_text_start:]
                        else:
                             buffer = "" # Successfully parsed or no need to concatenate
                    else:
                        buffer = content_to_search # Did not find '{', keep the current chunk
                else: # "model_stats": not found in the current chunk
                    buffer = current_chunk # Keep the current chunk entirely to concatenate with the previous chunk

                # If the beginning of the file has been reached and no result has been parsed from the buffer, parsing failed
                if position == 0:
                    break

        logger.warning(f"Could not find or parse valid model_stats in trajectory file: {trajectory_path}")
        return None

    except Exception as e:
        logger.error(f"Error reading or parsing trajectory file {trajectory_path}: {e}", exc_info=True)
        return None

# New: Global variables for accumulating costs (or as class members if refactored into a class)
global_overall_total_cost = 0.0
global_overall_total_tokens_sent = 0
global_overall_total_tokens_received = 0
global_overall_total_api_calls = 0
batch_results_summary_list_for_file: List[Dict[str, Any]] = [] # For final writing to JSONL file

def format_and_process_task_result(
    task_name: str,
    model_name: str, # Model name needed to construct run_id
    success: bool,
    output_str: Optional[str],
    model_stats: Optional[Dict[str, Any]],
    error_msg: Optional[str]
) -> None:
    """
    Formats the result of a single task, prints an immediate summary, and accumulates to global statistics.
    """
    global global_overall_total_cost, global_overall_total_tokens_sent
    global global_overall_total_tokens_received, global_overall_total_api_calls
    global batch_results_summary_list_for_file

    task_name_without_ext = os.path.splitext(task_name)[0]
    run_id = f"{model_name}-{task_name_without_ext}"

    instance_cost = model_stats.get("instance_cost") if model_stats else None
    tokens_sent = model_stats.get("tokens_sent") if model_stats else None
    tokens_received = model_stats.get("tokens_received") if model_stats else None
    api_calls = model_stats.get("api_calls") if model_stats else None

    # Print immediate cost summary for the current task
    logger.info(f"--- Cost Summary for Task: {task_name} ---")
    if success and model_stats:
        logger.info(f"  Status: SUCCESS")
        logger.info(f"  Task Cost: ${instance_cost:.4f}" if instance_cost is not None else "  Task Cost: N/A")
        logger.info(f"  Tokens Sent: {tokens_sent}")
        logger.info(f"  Tokens Received: {tokens_received}")
        logger.info(f"  API Calls: {api_calls}")
    elif success and not model_stats:
        logger.info(f"  Status: SUCCESS (but model_stats not found/parsed)")
        logger.warning(f"  Cost information unavailable. Error during parsing: {error_msg if error_msg else 'Unknown parsing error'}")
    else: # not success
        logger.info(f"  Status: FAILED")
        logger.warning(f"  Task failed. Error: {(error_msg or output_str or 'Unknown execution error').splitlines()[0][:100]}")
    logger.info(f"--- End Cost Summary for Task: {task_name} ---")

    # Build entry for JSONL file
    summary_entry = {
        "task_name": task_name,
        "run_id": run_id,
        "success": success,
        "instance_cost": instance_cost,
        "tokens_sent": tokens_sent,
        "tokens_received": tokens_received,
        "api_calls": api_calls,
        "error": error_msg if error_msg else (None if success else (output_str or "Task execution failed"))
    }
    batch_results_summary_list_for_file.append(summary_entry)

    # Accumulate to global statistics
    if success and model_stats: # Accumulate only if successful and stats are available
        if instance_cost is not None:
            global_overall_total_cost += instance_cost
        if tokens_sent is not None:
            global_overall_total_tokens_sent += tokens_sent
        if tokens_received is not None:
            global_overall_total_tokens_received += tokens_received
        if api_calls is not None:
            global_overall_total_api_calls += api_calls

def main():
    """
    Main function restored.
    """
    parser = argparse.ArgumentParser(
        description='Batch run SWE-agent tasks with post-task actions.'
    )
    # Add all arguments back (prompt-dir, workers, model-name, image, repo-path, config-path, host-repo-path, sleep-duration, skip-docker-prune, skip-git-commit, log-level)
    parser.add_argument(
        '--prompt-dir',
        type=str,
        required=True,
        help='Directory containing the .md problem statement files.'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of concurrent workers. Set to 1 for sequential post-task actions.'
    )
    parser.add_argument(
        '--model-name', type=str, required=True, help='Agent model name.'
    )
    parser.add_argument(
        '--image', type=str, required=True, help='Docker image.'
    )
    parser.add_argument(
        '--repo-path', type=str, required=True, help='Repo path inside container.'
    )
    parser.add_argument(
        '--config-path',
        type=str,
        required=True,
        nargs='+',  # Allows one or more config files
        help='SWE-agent config file(s). If multiple, they are merged, later files override earlier ones.'
    )
    parser.add_argument(
        '--host-repo-path', type=str, required=True, help='Host repo path for Git.'
    )
    parser.add_argument(
        '--sleep-duration', type=int, default=5, help='Sleep duration after task.'
    )
    parser.add_argument(
        '--skip-docker-prune', action='store_true', help='Skip Docker cleanup.'
    )
    parser.add_argument(
        '--skip-git-commit', action='store_true', help='Skip Git commit.'
    )
    parser.add_argument(
        '--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Logging level.'
    )
    # Add arguments for checking existing output
    parser.add_argument(
        '--output-base-dir',
        type=str,
        default='trajectories', # Default SWE-agent output base dir
        help='Base directory where SWE-agent saves task outputs.'
    )
    parser.add_argument(
        '--user-name',
        type=str,
        default='batch_user', # Default user for trajectory path
        help='Username used in the SWE-agent output trajectory path.'
    )

    args = parser.parse_args()

    # Argument Validation (Workers and Git path)
    if args.workers > 1:
        logger.warning(
            f"Running with {args.workers} workers. Post-task actions (Docker/Git) might interleave. Set --workers 1 for sequential execution."
        )
    if not args.skip_git_commit and not os.path.isdir(args.host_repo_path):
         logger.warning(
             f"Host Git repository path '{args.host_repo_path}' not found. Git actions will be skipped."
         )

    # Set logging level
    log_level_upper = args.log_level.upper()
    try:
        log_level_int = getattr(logging, log_level_upper)
        # Reconfigure logger level based on args
        logging.getLogger().setLevel(log_level_int)
        for handler in logging.getLogger().handlers:
            handler.setLevel(log_level_int)
        logger.info(f"Logging level set to {log_level_upper}")
    except AttributeError:
        logger.error(f"Invalid log level: {args.log_level}. Using INFO.")
        # Keep default INFO level from basicConfig

    # Validate prompt directory
    if not os.path.isdir(args.prompt_dir):
        logger.error(f"Prompt directory not found: {args.prompt_dir}")
        return

    all_md_files = [f for f in os.listdir(args.prompt_dir) if f.endswith('.md') and os.path.isfile(os.path.join(args.prompt_dir, f))]
    if not all_md_files:
        logger.warning(f"No .md files found in {args.prompt_dir}")
        return

    logger.info(f"Found {len(all_md_files)} total .md files in {args.prompt_dir}")

    # Filter out tasks with existing output directories
    md_files_to_run = []
    skipped_count = 0
    for md_file in all_md_files:
        task_name_without_ext = os.path.splitext(md_file)[0]
        # Construct the expected output path based on SWE-agent conventions
        expected_output_dir = os.path.join(
            args.output_base_dir,
            args.user_name,
            f"{args.model_name}-{task_name_without_ext}"
        )

        if os.path.isdir(expected_output_dir):
            logger.info(f"Skipping task '{md_file}': Output directory already exists at '{expected_output_dir}'")
            skipped_count += 1
        else:
            md_files_to_run.append(md_file)

    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} tasks because their output directories already exist.")

    # Modified exit condition: Only exit if no .md files were found initially.
    # If .md files exist but all were skipped, we still want to proceed for retrospective analysis.
    if not all_md_files: # If no md files were found initially
        logger.warning(f"No .md files found in {args.prompt_dir}. Nothing to do.")
        return
    elif not md_files_to_run and skipped_count == len(all_md_files):
        logger.info("All tasks from prompt_dir were skipped as their output directories already exist. Proceeding to analyze existing trajectories.")
    elif not md_files_to_run:
        # This situation should ideally not happen, as if all_md_files is not empty, either md_files_to_run is not empty or skipped_count == len(all_md_files)
        logger.warning("No tasks left to run and not all tasks were skipped. This is an unexpected state.")
        # Consider whether to continue here as well, or if this is an error condition that requires stopping
        # For safety, if it's not the "all skipped" case and there are no new tasks, it might also be good to prompt the user
        # But according to the requirements, as long as the scanning logic can run, it should continue
        logger.info("No new tasks to run, but proceeding to analyze existing trajectories if any.")

    if md_files_to_run:
        logger.info(f"Starting execution of {len(md_files_to_run)} new tasks...")
    else:
        logger.info("No new tasks to run in this batch. Proceeding to analyze existing trajectories.")

    # Log settings (print configuration information even if there are no new tasks)
    logger.info(f"User for trajectory path: {args.user_name}")
    logger.info(f"Output base directory for new tasks: {Path(args.output_base_dir) / args.user_name}")
    logger.info(f"Base directory for scanning existing trajectories: {Path(args.output_base_dir) / args.user_name}")
    logger.info(f"Workers: {args.workers}")

    base_cmd = [
        'sweagent', 'run',
    ]
    # Add a --config argument for each provided config file path
    if isinstance(args.config_path, list):
        for cfg_path in args.config_path:
            base_cmd.extend(['--config', cfg_path])
    else: # Case of a single config file
        base_cmd.extend(['--config', args.config_path])

    base_cmd.extend([
        '--agent.model.name', args.model_name,
        '--env.repo.path', args.repo_path,
        '--env.deployment.image', args.image,
    ])

    results_placeholder = {} # Used to track the original success/failure and output of tasks to decide whether to parse

    # Execute ThreadPoolExecutor only if there are new tasks to run
    if md_files_to_run:
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix='SWEAgentWorker') as executor:
            futures = {
                executor.submit(
                    run_sweagent_task,
                    base_cmd,
                    os.path.join(args.prompt_dir, md_file),
                    md_file,
                    Path(args.output_base_dir) / args.user_name / f"{args.model_name}-{os.path.splitext(md_file)[0]}"
                ): md_file
                for md_file in md_files_to_run
            }

            for future in as_completed(futures):
                task_name = futures[future]
                task_success = False
                task_output_str = ""
                model_stats_for_task = None
                cost_error_message = None

                try:
                    name, success, output_str = future.result()
                    results_placeholder[name] = {'success': success, 'output': output_str}  # Store original results
                    task_success = success
                    task_output_str = output_str
                except Exception as exc:
                    logger.error(f'{task_name} generated an exception during future processing: {exc}')
                    results_placeholder[task_name] = {'success': False, 'output': f"Exception: {str(exc)}"}
                    task_output_str = f"Exception: {str(exc)}"

                post_task_actions(
                    task_name=task_name,
                    host_repo_path=args.host_repo_path,
                    sleep_duration=args.sleep_duration,
                    skip_docker_prune=args.skip_docker_prune,
                    skip_git_commit=args.skip_git_commit
                )

                if task_success:
                    task_name_without_ext = os.path.splitext(task_name)[0]
                    custom_task_output_dir_for_find = Path(args.output_base_dir) / args.user_name / f"{args.model_name}-{task_name_without_ext}"

                    traj_file = find_trajectory_file(
                        str(custom_task_output_dir_for_find),
                        args.user_name,
                        args.model_name,
                        task_name
                    )
                    if traj_file:
                        model_stats_for_task = parse_trajectory_stats(traj_file)
                        if not model_stats_for_task:
                            cost_error_message = f"Could not parse model_stats from trajectory: {traj_file}"
                    else:
                        cost_error_message = "Trajectory file not found for cost analysis."
                else:
                    cost_error_message = task_output_str

                # Call the new helper function to process results and costs
                format_and_process_task_result(
                    task_name=task_name,
                    model_name=args.model_name,
                    success=task_success,
                    output_str=task_output_str,
                    model_stats=model_stats_for_task,
                    error_msg=cost_error_message
                )
    else:
        logger.info("No new tasks to run in this batch. Proceeding to analyze existing trajectories.")

    # --- Scan and supplement all eligible existing trajectories (this logic will always execute now) ---
    logger.info("--- Scanning for all existing relevant trajectories to complete the summary ---")
    processed_task_names_in_current_run = {entry['task_name'] for entry in batch_results_summary_list_for_file}

    base_scan_dir = Path(args.output_base_dir) / args.user_name
    if base_scan_dir.is_dir():
        for item_name in os.listdir(base_scan_dir):
            # Check if the directory name starts with the model name, following the model_name-task_name_no_ext pattern
            if item_name.startswith(f"{args.model_name}-"):
                # Attempt to extract the original task name (including .md) from the directory name
                # For example, extract "AnimeGANv3_03.md" from "gpt-4o-AnimeGANv3_03"
                potential_task_name_no_ext = item_name[len(args.model_name) + 1:]
                original_task_name_md = f"{potential_task_name_no_ext}.md"

                if original_task_name_md not in processed_task_names_in_current_run:
                    logger.info(f"Found existing task directory for (potentially skipped) task: {original_task_name_md}")
                    task_specific_output_dir = base_scan_dir / item_name

                    traj_file = find_trajectory_file(
                        str(task_specific_output_dir),  # This is the top-level task directory
                        args.user_name,
                        args.model_name,
                        original_task_name_md  # Use the original task name
                    )

                    model_stats = None
                    cost_error_message = None
                    success_for_skipped = False  # By default, skipped or un-run tasks are considered unsuccessful, unless information can be parsed from the trajectory

                    if traj_file:
                        model_stats = parse_trajectory_stats(traj_file)
                        if model_stats:
                            success_for_skipped = True  # If stats can be parsed, assume the task was at least partially successful
                            logger.info(f"  Successfully parsed stats for existing task: {original_task_name_md}")
                        else:
                            cost_error_message = f"Could not parse model_stats from existing trajectory: {traj_file}"
                            logger.warning(f"  {cost_error_message}")
                    else:
                        cost_error_message = f"Trajectory file not found for existing task: {original_task_name_md} in {task_specific_output_dir}"
                        logger.warning(f"  {cost_error_message}")

                        # Add/update the entry for this previously run or skipped task
                        # Note: output_str for skipped tasks will be unknown here
                    format_and_process_task_result(
                        task_name=original_task_name_md,
                        model_name=args.model_name,
                        success=success_for_skipped,# If trajectory exists and stats are parsed, consider it successful
                        output_str="Skipped in current run or output not captured.",
                        model_stats=model_stats,
                        error_msg=cost_error_message
                    )
    logger.info("--- Finished scanning existing trajectories ---")
    # --------------------------------------------

    # Reporting (Overall Summary Section) - batch_results_summary_list_for_file now contains all tasks
    successful_tasks = sum(1 for r_val in batch_results_summary_list_for_file if r_val['success'])
    failed_tasks = len(batch_results_summary_list_for_file) - successful_tasks

    # save batch_results.jsonl
    results_file_path = Path(args.output_base_dir) / args.user_name / "batch_results.jsonl"
    if args.user_name and not (Path(args.output_base_dir) / args.user_name).exists():
        try:
            (Path(args.output_base_dir) / args.user_name).mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning(f"Could not create user directory {Path(args.output_base_dir) / args.user_name}. Saving batch_results.jsonl to current directory.")
            results_file_path = Path("batch_results.jsonl")
    elif not args.user_name:
        if Path(args.output_base_dir).is_dir():
             results_file_path = Path(args.output_base_dir) / "batch_results.jsonl"
        else:
             results_file_path = Path("batch_results.jsonl")

    logger.info(f"Saving final batch summary to: {results_file_path.resolve()}")
    results_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file_path, 'w', encoding='utf-8') as f:
        for entry in batch_results_summary_list_for_file:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    logger.info("\n--- Overall Batch Run Summary ---")
    logger.info(f"Total tasks processed: {len(batch_results_summary_list_for_file)}")
    logger.info(f"Successful SWE-agent runs: {successful_tasks}")
    logger.info(f"Failed SWE-agent runs: {failed_tasks}")
    logger.info(f"Batch summary saved to: {results_file_path.resolve()}")

    if global_overall_total_cost > 0 or global_overall_total_tokens_sent > 0:
        logger.info("\n--- Overall Cost Summary ---")
        logger.info(f"Total cost: ${global_overall_total_cost:.4f}")
        logger.info(f"Total tokens sent: {global_overall_total_tokens_sent:,}")
        logger.info(f"Total tokens received: {global_overall_total_tokens_received:,}")
        logger.info(f"Total API calls: {global_overall_total_api_calls:,}")
        if successful_tasks > 0 and global_overall_total_cost > 0:
            logger.info(f"Average cost per successful task: ${global_overall_total_cost/successful_tasks:.4f}")

    if failed_tasks > 0:
        logger.warning("\nFailed SWE-agent runs list:")
        for entry in batch_results_summary_list_for_file:
            if not entry['success']:
                error_msg = entry.get('error')
                error_summary = error_msg.split('\n')[0][:100] if error_msg else "Unknown error"
                logger.warning(f"- {entry['task_name']} (Reason: {error_summary})")

if __name__ == "__main__":
    main()