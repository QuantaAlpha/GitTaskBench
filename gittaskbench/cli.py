# gittaskbench/cli.py
import sys
import argparse
import logging
from typing import List, Optional
from pathlib import Path

from gittaskbench import __version__
from gittaskbench.utils import logger, setup_logger
from gittaskbench.task_loader import load_task
from gittaskbench.evaluator import run_evaluation


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

    logger.info(f"Loading task: {args.taskid}")

    # Load task information
    task = load_task(args.taskid, args.output_dir, args.result)
    if not task:
        logger.error(f"Failed to load task: {args.taskid}")
        return 1

    # Run evaluation
    success = run_evaluation(task)

    return 0 if success else 1


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
        required=True,
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

    # Set the handler for the grade command
    grade_parser.set_defaults(func=grade_command)

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