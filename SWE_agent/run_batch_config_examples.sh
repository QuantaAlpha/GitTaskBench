#!/bin/bash

# SWE-agent 批处理脚本配置示例
# 根据不同的使用场景选择合适的配置

echo "SWE-agent 批处理脚本配置示例"
echo "================================"
echo ""
echo "请根据你的使用场景选择配置："
echo ""

# --- 场景1：解析现有轨迹文件（推荐用于成本统计） ---
echo "🔍 场景1：解析现有轨迹文件并生成成本统计"
echo "适用于：已经运行过SWE-agent，现在想要分析成本"
echo ""
cat << 'EOF'
# 配置参数
MODEL_NAME="claude-3-5-sonnet-20241022"
OUTPUT_BASE_DIR="/data/data/agent_test_codebase/GitTaskBench/eval_automation/sweagent_claude_35_output/traj_swe"
USER_NAME=""  # 空字符串，适用于直接任务名目录结构
SKIP_DOCKER_PRUNE="true"  # 跳过Docker清理
SKIP_GIT_COMMIT="true"    # 跳过Git提交

# 运行命令
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

# --- 场景2：运行新任务并跟踪成本 ---
echo "🚀 场景2：运行新任务并实时跟踪成本"
echo "适用于：运行新的SWE-agent任务并同时收集成本数据"
echo ""
cat << 'EOF'
# 配置参数
MODEL_NAME="claude-3-5-sonnet-20241022"
OUTPUT_BASE_DIR="trajectories"  # 标准SWE-agent输出目录
USER_NAME="batch_user"          # 标准用户名
SKIP_DOCKER_PRUNE=""            # 启用Docker清理
SKIP_GIT_COMMIT=""              # 启用Git提交

# 运行命令
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

# --- 场景3：GPT模型配置 ---
echo "🤖 场景3：使用GPT模型"
echo "适用于：使用OpenAI GPT模型而非Claude"
echo ""
cat << 'EOF'
# 配置参数
MODEL_NAME="gpt-4o"
OUTPUT_BASE_DIR="trajectories"
USER_NAME="batch_user"

# 运行命令（其他参数相同）
python3 batch_sweagent_run.py \
    --model-name "$MODEL_NAME" \
    --output-base-dir "$OUTPUT_BASE_DIR" \
    --user-name "$USER_NAME" \
    # ... 其他参数
EOF

echo ""
echo "---"
echo ""

# --- 场景4：自定义轨迹文件位置 ---
echo "📁 场景4：自定义轨迹文件位置"
echo "适用于：轨迹文件存储在非标准位置"
echo ""
cat << 'EOF'
# 配置参数
OUTPUT_BASE_DIR="/custom/path/to/trajectories"
USER_NAME="custom_user"  # 或者留空 ""

# 目录结构示例：
# /custom/path/to/trajectories/
# ├── TaskName1/
# │   └── hash1/
# │       └── hash1.traj
# ├── TaskName2/
# │   └── hash2/
# │       └── hash2.traj
# 或者
# /custom/path/to/trajectories/custom_user/
# ├── model-TaskName1/
# │   └── model-TaskName1.traj
# ├── model-TaskName2/
# │   └── model-TaskName2.traj
EOF

echo ""
echo "---"
echo ""

echo "💡 提示："
echo "1. 首次使用建议先用场景1测试轨迹文件解析功能"
echo "2. OUTPUT_BASE_DIR 应该指向包含轨迹文件的目录"
echo "3. USER_NAME 根据你的目录结构设置（可能为空）"
echo "4. 运行后检查 batch_results.jsonl 文件获取成本统计"
echo ""
echo "🔧 当前默认配置（run_batch.sh）使用场景1的设置" 