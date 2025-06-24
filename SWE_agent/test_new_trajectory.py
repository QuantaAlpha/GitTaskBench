#!/usr/bin/env python3
"""
测试新生成的轨迹文件查找和解析功能
"""
from batch_sweagent_run import find_trajectory_file, parse_trajectory_stats
import os

def test_new_trajectory():
    print("🔍 测试新轨迹文件查找和解析...")
    print("=" * 50)
    
    # 测试查找最新的轨迹文件
    test_cases = [
        'AnimeGANv3_03.md',
        'dea290.md',  # 使用hash作为任务名
    ]
    
    for task_name in test_cases:
        print(f"\n📋 测试任务: {task_name}")
        
        traj_file = find_trajectory_file(
            task_name,
            '/data/code/agent_new/SWE-agent/trajectories',
            'i-youwang',
            'gpt-4o'
        )
        
        if traj_file:
            print(f'✅ 找到轨迹文件: {traj_file}')
            if os.path.exists(traj_file):
                print(f'✅ 文件存在，大小: {os.path.getsize(traj_file) / 1024 / 1024:.2f} MB')
                
                # 测试解析
                stats = parse_trajectory_stats(traj_file)
                if stats:
                    print(f'✅ 解析成功!')
                    print(f'  成本: ${stats.get("instance_cost", 0):.4f}')
                    print(f'  令牌发送: {stats.get("tokens_sent", 0):,}')
                    print(f'  令牌接收: {stats.get("tokens_received", 0):,}')
                    print(f'  API调用: {stats.get("api_calls", 0)}')
                else:
                    print('❌ 解析失败')
            else:
                print('❌ 文件不存在')
        else:
            print('❌ 未找到轨迹文件')
    
    # 测试最新的轨迹文件
    print(f"\n📋 查找最新的轨迹文件...")
    traj_dir = '/data/code/agent_new/SWE-agent/trajectories/i-youwang'
    if os.path.exists(traj_dir):
        # 获取最新的目录
        dirs = [d for d in os.listdir(traj_dir) if os.path.isdir(os.path.join(traj_dir, d))]
        if dirs:
            # 按修改时间排序
            dirs.sort(key=lambda x: os.path.getmtime(os.path.join(traj_dir, x)), reverse=True)
            latest_dir = dirs[0]
            print(f"最新目录: {latest_dir}")
            
            # 查找其中的轨迹文件
            latest_path = os.path.join(traj_dir, latest_dir)
            for item in os.listdir(latest_path):
                item_path = os.path.join(latest_path, item)
                if os.path.isdir(item_path):
                    for file in os.listdir(item_path):
                        if file.endswith('.traj'):
                            traj_file = os.path.join(item_path, file)
                            print(f"✅ 最新轨迹文件: {traj_file}")
                            
                            # 测试解析
                            stats = parse_trajectory_stats(traj_file)
                            if stats:
                                print(f'✅ 解析成功!')
                                print(f'  成本: ${stats.get("instance_cost", 0):.4f}')
                            break
                    break

if __name__ == "__main__":
    test_new_trajectory() 