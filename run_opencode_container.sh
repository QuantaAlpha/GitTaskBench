#!/bin/bash
# =============================================================================
# OpenCode Container Runner for GitTaskBench
# =============================================================================
#
# Runs OpenCode tasks in isolated Docker containers with:
# - True isolation between tasks (repo copied INTO container, changes discarded)
# - Full conversation logging in markdown format
# - Token tracking for summary.json
# - Resume support (skip completed tasks)
#
# Usage:
#   ./run_opencode_container.sh              # Run all tasks
#   ./run_opencode_container.sh --single     # Run only first task (for testing)
#   ./run_opencode_container.sh --tasks AnimeGANv3_01,AnimeGANv3_02
#   ./run_opencode_container.sh --build      # Force rebuild Docker image
#   ./run_opencode_container.sh --force-rerun  # Re-run completed tasks
#
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# Configuration
# =============================================================================

MODEL="${MODEL:-opencode/kimi-k2.5-free}"
TIMEOUT="${TIMEOUT:-3600}"
QUERIES_DIR="${QUERIES_DIR:-./queries}"
OUTPUT_DIR="${OUTPUT_DIR:-./results/opencode}"
IMAGE="${IMAGE:-gittaskbench/opencode-runner:latest}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"

# =============================================================================
# Parse arguments
# =============================================================================

TASKS=""
FORCE_BUILD=false
FORCE_RERUN=false
SINGLE_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --tasks)
            TASKS="$2"
            shift 2
            ;;
        --single)
            SINGLE_MODE=true
            shift
            ;;
        --build)
            FORCE_BUILD=true
            shift
            ;;
        --force-rerun)
            FORCE_RERUN=true
            shift
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --single          Run only the first task (for testing)"
            echo "  --tasks LIST      Comma-separated list of task IDs"
            echo "  --build           Force rebuild Docker image"
            echo "  --force-rerun     Force re-run of completed tasks"
            echo "  --model MODEL     Model to use (default: $MODEL)"
            echo "  --timeout SECS    Per-task timeout (default: $TIMEOUT)"
            echo "  --help, -h        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Pre-flight checks
# =============================================================================

echo "============================================================"
echo "OpenCode Container Runner for GitTaskBench"
echo "============================================================"
echo ""

# Check Docker
if ! docker info &>/dev/null; then
    echo "ERROR: Docker is not running"
    exit 1
fi
echo "Docker: OK"

# Check jq
if ! command -v jq &>/dev/null; then
    echo "ERROR: jq is required but not installed"
    exit 1
fi
echo "jq: OK"

# Check python3
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required but not installed"
    exit 1
fi
echo "python3: OK"

# Check queries directory
if [ ! -d "$QUERIES_DIR" ]; then
    echo "ERROR: Queries directory not found: $QUERIES_DIR"
    exit 1
fi

# Count tasks (directories with query.json)
TASK_COUNT=$(find "$QUERIES_DIR" -maxdepth 2 -name "query.json" 2>/dev/null | wc -l | tr -d ' ')
echo "Tasks found: $TASK_COUNT"

echo ""
echo "Configuration:"
echo "  Model:       $MODEL"
echo "  Timeout:     ${TIMEOUT}s per task"
echo "  Queries dir: $QUERIES_DIR"
echo "  Output dir:  $OUTPUT_DIR"
echo "  Image:       $IMAGE"
echo ""

# =============================================================================
# Build Docker image if needed
# =============================================================================

if [ "$FORCE_BUILD" = true ] || ! docker image inspect "$IMAGE" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE" "$SCRIPT_DIR/docker/opencode-runner/"
    echo ""
fi

# =============================================================================
# Prepare output directories
# =============================================================================

mkdir -p "$OUTPUT_DIR"

# Initialize or load summary
SUMMARY_FILE="$OUTPUT_DIR/summary.json"
RUN_ID="opencode_$(date +%Y-%m-%d_%H-%M-%S)"
STARTED_AT=$(date -Iseconds)

if [ ! -f "$SUMMARY_FILE" ] || [ "$FORCE_RERUN" = true ]; then
    cat > "$SUMMARY_FILE" << EOF
{
  "run_id": "$RUN_ID",
  "model": "$MODEL",
  "started_at": "$STARTED_AT",
  "updated_at": "$STARTED_AT",
  "tasks": {},
  "summary": {
    "total": 0,
    "completed": 0,
    "failed": 0,
    "skipped": 0,
    "timeout": 0,
    "total_tokens": {
      "input": 0,
      "output": 0,
      "reasoning": 0
    }
  }
}
EOF
fi

# =============================================================================
# Get list of tasks to run
# =============================================================================

if [ -n "$TASKS" ]; then
    # Specific tasks
    TASK_LIST=$(echo "$TASKS" | tr ',' '\n')
elif [ "$SINGLE_MODE" = true ]; then
    # First task only (find first directory with query.json)
    TASK_LIST=$(find "$QUERIES_DIR" -maxdepth 2 -name "query.json" 2>/dev/null | head -1 | xargs -I{} dirname {} | xargs -I{} basename {})
    echo "Single mode: Running only task '$TASK_LIST'"
else
    # All tasks (directories containing query.json)
    TASK_LIST=$(find "$QUERIES_DIR" -maxdepth 2 -name "query.json" 2>/dev/null | xargs -I{} dirname {} | xargs -I{} basename {} | sort)
fi

# =============================================================================
# Collect API keys to pass to container
# =============================================================================

get_api_key_envs() {
    local envs=""
    for KEY in OPENCODE_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY GOOGLE_API_KEY; do
        if [ -n "${!KEY}" ]; then
            envs="$envs -e $KEY=${!KEY}"
        fi
    done
    echo "$envs"
}

API_KEY_ENVS=$(get_api_key_envs)

# =============================================================================
# Generate prompt with container paths from query.json
# =============================================================================

generate_container_prompt() {
    local TASK_ID="$1"
    local QUERY_JSON="$QUERIES_DIR/$TASK_ID/query.json"
    
    if [ ! -f "$QUERY_JSON" ]; then
        echo "ERROR: Query file not found: $QUERY_JSON" >&2
        return 1
    fi
    
    # Extract fields from query.json using jq
    local TASK_DESC=$(jq -r '.task_description // "No description"' "$QUERY_JSON")
    local REPO_NAME=$(jq -r '.repositories[0].name // "unknown"' "$QUERY_JSON")
    local REPO_URL=$(jq -r '.repositories[0].url // ""' "$QUERY_JSON")
    local GUIDELINES=$(jq -r '.repositories[0].understanding_guidelines // []' "$QUERY_JSON")
    local PROMPT_FILE_REL=$(jq -r '.prompt_file // ""' "$QUERY_JSON")
    
    # Generate input files section with container paths
    local INPUT_SECTION=""
    local INPUT_COUNT=$(jq -r '.file_paths.input_files | length' "$QUERY_JSON")
    if [ "$INPUT_COUNT" -gt 0 ] 2>/dev/null; then
        for i in $(seq 0 $((INPUT_COUNT - 1))); do
            local ORIG_PATH=$(jq -r ".file_paths.input_files[$i].path" "$QUERY_JSON")
            local FILENAME=$(basename "$ORIG_PATH")
            local DESC=$(jq -r ".file_paths.input_files[$i].description // \"\"" "$QUERY_JSON")
            INPUT_SECTION+="文件路径 (绝对): /inputs/$FILENAME
文件描述: $DESC

"
        done
    fi
    
    # Read supplemental prompt file
    local PROMPT_ADDITION=""
    if [ -n "$PROMPT_FILE_REL" ] && [ "$PROMPT_FILE_REL" != "null" ]; then
        # Remove /GitTaskBench prefix if present and resolve relative to SCRIPT_DIR
        local PROMPT_FILE_ABS="$SCRIPT_DIR${PROMPT_FILE_REL#/GitTaskBench}"
        if [ -f "$PROMPT_FILE_ABS" ]; then
            PROMPT_ADDITION=$(cat "$PROMPT_FILE_ABS")
        fi
    fi
    
    # Generate the prompt with container paths
    cat << EOF
## 任务描述
$TASK_DESC

## 可用仓库
仓库名称: $REPO_NAME
仓库路径 (绝对): /workspace
仓库URL: $REPO_URL
理解指南: $GUIDELINES

## 文件路径
输入：
${INPUT_SECTION:-无输入文件信息。}
输出：
输出文件目录:/workspace, 如果只有一个文件，就以 \`output.xxx\` 命名; 如果存在多个以 \`output_01.xxx\`开始命名，后缀\`.xxx\`即输出文件的格式，根据任务给定的要求或需求确定。

## 补充说明
$PROMPT_ADDITION
EOF
}

# =============================================================================
# Process each task
# =============================================================================

TOTAL_TASKS=$(echo "$TASK_LIST" | wc -l | tr -d ' ')
CURRENT=0
COMPLETED=0
FAILED=0
SKIPPED=0
TIMED_OUT=0
TOTAL_INPUT=0
TOTAL_OUTPUT=0
TOTAL_REASONING=0

for TASK_ID in $TASK_LIST; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "============================================================"
    echo "[$CURRENT/$TOTAL_TASKS] Task: $TASK_ID"
    echo "============================================================"
    
    QUERY_FILE="$QUERIES_DIR/${TASK_ID}/query.json"
    
    if [ ! -f "$QUERY_FILE" ]; then
        echo "WARNING: Query file not found: $QUERY_FILE"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi
    
    # Check if already completed (resume support)
    if [ "$FORCE_RERUN" != true ]; then
        PREV_STATUS=$(jq -r ".tasks[\"$TASK_ID\"].status // \"\"" "$SUMMARY_FILE" 2>/dev/null || echo "")
        if [ "$PREV_STATUS" = "success" ]; then
            echo "Skipping (status: $PREV_STATUS)"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    fi
    
    # Extract repo path from query.json (host path for copying)
    REPO_PATH_REL=$(jq -r '.repositories[0].path // ""' "$QUERY_FILE")
    # Remove /GitTaskBench prefix and resolve relative to SCRIPT_DIR
    REPO_PATH="$SCRIPT_DIR${REPO_PATH_REL#/GitTaskBench}"
    
    if [ -z "$REPO_PATH" ] || [ ! -d "$REPO_PATH" ]; then
        echo "ERROR: Repo path not found or invalid: $REPO_PATH"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    REPO_NAME=$(basename "$REPO_PATH")
    echo "Repo: $REPO_NAME ($REPO_PATH)"
    
    # Create task output directory
    TASK_OUTPUT_DIR="$OUTPUT_DIR/$TASK_ID"
    mkdir -p "$TASK_OUTPUT_DIR"
    
    # Create temp directory for container output extraction
    TEMP_OUTPUT=$(mktemp -d)
    
    # =========================================================================
    # TRUE ISOLATION: docker create + docker cp pattern
    # =========================================================================
    
    CONTAINER_NAME="opencode-${TASK_ID}-$$"
    
    echo "Creating container..."
    
    # 1. Create container (not started)
    docker create \
        --name "$CONTAINER_NAME" \
        -e TASK_ID="$TASK_ID" \
        -e MODEL="$MODEL" \
        -e TASK_TIMEOUT="$TIMEOUT" \
        -e PYTHON_VERSION="$PYTHON_VERSION" \
        $API_KEY_ENVS \
        "$IMAGE" \
        > /dev/null
    
    # 2. Copy repo INTO container (true isolation)
    echo "Copying repo into container..."
    docker cp "$REPO_PATH/." "$CONTAINER_NAME:/workspace/"
    
    # 3. Generate and copy prompt file with container paths
    TEMP_PROMPT=$(mktemp)
    INPUT_DIR="$QUERIES_DIR/${TASK_ID}/input"
    generate_container_prompt "$TASK_ID" > "$TEMP_PROMPT"
    docker cp "$TEMP_PROMPT" "$CONTAINER_NAME:/prompt.md"
    rm -f "$TEMP_PROMPT"
    
    # 4. Copy input files if they exist
    if [ -d "$INPUT_DIR" ]; then
        echo "Copying input files..."
        docker cp "$INPUT_DIR/." "$CONTAINER_NAME:/inputs/"
    fi
    
    # 5. Start container and wait for completion
    echo "Starting OpenCode..."
    START_TIME=$(date +%s)
    
    docker start -a "$CONTAINER_NAME" 2>&1 | tee "$TASK_OUTPUT_DIR/console.log" || true
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # 6. Extract output files from container
    echo "Extracting results..."
    docker cp "$CONTAINER_NAME:/output/." "$TEMP_OUTPUT/" 2>/dev/null || true
    
    # 7. Remove container (changes discarded)
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1 || true
    
    # =========================================================================
    # Process results
    # =========================================================================
    
    SESSION_ID=""
    INPUT_TOKENS=0
    OUTPUT_TOKENS=0
    REASONING_TOKENS=0
    STATUS="failed"
    ERROR=""
    OUTPUT_FILES=""
    
    # Read status from container
    if [ -f "$TEMP_OUTPUT/status.txt" ]; then
        CONTAINER_STATUS=$(cat "$TEMP_OUTPUT/status.txt")
        if [ "$CONTAINER_STATUS" = "timeout" ]; then
            STATUS="timeout"
        elif [ "$CONTAINER_STATUS" = "completed" ]; then
            STATUS="success"
        fi
    fi
    
    # Read session ID
    if [ -f "$TEMP_OUTPUT/session_id.txt" ]; then
        SESSION_ID=$(cat "$TEMP_OUTPUT/session_id.txt")
    fi
    
    # Read tokens
    if [ -f "$TEMP_OUTPUT/tokens.json" ]; then
        INPUT_TOKENS=$(jq -r '.input // 0' "$TEMP_OUTPUT/tokens.json")
        OUTPUT_TOKENS=$(jq -r '.output // 0' "$TEMP_OUTPUT/tokens.json")
        REASONING_TOKENS=$(jq -r '.reasoning // 0' "$TEMP_OUTPUT/tokens.json")
    fi
    
    # Check for output files
    if [ -d "$TEMP_OUTPUT/task_files" ] && [ "$(ls -A "$TEMP_OUTPUT/task_files" 2>/dev/null)" ]; then
        if [ "$STATUS" != "timeout" ]; then
            STATUS="success"
        fi
        OUTPUT_FILES=$(ls "$TEMP_OUTPUT/task_files" | tr '\n' ',' | sed 's/,$//')
        
        # Copy output files to opencode_output/{task_id}/
        mkdir -p "$OUTPUT_DIR/$TASK_ID"
        cp -r "$TEMP_OUTPUT/task_files/"* "$OUTPUT_DIR/$TASK_ID/"
        echo "Output files: $OUTPUT_FILES"
    fi
    
    # Check for errors in output
    if [ "$STATUS" = "failed" ] && [ -f "$TEMP_OUTPUT/run_output.jsonl" ]; then
        if grep -q '"type":"error"' "$TEMP_OUTPUT/run_output.jsonl" 2>/dev/null; then
            ERROR=$(grep '"type":"error"' "$TEMP_OUTPUT/run_output.jsonl" | jq -r '.message // "Unknown error"' | head -1)
        fi
    fi
    
    # Convert session.json to markdown log
    if [ -f "$TEMP_OUTPUT/session.json" ]; then
        python3 "$SCRIPT_DIR/scripts/session_to_markdown.py" \
            "$TEMP_OUTPUT/session.json" \
            "$TASK_OUTPUT_DIR/conversation.md" \
            --task-id "$TASK_ID" \
            --status "$STATUS" \
            --tokens-json "$TEMP_OUTPUT/tokens.json" \
            --duration "$DURATION" \
            2>/dev/null || echo "Warning: Failed to convert session to markdown"
    fi
    
    # Update summary
    UPDATED_AT=$(date -Iseconds)
    
    jq --arg task_id "$TASK_ID" \
       --arg status "$STATUS" \
       --arg session_id "$SESSION_ID" \
       --argjson input "$INPUT_TOKENS" \
       --argjson output "$OUTPUT_TOKENS" \
       --argjson reasoning "$REASONING_TOKENS" \
       --argjson duration "$DURATION" \
       --arg error "$ERROR" \
       --arg output_files "$OUTPUT_FILES" \
       --arg log_file "${TASK_ID}/conversation.md" \
       --arg updated_at "$UPDATED_AT" \
       '.tasks[$task_id] = {
          "status": $status,
          "session_id": $session_id,
          "tokens": {"input": $input, "output": $output, "reasoning": $reasoning},
          "duration_seconds": $duration,
          "error": (if $error == "" then null else $error end),
          "output_files": (if $output_files == "" then [] else ($output_files | split(",")) end),
          "log_file": $log_file
        } | .updated_at = $updated_at' \
       "$SUMMARY_FILE" > "${SUMMARY_FILE}.tmp" && mv "${SUMMARY_FILE}.tmp" "$SUMMARY_FILE"
    
    # Update counters
    case "$STATUS" in
        success)
            COMPLETED=$((COMPLETED + 1))
            ;;
        timeout)
            TIMED_OUT=$((TIMED_OUT + 1))
            ;;
        *)
            FAILED=$((FAILED + 1))
            ;;
    esac
    
    TOTAL_INPUT=$((TOTAL_INPUT + INPUT_TOKENS))
    TOTAL_OUTPUT=$((TOTAL_OUTPUT + OUTPUT_TOKENS))
    TOTAL_REASONING=$((TOTAL_REASONING + REASONING_TOKENS))
    
    # Cleanup temp directory
    rm -rf "$TEMP_OUTPUT"
    
    echo "Status: $STATUS (${DURATION}s)"
    echo "Tokens - Input: $INPUT_TOKENS, Output: $OUTPUT_TOKENS, Reasoning: $REASONING_TOKENS"
    
    # Verify no new files created in repo (true isolation check)
    NEW_FILES=$(git -C "$REPO_PATH" ls-files --others --exclude-standard 2>/dev/null | grep -v '__pycache__' | head -3)
    if [ -n "$NEW_FILES" ]; then
        echo "WARNING: New files created in repo (should not happen with true isolation):"
        echo "$NEW_FILES"
    fi
done

# =============================================================================
# Update final summary (recalculate from tasks object for accurate resume support)
# =============================================================================

# Calculate summary from actual tasks data (handles interrupted runs correctly)
jq '.summary = {
      "total": (.tasks | length),
      "completed": ([.tasks[] | select(.status == "success")] | length),
      "failed": ([.tasks[] | select(.status == "failed")] | length),
      "skipped": 0,
      "timeout": ([.tasks[] | select(.status == "timeout")] | length),
      "total_tokens": {
        "input": ([.tasks[].tokens.input] | add // 0),
        "output": ([.tasks[].tokens.output] | add // 0),
        "reasoning": ([.tasks[].tokens.reasoning] | add // 0)
      }
    }' \
   "$SUMMARY_FILE" > "${SUMMARY_FILE}.tmp" && mv "${SUMMARY_FILE}.tmp" "$SUMMARY_FILE"

# =============================================================================
# Print final summary
# =============================================================================

# Read calculated values from summary for display
FINAL_TOTAL=$(jq -r '.summary.total' "$SUMMARY_FILE")
FINAL_COMPLETED=$(jq -r '.summary.completed' "$SUMMARY_FILE")
FINAL_FAILED=$(jq -r '.summary.failed' "$SUMMARY_FILE")
FINAL_TIMEOUT=$(jq -r '.summary.timeout' "$SUMMARY_FILE")
FINAL_INPUT=$(jq -r '.summary.total_tokens.input' "$SUMMARY_FILE")
FINAL_OUTPUT=$(jq -r '.summary.total_tokens.output' "$SUMMARY_FILE")
FINAL_REASONING=$(jq -r '.summary.total_tokens.reasoning' "$SUMMARY_FILE")

echo ""
echo "============================================================"
echo "BATCH COMPLETE"
echo "============================================================"
echo "  Total tasks:   $FINAL_TOTAL"
echo "  Completed:     $FINAL_COMPLETED"
echo "  Failed:        $FINAL_FAILED"
echo "  Timeout:       $FINAL_TIMEOUT"
echo "  Total tokens:  Input=$FINAL_INPUT, Output=$FINAL_OUTPUT, Reasoning=$FINAL_REASONING"
echo ""
echo "  Summary file:  $SUMMARY_FILE"
echo "  Results dir:   $OUTPUT_DIR"
echo ""
echo "To grade results:"
echo "  gittaskbench grade --all --output_dir $OUTPUT_DIR"
echo "  gittaskbench eval"
echo "============================================================"

# Exit with error if any tasks failed
if [ "$FINAL_FAILED" -gt 0 ] || [ "$FINAL_TIMEOUT" -gt 0 ]; then
    exit 1
fi
exit 0
