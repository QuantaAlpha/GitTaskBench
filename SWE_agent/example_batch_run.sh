#!/bin/bash

# Example: Using the improved batch_sweagent_run.py script
# The script now supports trajectory file parsing and cost statistics

# Set base parameters
PROMPT_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt"
MODEL_NAME="claude-3-5-sonnet-20241022"
IMAGE="sweagent/swe-agent:latest"
REPO_PATH="/data/data/agent_test_codebase/GitTaskBench"
CONFIG_PATH="/data/code/agent_new/SWE-agent/config/default.yaml"
HOST_REPO_PATH="/data/data/agent_test_codebase/GitTaskBench"

# Trajectory file related parameters
OUTPUT_BASE_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/sweagent_claude_35_output/traj_swe"
USER_NAME=""  # The username is empty in this structure

# Run batch script
python3 batch_sweagent_run.py \
    --prompt-dir "$PROMPT_DIR" \
    --model-name "$MODEL_NAME" \
    --image "$IMAGE" \
    --repo-path "$REPO_PATH" \
    --config-path "$CONFIG_PATH" \
    --host-repo-path "$HOST_REPO_PATH" \
    --output-base-dir "$OUTPUT_BASE_DIR" \
    --user-name "$USER_NAME" \
    --workers 1 \
    --sleep-duration 5 \
    --skip-docker-prune \
    --skip-git-commit \
    --log-level INFO

echo "Batch run completed!"
echo "Results have been saved to the batch_results.jsonl file"
echo "This file contains cost statistics for each task, including:"
echo "- instance_cost: instance cost"
echo "- tokens_sent: number of tokens sent"
echo "- tokens_received: number of tokens received"
echo "- api_calls: number of API calls"