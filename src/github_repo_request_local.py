import re
import argparse
import subprocess
from pathlib import Path
import pandas as pd
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root
from utils.export_to_rdf import dataframe_to_ttl
import shutil
import sys

"""
This script automates the process of cloning GitHub repositories listed in a
CSV file, retrieves the last commit hash for each repository, and saves this
information back to the CSV. It also counts the number of test files in each
repository, excluding specific file extensions based on command-line arguments,
and saves both the count and the list of test filenames to a text file. This
facilitates detailed record-keeping and auditing of test file existence across
repositories. The script is designed to handle interruptions and errors more
robustly by independently verifying the completion of each critical operation
including cloning, commit hash retrieval, test file counting, and the writing
of test file records. It saves progress incrementally and can resume where it
left off, ensuring that data from previous runs is properly managed.

Enhancements include:

- Exclusion of specific file extensions during the test file count to tailor
  the data collection.
- Optional retention of cloned repositories post-processing, controlled via
  command-line arguments.
- Batch processing capabilities to manage large sets of data efficiently and
  save progress periodically.
- Conversion of the final data collection to Turtle (TTL) format for RDF
  compliant data storage, with the ability to specify the output location.
- Writing of repository URLs and associated test filenames to a text file for
  easy auditing and verification. The location of this text file can be
  specified via command-line arguments.

Users can specify excluded file extensions, choose a custom directory for
cloning repositories, and set paths for output files (both CSV and text formats).
The script also allows specification of the output path for the TTL format file,
facilitating easy integration with semantic web technologies.

Command Line Arguments:
- --exclude: Specify file extensions to exclude from test file counts.
- --clone-dir: Set a custom directory for cloning the repositories.
- --keep-clones: Option to retain cloned repositories after processing, which
  can be useful for subsequent manual reviews or further automated tasks.
- --input-file: Path to the input CSV file.
- --output-file: Path to the output CSV file that includes test file counts and
  last commit hashes.
- --test-file-list: Path to the text file for recording repository URLs and
  test filenames.
- --ttl-file: Path to save the Turtle (TTL) format file.
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
            Path(get_working_directory_or_git_root()) / "data" / "cloned_repos"
        ),
        help="Defaults to a subdirectory within the project's data folder.",
    )
    parser.add_argument(
        "--keep-clones",
        action="store_true",
        help="Keep cloned repositories after processing. If not specified, "
        "cloned repositories will be deleted.",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=str(Path("data/original_massive_df.csv")),
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=str(Path("data/updated_local_github_df_test_count.csv")),
        help="Path to the output CSV file.",
    )
    parser.add_argument(
        "--ttl-file",
        type=str,
        default=str(Path("data/all_data.ttl")),
        help="Path to save the Turtle (TTL) format file.",
    )
    parser.add_argument(
        "--test-file-list",
        type=str,
        default=str(Path("data/test_files_list.txt")),
        help="Path to the text file for writing repository URLs and test filenames.",
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


def get_last_commit_hash(repo_dir: Path):
    """
    Fetches the hash of the last commit of the Git repository located in
    repo_dir.

    Parameters:
    - repo_dir (Path): The path to the cloned Git repository.

    Returns:
    - str: The hash of the last commit if successful, None otherwise.
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
            f"Failed to fetch last commit hash for {repo_dir}. " f"Exception: {e}"
        )
        return None  # Return None to indicate failure


def sanitise_directory_name(name):
    """Sanitise the directory name by removing or replacing non-alphanumeric
    characters."""
    # Replace periods and other non-alphanumeric characters with an underscore
    # This regex replaces all non-alphanumeric, non-hyphen characters with an
    # underscore
    sanitised_name = re.sub(r"[^\w-]", "_", name)
    return sanitised_name


if __name__ == "__main__":
    args = parse_args()
    input_file = args.input_file
    output_file = args.output_file
    # Log the excluded file extensions
    logger.info(f"Excluded file extensions: {', '.join(args.exclude)}")

    # Use get_working_directory_or_git_root to define paths relative to the
    # repository root
    repo_root = get_working_directory_or_git_root()
    logger.info(f"repo_root is: {repo_root}")

    error_log_path = repo_root / Path("data/error_log.txt")
    error_log_file = open(error_log_path, "a")  # Open the file in append mode

    updated_csv_path = repo_root / output_file
    logger.info(f"updated_csv_path is: {updated_csv_path}")

    clone_dir_base = repo_root / Path(args.clone_dir)
    # Ensures the directory exists
    clone_dir_base.mkdir(parents=True, exist_ok=True)

    if updated_csv_path.exists():
        logger.info("Resuming from previously saved progress.")
        df = pd.read_csv(updated_csv_path)
    else:
        csv_file_path = repo_root / input_file

        if csv_file_path.exists():
            df = pd.read_csv(csv_file_path)
            df["testfilecountlocal"] = -1  # Initialise if first run
            df["clone_status"] = None  # Initialise the clone status column
        else:
            logger.error(
                f"The input file has not been found at {csv_file_path}. Exiting..."
            )
            # Exit with error code 1 indicating that an error occurred
            sys.exit(1)

    if "last_commit_hash" not in df.columns:
        df["last_commit_hash"] = None  # Initialize the column with None

    # Number of repositories to process before saving to CSV
    BATCH_SIZE = 10

    # Track the number of processed repositories in the current batch
    processed_count = 0

    # Define the path for the text file where test filenames and URLs will be
    # saved otherwise the default path will be used:
    # repo_root / "data" / "test_files_list.txt"
    test_file_list_path = repo_root / Path(args.test_file_list)
    logger.info(f"test_file_list_path is: {test_file_list_path}")

    # Open the text file just before the loop begins
    with open(test_file_list_path, "a") as file:
        for index, row in df.iterrows():
            # Check if we need to skip this repository because it's fully
            # processed
            if row["testfilecountlocal"] != -1 and pd.notna(row["last_commit_hash"]):
                continue

            repo_url = row["repourl"]
            if not repo_url or repo_url is None:
                logger.info(f"Invalid repository URL: {repo_url}")
                continue

            repo_domain = row["repodomain"]
            # Sanitise the domain name
            sanitised_domain = sanitise_directory_name(repo_domain)
            repo_name = Path(repo_url.split("/")[-1]).stem
            # Adjusted path including domain
            domain_specific_dir = clone_dir_base / sanitised_domain
            domain_specific_dir.mkdir(parents=True, exist_ok=True)
            clone_dir = domain_specific_dir / repo_name
            logger.info(f"Sanitised clone directory is: {clone_dir}")

            # Clone only if directory doesn't exist
            if not clone_dir.exists():
                try:
                    logger.info(f"Trying to clone {repo_url} into {clone_dir}")
                    subprocess.run(
                        ["git", "clone", repo_url, str(clone_dir)],
                        check=True,
                        capture_output=True,
                        text=True,  # Output is captured as text
                    )
                    df.at[index, "clone_status"] = "successful"
                    logger.info(f"Successfully cloned the repo: {repo_name}")

                    # Fetch the last commit hash and store it in the DataFrame
                    last_commit_hash = get_last_commit_hash(clone_dir)
                    if last_commit_hash is not None:
                        df.at[index, "last_commit_hash"] = last_commit_hash

                    # On successful clone, increment the processed_count
                    processed_count += 1

                except subprocess.CalledProcessError as e:
                    # Capture the error message from stderr
                    error_message = e.stderr.strip()
                    logger.error(
                        f"Failed to clone the repo: {repo_name}.Exception: {e},"
                        f"Error mesage {error_message}"
                    )
                    df.at[index, "clone_status"] = "failed"
                    df.at[index, "testfilecountlocal"] = -1

                    # Even on failure, consider it processed for this batch
                    processed_count += 1
                    # Write the error information to the error log file
                    error_log_file.write(
                        f"Repository URL: {repo_url}\nError Message: "
                        f"{error_message}\n\n"
                    )
                    continue
            else:
                # If already exists, consider as successful unless checked
                # otherwise
                df.at[index, "clone_status"] = "successful"

            # Always attempt to fetch the last commit hash if not already
            # fetched
            if pd.isna(row["last_commit_hash"]):
                last_commit_hash = get_last_commit_hash(clone_dir)
                df.at[index, "last_commit_hash"] = last_commit_hash

            # Count test files if not already counted
            if row["testfilecountlocal"] == -1:
                test_file_names = list_test_files(clone_dir, args.exclude)
                count = len(test_file_names)
                df.at[index, "testfilecountlocal"] = count

                # Write the repository URL and each test filename to the text
                # file
                file.write(f"Repository URL: {repo_url}\n")
                file.writelines(
                    f"{name}\n" for name in test_file_names
                )  # Write each test filename
                file.write("\n")  # Add a blank line for separation
                logger.info(
                    f"Test file names for the repo `{repo_name}`"
                    f" has been written to '{test_file_list_path}'"
                )

            processed_count += 1

            # Processed count increment and batch check
            if processed_count >= BATCH_SIZE:
                # Save the DataFrame to CSV
                df.to_csv(updated_csv_path, index=False)
                logger.info(
                    f"Batch of {BATCH_SIZE} repositories processed. "
                    f"Progress saved in {updated_csv_path}."
                )

                # Reset the processed_count for the next batch
                processed_count = 0

    # Save any remaining changes at the end of processing
    if processed_count > 0:
        df.to_csv(updated_csv_path, index=False)
        logger.info(f"Final batch processed. DataFrame saved in {updated_csv_path}.")

        # Cleanup based on user's command-line option
        if not args.keep_clones:
            # If user did not specify --keep-clones, delete the directory
            logger.info(
                '"--keep-clones" flag was not specified, deleting the directory"'
            )
            shutil.rmtree(clone_dir)

    logger.info("All repositories processed. DataFrame saved.")

    # Exporting the result to an RDF format

    # Use the path from the arguments to save the TTL file or saving the file
    # in the default location : "data/all_data.ttl"
    path_to_save_ttl = repo_root / Path(args.ttl_file)

    # Convert DataFrame to Turtle format
    ttl_data = dataframe_to_ttl(df)

    # Save all Turtle strings to a single file
    with open(path_to_save_ttl, "w") as f:
        for ttl in ttl_data:
            f.write(ttl)
            f.write(
                "\n"
            )  # Optionally add a newline between each entry for better readability

    error_log_file.close()
