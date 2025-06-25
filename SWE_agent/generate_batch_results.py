#!/usr/bin/env python3
import os
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional

def find_trajectory_file(task_dir: str) -> Optional[str]:
    """
    在给定的任务目录中查找轨迹文件
    """
    try:
        # 首先在一级子目录下查找
        for subdir in os.listdir(task_dir):
            subdir_path = os.path.join(task_dir, subdir)
            if os.path.isdir(subdir_path):
                for file in os.listdir(subdir_path):
                    if file.endswith('.traj'):
                        return os.path.join(subdir_path, file)
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error accessing directory {task_dir}: {e}")
    
    return None

def parse_trajectory_stats(trajectory_path: str) -> Optional[Dict[str, Any]]:
    """
    解析轨迹文件中的model_stats信息
    """
    try:
        if not os.path.exists(trajectory_path):
            print(f"Trajectory file not found: {trajectory_path}")
            return None
            
        # 尝试直接将整个文件作为JSON对象加载
        try:
            with open(trajectory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否包含info.model_stats
            if isinstance(data, dict):
                if 'info' in data and isinstance(data['info'], dict) and \
                   'model_stats' in data['info'] and isinstance(data['info']['model_stats'], dict):
                    return data['info']['model_stats']
                
                if 'model_stats' in data and isinstance(data['model_stats'], dict):
                    return data['model_stats']
        except (json.JSONDecodeError, MemoryError) as e:
            print(f"Failed to load trajectory as single JSON object: {e}. Trying line-by-line parsing.")
            
        # 如果上面的方法失败，尝试从文件末尾查找model_stats
        with open(trajectory_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # 移动到文件末尾
            file_size = f.tell()
            
            chunk_size = 100000  # 读取最后100KB
            position = file_size
            
            buffer = ""
            while position > 0:
                read_size = min(chunk_size, position)
                position -= read_size
                f.seek(position)
                
                # 读取块并与上一个块的未解析部分拼接
                current_chunk = f.read(read_size)
                content_to_search = current_chunk + buffer 
                
                # 查找 "model_stats": { ... } 结构
                last_match_pos = -1
                search_start_pos = 0
                while True:
                    match_pos = content_to_search.find('"model_stats":', search_start_pos)
                    if match_pos != -1:
                        last_match_pos = match_pos
                        search_start_pos = match_pos + 1
                    else:
                        break
                
                if last_match_pos != -1:
                    # 找到了 "model_stats":，尝试提取其后的JSON对象
                    json_text_start = content_to_search.find('{', last_match_pos + len('"model_stats":'))
                    if json_text_start != -1:
                        brace_count = 0
                        json_obj_str = ""
                        for i in range(json_text_start, len(content_to_search)):
                            char = content_to_search[i]
                            json_obj_str += char
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    try:
                                        model_stats = json.loads(json_obj_str)
                                        print(f"Successfully parsed model_stats from chunk in {trajectory_path}")
                                        return model_stats
                                    except json.JSONDecodeError:
                                        # 解析失败，可能JSON对象不完整或格式错误
                                        print(f"JSONDecodeError for model_stats chunk")
                                        # 继续在外层循环中寻找下一个model_stats出现的位置或读取更多内容
                                        break
                        # 如果内层循环结束时brace_count不为0，说明JSON对象可能跨块了
                        if brace_count != 0:
                             buffer = content_to_search[json_text_start:] 
                        else:
                             buffer = ""
                    else:
                        buffer = content_to_search
                else:
                    buffer = current_chunk

                # 如果已经读到文件开头，并且buffer中仍未解析出结果，则解析失败
                if position == 0:
                    break
                    
        print(f"Could not find or parse valid model_stats in trajectory file: {trajectory_path}")
        return None
        
    except Exception as e:
        print(f"Error reading or parsing trajectory file {trajectory_path}: {e}")
        return None

def main():
    # 路径配置
    base_dir = "/data/code/agent_new/SWE-agent/trajectories/youwang-claude4-opus"
    openai_dir = os.path.join(base_dir, "openai")
    batch_results_file = os.path.join(base_dir, "batch_results.jsonl")
    
    # 结果列表
    results = []
    
    # 遍历openai目录下的所有任务目录
    print(f"Scanning directory: {openai_dir}")
    task_dirs = glob.glob(os.path.join(openai_dir, "claude-opus-4-*"))
    print(f"Found {len(task_dirs)} task directories")
    
    for task_dir in task_dirs:
        task_name = os.path.basename(task_dir)
        print(f"Processing task directory: {task_name}")
        
        # 从目录名中提取任务的原始名称（不含扩展名）
        # 例如 claude-opus-4-20250514-Faker_01 -> Faker_01
        if "-" in task_name:
            parts = task_name.split("-")
            if len(parts) >= 5:  # claude-opus-4-20250514-Faker_01
                original_task_name = parts[4]  # 获取Faker_01部分
                if len(parts) > 5:  # 处理任务名称中可能包含的额外连字符
                    original_task_name = "-".join(parts[4:])
            else:
                original_task_name = task_name
        else:
            original_task_name = task_name
            
        # 添加.md扩展名获得完整任务名
        md_task_name = f"{original_task_name}.md"
        
        # 查找轨迹文件
        traj_file = find_trajectory_file(task_dir)
        if traj_file:
            print(f"Found trajectory file: {traj_file}")
            
            # 解析model_stats
            model_stats = parse_trajectory_stats(traj_file)
            
            if model_stats:
                # 构建结果条目
                entry = {
                    "task_name": md_task_name,
                    "run_id": task_name,
                    "success": True,  # 假设有stats就是成功的
                    "instance_cost": model_stats.get("instance_cost"),
                    "tokens_sent": model_stats.get("tokens_sent"),
                    "tokens_received": model_stats.get("tokens_received"),
                    "api_calls": model_stats.get("api_calls"),
                    "error": None
                }
                
                results.append(entry)
                print(f"Added stats for {md_task_name}: cost={entry['instance_cost']}, tokens_sent={entry['tokens_sent']}")
            else:
                # 无法解析model_stats但找到了轨迹文件
                entry = {
                    "task_name": md_task_name,
                    "run_id": task_name,
                    "success": False,
                    "instance_cost": None,
                    "tokens_sent": None,
                    "tokens_received": None,
                    "api_calls": None,
                    "error": "Could not parse model_stats from trajectory file"
                }
                
                results.append(entry)
                print(f"Failed to parse stats for {md_task_name}")
        else:
            # 未找到轨迹文件
            entry = {
                "task_name": md_task_name,
                "run_id": task_name,
                "success": False,
                "instance_cost": None,
                "tokens_sent": None,
                "tokens_received": None,
                "api_calls": None,
                "error": "Trajectory file not found"
            }
            
            results.append(entry)
            print(f"No trajectory file found for {md_task_name}")
    
    # 保存结果到batch_results.jsonl
    print(f"\nSaving {len(results)} results to {batch_results_file}")
    with open(batch_results_file, 'w', encoding='utf-8') as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    # 计算总成本和统计信息
    total_cost = sum(entry.get("instance_cost") or 0 for entry in results)
    total_tokens_sent = sum(entry.get("tokens_sent") or 0 for entry in results)
    total_tokens_received = sum(entry.get("tokens_received") or 0 for entry in results)
    total_api_calls = sum(entry.get("api_calls") or 0 for entry in results)
    successful_tasks = sum(1 for entry in results if entry.get("success", False))
    
    print("\n--- Overall Statistics ---")
    print(f"Total tasks processed: {len(results)}")
    print(f"Successful tasks: {successful_tasks}")
    print(f"Failed tasks: {len(results) - successful_tasks}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Total tokens sent: {total_tokens_sent:,}")
    print(f"Total tokens received: {total_tokens_received:,}")
    print(f"Total API calls: {total_api_calls:,}")
    if successful_tasks > 0:
        print(f"Average cost per successful task: ${total_cost/successful_tasks:.4f}")

if __name__ == "__main__":
    main() 