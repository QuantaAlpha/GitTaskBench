# OpenHands Batch Execution Script (`run_batch.py`)

This script facilitates running multiple OpenHands tasks in batch mode using prompt files, without requiring the frontend UI.

## Features

*   **Batch Processing:** Executes OpenHands tasks based on multiple `.md` prompt files found in a specified directory.
*   **Serial Execution (Default):** Runs tasks one by one to manage resource consumption (configurable for parallel execution).
*   **Trajectory Saving:** Automatically configures OpenHands to save the execution trajectory for each task.
*   **Logging & Metrics:** Records execution time, final status, stdout/stderr, and attempts to parse total token count and cost from the OpenHands CLI output.
*   **Configurable Output:** Allows specifying an absolute or relative path for all outputs (results, logs, trajectories).
*   **Task Timeout:** Optional timeout setting for individual tasks.

## Prerequisites

1.  **OpenHands Project:** This script should be placed within the root directory of your OpenHands project (`/data/code/agent_new/OpenHands/` in this case).
2.  **Poetry:** The project dependencies must be installed using Poetry (`poetry install`).
3.  **Prompt Files:** A directory containing `.md` files, where each file contains the prompt for a single OpenHands task.
4.  **OpenHands Configuration (Potentially):** While the script generates a temporary config (`batch_config.toml`) to manage trajectory saving, you might need to ensure your main `config.toml` or environment variables have the necessary LLM API keys set up, unless you modify `batch_config.toml` directly after its first creation.

## Configuration & Usage

Run the script from the OpenHands project root directory using `poetry`:

```bash
poetry run python run_batch.py [OPTIONS]
```

**Command-line Options:**

*   `--prompt-dir`: Path to the directory containing your `.md` prompt files.
    *   Default: `/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt`
*   `--project-dir`: Path to the OpenHands project directory (where `poetry.lock` is).
    *   Default: `/data/code/agent_new/OpenHands`
*   `--output-dir`: Directory to save all outputs (results, logs, trajectories). Can be an absolute path or a path relative to the `--project-dir`. If omitted, defaults to `batch_output` inside the project directory.
    *   Example (Absolute): `--output-dir /mnt/data/my_batch_results`
    *   Example (Relative): `--output-dir custom_run_outputs` (becomes `<project_dir>/custom_run_outputs`)
*   `--max-workers`: Number of tasks to run in parallel. **Defaults to 1 (serial execution)** due to potential high memory usage of OpenHands.
    *   *Caution:* Increasing this value requires sufficient system resources (CPU, RAM) and may depend on the chosen OpenHands runtime (Docker vs. Local).
*   `--timeout`: Maximum time in seconds allowed for each individual task before it's terminated. (Optional)
    *   Example: `--timeout 1800` (30 minutes)
*   `--config-name`: Name for the temporary configuration file generated within the project directory.
    *   Default: `batch_config.toml`
*   `--results-name`: Name for the JSON Lines results file generated within the output directory.
    *   Default: `batch_results.jsonl`

**Important Runtime Note:**

The script uses OpenHands' default runtime, which is typically **Docker**. If you need to use a different runtime (e.g., `local` to run directly on the host), you need to configure it. The easiest way is to **run the script once**, let it generate the `batch_config.toml` file in the project directory, then **edit that file** to uncomment and set `runtime = "local"` (or other desired runtime) within the `[core]` section before running the script again.

```toml
# Example batch_config.toml modification
[core]
save_trajectory_path = "/path/to/your/output/trajectories"
runtime = "local" # Changed from default docker

#[llm]
# ... (Optionally configure LLM details here too)
```

## Examples

**1. Run with all default settings (serial execution, default directories):**

```bash
poetry run python run_batch.py
```
*   Uses prompts from `/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt`.
*   Outputs results to `/data/code/agent_new/OpenHands/batch_output`.
*   Runs tasks one by one.
*   Uses Docker runtime unless `batch_config.toml` is modified.

**2. Specify an absolute output directory:**

```bash
poetry run python run_batch.py --output-dir /mnt/shared/openhands_batch_may_24
```
*   Outputs results, logs, and trajectories to `/mnt/shared/openhands_batch_may_24`.

**3. Specify a different prompt directory, relative output, and a timeout:**

```bash
poetry run python run_batch.py \
    --prompt-dir ./my_special_prompts \
    --output-dir run_results_set_1 \
    --timeout 3600
```
*   Uses prompts from `/data/code/agent_new/OpenHands/my_special_prompts`.
*   Outputs results to `/data/code/agent_new/OpenHands/run_results_set_1`.
*   Sets a 1-hour timeout for each task.

**4. Run tasks in parallel (use with caution):**

```bash
# Ensure you have enough RAM/CPU and Docker resources
poetry run python run_batch.py --max-workers 4
```
*   Attempts to run up to 4 tasks concurrently.

**5. Run using local runtime (after modifying `batch_config.toml`):**

```bash
# Step 1: Run once to generate config
# poetry run python run_batch.py
# Step 2: Edit <project_dir>/batch_config.toml, uncomment and set runtime = "local"
# Step 3: Run again
poetry run python run_batch.py --output-dir /data/local_run_results
```

## Output Files

The script generates the following files in the specified `--output-dir`:

1.  **`batch_results.jsonl`**: A JSON Lines file where each line is a JSON object containing the results for a single task. Includes:
    *   `task_name`: Base name of the prompt file.
    *   `prompt_file`: Full path to the prompt file.
    *   `status`: `success`, `failed`, `timeout`, or `error`.
    *   `return_code`: Exit code from the OpenHands process.
    *   `elapsed_time_seconds`: Task duration.
    *   `stdout`: Standard output from the OpenHands process.
    *   `stderr`: Standard error from the OpenHands process.
    *   `total_cost`, `total_input_tokens`, `total_output_tokens`: Parsed metrics (if available in stdout).
2.  **`batch_run.log`**: A log file detailing the script's execution steps, including task start/end times, status, and any errors during the batch process itself.
3.  **`trajectories/`**: A subdirectory containing the saved trajectory files (`.json`) generated by OpenHands for each successfully completed task (filename usually corresponds to the session ID).

**Note:** The temporary configuration file (`batch_config.toml` by default) is created in the project directory during the run and removed upon completion. 


python3 run_batch.py --output-dir /data/data/agent_test_codebase/GitTaskBench/eval_automation/output 