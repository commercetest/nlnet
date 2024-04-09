from pathlib import Path
import subprocess
from loguru import logger

"""
Utility module for working with Git repositories in Python scripts.
Provides functions to determine the root of the current Git repository
and to handle decisions related to repository processing tasks.
"""


def git_codebase_root():
    """
    Determine the root directory of the current Git repository.

    Uses the `git rev-parse --show-toplevel` command to find the root directory.

    Returns:
        pathlib.Path: The path to the top-level directory of the current Git
        repository.

        None: If the current directory is not within a Git repository.
    """

    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return Path(root.decode().strip())
    except subprocess.CalledProcessError:
        logger.warning("Not inside a Git repository.")
        return None


def get_working_directory_or_git_root():
    """
    Obtain the Git repository root or the current working directory.

    This is a wrapper function that calls `git_codebase_root()` and falls back
    to the current working directory if the former returns None, indicating
    that the current directory is not a Git repository.

    Returns:
        pathlib.Path: The top-level directory of the Git repository if inside a
        Git repo, otherwise the current working directory.
    """
    git_root = git_codebase_root()
    return git_root if git_root is not None else Path.cwd()
