import json
import os
import argparse
import subprocess
import sys
import datetime
from pathlib import Path
import logging
import time
import re
import shutil
import signal
import shlex
import select

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MDBatchRunner")

# 全局变量，用于跟踪 Ctrl+C 状态
interrupt_count = 0
interrupted_current_task = False

def signal_handler(sig, frame):
    """处理 SIGINT (Ctrl+C)"""
    global interrupt_count, interrupted_current_task
    interrupt_count += 1
    interrupted_current_task = True
    if interrupt_count == 1:
        logger.warning("\n检测到 Ctrl+C！将尝试终止当前任务并继续下一个任务。")
        logger.warning("再次按下 Ctrl+C 将强制退出整个批处理。")
    elif interrupt_count >= 2:
        logger.warning("\n检测到第二次 Ctrl+C！强制退出批处理。")
        sys.exit(1)

def strip_ansi_codes(text: str) -> str:
    """移除文本中的ANSI转义码。"""
    ansi_escape = re.compile(r'\x1B(?:[@\-_]|\\\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='从 .md 文件批量运行 Aider 任务')
    parser.add_argument('--md-prompt-dir', type=str, required=True,
                        help='包含 .md 任务描述文件的主目录路径')
    parser.add_argument('--output-dir', type=str, default='./md_aider_runs',
                        help='主输出目录，用于存放所有任务日志和摘要。如果目录已存在且包含 batch_summary.json，脚本将尝试从中加载状态并跳过已成功完成的任务 (除非使用 --force-rerun)。')
    parser.add_argument('--keep-meta-workdirs', action='store_true',
                        help='为每个任务保留元数据工作目录 (包含stdout/stderr日志和Docker输入)')
    parser.add_argument('--model', type=str, default='gpt-4o',
                        help='要传递给 Aider 的 LLM 模型名称')
    parser.add_argument('--tasks', type=str, default=None,
                        help='指定要运行的任务列表 (.md 文件名，不含扩展名，逗号分隔)')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='设置脚本的日志级别')
    parser.add_argument('--aider-args', type=str, default=None,
                        help='传递给aider的额外参数字符串，例如 "--show-diff --auto-apply"')
    parser.add_argument('--force-rerun', action='store_true',
                        help='如果设置，将强制重新运行所有选定的任务，即使它们在之前的摘要中标记为成功完成。')
    parser.add_argument('--llm-api-key', type=str, default=None,
                        help='要用于 LLM 的 API 密钥。如果提供，将设置为 OPENAI_API_KEY 环境变量。')
    parser.add_argument('--llm-base-url', type=str, default=None,
                        help='LLM API 的基础 URL。如果提供，将设置为 OPENAI_API_BASE 环境变量。')
    parser.add_argument('--task-timeout', type=int, default=720,
                        help='单个 Aider 任务的最大执行时间（秒）。默认为 720 秒（12 分钟）。')
    return parser.parse_args()

def parse_md_task_file(md_file_path: Path) -> dict:
    content = md_file_path.read_text(encoding='utf-8')
    
    task_payload = {
        "repo_path": None,
        "input_files": [],
        "output_dir_expected": None,
        "original_md_path": str(md_file_path.resolve()),
    }

    repo_path_text_source = content
    input_files_matches = re.findall(r"文件路径 \\(绝对\\): (.*?)(?:\\n|$)", repo_path_text_source)
    task_payload["input_files"].extend([match.strip() for match in input_files_matches if match.strip()])

    output_dir_match = re.search(r"输出文件目录:(.*?)(?:,|$|\\n)", repo_path_text_source)
    if output_dir_match:
        task_payload["output_dir_expected"] = output_dir_match.group(1).strip()

    logger.debug(f"== DEBUG: Attempting to parse repo_path from content for {md_file_path.name} ==")
    # logger.debug(f"Full content for {md_file_path.name}:\n---\n{content}\n---") # Can be very verbose
    
    expected_key = "仓库路径 (绝对):"
    # Try to find the key with flexible spacing around colon for robustness
    flexible_key_match = re.search(r"仓库路径\s*\(绝对\)\s*:\s*", content)

    if flexible_key_match:
        start_index = flexible_key_match.start()
        # Extract a few lines for context
        lines_around = content[max(0, start_index - 100):min(len(content), start_index + 200)].splitlines()
        context_snippet = "\n".join(line for line in lines_around if expected_key in line or "仓库路径" in line)
        if not context_snippet: # Fallback if specific key not in snippet lines
            context_snippet = "\n".join(lines_around[:5]) # Show first 5 lines of the broader context
        logger.debug(f"Relevant content snippet for {md_file_path.name} (key '{expected_key}' found with flex search at {start_index}):\n---\n{context_snippet}\n---")
    else:
        logger.debug(f"The key '{expected_key}' was NOT found in {md_file_path.name} even with flexible spacing search.")

    # Original regex for repo path:
    # repo_path_match = re.search(r"仓库路径 \\(绝对\\): (.*?)(?:\\n|$)", content)
    # More robust regex, allowing for variable spaces and ensuring it captures until newline or end of string:
    repo_path_regex = r"^\s*仓库路径\s*\(绝对\)\s*:\s*(.*?)(?:\r?\n|$)"
    logger.debug(f"Repo path regex used: r'{repo_path_regex}'")
    
    # Search for the repo path line by line to handle potential multiline issues or leading/trailing spaces on the key line
    repo_path_value = None
    for line in content.splitlines():
        match = re.match(repo_path_regex, line.strip()) # .strip() on line to handle potential leading/trailing spaces for the line itself
        if match:
            repo_path_value = match.group(1).strip()
            break # Found it
            
    if repo_path_value:
        task_payload["repo_path"] = repo_path_value
        logger.debug(f"Repo path MATCHED for {md_file_path.name}! Extracted: '{repo_path_value}'")
    else:
        logger.debug(f"Repo path DID NOT MATCH for {md_file_path.name} using line-by-line regex scan.")
    logger.debug(f"== DEBUG: End parsing repo_path for {md_file_path.name} ==")

    if not task_payload["repo_path"]:
        logger.warning(f"仓库路径未在 {md_file_path.name} 中明确找到。Aider 运行可能依赖于 CWD 或其内部逻辑来确定仓库。")

    return {
        "_task_name_original": md_file_path.stem,
        "name": md_file_path.stem,
        "payload": task_payload
    }

def load_tasks(md_prompt_dir: str) -> list[dict]:
    md_prompt_path = Path(md_prompt_dir)
    task_configs = []
    if not md_prompt_path.is_dir():
        logger.error(f"错误: 指定的 MD Prompt 路径 '{md_prompt_path}' 不是一个有效的目录。")
        sys.exit(1)
    logger.info(f"从 MD Prompt 目录加载任务: {md_prompt_path}")
    for item in sorted(md_prompt_path.glob("*.md")):
        if item.is_file():
            logger.info(f"  发现任务文件: {item.name}")
            try:
                task_config = parse_md_task_file(item)
                task_configs.append(task_config)
            except Exception as e:
                logger.error(f"无法解析任务文件 '{item.name}': {e} - 跳过", exc_info=True)
    if not task_configs:
        logger.error(f"错误: 在目录 '{md_prompt_path}' 下未能加载任何有效的 .md 任务。")
        sys.exit(1)
    return task_configs

def sanitize_filename(name: str) -> str:
    name = str(name)
    name = re.sub(r'[<>:"/\\\\|?*\s]+', '_', name)
    return name[:100]

def run_single_task(task_config: dict, base_output_dir: Path, index: int, args: argparse.Namespace) -> dict:
    global interrupted_current_task
    task_name_original = task_config.get('_task_name_original', f'task_{index + 1:03d}')
    task_name_sanitized = sanitize_filename(task_config.get('name', task_name_original))
    
    task_payload = task_config["payload"]
    repo_to_edit_str = task_payload.get("repo_path")
    input_files_for_aider = task_payload.get("input_files", [])
    original_md_file_path_str = task_payload.get("original_md_path")

    # Initialize summary lists early to prevent UnboundLocalError
    stdout_lines_for_summary: list[str] = []
    stderr_lines_for_summary: list[str] = []
    max_summary_lines = 20

    # Token usage tracking
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    # Regex to capture token usage from Aider's output, accommodating 'k' for thousands.
    # Example: "Tokens: 10k sent, 645 received."
    # Groups: 1: sent_num, 2: sent_suffix (k or empty), 3: recv_num, 4: recv_suffix (k or empty)
    token_usage_regex = re.compile(r"Tokens: (\d+)([kK]?)\s*sent, (\d+)([kK]?)\s*received")

    task_meta_workdir = base_output_dir / task_name_sanitized
    task_meta_workdir.mkdir(parents=True, exist_ok=True)
    meta_workdir_path_str = str(task_meta_workdir.resolve())

    logger.info(f"---")
    logger.info(f"开始执行任务 {index + 1}: {task_name_sanitized} (源 MD: {task_name_original}.md)")
    logger.info(f"此任务的日志/元数据将保存在: {meta_workdir_path_str}")

    if not repo_to_edit_str:
        logger.error(f"任务 {task_name_sanitized}: 未在MD文件中指定仓库路径 (repo_path)。跳过任务。")
        return {
            "task_name_original": task_name_original,
            "md_file_path": original_md_file_path_str,
            "meta_workdir": meta_workdir_path_str,
            "repo_path_intended": repo_to_edit_str,
            "overall_success": False, "exit_code": -1, "duration_seconds": 0, "status_message": "配置错误",
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "stdout_preview": [], "stderr_preview": ["未在MD文件中指定仓库路径 (repo_path)。"],
        }
    
    repo_to_edit = Path(repo_to_edit_str)
    if not repo_to_edit.is_dir():
        logger.error(f"任务 {task_name_sanitized}: 指定的仓库路径 \'{repo_to_edit_str}\' 不是一个有效的目录。跳过任务。")
        return {
            "task_name_original": task_name_original,
            "md_file_path": original_md_file_path_str,
            "meta_workdir": meta_workdir_path_str,
            "repo_path_intended": repo_to_edit_str,
            "overall_success": False, "exit_code": -2, "duration_seconds": 0, "status_message": "配置错误",
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "stdout_preview": [], "stderr_preview": [f"指定的仓库路径 '{repo_to_edit_str}' 不是一个有效的目录。"],
        }

    # --- Aider command construction ---
    # Base command
    aider_command = ['aider', '--model', args.model, '--yes-always'] # --yes-always is now default based on prior fixes

    # Add files for Aider to process (including the original .md as message file)
    for file_path_str in input_files_for_aider:
        # Ensure the file exists before adding it, or Aider might complain.
        # However, Aider itself should handle non-existent files gracefully.
        # For now, we assume paths provided in .md are meant to be passed.
        # We are NOT adding them to aider_command here anymore, as they are part of the .md prompt
        pass 
    
    # Add the .md file itself as the primary message/instruction file
    if original_md_file_path_str:
         # Read the content of the MD file, remove proxy command, pass as --message
        original_md_content = Path(original_md_file_path_str).read_text(encoding='utf-8')
        
        # Regex to find and comment out the proxy command
        # This will find "eval $(curl ...)" and replace it with "# eval $(curl ...)"
        # It handles variations in spacing and the exact curl command.
        proxy_command_pattern = re.compile(r"^\\s*(eval\\s*\\$\\((?:curl|wget)[^)]+\\))\\s*$", re.MULTILINE)
        modified_md_content = proxy_command_pattern.sub(r"# \\1", original_md_content)

        if modified_md_content != original_md_content:
            logger.info(f"任务 {task_name_sanitized}: 从MD内容中注释掉了代理命令。")
        
        # Use a temporary file for the modified message if it's too long for an argument
        # For now, passing directly via --message. If issues arise, switch to temp file.
        aider_command.extend(['--message', modified_md_content])
    else:
        logger.warning(f"任务 {task_name_sanitized}: 原始 MD 文件路径未提供，无法作为 --message 传递。")


    # Add any extra Aider arguments from command line
    if args.aider_args:
        aider_command.extend(shlex.split(args.aider_args))
    
    # Log files for Aider history
    aider_command.extend([
        '--chat-history-file', str(task_meta_workdir / f"{task_name_sanitized}.aider.chat.history.md"),
        '--input-history-file', str(task_meta_workdir / f"{task_name_sanitized}.aider.input.history"),
        '--llm-history-file', str(task_meta_workdir / f"{task_name_sanitized}.aider.llm.history.jsonl"),
    ])

    logger.info(f"任务 {task_name_sanitized}: Aider 命令: {' '.join(shlex.quote(str(c)) for c in aider_command)}")
    command_cwd = str(repo_to_edit.resolve()) # CWD for Aider is the repo itself
    logger.info(f"任务 {task_name_sanitized}: Aider CWD: {command_cwd}")
    
    current_env = os.environ.copy()
    if args.llm_api_key:
        current_env["OPENAI_API_KEY"] = args.llm_api_key
    if args.llm_base_url:
        current_env["OPENAI_API_BASE"] = args.llm_base_url
        current_env["LITELLM_BASE_URL"] = args.llm_base_url # Also for litellm

    # --- Proxy Setup Restoration for Aider Subprocess ---
    # This ensures Aider itself runs with the proxy, if defined.
    # The proxy command was removed from the .md content Aider reads,
    # but the Aider process itself should run under the proxy.
    proxy_setup_script = 'eval $(curl -s http://deploy.i.shaipower.com/httpproxy)'
    # Wrap the Aider command: bash -c 'proxy_script && exec aider_command ...'
    # `exec "$@"` ensures that `bash` replaces itself with the `aider` command,
    # so Aider becomes the direct child of this script for signal handling.
    # The arguments to aider_command are passed after 'bash'.
    final_command_for_popen = ['bash', '-c', f'{proxy_setup_script} && exec "$@"', 'bash'] + aider_command
    logger.info(f"执行代理设置并包装命令: {' '.join(shlex.quote(str(c)) for c in final_command_for_popen)}")
    logger.info(f"DEBUG: Final command for Popen before execution: {final_command_for_popen}")
        # --- End Proxy Setup Restoration ---

    stdout_file_path = task_meta_workdir / "aider_stdout.live.log"
    stderr_file_path = task_meta_workdir / "aider_stderr.live.log"
    logger.info(f"实时 Aider 输出 (stdout) 将保存到: {stdout_file_path}")
    logger.info(f"实时 Aider 错误输出 (stderr) 将保存到: {stderr_file_path}")

    stdout_full_bytes = b""
    stderr_full_bytes = b""
    exit_code: int = -1 # Default exit code
    overall_success: bool = False # Default status
    status_message: str = "未知错误" # Default message
    status_message_override: str = "" # For specific overrides like timeout

    start_time = time.monotonic()
    process = None
    try:
        process = subprocess.Popen(
            final_command_for_popen,
            cwd=command_cwd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False, # Handle bytes directly for robustness
            env=current_env,
            # preexec_fn=os.setsid # To run in a new session, useful for detaching, but might affect Ctrl+C
        )
        logger.info(f"Aider 进程已启动 (PID: {process.pid}) for task: {task_name_sanitized}")

        # Real-time output processing
        with open(stdout_file_path, 'wb') as f_stdout, open(stderr_file_path, 'wb') as f_stderr:
            while True:
                reads = [process.stdout.fileno(), process.stderr.fileno()]
                ret = select.select(reads, [], []) # Blocking call with no timeout here

                for fd in ret[0]:
                    if fd == process.stdout.fileno():
                        read_bytes = process.stdout.read1(1024) # Read non-blockingly
                        if read_bytes:
                            f_stdout.write(read_bytes)
                            f_stdout.flush()
                            stdout_full_bytes += read_bytes
                    elif fd == process.stderr.fileno():
                        read_bytes = process.stderr.read1(1024) # Read non-blockingly
                        if read_bytes:
                            f_stderr.write(read_bytes)
                            f_stderr.flush()
                            stderr_full_bytes += read_bytes

                if process.poll() is not None: # Process has terminated
                    break

            # After process terminates, read any remaining buffered output
            remaining_stdout = process.stdout.read()
            if remaining_stdout:
                f_stdout.write(remaining_stdout)
                f_stdout.flush()
                stdout_full_bytes += remaining_stdout
            
            remaining_stderr = process.stderr.read()
            if remaining_stderr:
                f_stderr.write(remaining_stderr)
                f_stderr.flush()
                stderr_full_bytes += remaining_stderr

        logger.info(f"等待 Aider 进程完成 (超时时间: {args.task_timeout}s): {task_name_sanitized}")
        _comm_stdout, _comm_stderr = process.communicate(timeout=args.task_timeout)
        
        if _comm_stdout: stdout_full_bytes += _comm_stdout
        if _comm_stderr: stderr_full_bytes += _comm_stderr
        
        exit_code = process.returncode
        logger.info(f"Aider 进程 {task_name_sanitized} 已正常退出，退出码: {exit_code}")

    except subprocess.TimeoutExpired:
        logger.error(f"任务 {task_name_sanitized} 超时 (超过 {args.task_timeout} 秒)!")
        stderr_lines_for_summary.append(f"任务执行超时 (超过 {args.task_timeout} 秒)。")
        status_message_override = "超时"
        overall_success = False
        exit_code = -99 # Special exit code for timeout
        
        if process:
            logger.warning(f"尝试终止超时进程 PID: {process.pid}...")
            try:
                process.terminate() # SIGTERM
                try:
                    process.wait(timeout=10) # Wait for graceful termination
                    logger.info(f"超时进程 PID: {process.pid} 已终止。")
                except subprocess.TimeoutExpired:
                    logger.warning(f"进程 PID: {process.pid} 未能在10秒内终止，尝试强制杀死...")
                    process.kill() # SIGKILL
                    process.wait() # Ensure kill is processed
                    logger.info(f"进程 PID: {process.pid} 已被强制杀死。")
            except Exception as e_term:
                logger.error(f"终止/杀死进程 PID: {process.pid} 时发生错误: {e_term}")
        
        if process and process.stdout and not process.stdout.closed:
            try: 
                final_stdout_bytes = process.stdout.read()
                if final_stdout_bytes: stdout_full_bytes += final_stdout_bytes
            except: pass
        if process and process.stderr and not process.stderr.closed:
            try:
                final_stderr_bytes = process.stderr.read()
                if final_stderr_bytes: stderr_full_bytes += final_stderr_bytes
            except: pass

    except KeyboardInterrupt:
        logger.warning(f"任务 {task_name_sanitized} 被用户中断 (Ctrl+C)。")
        interrupted_current_task = True # Signal to main loop
        # Attempt to terminate the child process if it's running
        if process and process.poll() is None:
            logger.warning(f"尝试终止由 Ctrl+C 中断的子进程 PID: {process.pid}...")
            try:
                process.terminate()
                time.sleep(1) # Give it a moment
                if process.poll() is None: # Still running
                    process.kill()
                    logger.info(f"子进程 PID: {process.pid} 已被强制杀死。")
                else:
                    logger.info(f"子进程 PID: {process.pid} 已终止。")
            except Exception as e_kill:
                logger.error(f"杀死子进程 PID: {process.pid} 时出错: {e_kill}")
        # Specific exit code for KeyboardInterrupt if not set by process
        exit_code = -98 if process is None or process.poll() is None else process.returncode

    finally:
        if process and process.poll() is None: # Should not happen if communicate/wait completed or timeout/interrupt handled
            logger.warning(f"Aider 进程 {task_name_sanitized} (PID: {process.pid}) 在 finally 块中仍在运行。尝试最后清理。")
            try:
                process.kill()
                process.wait(timeout=5)
            except Exception as e_final_kill:
                logger.error(f"Final kill attempt for PID {process.pid} failed: {e_final_kill}")

        duration_seconds = time.monotonic() - start_time

        # Decode stdout/stderr for summary
        # Use 'replace' for robustness against decoding errors
        stdout_str = stdout_full_bytes.decode('utf-8', errors='replace')
        stderr_str = stderr_full_bytes.decode('utf-8', errors='replace')

        # Extract token usage from stdout
        for line in stdout_str.splitlines():
            match = token_usage_regex.search(line)
            if match:
                try:
                    sent_num_str, sent_suffix, recv_num_str, recv_suffix = match.groups()
                    
                    current_sent = int(sent_num_str)
                    if sent_suffix.lower() == 'k':
                        current_sent *= 1000
                    
                    current_recv = int(recv_num_str)
                    if recv_suffix.lower() == 'k':
                        current_recv *= 1000
                    
                    input_tokens += current_sent
                    output_tokens += current_recv
                    # total_tokens is calculated at the end of the summary in the current script structure
                    # For a running total within the loop, it would be: total_tokens += current_sent + current_recv
                    # However, the current script initializes total_tokens and then sums input_tokens and output_tokens later.
                    # To maintain consistency with that, we just update input_tokens and output_tokens here.
                    # The final total_tokens will be sum of all input_tokens and output_tokens after the loop.

                except ValueError:
                    logger.warning(f"无法从行解析 token 数量: {line}")
        
        # Recalculate total_tokens based on accumulated input_tokens and output_tokens
        total_tokens = input_tokens + output_tokens

        stdout_lines = stdout_str.splitlines()
        stderr_lines = stderr_str.splitlines()

        stdout_lines_for_summary.extend(stdout_lines[-max_summary_lines:])
        stderr_lines_for_summary.extend(stderr_lines[-max_summary_lines:])

        if status_message_override: # Set by TimeoutExpired
            status_message = status_message_override
            # overall_success and exit_code already set in TimeoutExpired block
        elif interrupted_current_task:
            status_message = "用户中断"
            overall_success = False
            if exit_code == -1 or exit_code == -98: # if -1 (default) or already -98 (set by kbd int.)
                 exit_code = -98 
        elif exit_code == 0:
            status_message = "成功"
            overall_success = True
        else:
            status_message = f"失败 (退出码: {exit_code})"
            overall_success = False
        
        logger.info(f"任务 {task_name_sanitized} 完成。状态: {status_message}，耗时: {duration_seconds:.2f}s，退出码: {exit_code}")
        if input_tokens > 0 or output_tokens > 0:
            logger.info(f"任务 {task_name_sanitized}: Tokens - Sent: {input_tokens}, Received: {output_tokens}, Total: {total_tokens}")

        if not args.keep_meta_workdirs and overall_success:
            try:
                # shutil.rmtree(task_meta_workdir)
                # logger.info(f"已删除成功的任务元数据目录: {task_meta_workdir}")
                pass # 保留目录，直到测试验证OK
            except Exception as e_rm:
                logger.warning(f"无法删除任务元数据目录 {task_meta_workdir}: {e_rm}")
        
        return {
        "task_name_original": task_name_original,
        "md_file_path": original_md_file_path_str,
        "meta_workdir": meta_workdir_path_str, 
            "repo_path_intended": repo_to_edit_str,
            "overall_success": overall_success,
        "exit_code": exit_code,
            "duration_seconds": round(duration_seconds, 2),
            "status_message": status_message,
            "input_tokens": input_tokens,
        "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "stdout_preview": [strip_ansi_codes(line) for line in stdout_lines_for_summary],
            "stderr_preview": [strip_ansi_codes(line) for line in stderr_lines_for_summary],
    }

def save_batch_summary(summary_data: dict, summary_file_path: Path):
    """将批处理摘要数据写入指定的JSON文件。"""
    try: 
        with open(summary_file_path, 'w', encoding='utf-8') as f: 
            json.dump(summary_data, f, indent=4, ensure_ascii=False)
        logger.info(f"批处理摘要已更新并写入: {summary_file_path}")
    except Exception as e: 
        logger.error(f"写入批处理摘要文件 '{summary_file_path}' 失败: {e}")

def main():
    # print(f"DEBUG: Raw sys.argv: {sys.argv}") # Keep for now, remove after fix confirmed
    signal.signal(signal.SIGINT, signal_handler)
    args = parse_arguments()
    logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))

    # Use the specified output directory directly, no timestamped subdirectory
    batch_output_dir = Path(args.output_dir)
    try: 
        batch_output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e: 
        logger.error(f"无法创建或访问批处理输出目录 '{batch_output_dir}': {e}"); sys.exit(1)
    logger.info(f"批处理主输出/日志目录: {batch_output_dir}")

    # Trajectory directory will be directly under the main output directory
    traj_dir = batch_output_dir / "traj" # Changed from args.output_dir to batch_output_dir
    try:
        traj_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"共享轨迹文件目录: {traj_dir}")
    except Exception as e:
        logger.error(f"无法创建轨迹文件目录 '{traj_dir}': {e}")

    all_task_configs = load_tasks(args.md_prompt_dir)
    total_tasks_available_in_dir = len(all_task_configs) # Renamed for clarity
    logger.info(f"在 MD Prompt 目录中发现 {total_tasks_available_in_dir} 个可用任务。")

    # --- Load previous summary and initialize results ---
    summary_file_path = batch_output_dir / "batch_summary.json"
    all_results: list[dict] = [] # Holds results from previous runs and this run
    completed_successfully_task_names: set[str] = set()

    if summary_file_path.exists() and not args.force_rerun:
        logger.info(f"发现现有摘要文件: {summary_file_path}，将加载并跳过已成功完成的任务。")
        try:
            with open(summary_file_path, 'r', encoding='utf-8') as f:
                previous_summary = json.load(f)
            # Use 'tasks_results' if it exists, otherwise try 'tasks' for backward compatibility
            loaded_results = previous_summary.get("tasks_results", previous_summary.get("tasks", []))
            all_results.extend(loaded_results) # Start with all previous results
            for res in loaded_results:
                if res.get("overall_success"):
                    completed_successfully_task_names.add(res.get("task_name_original"))
            logger.info(f"从摘要中加载了 {len(loaded_results)} 个任务结果，其中 {len(completed_successfully_task_names)} 个已成功。")
        except Exception as e:
            logger.warning(f"加载或解析现有摘要文件 '{summary_file_path}' 失败: {e}。将运行所有选定任务。")
            all_results = [] # Reset if loading failed
            completed_successfully_task_names = set()
    elif summary_file_path.exists() and args.force_rerun:
        logger.info(f"--force-rerun 已设置。将从现有摘要 '{summary_file_path}' 加载结果，但会重跑选定的任务。")
        try:
            with open(summary_file_path, 'r', encoding='utf-8') as f:
                previous_summary = json.load(f)
            # Load all previous results initially. We'll filter out those that are part of the current --tasks selection later.
            all_results.extend(previous_summary.get("tasks_results", previous_summary.get("tasks", [])))
            logger.info(f"从摘要中加载了 {len(all_results)} 个历史任务结果。选定的任务将被强制重跑。")
        except Exception as e:
            logger.warning(f"加载或解析现有摘要文件 '{summary_file_path}' 失败: {e}。")
            all_results = [] # Reset if loading failed
    else:
        logger.info("未找到现有摘要文件或未指定从摘要加载的逻辑。")

    # --- Filter tasks based on names from --tasks CLI arg ---
    selected_task_configs_from_cli: list[dict] = []
    if args.tasks:
        target_task_names_from_cli = {name.strip() for name in args.tasks.split(',') if name.strip()}
        logger.info(f"根据 --tasks 参数筛选任务 (基于 .md 文件名不含扩展名)，请求运行: {', '.join(target_task_names_from_cli)}")
        selected_task_configs_from_cli = [
            c for c in all_task_configs if c.get('_task_name_original') in target_task_names_from_cli
        ]
        # Warnings for missing names
        found_names_in_dir = {c.get('_task_name_original') for c in selected_task_configs_from_cli}
        missing_names_in_dir = target_task_names_from_cli - found_names_in_dir
        if missing_names_in_dir:
            logger.warning(f"警告: 在 MD Prompt 目录中未找到以下 --tasks 指定的任务名称: {', '.join(missing_names_in_dir)}")
    else:
        logger.info("未指定 --tasks 参数，将考虑所有在 MD Prompt 目录中找到的任务。")
        selected_task_configs_from_cli = all_task_configs # All tasks from dir are candidates

    # --- Further filter tasks based on completion status (if not --force-rerun) ---
    tasks_to_run_this_session: list[dict] = []
    if args.force_rerun:
        tasks_to_run_this_session = selected_task_configs_from_cli
        logger.info(f"--force-rerun: 将尝试运行 {len(tasks_to_run_this_session)} 个选定任务，无论其先前状态如何。")
        # If forcing rerun, remove these tasks from 'all_results' so they don't appear duplicated later.
        # We keep results for tasks NOT in the current forced run.
        task_names_to_force_rerun = {t.get("_task_name_original") for t in tasks_to_run_this_session}
        all_results = [res for res in all_results if res.get("task_name_original") not in task_names_to_force_rerun]
        logger.info(f"强制重跑前，已从 all_results 中移除 {len(task_names_to_force_rerun)} 个任务的旧条目。现在 all_results 包含 {len(all_results)} 个非重跑任务的条目。")

    else: # Not --force-rerun, so skip successfully completed tasks
        for task_config in selected_task_configs_from_cli:
            task_name = task_config.get('_task_name_original')
            if task_name in completed_successfully_task_names:
                logger.info(f"任务 '{task_name}' 已在先前成功完成，且未指定 --force-rerun。跳过。")
            else:
                tasks_to_run_this_session.append(task_config)
        logger.info(f"过滤后 (跳过已成功完成的)，本轮会话计划运行 {len(tasks_to_run_this_session)} 个任务。")
    
    total_tasks_selected_for_run = len(tasks_to_run_this_session) # Renamed for clarity
    if not tasks_to_run_this_session: 
        logger.info("没有需要在此会话中运行的新任务或强制重跑的任务。")
        # Save summary even if no tasks run, to update timestamps etc.
        batch_session_start_time = time.time()
        current_batch_session_duration = round(time.time() - batch_session_start_time, 2)
        summary_data = {
            "batch_last_session_start_iso": datetime.datetime.now().isoformat(),
            "total_tasks_available_in_dir": total_tasks_available_in_dir,
            "total_tasks_selected_for_this_session_run": 0, # No tasks selected to run
            "total_tasks_attempted_this_session": 0,
            "overall_batch_success_this_session": True, # No failures as no tasks ran
            "batch_was_interrupted_this_session": False,
            "current_batch_session_duration_seconds": current_batch_session_duration,
            "tasks_results": all_results # Contains all historical results
        }
        save_batch_summary(summary_data, summary_file_path)
        sys.exit(0) # Exit cleanly
    
    logger.info(f"本轮会话共选中 {total_tasks_selected_for_run} 个任务进行处理。")

    # all_results is already initialized with historical data (or empty if no history / load fail)
    # overall_batch_success will track success *for this session*
    overall_batch_success_this_session = True 
    batch_interrupted_this_session = False # Tracks interruption *for this session*
    tasks_attempted_this_session = 0
    global interrupt_count
    
    batch_session_start_time = time.time() # Timestamp for the start of this specific run/session
    # summary_file_path is already defined

    for i, task_config in enumerate(tasks_to_run_this_session): # Iterate over tasks_to_run_this_session
        tasks_attempted_this_session += 1
        global interrupted_current_task
        interrupted_current_task = False
        
        # Find original index if needed (e.g. if all_task_configs was the base for indexing before filtering)
        # For logging or consistent ID, it's better to rely on task_name_original directly.
        # original_index_in_load_order = all_task_configs.index(task_config) if task_config in all_task_configs else i
        # Using 'i' relative to tasks_to_run_this_session for task numbering in this session.
        
        result = run_single_task(task_config, batch_output_dir, i, args) # Pass 'i' as current index
        
        # Update all_results: remove old entry for this task (if any from failed/interrupted prev. run) and add new one
        task_name_original = result.get("task_name_original")
        all_results = [res for res in all_results if res.get("task_name_original") != task_name_original]
        all_results.append(result)
            
        if not result.get("overall_success", False): 
            overall_batch_success_this_session = False

        # 更新并保存摘要
        current_batch_session_duration = round(time.time() - batch_session_start_time, 2)
        summary_data = {
            "batch_last_session_start_iso": datetime.datetime.fromtimestamp(batch_session_start_time).isoformat(),
            "total_tasks_available_in_dir": total_tasks_available_in_dir,
            "total_tasks_selected_for_this_session_run": total_tasks_selected_for_run,
            "total_tasks_attempted_this_session": tasks_attempted_this_session,
            "overall_batch_success_this_session": overall_batch_success_this_session and not batch_interrupted_this_session,
            "batch_was_interrupted_this_session": batch_interrupted_this_session,
            "current_batch_session_duration_seconds": current_batch_session_duration,
            "tasks_results": all_results # Contains all results (historical and current session)
        }
        save_batch_summary(summary_data, summary_file_path)
        
        if interrupt_count >= 2: 
            logger.warning("检测到第二次 Ctrl+C，停止后续任务执行。")
            batch_interrupted_this_session = True # Mark as interrupted before breaking
            summary_data["batch_was_interrupted_this_session"] = True
            summary_data["overall_batch_success_this_session"] = False 
            save_batch_summary(summary_data, summary_file_path)
            break
            
    logger.info(f"--- MD 文件批处理会话 ({datetime.datetime.fromtimestamp(batch_session_start_time).isoformat()}) 执行结束 ---")
    final_exit_code = 0
    if batch_interrupted_this_session: 
        logger.warning(f"本批处理会话因用户连续两次 Ctrl+C 而提前终止。")
        final_exit_code = 1
    elif not overall_batch_success_this_session: 
        logger.error(f"本批处理会话完成，但至少有一个任务失败。")
        final_exit_code = 2 # Changed to 2 to differentiate from general interrupt
    else: 
        logger.info(f"本批处理会话中所有选定并尝试的任务据报告成功完成。")
    
    # Check overall status from all_results for a historical perspective if needed
    # For now, exit code reflects *this session's* outcome.
    sys.exit(final_exit_code)

if __name__ == "__main__":
    main() 