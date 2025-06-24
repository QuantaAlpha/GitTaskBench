import os
import json
import argparse
import traceback # Import traceback module
from typing import Dict, List, Any, Optional # Import Optional


def _resolve_path(base_dir: Optional[str], relative_path: Optional[str]) -> str:
    """Helper function to safely resolve paths relative to a base directory.

    Args:
        base_dir: The base directory (e.g., git_root_dir).
        relative_path: The relative path string, possibly starting with '/'.

    Returns:
        The absolute path, or 'N/A' if inputs are invalid.
    """
    if not base_dir or not relative_path:
        return "N/A"
    # Remove leading '/' before joining
    clean_relative_path = relative_path.lstrip('/')
    return os.path.abspath(os.path.join(base_dir, clean_relative_path))

def prompt_format_repositories(repositories: List[Dict[str, Any]], git_root_dir: Optional[str]) -> str:
    """Formats repository information into a string, resolving paths relative to git_root_dir.

    Args:
        repositories: A list of dictionaries, each containing repository details.
        git_root_dir: The root directory of the Git project.

    Returns:
        A formatted string containing information about all repositories.
    """
    repositories_info = ""
    for repo in repositories:
        repo_path_rel = repo.get('path')
        repo_path_abs = _resolve_path(git_root_dir, repo_path_rel)
        repositories_info += f"仓库名称: {repo.get('name', 'N/A')}\n"
        repositories_info += f"仓库路径 (绝对): {repo_path_abs}\n" # Show absolute path
        repositories_info += f"仓库URL: {repo.get('url', 'N/A')}\n"
        repositories_info += f"理解指南: {repo.get('understanding_guidelines', [])}\n\n" # Default to empty list, add newline

    return repositories_info.strip() # Remove trailing newline

def prompt_format_file_paths(file_paths: List[Dict[str, Any]], git_root_dir: Optional[str]) -> str:
    """Formats file path information into a string, resolving paths relative to git_root_dir.

    Args:
        file_paths: A list of dictionaries, each containing file path details.
        git_root_dir: The root directory of the Git project.

    Returns:
        A formatted string containing information about all file paths.
    """
    file_paths_info = ""
    for file_info in file_paths: # Renamed variable for clarity
        file_path_rel = file_info.get('path')
        file_path_abs = _resolve_path(git_root_dir, file_path_rel)
        file_paths_info += f"文件路径 (绝对): {file_path_abs}\n" # Show absolute path
        file_paths_info += f"文件描述: {file_info.get('description', 'N/A')}\n\n" # Add newline for separation
    return file_paths_info.strip() # Remove trailing newline


def prompt_format_query(
    query_json: Dict[str, Any],
    git_root_dir: str, # Changed from queries_dir
    promt_save_path: str,
    working_dir: str,
    sub_dir_name: str
) -> str:
    """Formats a query dictionary into a detailed prompt string.

    Args:
        query_json: The dictionary containing query details.
        git_root_dir: The root directory of the Git project.
        promt_save_path: The path where the generated prompt markdown file will be saved.

    Returns:
        A formatted prompt string.

    Raises:
        FileNotFoundError: If the prompt file specified in query_json is not found.
        KeyError: If essential keys are missing from query_json.
    """
    # Use a more readable multi-line string format
    prompt_template = """
## 任务描述
{task_description}

## 可用仓库
{repositories_info}

## 文件路径
输入：
{input_file_paths_info}

输出：
{output_file_paths_info}

## 补充说明
{prompt_addition}
"""

    # Safely access keys using .get() with defaults or raise specific errors
    task_description = query_json.get("task_description", "无任务描述")
    repositories = query_json.get("repositories", [])
    file_paths_data = query_json.get("file_paths", {})
    input_files = file_paths_data.get("input_files", [])
    prompt_file_rel_path = query_json.get("prompt_file")
    output_file = sub_dir_name

    if not prompt_file_rel_path:
        prompt_addition = "无补充说明文件。"
    else:
        # Construct absolute path relative to the git root directory
        prompt_file_abs_path = _resolve_path(git_root_dir, prompt_file_rel_path)
        if prompt_file_abs_path == "N/A":
             prompt_addition = f"无法解析补充说明文件路径: {prompt_file_rel_path}"
        else:
            try:
                with open(prompt_file_abs_path, "r", encoding='utf-8') as f: # Specify encoding
                    prompt_addition = f.read()
            except FileNotFoundError:
                # Provide more context in the error message
                raise FileNotFoundError(f"补充说明文件未找到: {prompt_file_abs_path}")
            except Exception as e:
                # Catch other potential file reading errors
                print(f"读取补充说明文件时出错 {prompt_file_abs_path}: {e}")
                prompt_addition = "读取补充说明文件时出错。"


    # Format repository info using the git_root_dir
    repositories_info = prompt_format_repositories(repositories, git_root_dir) if repositories else "无可用的仓库信息。"
    # Format input file paths using the git_root_dir
    input_file_paths_info = prompt_format_file_paths(input_files, git_root_dir) if input_files else "无输入文件信息。"
    # Format output file paths using the git_root_dir
    output_file_paths_info = f"输出文件目录:{working_dir}/{output_file}, 如果只有一个文件，就以 `output.xxx` 命名; 如果存在多个以 `output_01.xxx`开始命名，后缀`.xxx`即输出文件的格式，根据任务给定的要求或需求确定。"

    prompt = prompt_template.format(
        task_description=task_description,
        repositories_info=repositories_info,
        input_file_paths_info=input_file_paths_info, # Renamed variable
        output_file_paths_info=output_file_paths_info, # Use formatted output paths
        prompt_addition=prompt_addition # Ensure prompt_addition is included
    )


    # 将prompt保存到promt_save_path

    # Ensure the directory for the prompt file exists
    os.makedirs(os.path.dirname(promt_save_path), exist_ok=True)
    with open(promt_save_path, "w", encoding='utf-8') as f: # Specify encoding
        f.write(prompt)

    return prompt.strip() # Remove leading/trailing whitespace


def run_setup(
    queries_dir: str,
    working_dir: str, # Keep working_dir for prompt saving location
    git_root_dir: str # Add git_root_dir
) -> None:
    """Processes query files to generate formatted prompts.

    Reads JSON query files from subdirectories within queries_dir,
    formats them using prompt_format_query, and saves the resulting
    prompts to a 'prompt' subdirectory within working_dir.

    Args:
        queries_dir: The directory containing subdirectories of query JSON files.
        working_dir: The base directory where the 'prompt' subdirectory will be created.
        git_root_dir: The root directory of the Git project, used for resolving paths in JSON.
    """

    print(f"queries_dir: {queries_dir}")
    print(f"working_dir: {working_dir}")
    print(f"git_root_dir: {git_root_dir}")

    # Save prompts relative to the working directory (e.g., ./res/prompt)
    prompt_save_dir = os.path.join(working_dir, "prompt")
    os.makedirs(prompt_save_dir, exist_ok=True)
    print(f"将在以下目录保存生成的 Prompt: {prompt_save_dir}")

    processed_files = 0
    error_files = []

    # Iterate through subdirectories and files in queries_dir
    for sub_query_dir_name in os.listdir(queries_dir):
        sub_query_dir_path = os.path.join(queries_dir, sub_query_dir_name)
        if not os.path.isdir(sub_query_dir_path):
            continue # Skip if it's not a directory

        print(f"正在处理子目录: {sub_query_dir_name}")
        for query_file_name in os.listdir(sub_query_dir_path):
            if not query_file_name.endswith(".json"):
                continue # Process only JSON files


            query_file_path = os.path.join(sub_query_dir_path, query_file_name)
            # Output prompt file name based on query file name, saved in prompt_save_dir

            prompt_output_path = os.path.join(prompt_save_dir, f"{sub_query_dir_name}.md")

            try:
                print(f"  正在处理文件: {query_file_path}")
                with open(query_file_path, "r", encoding='utf-8') as f: # Specify encoding
                    query_json = json.load(f)

                # Pass git_root_dir to prompt_format_query
                prompt = prompt_format_query(
                    query_json=query_json,
                    git_root_dir=git_root_dir, # Pass git_root_dir
                    promt_save_path=prompt_output_path,
                    working_dir=working_dir,
                    sub_dir_name=sub_query_dir_name
                )

                # Writing is now handled inside prompt_format_query
                # with open(prompt_output_path, "w", encoding='utf-8') as f: # Specify encoding
                #     f.write(prompt)
                processed_files += 1
                print(f"    成功生成 Prompt: {prompt_output_path}")

            except FileNotFoundError as e:
                print(f"    错误: {e}")
                error_files.append(query_file_path)
            except KeyError as e:
                print(f"    错误: 处理文件 {query_file_path} 时缺少键: {e}")
                error_files.append(query_file_path)
            except json.JSONDecodeError:
                print(f"    错误: 文件 {query_file_path} 不是有效的 JSON。")
                error_files.append(query_file_path)
            except Exception as e:
                print(f"    处理文件 {query_file_path} 时发生未知错误: {e}")
                # Add traceback printing
                print("------ Traceback Start ------")
                traceback.print_exc()
                print("------- Traceback End -------")
                error_files.append(query_file_path)

    print(f"\n处理完成。共处理 {processed_files} 个文件。")
    if error_files:
        print("以下文件处理失败:")
        for error_file in error_files:
            print(f"- {error_file}")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="根据查询 JSON 文件生成 Prompt。")
    parser.add_argument(
        "--queries-dir",
        type=str,
        default="/data/data/agent_test_codebase/GitTask_bench/queries", # Default path
        help="包含查询 JSON 文件子目录的路径。"
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default="/data/data/agent_test_codebase/GitTask_bench/res", # Default path for results/prompts
        help="用于保存生成的 Prompt 文件的基准目录 (默认为 'res')."
    )
    parser.add_argument(
        "--git-root-dir", # Add git-root-dir argument
        type=str,
        default="/data/data/agent_test_codebase/GitTask_bench", # Default Git root
        help="Git 项目的根目录，用于解析 JSON 文件中的相对路径。"
    )
    # --result-save-dir is removed as prompts are saved relative to --working-dir

    args = parser.parse_args()

    # Validate paths (optional but recommended)
    if not os.path.isdir(args.queries_dir):
        print(f"错误: 查询目录不存在: {args.queries_dir}")
        exit(1)
    if not os.path.isdir(args.git_root_dir):
        print(f"错误: Git 根目录不存在: {args.git_root_dir}")
        exit(1)
    # working_dir will be created if it doesn't exist by run_setup




    # Run the setup process with provided arguments
    try:
        run_setup(
            queries_dir=args.queries_dir,
            working_dir=args.working_dir,
            git_root_dir=args.git_root_dir # Pass git_root_dir
        )
    except Exception as e:
        print(f"执行脚本时发生错误: {e}")
        # Also print traceback for errors during setup initialization or argument parsing
        print("------ Traceback Start ------")
        traceback.print_exc()
        print("------- Traceback End -------")
        exit(1) # Exit with error code

    exit(0) # Explicitly exit with success code
