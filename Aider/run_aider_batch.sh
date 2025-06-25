#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Set HTTP/HTTPS proxy for this script and all child processes
# Ensure this is the correct way to set the proxy for your environment and tools.
if command -v curl &> /dev/null; then
    PROXY_CMD=$(curl -s http://deploy.i.shaipower.com/httpproxy)
    if [ -n "$PROXY_CMD" ]; then
        eval "$PROXY_CMD"
        echo "Proxy set via curl command."
    else
        echo "Warning: curl command for proxy did not return a command."
    fi
else
    echo "Warning: curl command not found, cannot set proxy automatically."
fi

# --- Configuration ---
# Directory containing the .md problem statement files
# Example: MD_PROMPT_DIR="/path/to/your/md_prompts"
MD_PROMPT_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt" # MODIFY THIS if needed

# Path to the Python batch script for Aider MD processing
PYTHON_SCRIPT_AIDER_BATCH="/data/code/agent_new/aider/md_batch_runner.py" # Ensure this path is correct

# --- Aider Parameters (Modify as needed) ---
# Default model for Aider, can be overridden by md_batch_runner.py's default or command-line arg
AIDER_MODEL_NAME="stepfun/gpt-4o" 

# Base output directory for all batch runs (each batch run will create a timestamped subfolder here)
BATCH_OUTPUT_DIR_BASE="/data/code/agent_new/aider/aider_batch_runs_output" # MODIFY THIS if needed

# --- Batch Script Parameters ---
# Set to "true" to keep task-specific workdirs created by md_batch_runner.py
# These workdirs store logs/meta for each task's run.
KEEP_TASK_WORKDIR="false" 

# Optional: Specify a comma-separated list of task names (MD filenames without .md extension) to run.
# If empty or not set, all tasks in MD_PROMPT_DIR will be run.
# Example: TASKS_TO_RUN="AnimeGANv3_01,Faker_02"
TASKS_TO_RUN=""

# Logging level for the md_batch_runner.py script (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL="DEBUG"

# Optional: Extra arguments to pass to aider itself
# Add --yes for non-interactive execution. Enclose in quotes if multiple args.
AIDER_EXTRA_ARGS="--yes"

# --- Argument Construction for md_batch_runner.py ---
ARGS=()
ARGS+=("--md-prompt-dir" "$MD_PROMPT_DIR")
ARGS+=("--output-dir" "$BATCH_OUTPUT_DIR_BASE") # md_batch_runner.py will create a timestamped subdir
ARGS+=("--model" "$AIDER_MODEL_NAME")
ARGS+=("--log-level" "$LOG_LEVEL")

if [[ -n "$AIDER_EXTRA_ARGS" ]]; then
    ARGS+=("--aider-args=$AIDER_EXTRA_ARGS") # Use --option=value format
fi

if [[ "$KEEP_TASK_WORKDIR" == "true" ]]; then
    ARGS+=("--keep-workdirs")
fi

if [[ -n "$TASKS_TO_RUN" ]]; then
    ARGS+=("--tasks" "$TASKS_TO_RUN")
fi

# --- Execution ---
echo "🚀 Starting Aider batch run from MD files..."
echo "--------------------------------------------------"
echo "Python Script       : $PYTHON_SCRIPT_AIDER_BATCH"
echo "MD Prompt Directory : $MD_PROMPT_DIR"
echo "Aider Model         : $AIDER_MODEL_NAME"
echo "Base Output Dir     : $BATCH_OUTPUT_DIR_BASE"
echo "Log Level           : $LOG_LEVEL"
if [[ -n "$AIDER_EXTRA_ARGS" ]]; then
    echo "Aider Extra Args    : $AIDER_EXTRA_ARGS"
fi
if [[ "$KEEP_TASK_WORKDIR" == "true" ]]; then
    echo "Keep Task Workdirs  : ENABLED"
else
    echo "Keep Task Workdirs  : DISABLED (will clean up on failure/default)"
fi
if [[ -n "$TASKS_TO_RUN" ]]; then
    echo "Specific Tasks      : $TASKS_TO_RUN"
fi
echo "--------------------------------------------------"

# Create the base output directory if it doesn't exist
mkdir -p "$BATCH_OUTPUT_DIR_BASE"

# Ensure the Python script is executable (optional, as we call it with python3)
# chmod +x "$PYTHON_SCRIPT_AIDER_BATCH"

# Execute the Python script with all arguments
python3 "$PYTHON_SCRIPT_AIDER_BATCH" "${ARGS[@]}"

EXIT_CODE=$?

echo "--------------------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Aider MD batch run script finished successfully."
else
    echo "⚠️ Aider MD batch run script finished with errors (Exit Code: $EXIT_CODE)."
fi
echo "📊 Check subdirectories in $BATCH_OUTPUT_DIR_BASE for detailed results and logs."
echo "--------------------------------------------------"

exit $EXIT_CODE 