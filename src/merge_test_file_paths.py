"""
Script to extract and merge test file paths from cloned repositories.

This script reads a log file (`test_files_list.txt`) containing repository
URLs and their respective test file paths, groups the test file paths by
repository,and stores this information in a pandas DataFrame. The script then
merges this new DataFrame with an existing DataFrame
(`updated_local_github_df_test_count.csv`) on the repository URL. The resulting
 merged DataFrame is saved to `merged_df.csv`.
"""

import pandas as pd
from collections import defaultdict
from pathlib import Path
from utils.git_utils import get_working_directory_or_git_root


def read_test_file_paths(file_path):
    repos = defaultdict(list)
    current_repo = None
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("Repository URL:"):
                current_repo = line.split(": ")[1]
            elif current_repo:
                repos[current_repo].append(line)
    return repos


def create_dataframe(file_path):
    repo_dict = read_test_file_paths(file_path)
    df = pd.DataFrame(list(repo_dict.items()), columns=["repourl", "test_file_paths"])
    return df


if __name__ == "__main__":
    # Path to the log file
    working_directory = get_working_directory_or_git_root()
    file_path = working_directory / Path("data/test_files_list.txt")

    # Read the file and create the DataFrame
    df = create_dataframe(file_path)
    exising_df_file_path = (
        working_directory / "data/updated_local_github_df_test_count.csv"
    )
    existing_df = pd.read_csv(exising_df_file_path)

    # Merge the DataFrames on the 'repourl' column
    merged_df = pd.merge(existing_df, df, on="repourl", how="left")
    merged_df_path = working_directory / "data/merged_df.csv"

    merged_df.to_csv(merged_df_path, index=False)
