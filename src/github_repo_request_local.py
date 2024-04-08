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
    for path in directory.rglob("*"):
        # Check if the path is a file and either the file or its parent directory contains 'test'
        if path.is_file() and (
            "test" in path.name.lower() or "test" in str(path.parent).lower()
        ):
            # Exclude files with certain extensions
            if path.suffix not in excluded_extensions:
                test_files.append(str(path))
    return test_files


updated_csv_path = Path("../data/updated_local_github_df_test_count.csv")
if updated_csv_path.exists():
    logger.info("Resuming from previously saved progress.")
    df = pd.read_csv(updated_csv_path)
else:
    csv_file_path = Path("../data/local_github_df_test_count.csv")
    df = pd.read_csv(csv_file_path)
    df = df.drop("Unnamed: 0", axis=1)
    df["testfilecountlocal"] = -1  # Initialize if first run

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
    shutil.rmtree(clone_dir)  # Clean up

logger.info("All repositories processed. DataFrame saved.")
