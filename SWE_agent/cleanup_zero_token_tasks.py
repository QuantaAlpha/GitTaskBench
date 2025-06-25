import os
import json
import shutil
import logging
import time

# --- Configuration ---
# 设置为 False 来执行真正的删除操作。
# 设置为 True 则只打印哪些目录会被删除，不会执行任何删除。
DRY_RUN = False

# --- Paths ---
# 这些路径是根据你的工作区结构和 `batch_results.jsonl` 文件位置推断出来的。
# 在执行前，请确认它们是正确的。
USER_DIR = "youwang-claude4-opus"
BASE_TRAJECTORY_DIR = f"/data/code/agent_new/SWE-agent/trajectories/{USER_DIR}"
RESULTS_FILE_PATH = os.path.join(BASE_TRAJECTORY_DIR, "batch_results.jsonl")


def main():
    """
    读取结果文件，并删除 'tokens_sent' 为 0 的任务所对应的目录。
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )

    if DRY_RUN:
        logging.info("--- 当前为【试运行】模式，不会删除任何文件。 ---")
    else:
        logging.warning("--- !!! 当前为【执行】模式，目录将被永久删除。 !!! ---")
        # 给用户一个取消操作的机会
        try:
            print("5秒后将开始删除操作。按 Ctrl+C 可以取消。")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("操作已被用户取消。")
            return


    if not os.path.exists(RESULTS_FILE_PATH):
        logging.error(f"结果文件未找到: {RESULTS_FILE_PATH}")
        return

    logging.info(f"正在读取结果文件: {RESULTS_FILE_PATH}")

    tasks_to_delete = []
    try:
        with open(RESULTS_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    # 检查 'tokens_sent' 是否为 0
                    if data.get("tokens_sent") == 0:
                        run_id = data.get("run_id")
                        if run_id:
                            tasks_to_delete.append(run_id)
                        else:
                            logging.warning(f"找到一条 tokens_sent=0 的记录，但缺少 run_id: {line.strip()}")
                except json.JSONDecodeError:
                    logging.warning(f"无法解析为JSON格式: {line.strip()}")
    except IOError as e:
        logging.error(f"无法读取文件 {RESULTS_FILE_PATH}: {e}")
        return

    if not tasks_to_delete:
        logging.info("没有找到 tokens_sent=0 的任务。无需任何操作。")
        return

    logging.info(f"发现 {len(tasks_to_delete)} 个 tokens_sent=0 的任务需要处理。")

    deleted_count = 0
    skipped_count = 0
    for run_id in tasks_to_delete:
        # run_id 类似于 "openai/claude-opus-4-20250514-AnimeGANv3_01"
        # os.path.join 会正确地将其拼接为路径
        dir_to_delete = os.path.join(BASE_TRAJECTORY_DIR, run_id)

        if os.path.isdir(dir_to_delete):
            if DRY_RUN:
                logging.info(f"[试运行] 将删除目录: {dir_to_delete}")
            else:
                try:
                    shutil.rmtree(dir_to_delete)
                    logging.info(f"已删除: {dir_to_delete}")
                    deleted_count += 1
                except OSError as e:
                    logging.error(f"删除失败: {dir_to_delete}. 错误: {e}")
        else:
            logging.warning(f"已跳过 (目录未找到): {dir_to_delete}")
            skipped_count += 1

    logging.info("--- 清理总结 ---")
    if DRY_RUN:
        logging.info(f"模式: 试运行")
        logging.info(f"原本将尝试删除 {len(tasks_to_delete) - skipped_count} 个目录。")
    else:
        logging.info(f"模式: 执行")
        logging.info(f"成功删除 {deleted_count} 个目录。")

    logging.info(f"因目录未找到而跳过 {skipped_count} 个任务。")
    logging.info("--------------------")


if __name__ == "__main__":
    main() 