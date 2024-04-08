import argparse
import subprocess
from pathlib import Path
import pandas as pd
from loguru import logger
import shutil
from utils.git_utils import get_working_directory_or_git_root

"""
This script automates the process of cloning GitHub repositories listed in a CSV file,
counts the number of test files in each repository, and saves the count back to the CSV.
It's designed to handle interruptions by saving progress incrementally and resuming where
it left off. Users can specify excluded file extensions and choose a custom clone directory.
"""


def parse_args():
    """Parse command line arguments for excluded extensions and clone directory."""
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories and count " "test files."
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[".txt", ".md", ".h", ".xml", ".html", ".json", ".png", ".jpg"],
        help="File extensions to exclude. Pass each extension as a"
        " separate argument prefixed by --exclude.",
    )
    parser.add_argument(
        "--clone-dir",
        type=str,
        default=str(Path.home() / "data" / "cloned_repos"),
        help="Directory to clone repositories into. Defaults to "
        "~/data/cloned_repos.",
    )
    parser.add_argument(
        "--keep-clones",
        action="store_true",
        help="Keep cloned repositories after processing. If not specified, cloned"
        " repositories ill be deleted.",
    )
    return parser.parse_args()


def list_test_files(directory, excluded_extensions):
    """List test files in the directory, excluding specified extensions."""
    logger.info(f"Processing the directory {directory}")
    test_files = []

    for item in directory.rglob("*"):
        # Check if the item is a file and either the file or its parent directory contains 'test'
        if item.is_file() and (
            "test" in item.name.lower() or "test" in str(item.parent).lower()
        ):
            # Exclude files with certain extensions
            if item.suffix not in excluded_extensions:
                test_files.append(str(item))
    return test_files


args = parse_args()
# Log the excluded file extensions
logger.info(f"Excluded file extensions: {', '.join(args.exclude)}")

# Use git_codebase_root to define paths relative to the repository root
repo_root = get_working_directory_or_git_root()
updated_csv_path = repo_root / "data" / "updated_local_github_df_test_count.csv"
clone_dir_base = Path(args.clone_dir)

if updated_csv_path.exists():
    logger.info("Resuming from previously saved progress.")
    df = pd.read_csv(updated_csv_path)
else:
    csv_file_path = repo_root / "data" / "local_github_df_test_count.csv"

    if csv_file_path.exists():
        df = pd.read_csv(csv_file_path)
        df = df.drop("Unnamed: 0", axis=1)
        df["testfilecountlocal"] = -1  # Initialise if first run
    else:
        logger.error(f"CSV file not found at {csv_file_path}.")


for index, row in df.iterrows():
    if row["testfilecountlocal"] != -1:
        continue  # Skip processed repositories

    repo_url = row["repourl"]
    repo_name = Path(repo_url.split("/")[-1]).stem
    clone_dir = clone_dir_base / repo_name

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

    test_file_names = list_test_files(clone_dir, args.exclude)
    count = len(test_file_names)
    df.at[index, "testfilecountlocal"] = count
    formatted_names = "\n".join(test_file_names)
    logger.info(f"Test file names for {repo_name}:\n{formatted_names}")

    # Save after each update
    df.to_csv(updated_csv_path, index=False)

    # Cleanup based on user's command-line option
    if (
        not args.keep_clones
    ):  # If user did not specify --keep-clones, delete the directory
        shutil.rmtree(clone_dir)


logger.info("All repositories processed. DataFrame saved.")
