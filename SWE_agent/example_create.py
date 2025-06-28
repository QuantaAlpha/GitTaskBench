#!/usr/bin/env python3
import json
from batch_sweagent_run import parse_trajectory_stats

# Create example results
traj_file = '/data/data/agent_test_codebase/GitTaskBench/eval_automation/sweagent_claude_35_output/traj_swe/Scrapy_02/fc213f/fc213f.traj'
stats = parse_trajectory_stats(traj_file)

result = {
    'task_name': 'Scrapy_02.md',
    'run_id': 'claude-3-5-sonnet-20241022-Scrapy_02',
    'success': True,
    'instance_cost': stats.get('instance_cost') if stats else None,
    'tokens_sent': stats.get('tokens_sent') if stats else None,
    'tokens_received': stats.get('tokens_received') if stats else None,
    'api_calls': stats.get('api_calls') if stats else None,
    'error': None
}

with open('example_batch_results.jsonl', 'w') as f:
    f.write(json.dumps(result, ensure_ascii=False) + '\n')

print('Example batch_results.jsonl created!')
print('Content:', json.dumps(result, ensure_ascii=False, indent=2))