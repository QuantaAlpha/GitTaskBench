#!/bin/bash

# SWE-agent Batch Script Configuration Example
# Choose appropriate configuration based on your use case

echo "SWE-agent Batch Script Configuration Example"
echo "================================"
echo ""
echo "Please select configuration based on your use case:"
echo ""

# --- Scenario 1: Parse existing trajectory files (Recommended for cost analysis) ---
echo "🔍 Scenario 1: Parse existing trajectory files and generate cost statistics"
echo "Use case: Already ran SWE-agent, now want to analyze costs"
echo ""
cat << 'EOF'
# Configuration parameters
MODEL_NAME="claude-3-5-sonnet-20241022"
OUTPUT_BASE_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/sweagent_claude_35_output/traj_swe"
USER_NAME=""  # Empty string for direct task name directory structure
SKIP_DOCKER_PRUNE="true"  # Skip Docker cleanup
SKIP_GIT_COMMIT="true"    # Skip Git commit

# Run command
python3 batch_sweagent_run.py \
    --prompt-dir "/path/to/prompts" \
    --model-name "$MODEL_NAME" \
    --output-base-dir "$OUTPUT_BASE_DIR" \
    --user-name "$USER_NAME" \
    --skip-docker-prune \
    --skip-git-commit \
    --workers 1
EOF

echo ""
echo "---"
echo ""

# --- Scenario 2: Run new tasks with cost tracking ---
echo "🚀 Scenario 2: Run new tasks with real-time cost tracking"
echo "Use case: Running new SWE-agent tasks while collecting cost data"
echo ""
cat << 'EOF'
# Configuration parameters
MODEL_NAME="claude-3-5-sonnet-20241022"
OUTPUT_BASE_DIR="trajectories"  # Standard SWE-agent output directory
USER_NAME="batch_user"          # Standard username
SKIP_DOCKER_PRUNE=""            # Enable Docker cleanup
SKIP_GIT_COMMIT=""              # Enable Git commit

# Run command
python3 batch_sweagent_run.py \
    --prompt-dir "/path/to/prompts" \
    --model-name "$MODEL_NAME" \
    --image "sweagent/swe-agent:latest" \
    --repo-path "/path/to/repo" \
    --config-path "/path/to/config.yaml" \
    --host-repo-path "/path/to/host/repo" \
    --output-base-dir "$OUTPUT_BASE_DIR" \
    --user-name "$USER_NAME" \
    --workers 1
EOF

echo ""
echo "---"
echo ""

# --- Scenario 3: GPT model configuration ---
echo "🤖 Scenario 3: Using GPT models"
echo "Use case: Using OpenAI GPT models instead of Claude"
echo ""
cat << 'EOF'
# Configuration parameters
MODEL_NAME="gpt-4o"
OUTPUT_BASE_DIR="trajectories"
USER_NAME="batch_user"

# Run command (other parameters remain same)
python3 batch_sweagent_run.py \
    --model-name "$MODEL_NAME" \
    --output-base-dir "$OUTPUT_BASE_DIR" \
    --user-name "$USER_NAME" \
    # ... other parameters
EOF

echo ""
echo "---"
echo ""

# --- Scenario 4: Custom trajectory file locations ---
echo "📁 Scenario 4: Custom trajectory file locations"
echo "Use case: Trajectory files stored in non-standard locations"
echo ""
cat << 'EOF'
# Configuration parameters
OUTPUT_BASE_DIR="/custom/path/to/trajectories"
USER_NAME="custom_user"  # Or leave empty ""

# Directory structure example:
# /custom/path/to/trajectories/
# ├── TaskName1/
# │   └── hash1/
# │       └── hash1.traj
# ├── TaskName2/
# │   └── hash2/
# │       └── hash2.traj
# Or
# /custom/path/to/trajectories/custom_user/
# ├── model-TaskName1/
# │   └── model-TaskName1.traj
# ├── model-TaskName2/
# │   └── model-TaskName2.traj
EOF

echo ""
echo "---"
echo ""

echo "💡 Tips:"
echo "1. For first-time use, try Scenario 1 to test trajectory file parsing"
echo "2. OUTPUT_BASE_DIR should point to directory containing trajectory files"
echo "3. Set USER_NAME according to your directory structure (may be empty)"
echo "4. Check batch_results.jsonl file for cost statistics after running"
echo ""
echo "🔧 Current default configuration (run_batch.sh) uses Scenario 1 settings"