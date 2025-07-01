import os
import subprocess
import glob
import time
import re
import json
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import docker
from docker.errors import NotFound, APIError

# --- Configuration ---
DEFAULT_PROMPT_DIR = "/data/data/agent_test_codebase/GitTaskBench/prompt/prompt"
DEFAULT_OPENHANDS_PROJECT_DIR = "/data/code/agent_new/OpenHands" # Directory containing poetry.lock
# DEFAULT_OUTPUT_DIR removed, will be handled by argparse
DEFAULT_MAX_WORKERS = 1 # Set to 1 for serial execution due to memory limits

# --- Helper Functions ---

def setup_logging(log_file_path: str):
    """Basic logging setup."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def create_config_file(project_dir: str, output_dir_abs: str, config_file_name: str, target_workspace: str) -> str:
    """Creates the config file for batch processing, setting workspace and file store/trajectory paths."""
    config_file_path = os.path.join(project_dir, config_file_name) # Config file itself is still in project dir
    # <<< Define the trajectory/event store path directly in the output directory >>>
    trajectory_store_path = os.path.join(output_dir_abs, "trajectories")
    os.makedirs(trajectory_store_path, exist_ok=True)

    # Ensure paths use forward slashes for TOML
    trajectory_store_path_for_toml = trajectory_store_path.replace(os.sep, '/')
    target_workspace_for_toml = target_workspace.replace(os.sep, '/')

    config_content = f"""
[core]
# Workspace settings
workspace_base = "{target_workspace_for_toml}"
workspace_mount_path = "{target_workspace_for_toml}"
workspace_mount_path_in_sandbox = "{target_workspace_for_toml}"

# <<< Set BOTH file_store_path and save_trajectory_path >>>
file_store_path = "{trajectory_store_path_for_toml}" # Direct events here
save_trajectory_path = "{trajectory_store_path_for_toml}" # Use same path (redundant? but ensures config)

# IMPORTANT: Uncomment and set runtime if you DON'T want the default 'docker'
# runtime = "local"
max_iterations = 100

[sandbox]
# Sandbox timeout in seconds
timeout = 600

# Optional: Configure LLM details if not set elsewhere
[llm]
model = "openai/gpt-4o-2024-11-20" # Replace with actual model from call.py if different
api_key = "your_key" 
base_url = "https://models-proxy.stepfun-inc.com/v1"
num_retries = 30
"""
    with open(config_file_path, "w") as f:
        f.write(config_content.strip())
    logger.info(f"Created config file: {config_file_path}")
    logger.info(f"  - Workspace Base/Mount/Sandbox Path: {target_workspace}")
    # <<< Update log message >>>
    logger.info(f"  - Trajectory / Event Store Path: {trajectory_store_path}")
    return config_file_path

def parse_token_cost(output: str) -> dict:
    """Parses token and cost information from the CLI output."""
    metrics = {
        "total_cost": None,
        "total_input_tokens": None,
        "total_output_tokens": None,
    }
    # Regex patterns to find the summary lines
    cost_match = re.search(r"Total Cost:\s+\$([\d\.]+)", output, re.IGNORECASE)
    input_tokens_match = re.search(r"Total Input Tokens:\s+(\d+)", output, re.IGNORECASE)
    output_tokens_match = re.search(r"Total Output Tokens:\s+(\d+)", output, re.IGNORECASE)

    if cost_match:
        try:
            metrics["total_cost"] = float(cost_match.group(1))
        except ValueError:
            logger.warning("Could not parse total_cost value.")
    if input_tokens_match:
        try:
            metrics["total_input_tokens"] = int(input_tokens_match.group(1))
        except ValueError:
            logger.warning("Could not parse total_input_tokens value.")
    if output_tokens_match:
        try:
            metrics["total_output_tokens"] = int(output_tokens_match.group(1))
        except ValueError:
            logger.warning("Could not parse total_output_tokens value.")
    return metrics

def run_task(args: tuple[str, str, str, int | None]) -> dict:
    """Runs a single OpenHands task, printing output real-time, and reads summary from file."""
    prompt_file, project_dir, config_file_path, timeout_seconds = args
    start_time = time.time()
    task_name = os.path.basename(prompt_file)
    logger.info(f"--- Running task: {task_name} ---")
    print(f"\n{'='*15} Starting OpenHands Task: {task_name} {'='*15}\n", flush=True)

    # <<< Generate unique summary file path >>>
    # Place it in the output directory for easy cleanup/access
    summary_filename = f".{task_name}.summary.json" # Hidden file
    summary_file_path = os.path.join(os.path.dirname(config_file_path), os.path.dirname(results_file_path), summary_filename)
    # Ensure the directory for the summary file exists (should be the output dir)
    os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)

    command = [
        "poetry", "run", "python", "-m", "openhands.core.cli",
        "-f", prompt_file,
        "--config-file", config_file_path,
        "--run-once",
        "--summary-file", summary_file_path
    ]

    result = {
        "task_name": task_name,
        "prompt_file": prompt_file,
        "stdout": "(Real-time, not captured)",
        "stderr": "(Real-time, not captured)",
        # Initialize metrics to None, will be updated later if summary file is read
        "total_cost": None,
        "total_input_tokens": None,
        "total_output_tokens": None,
        "total_tokens": None, # Adding total tokens field
        "cache_read_tokens": None, # Adding cache fields
        "cache_write_tokens": None,
        "session_id": None # Adding session id
    }

    try:
        process = subprocess.run(
            command,
            cwd=project_dir,
            # capture_output=False, # Keep output streaming
            check=False,
            timeout=timeout_seconds
        )
        end_time = time.time()
        elapsed_time = end_time - start_time

        result["status"] = "success" if process.returncode == 0 else "failed"
        result["return_code"] = process.returncode
        result["elapsed_time_seconds"] = round(elapsed_time, 2)

        # <<< START: Read summary file if task succeeded >>>
        if result["status"] == "success" and os.path.exists(summary_file_path):
            try:
                with open(summary_file_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                # Update result dict with metrics from summary file
                result["total_cost"] = summary_data.get("total_cost_usd")
                result["total_input_tokens"] = summary_data.get("total_input_tokens")
                result["total_output_tokens"] = summary_data.get("total_output_tokens")
                result["total_tokens"] = summary_data.get("total_tokens")
                result["cache_read_tokens"] = summary_data.get("cache_read_tokens")
                result["cache_write_tokens"] = summary_data.get("cache_write_tokens")
                result["session_id"] = summary_data.get("session_id")
                logger.info(f"Successfully read summary metrics from: {summary_file_path}")
            except Exception as e:
                logger.error(f"Failed to read or parse summary file {summary_file_path}: {e}")
        elif result["status"] == "success":
            logger.warning(f"Task succeeded but summary file not found: {summary_file_path}")
        # <<< END: Read summary file >>>

        print(f"\n{'='*15} Finished OpenHands Task: {task_name} (Status: {result['status']}) {'='*15}\n", flush=True)
        logger.info(f"--- Finished task: {task_name} ({result['status']}) ---")
        # Log metrics read from file
        logger.info(f"    Time: {result['elapsed_time_seconds']:.2f}s")
        logger.info(f"    Cost: ${result['total_cost'] if result['total_cost'] is not None else 'N/A'}")
        logger.info(f"    Input Tokens: {result['total_input_tokens'] if result['total_input_tokens'] is not None else 'N/A'}")
        logger.info(f"    Output Tokens: {result['total_output_tokens'] if result['total_output_tokens'] is not None else 'N/A'}")

    except subprocess.TimeoutExpired:
        end_time = time.time()
        elapsed_time = end_time - start_time
        result["status"] = "timeout"
        result["return_code"] = -1 # Convention for timeout
        result["elapsed_time_seconds"] = round(elapsed_time, 2)
        print(f"\n{'='*15} Task TIMEOUT: {task_name} {'='*15}\n", flush=True)
        logger.error(f"--- Task TIMEOUT: {task_name} after {timeout_seconds} seconds ---")

    except Exception as e:
        end_time = time.time()
        elapsed_time = end_time - start_time
        result["status"] = "error"
        result["return_code"] = -1 # Convention for script error
        result["elapsed_time_seconds"] = round(elapsed_time, 2)
        result["stderr"] = f"Batch script error during task execution: {str(e)}"
        print(f"\n{'='*15} Task ERROR: {task_name} {'='*15}\nError: {e}\n", flush=True)
        logger.error(f"--- Task ERROR: {task_name} ({e}) ---", exc_info=True)

    finally:
        # <<< Clean up summary file >>>
        if os.path.exists(summary_file_path):
            try:
                os.remove(summary_file_path)
                logger.debug(f"Removed temporary summary file: {summary_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary summary file {summary_file_path}: {e}")

    return result

def save_result(result: dict, results_file_path: str):
    """Appends a result to the JSONL file."""
    try:
        with open(results_file_path, "a") as f:
            json.dump(result, f)
            f.write("\n")
    except Exception as e:
        logger.error(f"Error writing results for {result.get('task_name', 'UNKNOWN')}: {e}", exc_info=True)

# <<< START: Add Docker cleanup function >>>
def cleanup_runtime_containers(container_name_prefix: str):
    """Finds, stops, and removes Docker containers matching the prefix."""
    logger.info(f"Attempting to clean up Docker containers starting with '{container_name_prefix}'...")
    cleaned_count = 0
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True, filters={'name': f'{container_name_prefix}*'})

        if not containers:
            logger.info("No matching Docker containers found to clean up.")
            return

        for container in containers:
            logger.info(f"Found container: {container.name} ({container.short_id}), status: {container.status}")
            try:
                if container.status == 'running':
                    logger.info(f"Stopping container {container.name}...")
                    container.stop(timeout=10) # 10 second timeout to stop
                    logger.info(f"Container {container.name} stopped.")
                else:
                    logger.info(f"Container {container.name} is not running, attempting removal directly.")

                logger.info(f"Removing container {container.name}...")
                container.remove()
                logger.info(f"Container {container.name} removed.")
                cleaned_count += 1
            except NotFound:
                logger.warning(f"Container {container.name} not found during cleanup (possibly already removed). Skipping.")
            except APIError as e:
                logger.error(f"API error during cleanup of container {container.name}: {e}. Continuing...")
            except Exception as e:
                logger.error(f"Unexpected error during cleanup of container {container.name}: {e}. Continuing...")

        logger.info(f"Docker cleanup finished. Removed {cleaned_count} container(s).")

    except APIError as e:
        logger.error(f"Docker API error during container cleanup process: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Docker container cleanup process: {e}")

    # Optional: Add a small delay after cleanup
    # time.sleep(1)
# <<< END: Add Docker cleanup function >>>

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OpenHands tasks in batch.")
    parser.add_argument("--target-workspace", type=str,
                        default="/data/data/agent_test_codebase/GitTaskBench", # Default to your target
                        help="The absolute path to use as the workspace base, mount path, and sandbox path.")
    parser.add_argument("--prompt-dir", type=str, default=DEFAULT_PROMPT_DIR,
                        help="Directory containing .md prompt files.")
    parser.add_argument("--project-dir", type=str, default=DEFAULT_OPENHANDS_PROJECT_DIR,
                        help="Path to the OpenHands project directory.")
    parser.add_argument("--output-dir", type=str, default=None, # Default is None now
                        help="Absolute or relative path for the output directory. "
                            "If relative, it's relative to the project directory. "
                            "If not provided, defaults to '<project_dir>/batch_output'.")
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS,
                        help="Number of parallel workers (set to 1 for serial).")
    parser.add_argument("--timeout", type=int, default=None,
                        help="Timeout in seconds for each task (optional).")
    parser.add_argument("--config-name", type=str, default="batch_config.toml",
                        help="Name for the generated temporary config file within the project dir.")
    parser.add_argument("--results-name", type=str, default="batch_results.jsonl",
                        help="Name for the results JSONL file within the output dir.")

    args = parser.parse_args()

    # --- Setup ---
    project_dir = os.path.abspath(args.project_dir)
    target_workspace_abs = os.path.abspath(args.target_workspace) # Ensure target workspace is absolute

    # Determine absolute output directory path
    if args.output_dir:
        if os.path.isabs(args.output_dir):
            output_dir_abs = args.output_dir
        else:
            # Interpret relative path relative to project directory
            output_dir_abs = os.path.abspath(os.path.join(project_dir, args.output_dir))
            # logger is not ready yet, print warning directly
            print(f"WARNING: Received relative output path '{args.output_dir}'. Interpreting it relative to project dir: {output_dir_abs}")
    else:
        # Default if not provided
        output_dir_abs = os.path.join(project_dir, "batch_output") # Default directory name
        # logger is not ready yet, print info directly
        print(f"INFO: No output directory specified, using default: {output_dir_abs}")


    results_file_path = os.path.join(output_dir_abs, args.results_name)
    log_file_path = os.path.join(output_dir_abs, "batch_run.log")

    os.makedirs(output_dir_abs, exist_ok=True) # Create output dir
    logger = setup_logging(log_file_path) # Setup logging after output dir exists

    # Log the paths now that logger is initialized
    if args.output_dir and not os.path.isabs(args.output_dir):
        logger.warning(f"Received relative output path '{args.output_dir}'. Interpreting it relative to project dir: {output_dir_abs}")
    elif not args.output_dir:
        logger.info(f"No output directory specified, using default: {output_dir_abs}")

    logger.info("Starting batch run...")
    logger.info(f"Project Directory: {project_dir}")
    logger.info(f"Target Workspace: {target_workspace_abs}") # Log the target workspace
    logger.info(f"Prompt Directory: {args.prompt_dir}")
    logger.info(f"Output Directory (Absolute): {output_dir_abs}") # Log the absolute path
    logger.info(f"Max Workers: {args.max_workers}")
    logger.info(f"Task Timeout: {args.timeout if args.timeout else 'None'}")

    # Pass target_workspace_abs to create_config_file
    config_file_path = create_config_file(project_dir, output_dir_abs, args.config_name, target_workspace_abs)

    # <<< START MODIFICATION: Use target_workspace_abs for agreement file >>>
    agreement_dir = os.path.join(target_workspace_abs, ".openhands")
    agreement_file = os.path.join(agreement_dir, "agreed_to_terms")

    try:
        os.makedirs(agreement_dir, exist_ok=True)
        if not os.path.exists(agreement_file):
            with open(agreement_file, "w") as f:
                f.write("agreed") # Content doesn't matter, just existence
            logger.info(f"Created agreement file in target workspace: {agreement_file}")
        else:
            logger.info(f"Agreement file already exists in target workspace: {agreement_file}")
    except OSError as e:
        logger.error(f"Failed to create agreement file directory/file at {agreement_dir}: {e}. Batch run might hang if security prompt appears.")
    # <<< END MODIFICATION >>>

    prompt_files = glob.glob(os.path.join(args.prompt_dir, "*.md"))
    logger.info(f"Found {len(prompt_files)} prompt files.")

    if not prompt_files:
        logger.warning("No prompt files found. Exiting.")
        exit()

    # <<< START NEW MODIFICATION: Filter tasks based on batch_results.jsonl >>>
    completed_task_names: set[str] = set()
    if os.path.exists(results_file_path):
        logger.info(f"Checking for completed tasks in {results_file_path}...")
        try:
            with open(results_file_path, "r", encoding='utf-8') as f_results:
                for line_number, line in enumerate(f_results):
                    try:
                        entry = json.loads(line)
                        if "task_name" in entry and "status" in entry and entry["status"] == "success":
                            completed_task_names.add(entry["task_name"])
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed JSON line {line_number + 1} in results file: {line.strip()}")
            logger.info(f"Loaded {len(completed_task_names)} successfully completed task names from {results_file_path}.")
        except Exception as e:
            logger.error(f"Error reading or processing results file {results_file_path}: {e}. Will not skip any tasks based on this file.")
            # Ensure completed_task_names is empty or in a known state if reading fails
            completed_task_names = set()
    else:
        logger.info(f"Results file {results_file_path} not found. No tasks will be skipped based on previous results.")

    tasks_to_run_args = []
    skipped_tasks_count = 0
    logger.info("Filtering tasks based on completion status in results file...")

    for pf in prompt_files:
        current_task_name = os.path.basename(pf) # e.g., Faker_01.md (matches task_name in jsonl)
        if current_task_name in completed_task_names:
            logger.info(f"Skipping task '{current_task_name}' because it is marked as 'success' in {results_file_path}")
            skipped_tasks_count += 1
        else:
            tasks_to_run_args.append((pf, project_dir, config_file_path, args.timeout))

    logger.info(f"Found {len(tasks_to_run_args)} tasks to run. Skipped {skipped_tasks_count} previously completed tasks.")
    # <<< END NEW MODIFICATION >>>

    # <<< START: Remove or comment out file deletion >>>
    # # Clear results file if it exists - REMOVED TO ALLOW APPENDING
    # if os.path.exists(results_file_path):
    #     logger.info(f"Removing existing results file: {results_file_path}")
    #     os.remove(results_file_path)
    logger.info(f"Results will be appended to: {results_file_path}")
    # <<< END: Remove or comment out file deletion >>>

    # Use the filtered list of task arguments
    # tasks_to_run = [(pf, project_dir, config_file_path, args.timeout) for pf in prompt_files]

    # --- Execution ---
    if args.max_workers > 1:
        logger.info(f"Running tasks in parallel with {args.max_workers} workers...")
        # NOTE: Ensure OpenHands runtime (Docker/Local) and system resources
        # can handle parallel execution if max_workers > 1.
        logger.warning("Docker container cleanup is NOT automatically performed between tasks in parallel mode.")
        with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
            # Map future to prompt_file for error reporting
            # Use tasks_to_run_args here
            futures = {executor.submit(run_task, task_args): task_args[0] for task_args in tasks_to_run_args}
            for future in as_completed(futures):
                prompt_file = futures[future] # Get the prompt file associated with this future
                try:
                    result = future.result()
                    save_result(result, results_file_path)
                except Exception as exc:
                    # Log error with correct prompt file context
                    logger.error(f'Task for {prompt_file} generated an exception in executor: {exc}', exc_info=True)
                    error_result = {
                        "task_name": os.path.basename(prompt_file),
                        "prompt_file": prompt_file,
                        "status": "executor_error",
                        "return_code": -1,
                        "elapsed_time_seconds": 0,
                        "stdout": "(Real-time, not captured)", # Match structure
                        "stderr": f"Executor error: {str(exc)}",
                        "total_cost": None,
                        "total_input_tokens": None,
                        "total_output_tokens": None,
                        "total_tokens": None,
                        "cache_read_tokens": None,
                        "cache_write_tokens": None,
                        "session_id": None
                    }
                    save_result(error_result, results_file_path)
    else:
        logger.info("Running tasks serially...")
        for task_args in tasks_to_run_args:
            result = run_task(task_args)
            save_result(result, results_file_path)
            # <<< Call cleanup after each serial task >>>
            cleanup_runtime_containers("openhands-runtime-")
            # Optional: Add a small sleep if cleanup seems too fast
            # time.sleep(2)

    logger.info("-" * 30)
    logger.info(f"Batch processing complete.")
    logger.info(f"Results saved to: {results_file_path}")
    logger.info(f"Log file saved to: {log_file_path}")
    logger.info(f"Trajectories saved in: {os.path.join(output_dir_abs, 'trajectories')}") # Log absolute path

    # --- Cleanup ---
    if os.path.exists(config_file_path):
        logger.info(f"Removing temporary config file: {config_file_path}")
        os.remove(config_file_path)

    logger.info("Batch run completed successfully.") 