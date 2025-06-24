#!/usr/bin/env python3
"""分析SWE-agent批处理结果"""
import json
from pathlib import Path

# 读取批处理结果
results_file = Path('trajectories/youwang-claude35/batch_results.jsonl')
results = []
with open(results_file, 'r') as f:
    for line in f:
        results.append(json.loads(line))

# 统计
total_tasks = len(results)
successful_tasks = sum(1 for r in results if r['success'])
failed_tasks = total_tasks - successful_tasks

# 成本统计（仅成功的任务）
total_tokens_sent = sum(r.get('tokens_sent', 0) or 0 for r in results if r['success'])
total_tokens_received = sum(r.get('tokens_received', 0) or 0 for r in results if r['success'])
total_api_calls = sum(r.get('api_calls', 0) or 0 for r in results if r['success'])

print(f'=== 批处理运行统计 ===')
print(f'总任务数: {total_tasks}')
print(f'成功: {successful_tasks} ({successful_tasks/total_tasks*100:.1f}%)')
print(f'失败: {failed_tasks} ({failed_tasks/total_tasks*100:.1f}%)')
print()
print(f'=== 成功任务的成本统计 ===')
print(f'总发送令牌数: {total_tokens_sent:,}')
print(f'总接收令牌数: {total_tokens_received:,}')
print(f'总API调用次数: {total_api_calls:,}')
print(f'平均每个成功任务:')
if successful_tasks > 0:
    print(f'  - 发送令牌: {total_tokens_sent/successful_tasks:,.0f}')
    print(f'  - 接收令牌: {total_tokens_received/successful_tasks:,.0f}')
    print(f'  - API调用: {total_api_calls/successful_tasks:.1f}')
print()
print('=== 成功的任务列表 ===')
for r in results:
    if r['success']:
        print(f'- {r["task_name"]}: {r["tokens_sent"]:,} tokens sent, {r["api_calls"]} API calls')
print()
print('=== 失败的任务列表 ===')
for r in results:
    if not r['success']:
        print(f'- {r["task_name"]}: {r.get("error", "Unknown error")}') 