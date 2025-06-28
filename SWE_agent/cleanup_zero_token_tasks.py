import os
import json
import shutil
import logging
import time

# --- Configuration ---
# Set to False to perform the actual deletion.
# Set to True to only print which directories would be deleted, without performing any deletion.
DRY_RUN = False

# --- Paths ---
# These paths are inferred from your workspace structure and the `batch_results.jsonl` file location.
# Please confirm they are correct before execution.
USER_DIR = "youwang-claude4-opus"
BASE_TRAJECTORY_DIR = f"/data/code/agent_new/SWE-agent/trajectories/{USER_DIR}"
RESULTS_FILE_PATH = os.path.join(BASE_TRAJECTORY_DIR, "batch_results.jsonl")


def main():
    """
    Reads the results file and deletes directories corresponding to tasks where 'tokens_sent' is 0.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    if DRY_RUN:
        logging.info("--- Currently in [Dry Run] mode, no files will be deleted. ---")
    else:
        logging.warning("--- !!! Currently in [Execution] mode, directories will be permanently deleted. !!! ---")
        # Give the user a chance to cancel the operation
        try:
            print("Deletion will start in 5 seconds. Press Ctrl+C to cancel.")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("Operation cancelled by user.")
            return


    if not os.path.exists(RESULTS_FILE_PATH):
        logging.error(f"Results file not found: {RESULTS_FILE_PATH}")
        return

    logging.info(f"Reading results file: {RESULTS_FILE_PATH}")

    tasks_to_delete = []
    try:
        with open(RESULTS_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    # Check if 'tokens_sent' is 0
                    if data.get("tokens_sent") == 0:
                        run_id = data.get("run_id")
                        if run_id:
                            tasks_to_delete.append(run_id)
                        else:
                            logging.warning(f"Found a record with tokens_sent=0, but missing run_id: {line.strip()}")
                except json.JSONDecodeError:
                    logging.warning(f"Failed to parse as JSON: {line.strip()}")
    except IOError as e:
        logging.error(f"Failed to read file {RESULTS_FILE_PATH}: {e}")
        return

    if not tasks_to_delete:
        logging.info("No tasks with tokens_sent=0 found. No action needed.")
        return

    logging.info(f"Found {len(tasks_to_delete)} tasks with tokens_sent=0 that need processing.")

    deleted_count = 0
    skipped_count = 0
    for run_id in tasks_to_delete:
        # run_id is similar to "openai/claude-opus-4-20250514-AnimeGANv3_01"
        # os.path.join will correctly concatenate it into a path
        dir_to_delete = os.path.join(BASE_TRAJECTORY_DIR, run_id)

        if os.path.isdir(dir_to_delete):
            if DRY_RUN:
                logging.info(f"[Dry Run] Will delete directory: {dir_to_delete}")
            else:
                try:
                    shutil.rmtree(dir_to_delete)
                    logging.info(f"Deleted: {dir_to_delete}")
                    deleted_count += 1
                except OSError as e:
                    logging.error(f"Failed to delete: {dir_to_delete}. Error: {e}")
        else:
            logging.warning(f"Skipped (directory not found): {dir_to_delete}")
            skipped_count += 1

    logging.info("--- Cleanup Summary ---")
    if DRY_RUN:
        logging.info(f"Mode: Dry Run")
        logging.info(f"Would have attempted to delete {len(tasks_to_delete) - skipped_count} directories.")
    else:
        logging.info(f"Mode: Execution")
        logging.info(f"Successfully deleted {deleted_count} directories.")

    logging.info(f"Skipped {skipped_count} tasks because the directory was not found.")
    logging.info("--------------------")


if __name__ == "__main__":
    main()