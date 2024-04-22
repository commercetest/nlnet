"""
This script reads a TSV file into a Pandas DataFrame, performs data cleaning
and preprocessing steps, and saves the results as CSV files. It also checks for
null values and duplicate rows in the DataFrame.

In addition to this, the rows from the original DataFrame where the code is
hosted in the github.com domain are extracted and saved separately.

The script supports command-line arguments that allow users to specify
custom paths for the input TSV file and the output directory for the CSV files.
This enhancement makes the script more flexible and suitable for integrating
into automated workflows where input and output paths may vary.

Features:
- Reads a TSV file specified by the user.
- Performs data cleaning, including checking for null values and duplicates.
- Saves cleaned data to a CSV file.
- Extracts and saves rows containing 'github.com' URLs to a separate CSV file.
- Allows users to define custom paths for input and output through command-line
 arguments.

Command Line Arguments:
- --input-file: Specifies the path to the input TSV file. Defaults to
'data/project_repos_from_jos_2024-feb-22.tsv'.
- --output-dir: Specifies the directory where output CSV files will be saved.
Defaults to 'data/'.

Usage:
To run the script with default paths:
    python <script_name.py>

To specify custom paths:
    python <script_name.py> --input-file path/to/input_file.tsv
    --output-dir path/to/output_directory
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reads and processes TSV data, checking for nulls and "
        "duplicates, and saves cleaned data as CSV."
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=str(
            get_working_directory_or_git_root()
            / "data"
            / "project_repos_from_jos_2024-feb-22.tsv"
        ),
        help="Path to the input TSV file.",
    )
    parser.add_argument(
        "--output-folder",
        type=str,
        default=str(get_working_directory_or_git_root() / "data"),
        help="Directory to save output CSV files.",
    )
    return parser.parse_args()


def check_and_clean_data(df):
    # Checking for null values
    null_counts = df.isnull().sum()
    if np.any(null_counts):
        logger.info("Null values found:")
        logger.info(null_counts[null_counts > 0])
    else:
        logger.info("No null values found.")

    # Checking for duplicates
    duplicates = df.duplicated().sum()
    if duplicates:
        logger.info(f"Number of duplicate rows: {duplicates}")
    else:
        logger.info("No duplicate rows found.")


if __name__ == "__main__":
    args = parse_args()

    git_working_dir = get_working_directory_or_git_root()
    logger.info(f"git_working_dir is : {git_working_dir}")

    # Define the full input path
    df_path = Path(args.input_file)
    logger.info(f"Input file path is : {df_path}")

    # Define the directory to save output files and ensuring the directory
    # exists
    output_dir = Path(args.output_folder)
    logger.info(f"Output file path is: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize lists to hold the column data
    a_values, b_values, c_values = [], [], []

    # Read the file line by line
    with open(df_path, "r") as file:
        for line in file:
            columns = line.strip().split("\t")

            if len(columns) == 3:
                # If there are three columns, append them directly
                a_values.append(columns[0])
                b_values.append(columns[1])
                c_values.append(columns[2])
            elif len(columns) == 1:
                # If there is one column, use the previous 'a' and 'b' values, and
                # append 'c'
                a_values.append(a_values[-1] if a_values else pd.NA)
                b_values.append(b_values[-1] if b_values else pd.NA)
                c_values.append(columns[0])
            else:
                raise ValueError(f"Unexpected number of columns: {len(columns)}")

    # Create a DataFrame from the accumulated lists
    df = pd.DataFrame(
        {"projectref": a_values, "nlnetpage": b_values, "repourl": c_values}
    )

    # Applying preprocessing steps
    check_and_clean_data(df)
    # I will keep the first occurrence of each duplicate row and remove the
    # others:
    df = df.drop_duplicates(keep="first")

    # Save the dataframe as a CSV file
    df.to_csv(output_dir / "original.csv", index=False)

    # Extracting the rows which host the code on github.com domain
    original_github_df = df[df["repourl"].str.contains("github.com")]
    original_github_df.to_csv(output_dir / "original_github_df.csv", index=False)
