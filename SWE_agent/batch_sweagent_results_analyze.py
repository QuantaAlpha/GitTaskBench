#!/usr/bin/env python3
"""Analyze SWE-agent batch results"""
import json
from pathlib import Path

# Read batch results
results_file = Path('trajectories/youwang-claude35/batch_results.jsonl')
results = []
with open(results_file, 'r') as f:
    for line in f:
        results.append(json.loads(line))

# Statistics
total_tasks = len(results)
successful_tasks = sum(1 for r in results if r['success'])
failed_tasks = total_tasks - successful_tasks

# Cost statistics (only for successful tasks)
total_tokens_sent = sum(r.get('tokens_sent', 0) or 0 for r in results if r['success'])
total_tokens_received = sum(r.get('tokens_received', 0) or 0 for r in results if r['success'])
total_api_calls = sum(r.get('api_calls', 0) or 0 for r in results if r['success'])

print(f'=== Batch Run Statistics ===')
print(f'Total tasks: {total_tasks}')
print(f'Successful: {successful_tasks} ({successful_tasks/total_tasks*100:.1f}%)')
print(f'Failed: {failed_tasks} ({failed_tasks/total_tasks*100:.1f}%)')
print()
print(f'=== Cost Statistics for Successful Tasks ===')
print(f'Total tokens sent: {total_tokens_sent:,}')
print(f'Total tokens received: {total_tokens_received:,}')
print(f'Total API calls: {total_api_calls:,}')
print(f'Average per successful task:')
if successful_tasks > 0:
    print(f'  - Tokens sent: {total_tokens_sent/successful_tasks:,.0f}')
    print(f'  - Tokens received: {total_tokens_received/successful_tasks:,.0f}')
    print(f'  - API calls: {total_api_calls/successful_tasks:.1f}')
print()
print('=== List of Successful Tasks ===')
for r in results:
    if r['success']:
        print(f'- {r["task_name"]}: {r["tokens_sent"]:,} tokens sent, {r["api_calls"]} API calls')
print()
print('=== List of Failed Tasks ===')
for r in results:
    if not r['success']:
        print(f'- {r["task_name"]}: {r.get("error", "Unknown error")}')