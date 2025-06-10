# gittaskbench/cli.py
import sys
import argparse
import logging
from typing import List, Optional
from pathlib import Path

from gittaskbench import __version__
from gittaskbench.utils import logger, setup_logger, find_project_root
from gittaskbench.task_loader import load_task
from gittaskbench.evaluator import run_evaluation
from gittaskbench.result_analyzer import analyze_results


def grade_command(args: argparse.Namespace) -> int:
    """
    Handle the 'grade' subcommand.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.all:
        project_root = find_project_root()
        config_dir = project_root / "config"
        if not config_dir.exists():
            logger.error(f"Config directory not found: {config_dir}")
            return 1

        all_task_ids = []
        for task_dir in config_dir.iterdir():
            if task_dir.is_dir():
                task_id = task_dir.name
                all_task_ids.append(task_id)

        overall_success = True
        for task_id in all_task_ids:
            logger.info(f"Loading task: {task_id}")
            task = load_task(task_id, args.output_dir, args.result)
            if not task:
                logger.error(f"Failed to load task: {task_id}")
                overall_success = False
                continue

            success = run_evaluation(task)
            if not success:
                overall_success = False

        return 0 if overall_success else 1
    else:
        if not args.taskid:
            logger.error("The --taskid argument is required when --all is false.")
            return 1

        logger.info(f"Loading task: {args.taskid}")

        # Load task information
        task = load_task(args.taskid, args.output_dir, args.result)
        if not task:
            logger.error(f"Failed to load task: {args.taskid}")
            return 1

        # Run evaluation
        success = run_evaluation(task)

        return 0 if success else 1


def eval_command(args: argparse.Namespace) -> int:
    """
    Handle the 'eval' subcommand.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    project_root = find_project_root()
    result_dir = project_root / (args.result if args.result else "test_results")
    if not result_dir.exists():
        logger.error(f"Result directory not found: {result_dir}")
        return 1

    # 如果没有指定 output_file 参数，使用默认文件名
    if args.output_file is None:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        output_file = Path(f"evaluation_report_{timestamp}.txt")
    else:
        output_file = Path(args.output_file)

    # Analyze results
    analyze_results(result_dir, output_file)

    return 0


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Command-line arguments to parse (defaults to sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="gittaskbench",
        description="GitTaskBench - A tool for benchmarking agent tasks"
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='Command to execute'
    )

    # Grade command
    grade_parser = subparsers.add_parser(
        'grade',
        help='Grade a task completion'
    )

    grade_parser.add_argument(
        '--taskid',
        help='Task ID to evaluate'
    )

    grade_parser.add_argument(
        '--output_dir',
        help='Directory containing agent output (overrides config file)'
    )

    grade_parser.add_argument(
        '--result',
        help='Directory to store the result file. If provided, overrides the config file.'
    )

    grade_parser.add_argument(
        '--all',
        action='store_true',
        default=False,
        help='Run evaluation for all tasks. Default is false.'
    )

    # Set the handler for the grade command
    grade_parser.set_defaults(func=grade_command)

    # Eval command
    eval_parser = subparsers.add_parser(
        'eval',
        help='Evaluate results from a directory'
    )

    eval_parser.add_argument(
        '--result',
        default="test_results",
        help='Directory containing the result files. Defaults to test_results.'
    )

    # add output_file
    eval_parser.add_argument(
        '--output_file',
        help='File path to write the evaluation report to. If not provided, a default file will be created in the current directory.'
    )

    # Set the handler for the eval command
    eval_parser.set_defaults(func=eval_command)

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Check if a command was provided
    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)

    return parsed_args


def main() -> int:
    """
    Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        args = parse_args()

        # Call the appropriate command handler
        if hasattr(args, 'func'):
            return args.func(args)
        else:
            logger.error("No command specified")
            return 1

    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        if logger.level == logging.DEBUG:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())