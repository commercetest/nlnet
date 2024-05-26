import pandas as pd
from pathlib import Path
from utils.measure_performance import measure_performance, performance_records
from src.github_repo_request_local import detect_test_runners, detect_test_runners2
from utils.git_utils import get_working_directory_or_git_root
from utils.string_utils import sanitise_directory_name
from loguru import logger
import argparse


def parse_args():
    """Parse command line arguments for excluded extensions and clone
    directory, and other options."""
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories and count " "test files."
    )
    parser.add_argument(
        "--clone-dir",
        type=str,
        default=str(
            Path(get_working_directory_or_git_root()) / "data" / "cloned_repos"
        ),
        help="Defaults to a subdirectory within the project's data folder.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=str(Path("data/performance_comparison.csv")),
        help="Path to the output CSV file.",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=str(Path("data/updated_local_github_df_test_count.csv")),
        help="Path to the input CSV file.",
    )

    return parser.parse_args()


def analyse_with_test_runner(df, test_runner_function, repo_root):
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

        # Now pull the latest entry from performance_records which contains the performance details
        latest_performance_record = (
            performance_records[-1] if performance_records else {}
        )

        performance_data.append(
            {
                "repo_url": repo_url,
                "performance": latest_performance_record,
                "test_runner_used": test_runner_function.__name__,
            }
        )

    # Convert performance data to a DataFrame and return it
    performance_df = pd.DataFrame(performance_data)
    return performance_df


args = parse_args()
input_file = args.input_file
output_file = args.output_file

repo_root = get_working_directory_or_git_root()
logger.info(f"repo_root is: {repo_root}")

df = pd.read_csv(repo_root / input_file)

logger.info("Performance analysis using the function: detect_test_runners ")
performance_df1 = analyse_with_test_runner(df, detect_test_runners, repo_root)

logger.info("Performance analysis using the function: detect_test_runners2 ")
performance_df2 = analyse_with_test_runner(df, detect_test_runners2, repo_root)

# Optionally, combine and save the performance data
combined_performance_df = pd.concat(
    [performance_df1, performance_df2], ignore_index=True
)
combined_performance_df.to_csv(repo_root / args.output_file, index=False)
