#!/bin/bash

# 示例：使用改进后的batch_sweagent_run.py脚本
# 该脚本现在支持轨迹文件解析和成本统计

# 设置基本参数
PROMPT_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/output/prompt"
MODEL_NAME="claude-3-5-sonnet-20241022"
IMAGE="sweagent/swe-agent:latest"
REPO_PATH="/data/data/agent_test_codebase/GitTaskBench"
CONFIG_PATH="/data/code/agent_new/SWE-agent/config/default.yaml"
HOST_REPO_PATH="/data/data/agent_test_codebase/GitTaskBench"

# 轨迹文件相关参数
OUTPUT_BASE_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/sweagent_claude_35_output/traj_swe"
USER_NAME=""  # 在这个结构中用户名为空

# 运行批处理脚本
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

echo "批处理运行完成！"
echo "结果已保存到 batch_results.jsonl 文件中"
echo "该文件包含每个任务的成本统计信息，包括："
echo "- instance_cost: 实例成本"
echo "- tokens_sent: 发送的令牌数"
echo "- tokens_received: 接收的令牌数"
echo "- api_calls: API调用次数" 