from pathlib import Path
import subprocess
from loguru import logger


def git_codebase_root():
    """Returns the Git repository root directory, or None if not in a Git repo."""
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return Path(root.decode().strip())
    except subprocess.CalledProcessError:
        logger.warning("Not inside a Git repository.")
        return None


def get_working_directory_or_git_root():
    """Returns the root of the Git repository, or the current working directory if not in a Git repo."""
    git_root = git_codebase_root()
    return git_root if git_root is not None else Path.cwd()
