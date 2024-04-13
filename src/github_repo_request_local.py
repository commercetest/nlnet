import argparse
import subprocess
from pathlib import Path
import pandas as pd
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root

"""
This script automates the process of cloning GitHub repositories listed in a
CSV file, counts the number of test files in each repository, and saves the
count and the last commit hash back to the CSV. The script is designed to handle
interruptions and errors more robustly by independently verifying the completion
of each critical operation (cloning, commit hash retrieval, and test file counting).
It saves progress incrementally and resumes where it left off, ensuring that
partial data from previous runs is handled properly. Users can specify excluded
file extensions and choose a custom clone directory.
"""


def parse_args():
    """Parse command line arguments for excluded extensions and clone
    directory."""
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories and count " "test files."
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[".txt", ".md", ".h", ".xml", ".html", ".json", ".png", ".jpg", ".md"],
        help="File extensions to exclude. Pass each extension as a"
        " separate argument prefixed by --exclude.",
    )
    parser.add_argument(
        "--clone-dir",
        type=str,
        default=str(
            Path(get_working_directory_or_git_root())
            / "data"
            / "cloned_repo_second_run"
        ),
        # default="/Volumes/BEXO MAN",
        help="Defaults to a subdirectory within the project's data folder.",
        # help="Directory to clone repositories into. Defaults to the USB drive" " path.",
    )
    parser.add_argument(
        "--keep-clones",
        action="store_true",
        help="Keep cloned repositories after processing. If not specified, "
        "cloned repositories will be deleted.",
    )
    return parser.parse_args()


def list_test_files(directory, excluded_extensions):
    """List test files in the directory, excluding specified extensions."""
    logger.info(f"Processing the directory {directory}")
    test_files = []

    for item in directory.rglob("*"):
        # Check if the item is a file and either the file or its parent
        # directory contains 'test'
        if item.is_file() and (
            "test" in item.name.lower() or "test" in str(item.parent).lower()
        ):
            # Exclude files with certain extensions
            if item.suffix not in excluded_extensions:
                test_files.append(str(item))
    return test_files


def get_last_commit_hash(repo_dir: Path) -> str:
    """
    Fetches the hash of the last commit of the Git repository located in repo_dir.

    Parameters:
    - repo_dir (Path): The path to the cloned Git repository.

    Returns:
    - str: The hash of the last commit if successful, an empty string otherwise.
    """
    try:
        # Execute the git command to get the last commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,  # Set the current working directory to the repo
            # directory
            capture_output=True,
            text=True,  # Capture the output as text
            check=True,  # Raise an exception if the command fails
        )
        return result.stdout.strip()  # Return the commit hash, stripped of any
        # newline characters
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to fetch last commit hash for {repo_dir}." f" Exception: {e}"
        )
        return ""  # Return an empty string to indicate failure


args = parse_args()
# Log the excluded file extensions
logger.info(f"Excluded file extensions: {', '.join(args.exclude)}")

# Use get_working_directory_or_git_root to define paths relative to the
# repository root
repo_root = get_working_directory_or_git_root()
updated_csv_path = repo_root / "data" / "updated_local_github_df_test_count.csv"
clone_dir_base = Path(args.clone_dir)

clone_dir_base.mkdir(parents=True, exist_ok=True)  # Ensures the directory exists

if updated_csv_path.exists():
    logger.info("Resuming from previously saved progress.")
    df = pd.read_csv(updated_csv_path)
else:
    csv_file_path = repo_root / "data" / "original_github_df.csv"

    if csv_file_path.exists():
        df = pd.read_csv(csv_file_path)
        df["testfilecountlocal"] = -1  # Initialise if first run
    else:
        logger.error(f"CSV file not found at {csv_file_path}.")

# Filter out rows where the URL doesn't have a repository name (83 rows)
if "repourl" in df.columns:
    # Identify rows with incomplete URLs
    incomplete_urls = df[
        df["repourl"].apply(lambda x: len(x.rstrip("/").split("/")) < 5)
    ]

    # Log the incomplete URLs
    if not incomplete_urls.empty:
        logger.info("Incomplete GitHub URLs found and will be excluded:")
        for url in incomplete_urls["repourl"]:
            logger.info(f"Excluding the repourl : {url}")

    df = df[df["repourl"].apply(lambda x: len(x.rstrip("/").split("/")) >= 5)]


if "last_commit_hash" not in df.columns:
    df["last_commit_hash"] = None  # Initialize the column with None

# replace http with https
df["repourl"] = df["repourl"].str.replace(r"^http\b", "https", regex=True)

# Some of the URLs end with "/". I need to remove them.
df["repourl"] = df["repourl"].str.rstrip("/")

# Number of repositories to process before saving to CSV
BATCH_SIZE = 10

# Track the number of processed repositories in the current batch
processed_count = 0

for index, row in df.iterrows():
    # Check if we need to skip this repository because it's fully processed
    if row["testfilecountlocal"] != -1 and pd.notna(row["last_commit_hash"]):
        continue

    repo_url = row["repourl"]
    repo_name = Path(repo_url.split("/")[-1]).stem
    clone_dir = clone_dir_base / repo_name

    # Clone only if directory doesn't exist
    if not clone_dir.exists():
        try:
            logger.info(f"Trying to clone {repo_url} into {clone_dir}")
            subprocess.run(
                ["git", "clone", repo_url, str(clone_dir)],
                check=True,
                capture_output=True,
            )
            logger.info(f"Successfully cloned the repo: {repo_name}")

            # Fetch the last commit hash and store it in the DataFrame
            last_commit_hash = get_last_commit_hash(clone_dir)
            df.at[index, "last_commit_hash"] = last_commit_hash

            # On successful clone, increment the processed_count
            processed_count += 1

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to clone the repo: {repo_name}." f" " f"Exception: {e}"
            )
            df.at[index, "testfilecountlocal"] = 0

            # Even on failure, consider it processed for this batch
            processed_count += 1

            continue

    # Always attempt to fetch the last commit hash if not already fetched
    if pd.isna(row["last_commit_hash"]):
        last_commit_hash = get_last_commit_hash(clone_dir)
        df.at[index, "last_commit_hash"] = last_commit_hash

    # Count test files if not already counted
    if row["testfilecountlocal"] == -1:
        test_file_names = list_test_files(clone_dir, args.exclude)
        count = len(test_file_names)
        df.at[index, "testfilecountlocal"] = count
        formatted_names = "\n".join(test_file_names)
        logger.info(f"Test file names for {repo_name}:\n{formatted_names}")

    processed_count += 1

    # Processed count increment and batch check
    if processed_count >= BATCH_SIZE:
        # Save the DataFrame to CSV
        df.to_csv(updated_csv_path, index=False)
        logger.info(f"Batch of {BATCH_SIZE} repositories processed. Progress saved.")

        # Reset the processed_count for the next batch
        processed_count = 0

# Save any remaining changes at the end of processing
if processed_count > 0:
    df.to_csv(updated_csv_path, index=False)
    logger.info("Final batch processed. DataFrame saved.")

    # Cleanup based on user's command-line option
    # if (
    #     not args.keep_clones
    # ):  # If user did not specify --keep-clones, delete the directory
    #     shutil.rmtree(clone_dir)


# logger.info("All repositories processed. DataFrame saved.")

# Exporting the result to an RDF format
# df_test = pd.read_csv('../data/updated_local_github_df_test_count1111.csv')
# first_row = df_test.iloc[0]
# rdf_string = dataframe_row_to_ttl(first_row)
# print(rdf_string)
