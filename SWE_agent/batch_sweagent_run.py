#!/usr/bin/env python3
import argparse
import os
import subprocess
import logging
import time # Added for sleep
import shlex # Added for command splitting
import json
# No need for platform module anymore, removed platform import
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Configure logging for the script itself
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - [BatchScript] %(message)s' # Added prefix
)
logger = logging.getLogger(__name__)

def run_subprocess_cmd(command: List[str], task_name: str, step_name: str) -> bool:
    """
    Runs a command as a subprocess and logs its output/errors.

    Args:
        command: The command to run as a list of strings.
        task_name: The name of the parent task for logging context.
        step_name: The name of the specific step being executed (e.g., "Docker Prune").

    Returns:
        True if the command executed successfully (return code 0), False otherwise.
    """
    try:
        # For commands involving shell expansion like $(docker ps -aq), use shell=True
        # and pass the command as a string. Be cautious with shell=True.
        is_shell_cmd = isinstance(command, str) or any("$" in str(arg) or "*" in str(arg) for arg in command)
        cmd_str = ' '.join(command) if not isinstance(command, str) else command
        logger.info(f"[{task_name}] Running {step_name}: {cmd_str}")

        result = subprocess.run(
            cmd_str if is_shell_cmd else command,
            capture_output=True,
            text=True,
            check=False,
            shell=is_shell_cmd # Enable shell if needed (e.g., for $(...))
        )

        if result.stdout:
            stdout_msg = f"[{task_name}] {step_name} stdout:\n{result.stdout.strip()}"
            logger.info(stdout_msg)
        if result.stderr:
            stderr_msg = f"[{task_name}] {step_name} stderr:\n{result.stderr.strip()}"
            logger.warning(stderr_msg)

        if result.returncode == 0:
            logger.info(f"[{task_name}] {step_name} completed successfully.")
            return True
        else:
            logger.error(f"[{task_name}] {step_name} failed (RC: {result.returncode}).")
            return False
    except FileNotFoundError:
        cmd_name = command[0] if isinstance(command, list) and command else str(command)
        logger.error(f"[{task_name}] {step_name} failed: Command not found ('{cmd_name}'). Ensure it's in PATH.")
        return False
    except Exception as e:
        logger.error(f"[{task_name}] {step_name} failed due to script exception: {e}")
        return False


def run_sweagent_task(
    base_cmd: List[str],
    problem_statement_path: str,
    task_name: str,
    custom_output_dir: Path  # 新增参数：自定义的输出目录
) -> Tuple[str, bool, str]:
    """
    Runs a single SWE-agent task, letting its output go directly to the terminal.

    Args:
        base_cmd: The base list of command arguments for sweagent run.
        problem_statement_path: The path to the specific .md problem statement.
        task_name: A descriptive name for the task (e.g., the .md filename).
        custom_output_dir: The custom base directory for this specific task's output.

    Returns:
        A tuple containing:
        - task_name (str): The name of the task.
        - success (bool): True if the command executed successfully (return code 0), False otherwise.
        - output (str): An empty string, as output is not captured directly here.
    """
    # 确保自定义输出目录存在
    custom_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 将 --output_dir 添加到命令中，指向我们自定义的、为该任务特定的目录
    # SWE-agent 会在这个目录下创建它自己的子目录结构 (通常是 problem_id)
    full_cmd = base_cmd + [
        '--problem_statement.path', problem_statement_path,
        '--output_dir', str(custom_output_dir) # 将整个自定义目录作为SWE-agent的输出根目录
    ]
    logger.info(f"Starting task: {task_name} | Command: {' '.join(full_cmd)}")
    logger.info(f"Output for this task will be in: {custom_output_dir}")
    logger.info(f"--- Output for {task_name} will appear below (interleaved if workers > 1) ---")
    try:
        # Let the subprocess inherit stdout/stderr from the parent for live output
        process = subprocess.Popen(full_cmd)
        returncode = process.wait()
        output = "" # Output is inherited, not captured

        if returncode == 0:
            logger.info(f"--- Task {task_name} completed successfully (RC: {returncode}) ---")
            return task_name, True, output
        else:
            logger.error(f"--- Task {task_name} failed (RC: {returncode}) ---")
            return task_name, False, output

    except Exception as e:
        logger.error(f"--- Task {task_name} failed to run due to script exception: {e} ---")
        rc = -1
        return task_name, False, f"Exception: {str(e)}\nReturn Code: {rc}"

def post_task_actions(
    task_name: str,
    host_repo_path: str,
    sleep_duration: int,
    skip_docker_prune: bool,
    skip_git_commit: bool
) -> None:
    """
    Performs cleanup and Git operations after a task finishes.
    Args are the same as before.
    """
    logger.info(f"--- Starting post-task actions for {task_name} ---")

    if not skip_docker_prune:
        logger.info(f"[{task_name}] Cleaning up Docker containers...")
        # Use shell=True for command substitution $()
        stop_cmd = "docker stop $(docker ps -aq)"
        rm_cmd = "docker rm $(docker ps -aq)"
        run_subprocess_cmd(stop_cmd, task_name, "Docker Stop")
        run_subprocess_cmd(rm_cmd, task_name, "Docker Remove")
        logger.info(f"[{task_name}] Docker cleanup finished.")
    else:
        logger.info(f"[{task_name}] Skipping Docker prune step.")

    if sleep_duration > 0:
        logger.info(f"[{task_name}] Sleeping for {sleep_duration} seconds...")
        time.sleep(sleep_duration)
        logger.info(f"[{task_name}] Sleep finished.")

    if not skip_git_commit:
        if not os.path.isdir(host_repo_path):
            logger.error(f"[{task_name}] Git repo path not found or not a directory: {host_repo_path}. Skipping Git actions.")
            return

        logger.info(f"[{task_name}] Performing Git actions in {host_repo_path}...")
        add_cmd = ['git', '-C', host_repo_path, 'add', '.']
        run_subprocess_cmd(add_cmd, task_name, "Git Add")

        commit_msg = f"SWE-agent task {task_name}: Post-run commit"
        commit_cmd = ['git', '-C', host_repo_path, 'commit', '--allow-empty', '--no-verify', '-m', commit_msg]
        run_subprocess_cmd(commit_cmd, task_name, "Git Commit")
    else:
         logger.info(f"[{task_name}] Skipping Git commit step.")

    logger.info(f"--- Finished post-task actions for {task_name} ---")

def find_trajectory_file(task_specific_output_dir: str, user_name_arg: str, model_name_arg: str, task_name: str) -> Optional[str]:
    """
    在指定的任务特定输出目录中查找轨迹文件。
    SWE-agent会在提供的 --output_dir (即 task_specific_output_dir) 下创建以 problem_id 命名的子目录。

    Args:
        task_specific_output_dir: 批处理脚本为该任务创建并传递给sweagent的--output_dir。
                                (例如：trajectories/your_user/model-task/)
        user_name_arg: 从命令行传入的user_name，此处主要用于日志或调试，路径构建已依赖task_specific_output_dir。
        model_name_arg: 从命令行传入的model_name，此处主要用于日志或调试。
        task_name: 原始任务名 (例如 "Scrapy_02.md")
        
    Returns:
        轨迹文件的路径，如果找不到则返回None
    """
    # task_specific_output_dir 已经是 .../trajectories/USER_NAME/MODEL_NAME-TASK_NAME_NO_EXT/
    base_search_dir = Path(task_specific_output_dir)
    
    logger.debug(f"[find_trajectory_file] Searching in base directory for task '{task_name}': {base_search_dir}")
    
    if not base_search_dir.is_dir():
        logger.warning(f"[find_trajectory_file] Base search directory not found: {base_search_dir}")
        return None
    
    # SWE-agent 会在 base_search_dir 下创建一个以 problem_statement.id 命名的子目录
    # 我们需要遍历 base_search_dir 下的子目录来找到轨迹文件
    try:
        for potential_problem_id_dir in base_search_dir.iterdir():
            if potential_problem_id_dir.is_dir():
                logger.debug(f"[find_trajectory_file] Checking subdir for .traj: {potential_problem_id_dir}")
                for file_in_subdir in potential_problem_id_dir.iterdir():
                    if file_in_subdir.is_file() and file_in_subdir.name.endswith('.traj'):
                        logger.info(f"[find_trajectory_file] Found trajectory file: {file_in_subdir}")
                        return str(file_in_subdir)
                logger.debug(f"[find_trajectory_file] No .traj file in {potential_problem_id_dir}")
            # 也检查base_search_dir自身是否直接包含traj文件（以防SWE-agent行为变更或简单任务没有problem_id子目录）
            elif potential_problem_id_dir.is_file() and potential_problem_id_dir.name.endswith('.traj'):
                 logger.info(f"[find_trajectory_file] Found trajectory file directly in task output dir: {potential_problem_id_dir}")
                 return str(potential_problem_id_dir)

    except OSError as e:
        logger.error(f"[find_trajectory_file] Error listing directories in {base_search_dir}: {e}")
        return None
        
    logger.warning(f"[find_trajectory_file] No .traj file found for task '{task_name}' in {base_search_dir} or its direct subdirectories.")
    return None

def parse_trajectory_stats(trajectory_path: str) -> Optional[Dict[str, Any]]:
    """
    解析轨迹文件中的model_stats信息。
    
    Args:
        trajectory_path: 轨迹文件的路径
        
    Returns:
        包含model_stats信息的字典，如果解析失败则返回None
    """
    try:
        if not os.path.exists(trajectory_path):
            logger.warning(f"Trajectory file not found: {trajectory_path}")
            return None
            
        # 尝试直接将整个文件作为JSON对象加载
        # 这适用于轨迹文件是单个大JSON对象的情况
        try:
            with open(trajectory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否包含info.model_stats 或直接的 model_stats
            if isinstance(data, dict):
                if 'info' in data and isinstance(data['info'], dict) and \
                   'model_stats' in data['info'] and isinstance(data['info']['model_stats'], dict):
                    return data['info']['model_stats']
                
                if 'model_stats' in data and isinstance(data['model_stats'], dict):
                    return data['model_stats']
        except (json.JSONDecodeError, MemoryError) as e:
            logger.debug(f"Failed to load trajectory as single JSON object ({trajectory_path}): {e}. Trying line-by-line parsing.")
            # 如果作为单个JSON对象加载失败，尝试逐行解析（适用于JSON Lines格式或末尾附加统计信息的情况）
            pass # 继续尝试下面的方法

        # 如果上面的方法失败，尝试从文件末尾查找model_stats
        with open(trajectory_path, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # 移动到文件末尾
            file_size = f.tell()
            
            chunk_size = 100000  # 读取最后100KB (可以根据model_stats通常出现的位置调整)
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
                # 从后往前查找，以获取最新的model_stats（如果文件中有多个）
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
                                        logger.debug(f"Successfully parsed model_stats from chunk in {trajectory_path}")
                                        return model_stats
                                    except json.JSONDecodeError:
                                        # 解析失败，可能JSON对象不完整或格式错误
                                        logger.debug(f"JSONDecodeError for model_stats chunk in {trajectory_path}: {json_obj_str}")
                                        # 继续在外层循环中寻找下一个model_stats出现的位置或读取更多内容
                                        break # 跳出内层for循环，继续while循环读取更多块
                        # 如果内层循环结束时brace_count不为0，说明JSON对象可能跨块了
                        # 将当前块的开始部分（可能包含不完整的JSON）存入buffer，以便与下一个块拼接
                        if brace_count != 0:
                             buffer = content_to_search[json_text_start:] 
                        else:
                             buffer = "" # 成功解析或无需拼接
                    else:
                        buffer = content_to_search # 未找到 '{'，保留当前块
                else: # 当前块没有 "model_stats":
                    buffer = current_chunk # 将当前块完整保留，与前一个块拼接

                # 如果已经读到文件开头，并且buffer中仍未解析出结果，则解析失败
                if position == 0:
                    break
                    
        logger.warning(f"Could not find or parse valid model_stats in trajectory file: {trajectory_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error reading or parsing trajectory file {trajectory_path}: {e}", exc_info=True)
        return None

# 新增：全局变量用于累积成本 (或者作为类的成员，如果将其重构为类)
global_overall_total_cost = 0.0
global_overall_total_tokens_sent = 0
global_overall_total_tokens_received = 0
global_overall_total_api_calls = 0
batch_results_summary_list_for_file: List[Dict[str, Any]] = [] # 用于最终写入JSONL文件

def format_and_process_task_result(
    task_name: str,
    model_name: str, # 需要模型名称来构建run_id
    success: bool,
    output_str: Optional[str],
    model_stats: Optional[Dict[str, Any]],
    error_msg: Optional[str]
) -> None:
    """
    格式化单个任务的结果，打印即时总结，并累积到全局统计中。
    """
    global global_overall_total_cost, global_overall_total_tokens_sent
    global global_overall_total_tokens_received, global_overall_total_api_calls
    global batch_results_summary_list_for_file

    task_name_without_ext = os.path.splitext(task_name)[0]
    run_id = f"{model_name}-{task_name_without_ext}"

    instance_cost = model_stats.get("instance_cost") if model_stats else None
    tokens_sent = model_stats.get("tokens_sent") if model_stats else None
    tokens_received = model_stats.get("tokens_received") if model_stats else None
    api_calls = model_stats.get("api_calls") if model_stats else None
    
    # 打印当前任务的即时成本总结
    logger.info(f"--- Cost Summary for Task: {task_name} ---")
    if success and model_stats:
        logger.info(f"  Status: SUCCESS")
        logger.info(f"  Task Cost: ${instance_cost:.4f}" if instance_cost is not None else "  Task Cost: N/A")
        logger.info(f"  Tokens Sent: {tokens_sent}")
        logger.info(f"  Tokens Received: {tokens_received}")
        logger.info(f"  API Calls: {api_calls}")
    elif success and not model_stats:
        logger.info(f"  Status: SUCCESS (but model_stats not found/parsed)")
        logger.warning(f"  Cost information unavailable. Error during parsing: {error_msg if error_msg else 'Unknown parsing error'}")
    else: # not success
        logger.info(f"  Status: FAILED")
        logger.warning(f"  Task failed. Error: {(error_msg or output_str or 'Unknown execution error').splitlines()[0][:100]}")
    logger.info(f"--- End Cost Summary for Task: {task_name} ---")

    # 构建用于JSONL文件的条目
    summary_entry = {
        "task_name": task_name,
        "run_id": run_id,
        "success": success,
        "instance_cost": instance_cost,
        "tokens_sent": tokens_sent,
        "tokens_received": tokens_received,
        "api_calls": api_calls,
        "error": error_msg if error_msg else (None if success else (output_str or "Task execution failed"))
    }
    batch_results_summary_list_for_file.append(summary_entry)

    # 累加到全局统计
    if success and model_stats: # 仅当成功且有统计数据时累加
        if instance_cost is not None:
            global_overall_total_cost += instance_cost
        if tokens_sent is not None:
            global_overall_total_tokens_sent += tokens_sent
        if tokens_received is not None:
            global_overall_total_tokens_received += tokens_received
        if api_calls is not None:
            global_overall_total_api_calls += api_calls

def main():
    """
    Main function restored.
    """
    parser = argparse.ArgumentParser(
        description='Batch run SWE-agent tasks with post-task actions.'
    )
    # Add all arguments back (prompt-dir, workers, model-name, image, repo-path, config-path, host-repo-path, sleep-duration, skip-docker-prune, skip-git-commit, log-level)
    parser.add_argument(
        '--prompt-dir',
        type=str,
        required=True,
        help='Directory containing the .md problem statement files.'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of concurrent workers. Set to 1 for sequential post-task actions.'
    )
    parser.add_argument(
        '--model-name', type=str, required=True, help='Agent model name.'
    )
    parser.add_argument(
        '--image', type=str, required=True, help='Docker image.'
    )
    parser.add_argument(
        '--repo-path', type=str, required=True, help='Repo path inside container.'
    )
    parser.add_argument(
        '--config-path',
        type=str,
        required=True,
        nargs='+',  # 允许一个或多个配置文件
        help='SWE-agent config file(s). If multiple, they are merged, later files override earlier ones.'
    )
    parser.add_argument(
        '--host-repo-path', type=str, required=True, help='Host repo path for Git.'
    )
    parser.add_argument(
        '--sleep-duration', type=int, default=5, help='Sleep duration after task.'
    )
    parser.add_argument(
        '--skip-docker-prune', action='store_true', help='Skip Docker cleanup.'
    )
    parser.add_argument(
        '--skip-git-commit', action='store_true', help='Skip Git commit.'
    )
    parser.add_argument(
        '--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Logging level.'
    )
    # Add arguments for checking existing output
    parser.add_argument(
        '--output-base-dir',
        type=str,
        default='trajectories', # Default SWE-agent output base dir
        help='Base directory where SWE-agent saves task outputs.'
    )
    parser.add_argument(
        '--user-name',
        type=str,
        default='batch_user', # Default user for trajectory path
        help='Username used in the SWE-agent output trajectory path.'
    )

    args = parser.parse_args()

    # Argument Validation (Workers and Git path)
    if args.workers > 1:
        logger.warning(
            f"Running with {args.workers} workers. Post-task actions (Docker/Git) might interleave. Set --workers 1 for sequential execution."
        )
    if not args.skip_git_commit and not os.path.isdir(args.host_repo_path):
         logger.warning(
             f"Host Git repository path '{args.host_repo_path}' not found. Git actions will be skipped."
         )

    # Set logging level
    log_level_upper = args.log_level.upper()
    try:
        log_level_int = getattr(logging, log_level_upper)
        # Reconfigure logger level based on args
        logging.getLogger().setLevel(log_level_int)
        for handler in logging.getLogger().handlers:
            handler.setLevel(log_level_int)
        logger.info(f"Logging level set to {log_level_upper}")
    except AttributeError:
        logger.error(f"Invalid log level: {args.log_level}. Using INFO.")
        # Keep default INFO level from basicConfig

    # Validate prompt directory
    if not os.path.isdir(args.prompt_dir):
        logger.error(f"Prompt directory not found: {args.prompt_dir}")
        return

    all_md_files = [f for f in os.listdir(args.prompt_dir) if f.endswith('.md') and os.path.isfile(os.path.join(args.prompt_dir, f))]
    if not all_md_files:
        logger.warning(f"No .md files found in {args.prompt_dir}")
        return

    logger.info(f"Found {len(all_md_files)} total .md files in {args.prompt_dir}")

    # Filter out tasks with existing output directories
    md_files_to_run = []
    skipped_count = 0
    for md_file in all_md_files:
        task_name_without_ext = os.path.splitext(md_file)[0]
        # Construct the expected output path based on SWE-agent conventions
        expected_output_dir = os.path.join(
            args.output_base_dir,
            args.user_name,
            f"{args.model_name}-{task_name_without_ext}"
        )

        if os.path.isdir(expected_output_dir):
            logger.info(f"Skipping task '{md_file}': Output directory already exists at '{expected_output_dir}'")
            skipped_count += 1
        else:
            md_files_to_run.append(md_file)

    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} tasks because their output directories already exist.")

    # 修改退出条件：只有在最初就没有找到任何.md文件时才退出。
    # 如果有.md文件，但它们都被跳过了，我们仍然希望继续执行以进行回顾性分析。
    if not all_md_files: # 如果最初就没有找到任何md文件
        logger.warning(f"No .md files found in {args.prompt_dir}. Nothing to do.")
        return
    elif not md_files_to_run and skipped_count == len(all_md_files):
        logger.info("All tasks from prompt_dir were skipped as their output directories already exist. Proceeding to analyze existing trajectories.")
    elif not md_files_to_run:
        # 这种情况理论上不应该发生，因为如果all_md_files非空，要么md_files_to_run非空，要么skipped_count == len(all_md_files)
        logger.warning("No tasks left to run and not all tasks were skipped. This is an unexpected state.")
        # 考虑是否在这里也应该继续，或者这是一个错误情况需要停止
        # 为了安全起见，如果不是"全部跳过"的情况，且没有新任务，则可能也该提示用户
        # 但根据需求，我们希望只要扫描逻辑能运行，就应该继续
        logger.info("No new tasks to run, but proceeding to analyze existing trajectories if any.")

    if md_files_to_run:
        logger.info(f"Starting execution of {len(md_files_to_run)} new tasks...")
    else:
        logger.info("No new tasks to run in this batch. Proceeding to analyze existing trajectories.")
        
    # Log settings (即使没有新任务，也打印配置信息)
    logger.info(f"User for trajectory path: {args.user_name}") 
    logger.info(f"Output base directory for new tasks: {Path(args.output_base_dir) / args.user_name}")
    logger.info(f"Base directory for scanning existing trajectories: {Path(args.output_base_dir) / args.user_name}")
    logger.info(f"Workers: {args.workers}")

    base_cmd = [
        'sweagent', 'run',
    ]
    # 为每个提供的配置文件路径添加一个 --config 参数
    if isinstance(args.config_path, list):
        for cfg_path in args.config_path:
            base_cmd.extend(['--config', cfg_path])
    else: #单个配置文件的情况
        base_cmd.extend(['--config', args.config_path])

    base_cmd.extend([
        '--agent.model.name', args.model_name,
        '--env.repo.path', args.repo_path,
        '--env.deployment.image', args.image,
    ])

    results_placeholder = {} # 用于跟踪任务的原始成功/失败和输出，以决定是否解析

    # 只有在有新任务要运行时才执行ThreadPoolExecutor
    if md_files_to_run:
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix='SWEAgentWorker') as executor:
            futures = {
                executor.submit(
                    run_sweagent_task,
                    base_cmd,
                    os.path.join(args.prompt_dir, md_file),
                        md_file,
                        Path(args.output_base_dir) / args.user_name / f"{args.model_name}-{os.path.splitext(md_file)[0]}"
                ): md_file
                for md_file in md_files_to_run
            }

            for future in as_completed(futures):
                task_name = futures[future]
                task_success = False
                task_output_str = ""
                model_stats_for_task = None
                cost_error_message = None

                try:
                    name, success, output_str = future.result()
                    results_placeholder[name] = {'success': success, 'output': output_str} # 存储原始结果
                    task_success = success
                    task_output_str = output_str
                except Exception as exc:
                    logger.error(f'{task_name} generated an exception during future processing: {exc}')
                    results_placeholder[task_name] = {'success': False, 'output': f"Exception: {str(exc)}"}
                    task_output_str = f"Exception: {str(exc)}"

                post_task_actions(
                    task_name=task_name,
                    host_repo_path=args.host_repo_path,
                    sleep_duration=args.sleep_duration,
                    skip_docker_prune=args.skip_docker_prune,
                    skip_git_commit=args.skip_git_commit
                )

                if task_success:
                    task_name_without_ext = os.path.splitext(task_name)[0]
                    custom_task_output_dir_for_find = Path(args.output_base_dir) / args.user_name / f"{args.model_name}-{task_name_without_ext}"
                    
                    traj_file = find_trajectory_file(
                        str(custom_task_output_dir_for_find),
                        args.user_name, 
                        args.model_name,
                        task_name 
                    )
                    if traj_file:
                        model_stats_for_task = parse_trajectory_stats(traj_file)
                        if not model_stats_for_task:
                            cost_error_message = f"Could not parse model_stats from trajectory: {traj_file}"
                    else:
                        cost_error_message = "Trajectory file not found for cost analysis."
                else: 
                    cost_error_message = task_output_str 

                # 调用新的辅助函数处理结果和成本
                format_and_process_task_result(
                    task_name=task_name,
                    model_name=args.model_name,
                    success=task_success,
                    output_str=task_output_str,
                    model_stats=model_stats_for_task, 
                    error_msg=cost_error_message 
                )
    else:
        logger.info("No new tasks to run in this batch. Proceeding to analyze existing trajectories.")

    # --- 扫描并补充处理所有符合条件的现有轨迹 (这部分逻辑现在总会执行) ---
    logger.info("--- Scanning for all existing relevant trajectories to complete the summary ---")
    processed_task_names_in_current_run = {entry['task_name'] for entry in batch_results_summary_list_for_file}
    
    base_scan_dir = Path(args.output_base_dir) / args.user_name
    if base_scan_dir.is_dir():
        for item_name in os.listdir(base_scan_dir):
            # 检查目录名是否以模型名开头，符合 model_name-task_name_no_ext 的模式
            if item_name.startswith(f"{args.model_name}-"):
                # 尝试从目录名中提取原始任务名（包括.md）
                # 例如，从 "gpt-4o-AnimeGANv3_03" 提取 "AnimeGANv3_03.md"
                potential_task_name_no_ext = item_name[len(args.model_name) + 1:]
                original_task_name_md = f"{potential_task_name_no_ext}.md"
                
                if original_task_name_md not in processed_task_names_in_current_run:
                    logger.info(f"Found existing task directory for (potentially skipped) task: {original_task_name_md}")
                    task_specific_output_dir = base_scan_dir / item_name
                    
                    traj_file = find_trajectory_file(
                        str(task_specific_output_dir), # 这是最顶层的任务目录
                        args.user_name, 
                        args.model_name,
                        original_task_name_md # 使用原始任务名
                    )
                    
                    model_stats = None
                    cost_error_message = None
                    success_for_skipped = False # 默认被跳过或未运行的任务是不成功的，除非能从轨迹解析出信息

                    if traj_file:
                        model_stats = parse_trajectory_stats(traj_file)
                        if model_stats:
                            success_for_skipped = True # 如果能解析出stats，认为任务至少部分成功过
                            logger.info(f"  Successfully parsed stats for existing task: {original_task_name_md}")
                        else:
                            cost_error_message = f"Could not parse model_stats from existing trajectory: {traj_file}"
                            logger.warning(f"  {cost_error_message}")
                    else:
                        cost_error_message = f"Trajectory file not found for existing task: {original_task_name_md} in {task_specific_output_dir}"
                        logger.warning(f"  {cost_error_message}")
                    
                    # 为这个之前运行或被跳过的任务添加/更新条目
                    # 注意：这里的 output_str 对于被跳过的任务将是未知的
                    format_and_process_task_result(
                        task_name=original_task_name_md,
                        model_name=args.model_name,
                        success=success_for_skipped, # 如果有轨迹并解析出stats，则认为成功
                        output_str="Skipped in current run or output not captured.",
                        model_stats=model_stats,
                        error_msg=cost_error_message
                    )
    logger.info("--- Finished scanning existing trajectories ---")
    # --------------------------------------------

    # Reporting (整体总结部分) - 现在 batch_results_summary_list_for_file 包含了所有任务
    successful_tasks = sum(1 for r_val in batch_results_summary_list_for_file if r_val['success'])
    failed_tasks = len(batch_results_summary_list_for_file) - successful_tasks
    
    # 保存 batch_results.jsonl 文件
    results_file_path = Path(args.output_base_dir) / args.user_name / "batch_results.jsonl"
    if args.user_name and not (Path(args.output_base_dir) / args.user_name).exists():
        try:
            (Path(args.output_base_dir) / args.user_name).mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning(f"Could not create user directory {Path(args.output_base_dir) / args.user_name}. Saving batch_results.jsonl to current directory.")
            results_file_path = Path("batch_results.jsonl")
    elif not args.user_name:
        if Path(args.output_base_dir).is_dir():
             results_file_path = Path(args.output_base_dir) / "batch_results.jsonl"
        else:
             results_file_path = Path("batch_results.jsonl")

    logger.info(f"Saving final batch summary to: {results_file_path.resolve()}")
    results_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file_path, 'w', encoding='utf-8') as f:
        for entry in batch_results_summary_list_for_file:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    logger.info("\n--- Overall Batch Run Summary ---")
    logger.info(f"Total tasks processed: {len(batch_results_summary_list_for_file)}")
    logger.info(f"Successful SWE-agent runs: {successful_tasks}")
    logger.info(f"Failed SWE-agent runs: {failed_tasks}")
    logger.info(f"Batch summary saved to: {results_file_path.resolve()}")
    
    if global_overall_total_cost > 0 or global_overall_total_tokens_sent > 0:
        logger.info("\n--- Overall Cost Summary ---")
        logger.info(f"Total cost: ${global_overall_total_cost:.4f}")
        logger.info(f"Total tokens sent: {global_overall_total_tokens_sent:,}")
        logger.info(f"Total tokens received: {global_overall_total_tokens_received:,}")
        logger.info(f"Total API calls: {global_overall_total_api_calls:,}")
        if successful_tasks > 0 and global_overall_total_cost > 0:
            logger.info(f"Average cost per successful task: ${global_overall_total_cost/successful_tasks:.4f}")
    
    if failed_tasks > 0:
        logger.warning("\nFailed SWE-agent runs list:")
        for entry in batch_results_summary_list_for_file:
            if not entry['success']:
                error_msg = entry.get('error')
                error_summary = error_msg.split('\n')[0][:100] if error_msg else "Unknown error"
                logger.warning(f"- {entry['task_name']} (Reason: {error_summary})")

if __name__ == "__main__":
    main() 