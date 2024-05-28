"""
This script is designed to analyse the performance of two different test
runner functions on a set of GitHub repositories. It utilises multiple
command-line parameters to manage input and output data paths and conducts
performance analysis using specified test runner functions.

The script processes a CSV file containing repository URLs, applies the test
runner functions to measure performance metrics such as execution time, memory
usage, and CPU usage, and then saves these metrics into separate CSV files.
Additionally, it combines all the metrics into a single CSV for a comprehensive
view.

Returns:
    pd.DataFrame: DataFrame containing performance metrics for each repository.

Example Usage:
    python script_name.py --input-file data/repositories.csv
    --clone-dir path/to/clone --output-file1 path/to/output1.csv
    --output-file2 path/to/output2.csv
    --output-file3 path/to/combined_output.csv
"""

import argparse
from pathlib import Path

import pandas as pd
from loguru import logger

from src.github_repo_request_local import detect_test_runners, detect_test_runners2
from utils.git_utils import get_working_directory_or_git_root
from utils.measure_performance import measure_performance, performance_records
from utils.string_utils import sanitise_directory_name


def parse_args():
    """Parse command line arguments for clone directory, input and output files,
    and other options."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clone-dir",
        type=str,
        default=str(
            Path(get_working_directory_or_git_root()) / "data" / "cloned_repos"
        ),
        help="Defaults to a subdirectory within the project's data folder.",
    )
    parser.add_argument(
        "--output-file1",
        type=str,
        default=str(Path("data/performance_df1.csv")),
        help="Path to the dataframe file created by the first function(detect_"
        "test_runners).",
    )
    parser.add_argument(
        "--output-file2",
        type=str,
        default=str(Path("data/performance_df2.csv")),
        help="Path to the dataframe file created by the second function(detect_"
        "test_runners2).",
    )
    parser.add_argument(
        "--output-file3",
        type=str,
        default=str(Path("data/combined_performance_comparison.csv")),
        help="Path to the combined dataframe CSV file.",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=str(Path("data/updated_local_github_df_test_count.csv")),
        help="Path to the input CSV file.",
    )

    return parser.parse_args()


def analyse_with_test_runner(df, test_runner_function, repo_root):
    """
    Analyses the performance of a specified test runner function applied to
    each repository described in the DataFrame. It records performance metrics
    and returns them in a new DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame containing repositories' data.
        test_runner_function (Callable): Function to be applied for
        performance analysis.
        repo_root (Path): Root directory for cloning repositories.

    """
    performance_data = []

    for index, row in df.iterrows():
        if row["clone_status"] != "successful":
            continue
        repo_url = row["repourl"]
        repo_domain = row["repodomain"]
        sanitised_domain = sanitise_directory_name(repo_domain)
        repo_name = Path(repo_url.split("/")[-1]).stem
        clone_dir = repo_root / Path(args.clone_dir) / sanitised_domain / repo_name

        # Measure the performance of the test runner function
        _ = measure_performance(test_runner_function, clone_dir)

        # Now pull the latest entry from performance_records which contains the
        # performance details
        if performance_records:
            latest_performance = performance_records[-1]
            performance_data.append(
                {
                    "repo_url": repo_url,
                    "execution_time": latest_performance.get("execution_time", "N/A"),
                    "memory_used_MB": latest_performance.get("memory_used", "N/A"),
                    "cpu_usage_user": latest_performance.get("cpu_usage_user", "N/A"),
                    "cpu_usage_system": latest_performance.get(
                        "cpu_usage_system", "N/A"
                    ),
                    "cpu_usage_idle": latest_performance.get("cpu_usage_idle", "N/A"),
                    "test_runner_used": test_runner_function.__name__,
                }
            )
    # Convert performance data to a DataFrame and return it
    performance_df = pd.DataFrame(performance_data)
    return performance_df


args = parse_args()
input_file = args.input_file
output_file1 = args.output_file1
output_file2 = args.output_file2
combined_df_file = args.output_file3
repo_root = get_working_directory_or_git_root()
logger.info(f"repo_root is: {repo_root}")

df = pd.read_csv(repo_root / input_file)

logger.info("Performance analysis using the function: detect_test_runners ")
performance_df1 = analyse_with_test_runner(df, detect_test_runners, repo_root)
performance_df1.to_csv(repo_root / output_file1, index=False)
logger.info(
    f"Performance analysis result(performance_df1.csv) using the function "
    f"`detect_test_runners` is saved in {repo_root / output_file1}"
)

logger.info("Performance analysis using the function: detect_test_runners2 ")
performance_df2 = analyse_with_test_runner(df, detect_test_runners2, repo_root)
performance_df2.to_csv(repo_root / output_file2, index=False)
logger.info(
    f"Performance analysis result(performance_df2.csv) using the function"
    f" `detect_test_runners2` is saved in {repo_root / output_file2}"
)


# Optionally, combine and save the performance data
combined_performance_df = pd.concat(
    [performance_df1, performance_df2], ignore_index=True
)
combined_performance_df.to_csv(repo_root / args.output_file3, index=False)
logger.info(
    f"Concatenated dataframes produced by analysing the performance of "
    f"functions `detect_test_runners` and `detect_test_runners2` is saved in"
    f" {repo_root / args.output_file3}"
)
