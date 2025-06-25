#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Set HTTP/HTTPS proxy for this script and all child processes
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
MD_PROMPT_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt" # MODIFY THIS if needed

# Path to the Python batch script for Aider MD processing
PYTHON_SCRIPT_AIDER_BATCH="/data/code/agent_new/aider/md_batch_runner.py" # Ensure this path is correct

# --- Aider & LiteLLM Parameters (Modify as needed) ---
# Model name for Aider, which will be passed to LiteLLM.
# For LiteLLM, this might include a provider prefix if necessary (e.g., "custom_openai/my_model").
# If your base_url serves a model directly by its name, this can be just the model name.
AIDER_MODEL_NAME="openai/deepseek-v3" # Example, use the model name LiteLLM expects

# --- LiteLLM Specific Configuration (IMPORTANT: REPLACE PLACEHOLDERS) ---
# API Key for the LLM provider. This will be set as OPENAI_API_KEY environment variable for the Python script.
LLM_API_KEY="" # <<< REPLACE WITH YOUR ACTUAL API KEY or load from a secure source

# Base URL for the LLM API. This will be set as OPENAI_API_BASE environment variable.
LLM_BASE_URL="https://models-proxy.stepfun-inc.com/v1" # <<< REPLACE WITH YOUR LLM'S BASE URL

# Base output directory for all batch runs
BATCH_OUTPUT_DIR_BASE="/data/code/agent_new/aider/aider_batch_runs_litellm_output" # MODIFY THIS if needed

# --- Batch Script Parameters ---
KEEP_TASK_WORKDIR="false"
TASKS_TO_RUN="" # Example: "Task_01,Task_02"
LOG_LEVEL="DEBUG"
AIDER_EXTRA_ARGS="--yes-always" # Add other Aider specific args here like "--show-diff"

# --- Argument Construction for md_batch_runner.py ---
ARGS=()
ARGS+=("--md-prompt-dir" "$MD_PROMPT_DIR")
ARGS+=("--output-dir" "$BATCH_OUTPUT_DIR_BASE")
ARGS+=("--model" "$AIDER_MODEL_NAME") # This is the model name Aider will use with LiteLLM
ARGS+=("--log-level" "$LOG_LEVEL")

# Add LiteLLM specific args
if [[ -n "$LLM_API_KEY" && "$LLM_API_KEY" != "YOUR_API_KEY_HERE" ]]; then
    ARGS+=("--llm-api-key" "$LLM_API_KEY")
else
    echo "Warning: LLM_API_KEY is not set or is still the placeholder. The script might rely on Aider's default LiteLLM configuration or other environment variables."
fi

if [[ -n "$LLM_BASE_URL" && "$LLM_BASE_URL" != "https://your_llm_base_url_here/v1" ]]; then # Adjusted placeholder check
    ARGS+=("--llm-base-url" "$LLM_BASE_URL")
else
    echo "Warning: LLM_BASE_URL is not set or is still a placeholder. The script might rely on Aider's default LiteLLM configuration or other environment variables."
fi

if [[ -n "$AIDER_EXTRA_ARGS" ]]; then
    ARGS+=("--aider-args=$AIDER_EXTRA_ARGS")
fi

if [[ "$KEEP_TASK_WORKDIR" == "true" ]]; then
    # Corrected argument name based on md_batch_runner.py which seems to expect --keep-meta-workdirs
    ARGS+=("--keep-meta-workdirs")
fi

if [[ -n "$TASKS_TO_RUN" ]]; then
    ARGS+=("--tasks" "$TASKS_TO_RUN")
fi

# --- Execution ---
echo "🚀 Starting Aider batch run from MD files (with LiteLLM custom_config)..."
echo "--------------------------------------------------"
echo "Python Script       : $PYTHON_SCRIPT_AIDER_BATCH"
echo "MD Prompt Directory : $MD_PROMPT_DIR"
echo "Aider/LiteLLM Model : $AIDER_MODEL_NAME"
echo "LLM API Key         : $([[ -n "$LLM_API_KEY" && "$LLM_API_KEY" != "YOUR_API_KEY_HERE" ]] && echo "Provided (Hidden)" || echo "Not Provided or Placeholder")"
echo "LLM Base URL        : $LLM_BASE_URL"
echo "Base Output Dir     : $BATCH_OUTPUT_DIR_BASE"
echo "Log Level           : $LOG_LEVEL"
if [[ -n "$AIDER_EXTRA_ARGS" ]]; then
    echo "Aider Extra Args    : $AIDER_EXTRA_ARGS"
fi
if [[ "$KEEP_TASK_WORKDIR" == "true" ]]; then
    echo "Keep Task Workdirs  : ENABLED"
else
    # Based on md_batch_runner.py's logic, it cleans successful task workdirs if not keep, and failed ones if not keep.
    echo "Keep Task Workdirs  : DISABLED (meta workdirs might be cleaned up by the Python script based on its logic)"
fi
if [[ -n "$TASKS_TO_RUN" ]]; then
    echo "Specific Tasks      : $TASKS_TO_RUN"
fi
echo "--------------------------------------------------"
echo "Full command to be executed (Python script + args):"
echo "python3 "$PYTHON_SCRIPT_AIDER_BATCH" ${ARGS[*]}" # Using [*] for quoting safety with spaces in args
echo "--------------------------------------------------"


# Create the base output directory if it doesn't exist
mkdir -p "$BATCH_OUTPUT_DIR_BASE"

# Execute the Python script with all arguments
python3 "$PYTHON_SCRIPT_AIDER_BATCH" "${ARGS[@]}"

EXIT_CODE=$?

echo "--------------------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Aider MD batch run script (LiteLLM config) finished successfully."
else
    echo "⚠️ Aider MD batch run script (LiteLLM config) finished with errors (Exit Code: $EXIT_CODE)."
fi
echo "📊 Check subdirectories in $BATCH_OUTPUT_DIR_BASE for detailed results and logs."
echo "--------------------------------------------------"

exit $EXIT_CODE 