"""
This script automates the process of cloning GitHub repositories listed in a
CSV file,

Command Line Arguments:
- --input-file-path: Path to the input CSV file.
- --exclude: Specify file extensions to exclude from test file counts.
- --clone-dir_path: Set a custom directory for cloning the repositories.
- --keep-clones: Option to retain cloned repositories after processing, which
can be useful for subsequent manual reviews or further automated tasks.

"""
import argparse
from pathlib import Path
from loguru import logger
import pandas as pd

from utils.git_utils import get_working_directory_or_git_root


def parse_args():
    """Parse command line arguments for excluded extensions and clone
        directory, and other options."""
    parser = argparse.ArgumentParser(
        description="Clone GitHub repositories listed in a CSV file."
    )
    parser.add_argument(
        "--input-file-path",
        type=str,
        default=str(Path(get_working_directory_or_git_root())/
                         "data"/ "original_massive_df.csv"),
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[".txt", ".md", ".h", ".xml", ".html", ".json", ".png",
                 ".jpg", ".md"],
        help=("File extensions to exclude. Pass each extension as a separate "
              "argument prefixed by --exclude.")
    )
    parser.add_argument(
        "--clone-dir-path",
        type=str,
        default=str(Path(get_working_directory_or_git_root()) / "data" /
                    "cloned_repos"
        ),
        help="Defaults to a subdirectory within the project's data folder.",
    )
    parser.add_argument(
        "--keep-clones",
        action="store_true",
        help="Keep cloned repositories after processing. If not specified, "
             "cloned repositories will be deleted."
    )

    return parser.parse_args()

def load_data(filepath):
    try:
        df = pd.read_csv(filepath)
        logger.info(f"Dataframe shape: {df.shape}")
        logger.info(f"Dataframe columns: {df.columns.tolist()}")
        df.info()
        return df

    except Exception as e:
        logger.error(f"Error Loading data from path {filepath} with "
                     f"exception" f" {e}")
    return None


if __name__ == "__main__":
    args = parse_args()
    input_file_path = args.input_file_path
    excluded_extensions = args.exclude
    clone_dir_path = args.clone_dir_path

    # Logging the excluded file extensions
    logger.info(f"Excluded extensions: {excluded_extensions}")

    # Retrieving and logging the repository root
    repo_root = get_working_directory_or_git_root()
    logger.info(f"Repository root is: {repo_root}")

    # Logging the input file path
    logger.info(f"Input file path is:  {input_file_path}")

    # Logging clone directory path
    clone_dir_path = repo_root/ Path(clone_dir_path)
    # Ensure the directory exists
    clone_dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Cloning directory path: {clone_dir_path}")

    # Loading the input file
    input_df = load_data(input_file_path)

    # Iterating the input dataframe
    for index, row in input_df.iterrows():
        if index in range(1):
            print(f"index is {index} value is: {row}")

