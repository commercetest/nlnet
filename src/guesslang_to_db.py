"""
Language Detector Script for Cloned Repositories

This script provides functionality to analyse files within cloned
repositories, detect their programming languages using
the guesslang library, and write the results to a Supabase database.

Run the script with the appropriate `--clone-dir` argument specifying the
directory where repositories are cloned or let it use the default directory.

Example:
    $ python script.py --clone-dir /path/to/cloned_repos

"""

import argparse
import os
from pathlib import Path

from loguru import logger
from tqdm import tqdm
from guesslang import Guess

from db import read_from_db, write_to_db
from utils.git_utils import get_working_directory_or_git_root

# Configure logger
logger.add("language_detector_script_log", rotation="500 MB")


def parse_args():
    """
    This function defines the command-line arguments for specifying the directory
    where repositories are cloned. The default directory is set to a subdirectory
    named 'cloned_repo' within the project's 'data' folder.

    Returns:
    argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Specify the directory for " "cloned repositories"
    )
    parser.add_argument(
        "--clone-dir",
        type=str,
        default=str(
            Path(get_working_directory_or_git_root()) / "data" / "cloned_repos"
        ),
        help="Directory where repositories are cloned. Defaults to "
        "'data/cloned_repo' within the project's root directory.",
    )
    return parser.parse_args()


def detect_language(file_path):
    """
    Detects the programming language of a given file using guesslang.
    Args:
        file_path (str): The path to the file.
    Returns:
        str: The name of the detected programming language.
    """
    logger.debug(f"Analysing file: {file_path}")

    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File '{file_path}' not found.")
        return "Unknown"

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        guess = Guess()
        language = guess.language_name(content)
        logger.debug(f"Detected language: {language}")
        return language
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return "Unknown"


def extract_languages(cloned_repos_base_path, processed_files):
    """
    Analyse and extract programming languages from files in cloned repositories.

    This function scans through a directory structure containing cloned
    repositories, detects the programming language of each file, and writes
    the results to a Supabase database. It skips files that have already been
     processed.

    Parameters:
    cloned_repos_base_path (str): The base path to the directory containing
    cloned repositories organized by hosting platform.
    processed_files (set): A set of file paths that have already been processed
    to avoid duplicate work.

    Procedure:
    1. Identify hosting platforms in the base directory.
    2. For each hosting platform, identify the repositories.
    3. For each repository, identify the files.
    4. For each file, detect the programming language if the file has not been
    processed.
    5. Write the detected language and file details to the database.

    The function logs information at various steps to provide insight into the
     progress and any potential issues.
    It uses `tqdm` to display progress bars for processing hosting platforms,
    repositories, and files.

    Example:
    ```python
    processed_files = read_from_db()  # Fetch previously processed files from
    the database
    extract_languages("/path/to/cloned_repos", processed_files)
    ```
    """

    org_paths = list(Path(cloned_repos_base_path).glob("*"))
    logger.info(f"Found {len(org_paths)} hosting platforms")

    for org_path in tqdm(org_paths, desc="Analysing hosting platforms", unit="org"):
        if org_path.is_dir():
            repo_paths = list(org_path.glob("*"))
            logger.info(f"Found {len(repo_paths)} repositories in" f" {org_path.name}")

            for repo_path in tqdm(
                repo_paths,
                desc=f"Analysing repositories" f" in {org_path.name}",
                unit="repo",
                leave=False,
            ):
                if repo_path.is_dir():
                    repo_name = repo_path.name
                    logger.info(f"Processing repository: {repo_name}")

                    file_paths = list(repo_path.rglob("*"))
                    logger.info(f"Found {len(file_paths)} files in {repo_name}")

                    for file_path in tqdm(
                        file_paths,
                        desc=f"Analysing files in" f" {repo_path.name}",
                        unit="file",
                        leave=False,
                    ):
                        if (
                            file_path.is_file()
                            and str(file_path) not in processed_files
                        ):
                            language = detect_language(str(file_path))
                            logger.info("Writing to the database: ")
                            write_to_db(
                                str(org_path.name),
                                str(repo_name),
                                str(file_path),
                                str(language),
                            )


if __name__ == "__main__":
    args = parse_args()

    # Base path to the cloned repositories
    cloned_repos_base_path = args.clone_dir

    # Path to the log file
    working_directory = get_working_directory_or_git_root()
    logger.info(f"Working Directory: {working_directory}")

    logger.info("Downloading the processed file paths from the database")
    processed_files = read_from_db()
    logger.info(f" Number of processed files: {len(processed_files)}")

    # Extract languages from the cloned repositories
    logger.info("Extracting languages from cloned repositories")
    extract_languages(cloned_repos_base_path, processed_files)

    logger.info("Script execution finished successfully.")
