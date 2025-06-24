# SWE-agent 批处理脚本改进

## 概述

`batch_sweagent_run.py` 脚本已经得到了重大改进，现在支持轨迹文件解析和成本统计功能。

## 新增功能

### 1. 轨迹文件解析
- 自动解析SWE-agent生成的轨迹文件（`.traj`）
- 提取`model_stats`信息，包括成本和令牌使用情况
- 支持多种目录结构的轨迹文件查找

### 2. 成本统计
脚本现在会自动收集和统计以下信息：
- `instance_cost`: 每个任务的实例成本（美元）
- `tokens_sent`: 发送给模型的令牌数
- `tokens_received`: 从模型接收的令牌数
- `api_calls`: API调用次数

### 3. 结果保存
运行完成后，脚本会生成一个 `batch_results.jsonl` 文件，包含：
- 每个任务的执行状态
- 详细的成本统计信息
- 错误信息（如果有）
- 总体成本汇总

## 使用方法

### 基本用法
```bash
python3 batch_sweagent_run.py \
    --prompt-dir /path/to/prompts \
    --model-name claude-3-5-sonnet-20241022 \
    --image sweagent/swe-agent:latest \
    --repo-path /path/to/repo \
    --config-path /path/to/config.yaml \
    --host-repo-path /path/to/host/repo \
    --output-base-dir /path/to/trajectory/output \
    --user-name "" \
    --workers 1
```

### 新增参数
- `--output-base-dir`: 轨迹文件输出的基础目录（默认：`trajectories`）
- `--user-name`: 轨迹路径中使用的用户名（默认：`batch_user`）

## 输出示例

### 控制台输出
```
[Scrapy_02.md] Cost: $1.5234, Tokens sent: 45,231, Tokens received: 892, API calls: 23

--- Batch Run Summary ---
Total tasks processed: 10
Successful SWE-agent runs: 8
Failed SWE-agent runs: 2
Results saved to: /path/to/batch_results.jsonl

--- Cost Summary ---
Total cost: $12.3456
Total tokens sent: 234,567
Total tokens received: 5,432
Total API calls: 156
Average cost per successful task: $1.5432
```

### batch_results.jsonl 格式
```json
{"task_name": "Scrapy_02.md", "run_id": "claude-3-5-sonnet-20241022-Scrapy_02", "success": true, "instance_cost": 1.5234, "tokens_sent": 45231, "tokens_received": 892, "api_calls": 23, "error": null}
{"task_name": "Failed_Task.md", "run_id": "claude-3-5-sonnet-20241022-Failed_Task", "success": false, "instance_cost": null, "tokens_sent": null, "tokens_received": null, "api_calls": null, "error": "Task execution failed"}
```

## 轨迹文件支持

脚本支持多种轨迹文件目录结构：

1. **标准SWE-agent结构**: `output_base_dir/user_name/model_name-task_name/`
2. **任务名目录**: `output_base_dir/task_name/`
3. **嵌套结构**: `output_base_dir/task_name/*/`

## 测试

使用 `test_trajectory_parser.py` 脚本来测试轨迹文件解析功能：

```bash
python3 test_trajectory_parser.py
```

## 示例脚本

参考 `example_batch_run.sh` 获取完整的使用示例。

## 注意事项

1. 轨迹文件解析支持大文件（通过分块读取）
2. 如果轨迹文件不存在或解析失败，相关字段将为 `null`
3. 成本统计仅针对成功完成的任务
4. 脚本会自动跳过已存在输出目录的任务 