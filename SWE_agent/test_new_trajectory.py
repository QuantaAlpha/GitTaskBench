#!/usr/bin/env python3
"""
Test the newly generated trajectory file finding and parsing functionality
"""
from batch_sweagent_run import find_trajectory_file, parse_trajectory_stats
import os

def test_new_trajectory():
    print("🔍 Testing new trajectory file finding and parsing...")
    print("=" * 50)

    # Test finding the latest trajectory files
    test_cases = [
        'AnimeGANv3_03.md',
        'dea290.md',  # Using hash as task name
    ]

    for task_name in test_cases:
        print(f"\n📋 Testing task: {task_name}")

        traj_file = find_trajectory_file(
            task_name,
            '/data/code/agent_new/SWE-agent/trajectories',
            'i-youwang',
            'gpt-4o'
        )

        if traj_file:
            print(f'✅ Found trajectory file: {traj_file}')
            if os.path.exists(traj_file):
                print(f'✅ File exists, size: {os.path.getsize(traj_file) / 1024 / 1024:.2f} MB')

                # Test parsing
                stats = parse_trajectory_stats(traj_file)
                if stats:
                    print(f'✅ Parsing successful!')
                    print(f'  Cost: ${stats.get("instance_cost", 0):.4f}')
                    print(f'  Tokens sent: {stats.get("tokens_sent", 0):,}')
                    print(f'  Tokens received: {stats.get("tokens_received", 0):,}')
                    print(f'  API calls: {stats.get("api_calls", 0)}')
                else:
                    print('❌ Parsing failed')
            else:
                print('❌ File does not exist')
        else:
            print('❌ No trajectory file found')

    # Test finding the newest trajectory file
    print(f"\n📋 Finding newest trajectory file...")
    traj_dir = '/data/code/agent_new/SWE-agent/trajectories/i-youwang'
    if os.path.exists(traj_dir):
        # Get newest directory
        dirs = [d for d in os.listdir(traj_dir) if os.path.isdir(os.path.join(traj_dir, d))]
        if dirs:
            # Sort by modification time
            dirs.sort(key=lambda x: os.path.getmtime(os.path.join(traj_dir, x)), reverse=True)
            latest_dir = dirs[0]
            print(f"Newest directory: {latest_dir}")

            # Find trajectory file in it
            latest_path = os.path.join(traj_dir, latest_dir)
            for item in os.listdir(latest_path):
                item_path = os.path.join(latest_path, item)
                if os.path.isdir(item_path):
                    for file in os.listdir(item_path):
                        if file.endswith('.traj'):
                            traj_file = os.path.join(item_path, file)
                            print(f"✅ Newest trajectory file: {traj_file}")

                            # Test parsing
                            stats = parse_trajectory_stats(traj_file)
                            if stats:
                                print(f'✅ Parsing successful!')
                                print(f'  Cost: ${stats.get("instance_cost", 0):.4f}')
                            break
                    break

if __name__ == "__main__":
    test_new_trajectory()