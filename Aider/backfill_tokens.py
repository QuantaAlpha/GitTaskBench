#!/usr/bin/env python3
import json
import argparse
import logging
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("TokenBackfiller")

# Regex to capture token usage from Aider's output, accommodating 'k' for thousands.
# Example: "Tokens: 10k sent, 432 received. Cost: $0.03 message, $0.03 session."
# 正则表达式组：1: 发送的数字, 2: 发送的后缀 (k 或空), 3: 接收的数字, 4: 接收的后缀 (k 或空)
TOKEN_USAGE_REGEX =r"Tokens: \b(\d+k?)\b"

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill token usage data into batch_summary.json from Aider logs.")
    parser.add_argument(
        "--summary-file",
        type=Path,
        required=True,
        help="Path to the batch_summary.json file to update."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Path to the main batch output directory (e.g., ./aider_batch_runs_litellm_output) containing task subdirectories."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the script's logging level."
    )
    return parser.parse_args()

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string to be a valid filename.
    This should ideally match the sanitization used in md_batch_runner.py if task directories are sanitized.
    """
    logger.debug(f"[sanitize_filename] INPUT: '{name}' (type: {type(name)})")
    logger.debug(f"[sanitize_filename] INPUT (ASCII): {ascii(name)}")
    original_name_for_debug = name
    name = str(name)
    name = re.sub(r'[<>:"/\\\\|?*\\s]+', '_', name)
    name = name[:100]
    logger.debug(f"[sanitize_filename] OUTPUT for '{original_name_for_debug}': '{name}'")
    return name

def find_token_logs(task_meta_workdir: Path, task_name_sanitized: str) -> list[Path]:
    """Finds potential Aider log files containing token information."""
    log_files = []
    # Priority 1: The .aider.chat.history.md file specific to the task (often in task_meta_workdir)
    chat_history_file = task_meta_workdir / f"{task_name_sanitized}.aider.chat.history.md"
    if chat_history_file.is_file():
        log_files.append(chat_history_file)
        logger.debug(f"Found chat history log: {chat_history_file}")

    # Priority 2: The live stdout log
    stdout_log_file = task_meta_workdir / "aider_stdout.live.log"
    if stdout_log_file.is_file():
        log_files.append(stdout_log_file)
        logger.debug(f"Found stdout live log: {stdout_log_file}")
    
    # Fallback for older structures or different naming in traj/
    # This part might need adjustment based on the exact structure of `traj` files if they are primary.
    # Assuming traj files are named consistently with task_name_sanitized if they exist.
    traj_dir_path = task_meta_workdir.parent / "traj" # Assuming traj is sibling to task output dirs
    if traj_dir_path.is_dir():
        traj_chat_history_file = traj_dir_path / f"{task_name_sanitized}.aider.chat.history.md" # Example naming
        if traj_chat_history_file.is_file() and traj_chat_history_file not in log_files:
            log_files.append(traj_chat_history_file)
            logger.debug(f"Found chat history log in traj: {traj_chat_history_file}")

    if not log_files:
        logger.warning(f"No token log files found for task in dir: {task_meta_workdir}")
    return log_files


def parse_tokens_from_file(log_file_path: Path) -> tuple[int, int]:
    """Parses a single log file and returns total input and output tokens found."""
    cumulative_input_tokens = 0
    cumulative_output_tokens = 0
    try:
        content = log_file_path.read_text(encoding='utf-8', errors='replace')
        logger.debug(f"  Reading and parsing token lines from: {log_file_path}")
        lines_processed = 0
        lines_matched = 0
        for i, line in enumerate(content.splitlines()):
            lines_processed += 1
            stripped_line = line.strip()
            if not stripped_line: # Skip empty lines
                continue

            match = re.findall(TOKEN_USAGE_REGEX, stripped_line)
            print(f"match: {match}")
            if match:
                lines_matched +=1
                logger.debug(f"    Line {i+1} MATCHED: '{stripped_line}'")
                try:
                    sent_num_str, sent_suffix, recv_num_str, recv_suffix = match.groups()
                    
                    current_sent = int(sent_num_str)
                    if sent_suffix.lower() == 'k':
                        current_sent *= 1000
                    
                    current_recv = int(recv_num_str)
                    if recv_suffix.lower() == 'k':
                        current_recv *= 1000
                    
                    cumulative_input_tokens += current_sent
                    cumulative_output_tokens += current_recv
                    logger.debug(f"      Parsed: sent={current_sent}, recv={current_recv}. Cumulative: in={cumulative_input_tokens}, out={cumulative_output_tokens}")
                except ValueError:
                    logger.warning(f"    Could not parse token numbers from matched line in {log_file_path}: '{stripped_line}'")
                except Exception as e_parse:
                    logger.error(f"    Error parsing matched token line in {log_file_path}: '{stripped_line}' - {e_parse}")
            # else: # Optionally log non-matching lines if needed for deep debugging
            #    if "token" in stripped_line.lower(): # Log lines that mention token but didn't match
            #        logger.debug(f"    Line {i+1} NON-MATCH (but contains 'token'): '{stripped_line}'")


        logger.debug(f"  Finished parsing {log_file_path}. Lines processed: {lines_processed}, lines matched for tokens: {lines_matched}.")

    except Exception as e_read:
        logger.error(f"Could not read or process log file {log_file_path}: {e_read}")
    
    if cumulative_input_tokens > 0 or cumulative_output_tokens > 0 or lines_matched > 0: # Log if any match occurred or tokens found
        logger.debug(f"  Final parsed from {log_file_path}: {cumulative_input_tokens} sent, {cumulative_output_tokens} received")
    return cumulative_input_tokens, cumulative_output_tokens

def main():
    # TEMPORARY DEBUGGING:
    test_name1 = "InvisibleWatermark_01"
    # Need to ensure logger is configured before use if main is called directly
    # For safety, re-fetch logger here if not globally configured early enough for this test
    # However, basicConfig at top level should be fine.
    current_logger = logging.getLogger("TokenBackfiller") # Use specific logger instance
    current_logger.info(f"TEMP DEBUG: Logger level for TokenBackfiller: {logging.getLevelName(current_logger.getEffectiveLevel())}")
    
    sanitized_test_name1 = sanitize_filename(test_name1)
    current_logger.info(f"TEMP DEBUG: sanitize_filename('{test_name1}') -> '{sanitized_test_name1}'")

    test_name2 = "Eparse_03"
    sanitized_test_name2 = sanitize_filename(test_name2)
    current_logger.info(f"TEMP DEBUG: sanitize_filename('{test_name2}') -> '{sanitized_test_name2}'")

    test_name3 = "A B C D.md"
    sanitized_test_name3 = sanitize_filename(test_name3)
    current_logger.info(f"TEMP DEBUG: sanitize_filename('{test_name3}') -> '{sanitized_test_name3}'")


    args = parse_arguments()
    # Ensure logger level is set from args AFTER the temp debug, or set it manually for temp debug
    # Setting it from args here as intended by original script structure.
    logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))
    # Re-log the level to confirm it's set by args if different from initial default
    current_logger.info(f"Logger level for TokenBackfiller set to: {args.log_level}") 


    if not args.summary_file.is_file():
        logger.error(f"Summary file not found: {args.summary_file}")
        sys.exit(1)

    if not args.output_dir.is_dir():
        logger.error(f"Batch output directory not found: {args.output_dir}")
        sys.exit(1)

    try:
        with open(args.summary_file, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
    except Exception as e:
        logger.error(f"Could not load or parse summary file {args.summary_file}: {e}")
        sys.exit(1)

    tasks_results = summary_data.get("tasks_results", [])
    if not tasks_results:
        logger.info("No task results found in the summary file. Nothing to backfill.")
        sys.exit(0)

    updated_count = 0
    for task_entry in tasks_results:
        task_name_original_from_json = task_entry.get("task_name_original") # Usually the .md file stem
        # 'name' from task_config in md_batch_runner.py is saved as 'name' in summary.
        name_field_from_json = task_entry.get("name") 

        # Determine the name that was actually sanitized by md_batch_runner.py
        # It prioritizes task_config['name'], then falls back to task_name_original (md_file.stem)
        name_to_sanitize = name_field_from_json if name_field_from_json else task_name_original_from_json
        logger.debug(f"Task entry: {task_entry}")
        logger.debug(f"name_field_from_json: '{name_field_from_json}', task_name_original_from_json: '{task_name_original_from_json}', CHOSEN name_to_sanitize: '{name_to_sanitize}'")

        if not name_to_sanitize:
            logger.warning(f"Skipping task entry because 'name' and 'task_name_original' are both missing: {task_entry}")
            # Ensure token fields exist if we are skipping, to maintain structure
            task_entry["input_tokens"] = task_entry.get("input_tokens", 0)
            task_entry["output_tokens"] = task_entry.get("output_tokens", 0)
            task_entry["total_tokens"] = task_entry.get("total_tokens", 0)
            continue

        task_name_sanitized = sanitize_filename(name_to_sanitize)
        task_meta_workdir = args.output_dir / task_name_sanitized
        
        # For logging purposes, prefer showing the original .md name if available
        display_task_name_for_log = task_name_original_from_json if task_name_original_from_json else name_to_sanitize
        logger.info(f"Processing task: '{display_task_name_for_log}' (source name for dir: '{name_to_sanitize}', checking dir: {task_meta_workdir})")

        if not task_meta_workdir.is_dir():
            logger.warning(f"  Meta workdir not found for task '{display_task_name_for_log}': {task_meta_workdir}. Skipping token backfill for this task.")
            # Ensure token fields exist if we are not updating them, to maintain structure
            task_entry["input_tokens"] = task_entry.get("input_tokens", 0)
            task_entry["output_tokens"] = task_entry.get("output_tokens", 0)
            task_entry["total_tokens"] = task_entry.get("total_tokens", 0)
            continue

        total_task_input_tokens = 0
        total_task_output_tokens = 0
        
        log_files_to_check = find_token_logs(task_meta_workdir, task_name_sanitized)

        if not log_files_to_check:
             logger.info(f"  No log files found for token parsing in {task_meta_workdir}. Token counts will remain as is or be set to 0.")
             # Ensure fields are present even if no logs found
             task_entry["input_tokens"] = task_entry.get("input_tokens", 0)
             task_entry["output_tokens"] = task_entry.get("output_tokens", 0)
             task_entry["total_tokens"] = task_entry.get("total_tokens", 0)


        for log_file in log_files_to_check:
            logger.debug(f"  Parsing tokens from: {log_file}")
            input_t, output_t = parse_tokens_from_file(log_file)
            total_task_input_tokens += input_t
            total_task_output_tokens += output_t
            # We sum up from all found log files for a given task,
            # though typically one file (chat.history.md) should contain all token lines.
            # This handles cases where token info might be split or in different logs.

        # --- Start of new update logic ---
        old_input_tokens = task_entry.get("input_tokens", 0)
        old_output_tokens = task_entry.get("output_tokens", 0)
        old_total_tokens = task_entry.get("total_tokens", 0)

        # Always update with the newly parsed values, even if they are 0.
        # This ensures that if a log file truly has no token info, it's reflected as 0.
        task_entry["input_tokens"] = total_task_input_tokens
        task_entry["output_tokens"] = total_task_output_tokens
        task_entry["total_tokens"] = total_task_input_tokens + total_task_output_tokens

        if old_input_tokens != total_task_input_tokens or \
           old_output_tokens != total_task_output_tokens:
            logger.info(f"  Updating tokens for '{display_task_name_for_log}': "
                        f"Old (In/Out/Total): {old_input_tokens}/{old_output_tokens}/{old_total_tokens} -> "
                        f"New (In/Out/Total): {total_task_input_tokens}/{total_task_output_tokens}/{task_entry['total_tokens']}")
            updated_count += 1
        else:
            # Values were already up-to-date (e.g., both old and new are 0, or values matched exactly)
            logger.info(f"  Token values for '{display_task_name_for_log}' remain unchanged (In/Out/Total): {total_task_input_tokens}/{total_task_output_tokens}/{task_entry['total_tokens']}. Already up-to-date or logs yielded same values.")
        # --- End of new update logic ---


    summary_data["tasks_results"] = tasks_results # Ensure the modified list is assigned back

    try:
        with open(args.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully updated {updated_count} task(s) in {args.summary_file}")
    except Exception as e:
        logger.error(f"Could not write updated summary to {args.summary_file}: {e}")

if __name__ == "__main__":
    main() 