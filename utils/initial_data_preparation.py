"""
This script processes a TSV file to create a DataFrame, from which it extracts
domains and organises entries into separate DataFrames based on these domains.
Each domain-specific DataFrame is saved as a CSV file if it contains more than
10 records. This structured approach ensures that data is organised and
easily accessible for further analysis. Additionally, the script performs
data cleaning, including checking for null values and duplicates within the
DataFrame.

The script is designed to be flexible, supporting command-line arguments that
allow users to specify custom paths for the input TSV file and the output
directory for the CSV files. This feature makes the script suitable for
integration into automated workflows where input and output paths may vary.

Features:
- Reads a TSV file specified by the user.
- Performs data cleaning, including checking for null values and duplicates.
- Extracts the domain from each URL in the 'repourl' column to determine where
  the code is hosted.
- Separates the DataFrame into multiple DataFrames based on unique domains,
  facilitating domain-specific analyses.
- Saves DataFrames that contain more than 10 entries into a structured directory
  format, specifically catering to repositories hosted under distinct domains.
- Outputs the count of repositories for each domain into a text file for
  easy reference and further analysis.

Command Line Arguments:
- --input-file: Specifies the path to the input TSV file. Defaults to
  'data/project_repos_from_jos_2024-feb-22.tsv'.
- --output-folder: Specifies the directory where output CSV files and other
  results will be saved. Defaults to 'data/'.

Usage:
To run the script with default paths:
    python initial_data_preparation.py

To specify custom paths:
    python initial_data_preparation.py --input-file path/to/input_file.tsv
                             --output-folder path/to/output_directory
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root
import os


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
        # I will keep the first occurrence of each duplicate row and remove the
        # others:
        df = df.drop_duplicates(keep="first")
        logger.info("First occurrence of each duplicate row has been kept. ")
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
    output_dir = git_working_dir / Path(args.output_folder)
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
                # If there is one column, use the previous 'a' and 'b' values,
                # and append 'c'
                a_values.append(a_values[-1] if a_values else pd.NA)
                b_values.append(b_values[-1] if b_values else pd.NA)
                c_values.append(columns[0])
            else:
                raise ValueError(f"Unexpected number of columns: {len(columns)}")

    # Create a DataFrame from the accumulated lists
    df = pd.DataFrame(
        {"projectref": a_values, "nlnetpage": b_values, "repourl": c_values}
    )
    logger.info(
        f'Dataframe "df" has been created from the input .tsv file in ' f"{output_dir}."
    )

    # Applying preprocessing steps
    check_and_clean_data(df)

    # Save the dataframe as a CSV file
    df.to_csv(output_dir / "original.csv", index=False)
    logger.info(f'Dataframe "df" saved in {output_dir} ')

    logger.info("Creating separate DataFrames for each domain: \n ")

    # Extract the domain from the URL
    df["domain"] = df["repourl"].str.extract(r"https?://(www\.)?([^/]+)")[1]

    # Get the distinct domains
    distinct_domains = df["domain"].unique()

    # A dictionary comprehension is used to create a separate DataFrame for each
    # unique domain. For each domain in the list of unique domains, we filter
    # the original DataFrame to only include rows where the 'Domain' column
    # matches the current domain. We then drop the 'Domain' column since it's
    # no longer needed and reset the index to clean up the DataFrame.

    dfs_by_domain = {
        domain: df[df["domain"] == domain].drop("domain", axis=1).reset_index(drop=True)
        for domain in distinct_domains
    }
    # Each key in the dictionary is a domain, and the value is the corresponding
    # DataFrame

    # Count the number of repositories for each domain
    repo_counts_by_domain = {
        domain: len(dfs_by_domain[domain]) for domain in distinct_domains
    }

    sorted_repo_counts_by_domain = dict(
        sorted(repo_counts_by_domain.items(), key=lambda item: item[1], reverse=True)
    )

    # Set the directory path for saving the DataFrames
    data_folder = output_dir / "source_code_hosting_platform_dfs"

    # Create the output directory if it doesn't exist
    os.makedirs(data_folder, exist_ok=True)

    # Saving the count of repositories for each domain in a text file
    with open(data_folder / "domain_counts.txt", "w") as f:
        f.write("Count of repositories for each domain:\n")
        for domain, count in sorted_repo_counts_by_domain.items():
            f.write(f"{domain}: {count}\n")
    logger.info(
        f"Count of repositories for each domain has been saved to : " f"{f.name}"
    )

    for domain, domain_df in dfs_by_domain.items():
        if len(domain_df) > 10:
            domain_df.to_csv(
                data_folder / f"{domain.replace('/', '_').replace(':', '_')}.csv",
                index=False,
            )
            logger.info(
                f"Saved {domain} domain DataFrame with "
                f"{len(domain_df)} entries to {data_folder}"
            )
