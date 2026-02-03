#!/bin/bash
set -e

# =============================================================================
# OpenCode Container Entrypoint
# =============================================================================
# Required env vars: TASK_ID, MODEL
# Optional: TASK_TIMEOUT (default: 720)
# API keys passed via env (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
# =============================================================================

TASK_ID="${TASK_ID:-unknown}"
MODEL="${MODEL:-opencode/kimi-k2.5-free}"
TASK_TIMEOUT="${TASK_TIMEOUT:-720}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"

# Auto-allow all permissions for non-interactive container execution
export OPENCODE_PERMISSION='{"*":"allow","external_directory":"allow"}'

echo "========================================"
echo "OpenCode Container Runner"
echo "========================================"
echo "Task ID:  $TASK_ID"
echo "Model:    $MODEL"
echo "Timeout:  ${TASK_TIMEOUT}s"
echo "========================================"

cd /workspace

# Create Python venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating Python venv..."
    uv venv --seed --python "$PYTHON_VERSION" .venv 2>/dev/null || true
fi

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    export PYTHONPATH="/workspace:$PYTHONPATH"
fi

# Check prompt file exists
if [ ! -f "/prompt.md" ]; then
    echo "ERROR: /prompt.md not found"
    exit 1
fi

PROMPT=$(cat /prompt.md)

# Run OpenCode with JSON output to capture session ID and tokens
echo "Starting OpenCode..."
START_TIME=$(date +%s)

# Disable exit-on-error for the timeout command
set +e
EXIT_CODE=0
timeout "${TASK_TIMEOUT}s" opencode run \
    --model "$MODEL" \
    --title "$TASK_ID" \
    --format json \
    "$PROMPT" \
    2>&1 | tee /output/run_output.jsonl
EXIT_CODE=${PIPESTATUS[0]}
set -e

# Handle timeout (exit code 124 for GNU, 143 for busybox) vs other failures
if [ "$EXIT_CODE" -eq 124 ] || [ "$EXIT_CODE" -eq 143 ]; then
    echo "timeout" > /output/status.txt
    echo '{"type":"error","message":"Task timed out after '${TASK_TIMEOUT}'s"}' >> /output/run_output.jsonl
    echo "Task timed out after ${TASK_TIMEOUT}s"
elif [ "$EXIT_CODE" -ne 0 ]; then
    echo "failed" > /output/status.txt
    echo "OpenCode exited with code $EXIT_CODE"
else
    echo "completed" > /output/status.txt
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "Duration: ${DURATION}s"

# Extract session ID from JSON output
SESSION_ID=$(grep -o '"sessionID":"[^"]*"' /output/run_output.jsonl | head -1 | cut -d'"' -f4 || echo "")
echo "Session ID: $SESSION_ID"

# Save session ID for host to use
echo "$SESSION_ID" > /output/session_id.txt

# Export full session for conversation log
if [ -n "$SESSION_ID" ]; then
    echo "Exporting session..."
    opencode export "$SESSION_ID" > /output/session.json 2>/dev/null || true
fi

# Extract tokens from step_finish events
echo "Extracting token usage..."
INPUT_TOKENS=$(grep '"type":"step_finish"' /output/run_output.jsonl | \
    jq -s '[.[].part.tokens.input // 0] | add' 2>/dev/null || echo "0")
OUTPUT_TOKENS=$(grep '"type":"step_finish"' /output/run_output.jsonl | \
    jq -s '[.[].part.tokens.output // 0] | add' 2>/dev/null || echo "0")
REASONING_TOKENS=$(grep '"type":"step_finish"' /output/run_output.jsonl | \
    jq -s '[.[].part.tokens.reasoning // 0] | add' 2>/dev/null || echo "0")

# Save token summary
cat > /output/tokens.json << EOF
{
  "input": ${INPUT_TOKENS:-0},
  "output": ${OUTPUT_TOKENS:-0},
  "reasoning": ${REASONING_TOKENS:-0}
}
EOF

echo "Tokens - Input: $INPUT_TOKENS, Output: $OUTPUT_TOKENS, Reasoning: $REASONING_TOKENS"

# Copy output files from workspace to /output/task_files/
echo "Copying task output files..."
mkdir -p /output/task_files
find /workspace -maxdepth 2 -type f \( -name "output.*" -o -name "output_*.*" \) \
    -exec cp {} /output/task_files/ \; 2>/dev/null || true

# List copied files
ls -la /output/task_files/ 2>/dev/null || echo "No output files found"

echo "========================================"
echo "Task Complete: $TASK_ID"
echo "========================================"
