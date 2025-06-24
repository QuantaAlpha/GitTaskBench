#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# !!! IMPORTANT: Set this to the absolute path of your Git repository on the HOST machine !!!
# Example: HOST_REPO_PATH="/home/user/my_project_repo"
HOST_REPO_PATH="/data/data/agent_test_codebase/GitTaskBench" # MODIFY THIS

# Directory containing the .md problem statement files
PROMPT_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt"

# Path to the Python batch script
PYTHON_SCRIPT="/data/code/agent_new/SWE-agent/batch_sweagent_run.py"

# --- SWE-agent Parameters (Modify as needed) ---
MODEL_NAME="openai/claude-3-5-sonnet-20241022"
# Find your image ID using 'docker images | grep sweagent'
# Example: DOCKER_IMAGE="sweagent/swe-agent:latest" or "3eb72bc4a848"
DOCKER_IMAGE="3eb72bc4a848" # MODIFY THIS if necessary
REPO_PATH_IN_CONTAINER="/data/data/agent_test_codebase/GitTaskBench" # Path inside the container

# 定义默认和自定义的配置文件路径
DEFAULT_CONFIG_FILE="/data/code/agent_new/SWE-agent/config/default.yaml"
CUSTOM_TIMEOUTS_CONFIG_FILE="/data/code/agent_new/SWE-agent/config/default.yaml"

# --- Batch Script Parameters ---
# Set to 1 for sequential post-task actions (recommended for Docker/Git safety)
NUM_WORKERS=1
# Sleep duration in seconds after each task's cleanup
SLEEP_DURATION=20
# Set to "true" to skip docker prune, leave empty or comment out to enable prune
SKIP_DOCKER_PRUNE="false"
# Set to "true" to skip git commit, leave empty or comment out to enable commit
SKIP_GIT_COMMIT="false"
# Logging level for the script (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL="INFO"

# --- Trajectory File Parameters (NEW) ---
# Base directory where SWE-agent trajectory files are stored
# This should point to where your existing trajectory files are located
OUTPUT_BASE_DIR="/data/code/agent_new/SWE-agent/trajectories"
# Username used in the trajectory path structure (empty for direct task name structure)
USER_NAME="youwang-claude35"  # Actual username from SWE-agent output

# --- Argument Construction ---
ARGS=(
    "--prompt-dir" "$PROMPT_DIR"
    "--host-repo-path" "$HOST_REPO_PATH"
    "--workers" "$NUM_WORKERS"
    "--sleep-duration" "$SLEEP_DURATION"
    "--log-level" "$LOG_LEVEL"
    # SWE-agent specific args
    "--model-name" "$MODEL_NAME"
    "--image" "$DOCKER_IMAGE"
    "--repo-path" "$REPO_PATH_IN_CONTAINER"
    # 传递两个配置文件给 --config-path
    # 注意：确保 batch_sweagent_run.py 的 --config-path 参数已修改为 nargs='+'
    "--config-path" "$DEFAULT_CONFIG_FILE" "$CUSTOM_TIMEOUTS_CONFIG_FILE"
    # Trajectory file parsing args (NEW)
    "--output-base-dir" "$OUTPUT_BASE_DIR"
    "--user-name" "$USER_NAME"
)

# Add optional flags if set
if [[ -n "$SKIP_DOCKER_PRUNE" && "$SKIP_DOCKER_PRUNE" == "true" ]]; then
    ARGS+=("--skip-docker-prune")
fi

if [[ -n "$SKIP_GIT_COMMIT" && "$SKIP_GIT_COMMIT" == "true" ]]; then
    ARGS+=("--skip-git-commit")
fi


# --- Execution ---
echo "Starting SWE-agent batch run with custom timeouts and cost tracking..."
echo "Python Script: $PYTHON_SCRIPT"
echo "Host Repo Path (for Git): $HOST_REPO_PATH"
echo "Prompt Directory: $PROMPT_DIR"
echo "Workers: $NUM_WORKERS"
echo "Sleep Duration: $SLEEP_DURATION"
echo "Log Level: $LOG_LEVEL"
echo "SWE-agent Model: $MODEL_NAME"
echo "SWE-agent Image: $DOCKER_IMAGE"
echo "SWE-agent Repo Path (Container): $REPO_PATH_IN_CONTAINER"
echo "SWE-agent Default Config: $DEFAULT_CONFIG_FILE"
echo "SWE-agent Custom Config (Timeouts): $CUSTOM_TIMEOUTS_CONFIG_FILE"
[[ -n "$SKIP_DOCKER_PRUNE" && "$SKIP_DOCKER_PRUNE" == "true" ]] && echo "Docker Prune: SKIPPED"
[[ -n "$SKIP_GIT_COMMIT" && "$SKIP_GIT_COMMIT" == "true" ]] && echo "Git Commit: SKIPPED"
echo "Trajectory Base Dir (for new tasks): $OUTPUT_BASE_DIR/$USER_NAME"
echo "User for directory structure: $USER_NAME"
echo "---"
echo "🔍 This script will parse trajectory files and generate cost statistics."
echo "📊 For new tasks, trajectories will be saved under $OUTPUT_BASE_DIR/$USER_NAME/<model-task_id>/<problem_id>/"
echo "📄 Results will be saved to $OUTPUT_BASE_DIR/$USER_NAME/batch_results.jsonl"
echo "---"


# Ensure the script is executable (optional, but good practice)
# chmod +x $PYTHON_SCRIPT

# Execute the Python script with all arguments
python3 "$PYTHON_SCRIPT" "${ARGS[@]}"

echo "---"
echo "✅ Batch run script finished."
echo "📊 Check $OUTPUT_BASE_DIR/$USER_NAME/batch_results.jsonl for detailed cost statistics including:"
echo "   - instance_cost: 每个任务的实例成本"
echo "   - tokens_sent: 发送的令牌数"
echo "   - tokens_received: 接收的令牌数"
echo "   - api_calls: API调用次数"
