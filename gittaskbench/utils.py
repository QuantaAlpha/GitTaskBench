# gittaskbench/utils.py
import os
import sys
import logging
import colorlog
from pathlib import Path
from typing import Optional, Dict, Any, Union, List


# Set up colorful logging
def setup_logger(name: str = "gittaskbench", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with color formatting.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )

    logger = colorlog.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Avoid duplicate handlers
    logger.propagate = False

    return logger


# Global logger instance
logger = setup_logger()


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Path object of the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_project_root() -> Path:
    """
    Find the project root directory by looking for config/ directory.

    Returns:
        Path object of the project root
    """
    current_dir = Path.cwd()

    # Check if we're already at the root
    if (current_dir / "config").exists():
        return current_dir

    # Try parent directories
    for parent in current_dir.parents:
        if (parent / "config").exists():
            return parent

    # If not found, use current directory and log a warning
    logger.warning(
        "Project root not found (config/ directory missing). "
        "Using current directory as root. This may cause issues."
    )
    return current_dir