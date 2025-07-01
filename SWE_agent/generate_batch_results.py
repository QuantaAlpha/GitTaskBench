#!/usr/bin/env python3
import os
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional

def find_trajectory_file(task_dir: str) -> Optional[str]:
    """
    Finds the trajectory file in the given task directory.
    """
    try:
        # First, look for .traj files directly in the task_dir
        # Then, look in immediate subdirectories for .traj files
        traj_files = glob.glob(os.path.join(task_dir, '*.traj')) + \
                    glob.glob(os.path.join(task_dir, '**', '*.traj'), recursive=True)

        for filepath in traj_files:
            if filepath.endswith('.traj'):
                return filepath
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error accessing directory {task_dir}: {e}")

    return None

def parse_trajectory_stats(trajectory_path: str) -> Optional[Dict[str, Any]]:
    """
    Parses model_stats information from the trajectory file.
    """
    try:
        if not os.path.exists(trajectory_path):
            print(f"Trajectory file not found: {trajectory_path}")
            return None

        # Try loading the entire file directly as a JSON object
        try:
            with open(trajectory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if it contains info.model_stats
            if isinstance(data, dict):
                if 'info' in data and isinstance(data['info'], dict) and \
                        'model_stats' in data['info'] and isinstance(data['info']['model_stats'], dict):
                    return data['info']['model_stats']

                if 'model_stats' in data and isinstance(data['model_stats'], dict):
                    return data['model_stats']
        except (json.JSONDecodeError, MemoryError) as e:
            print(f"Failed to load trajectory as single JSON object: {e}. Trying line-by-line parsing.")

        # If the above method fails, try to find model_stats from the end of the file
        with open(trajectory_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # Move to the end of the file
            file_size = f.tell()

            chunk_size = 100000  # Read last 100KB
            position = file_size

            buffer = ""
            while position > 0:
                read_size = min(chunk_size, position)
                position -= read_size
                f.seek(position)

                # Read chunk and concatenate with the unparsed part of the previous chunk
                current_chunk = f.read(read_size)
                content_to_search = current_chunk + buffer

                # Find "model_stats": { ... } structure
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
                    # Found "model_stats":, try to extract the JSON object after it
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
                                        # Parsing failed, possibly incomplete or malformed JSON object
                                        print(f"JSONDecodeError for model_stats chunk")
                                        # Continue in the outer loop to find the next occurrence of model_stats or read more content
                                        break
                        # If brace_count is not 0 when the inner loop finishes, the JSON object might span across chunks
                        if brace_count != 0:
                            buffer = content_to_search[json_text_start:]
                        else:
                            buffer = ""
                    else:
                        buffer = content_to_search
                else:
                    buffer = current_chunk

                # If already read to the beginning of the file, and still no result in buffer, parsing failed
                if position == 0:
                    break

        print(f"Could not find or parse valid model_stats in trajectory file: {trajectory_path}")
        return None

    except Exception as e:
        print(f"Error reading or parsing trajectory file {trajectory_path}: {e}")
        return None

def main():
    # Path configuration
    base_dir = "/data/code/agent_new/SWE-agent/trajectories/youwang-claude4-opus"
    openai_dir = os.path.join(base_dir, "openai")
    batch_results_file = os.path.join(base_dir, "batch_results.jsonl")

    # Results list
    results = []

    # Iterate through all task directories under the openai directory
    print(f"Scanning directory: {openai_dir}")
    task_dirs = glob.glob(os.path.join(openai_dir, "claude-opus-4-*"))
    print(f"Found {len(task_dirs)} task directories")

    for task_dir in task_dirs:
        task_name = os.path.basename(task_dir)
        print(f"Processing task directory: {task_name}")

        # Extract the original task name (without extension) from the directory name
        # E.g., claude-opus-4-20250514-Faker_01 -> Faker_01
        if "-" in task_name:
            parts = task_name.split("-")
            if len(parts) >= 5:  # claude-opus-4-20250514-Faker_01
                original_task_name = parts[4]  # Get the Faker_01 part
                if len(parts) > 5:  # Handle additional hyphens that might be in the task name
                    original_task_name = "-".join(parts[4:])
            else:
                original_task_name = task_name
        else:
            original_task_name = task_name

        # Add .md extension to get the full task name
        md_task_name = f"{original_task_name}.md"

        # Find the trajectory file
        traj_file = find_trajectory_file(task_dir)
        if traj_file:
            print(f"Found trajectory file: {traj_file}")

            # Parse model_stats
            model_stats = parse_trajectory_stats(traj_file)

            if model_stats:
                # Build the result entry
                entry = {
                    "task_name": md_task_name,
                    "run_id": task_name,
                    "success": True,  # Assume success if stats are present
                    "instance_cost": model_stats.get("instance_cost"),
                    "tokens_sent": model_stats.get("tokens_sent"),
                    "tokens_received": model_stats.get("tokens_received"),
                    "api_calls": model_stats.get("api_calls"),
                    "error": None
                }

                results.append(entry)
                print(
                    f"Added stats for {md_task_name}: cost={entry['instance_cost']}, tokens_sent={entry['tokens_sent']}")
            else:
                # Could not parse model_stats but trajectory file was found
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
            # Trajectory file not found
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

    # Save results to batch_results.jsonl
    print(f"\nSaving {len(results)} results to {batch_results_file}")
    with open(batch_results_file, 'w', encoding='utf-8') as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # Calculate total cost and statistics
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
        print(f"Average cost per successful task: ${total_cost / successful_tasks:.4f}")

if __name__ == "__main__":
    main()