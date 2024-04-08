import subprocess
from pathlib import Path
import pandas as pd
from loguru import logger
import shutil

"""
This script automates the process of cloning GitHub repositories listed in a CSV file,
counts the number of test files in each repository , and saves the count back to the CSV. It's designed to handle interruptions by saving progress
incrementally and resuming where it left off.
"""


def count_and_list_test_files(directory):
    logger.info(f"Processing the directory {directory}")
    test_files = []
    # Define a set of file extensions to exclude
    excluded_extensions = {
        ".txt",
        ".md",
        ".h",
        ".xml",
        ".html",
        ".json",
        ".png",
        ".jpg",
    }
    for item in directory.rglob("*"):
        # Check if the item is a file and either the file or its parent directory contains 'test'
        if item.is_file() and (
            "test" in item.name.lower() or "test" in str(item.parent).lower()
        ):
            # Exclude files with certain extensions
            if item.suffix not in excluded_extensions:
                test_files.append(str(item))
    return test_files


def git_codebase_root():
    """
    Returns the absolute path of the top-level directory of the current Git repository.
    If not in a Git repository, returns the current working directory as a fallback.
    """
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return Path(root.decode().strip())
    except subprocess.CalledProcessError:
        logger.warning("Not inside a Git repository. Defaulting to current directory.")
        return Path.cwd()


def should_keep_clones():
    """Prompt the user to decide whether to keep cloned repositories."""
    while True:  # Keep asking until we get a valid response
        response = (
            input("Keep cloned repositories after processing? (y/n): ").strip().lower()
        )
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            print("Please answer with 'y' or 'n'.")


# Use git_codebase_root to define paths relative to the repository root
repo_root = git_codebase_root()
updated_csv_path = repo_root / "data" / "updated_local_github_df_test_count.csv"

if updated_csv_path.exists():
    logger.info("Resuming from previously saved progress.")
    df = pd.read_csv(updated_csv_path)
else:
    csv_file_path = repo_root / "data" / "local_github_df_test_count.csv"

    if csv_file_path.exists():
        df = pd.read_csv(csv_file_path)
        df = df.drop("Unnamed: 0", axis=1)
        df["testfilecountlocal"] = -1  # Initialise if first run
    else:  # Added block
        logger.error(f"CSV file not found at {csv_file_path}.")


keep_clones = should_keep_clones()  # Ask the user before starting the processing loop

for index, row in df.iterrows():
    if row["testfilecountlocal"] != -1:
        continue  # Skip processed repositories

    repo_url = row["repourl"]
    repo_name = Path(repo_url.split("/")[-1]).stem
    clone_dir = Path.home() / "data" / "cloned_repos" / repo_name

    if not clone_dir.exists():
        try:
            logger.info(f"Trying to clone {repo_url} into {clone_dir}")
            subprocess.run(
                ["git", "clone", repo_url, str(clone_dir)],
                check=True,
                capture_output=True,
            )
            logger.info(f"Successfully cloned the repo: {repo_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone the repo: {repo_name}. Exception: {e}")
            df.at[index, "testfilecountlocal"] = 0
            continue

    test_file_names = count_and_list_test_files(clone_dir)
    count = len(test_file_names)
    df.at[index, "testfilecountlocal"] = count
    formatted_names = "\n".join(test_file_names)
    logger.info(f"Test file names for {repo_name}:\n{formatted_names}")

    # Save after each update
    df.to_csv(updated_csv_path, index=False)

    # Cleanup based on user's choice
    if not keep_clones:  # If user chose not to keep clones, delete the directory
        shutil.rmtree(clone_dir)


logger.info("All repositories processed. DataFrame saved.")
