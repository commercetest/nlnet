"""
This script processes a TSV file to create a DataFrame, from which it extracts
domains and organises entries into separate DataFrames based on these domains.
Each domain-specific DataFrame is saved as a CSV file if it contains more than
10 records. Additionally, the script performs data cleaning by removing rows
with null values and duplicates, and ensures URLs are complete and well-formed
before extracting the domain for analysis.

The script also includes functionality to replace HTTP with HTTPS in URLs,
remove trailing slashes, and save the count of repositories for each domain
into a text file, facilitating easy reference and further analysis. It's
designed for flexibility, supporting command-line arguments that allow users to
specify custom paths for the input TSV file and the output directory.

Features:
- Reads a TSV file specified by the user.
- Performs data cleaning, including checking for null values,
  duplicates, and URL completeness.
- Extracts the domain from each URL in the 'repourl' column to determine where
  the code is hosted.
- Separates the DataFrame into multiple DataFrames based on unique domains,
  facilitating domain-specific analyses.
- Saves DataFrames with more than 10 entries to a structured directory format,
  catering to repositories hosted under distinct domains.
- Outputs the count of repositories for each domain into a text file for easy
  reference and further analysis.
- Converts HTTP to HTTPS in URLs and cleans them by removing trailing slashes.

Command Line Arguments:
- --input-file: Specifies the path to the input TSV file.
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
from urllib.parse import urlparse


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


def remove_duplicates(df):
    """
    Removes duplicate rows from the DataFrame and logs the result.

    Parameters:
        df (pd.DataFrame): The DataFrame from which to remove duplicates.

    Returns:
        tuple: A tuple containing the deduplicated DataFrame and the count of
         removed rows.
    """
    logger.info("Starting to remove duplicate rows.")
    initial_count = len(df)
    duplicates = df.duplicated().sum()

    if duplicates:
        logger.info(f"Number of duplicate rows: {duplicates}")
        # Keep the first occurrence of each duplicate row and remove the others
        deduped_df = df.drop_duplicates(keep="first")
        duplicates_removed = initial_count - len(deduped_df)
        logger.info(
            f"First occurrence of each duplicate row has been kept. "
            f"Dropped {duplicates_removed} duplicate rows."
        )
    else:
        logger.info("No duplicate rows found.")
        deduped_df = df.copy()
        duplicates_removed = 0  # No duplicates found, so no rows removed

    return deduped_df, duplicates_removed


def remove_null_values(df):
    """
    Removes rows with null values from the DataFrame and logs the result.

    Parameters:
        df (pd.DataFrame): The DataFrame from which to remove nulls.

    Returns:
        tuple: A tuple containing the non-null DataFrame and the count of
        removed rows.
    """
    initial_count = len(df)
    null_counts = df.isnull().sum()

    if np.any(null_counts):
        logger.info("Null values found:")
        logger.info(null_counts[null_counts > 0])
        # Drop rows with any null values
        non_null_df = df.dropna()
        nulls_removed = initial_count - len(non_null_df)
        logger.info(f"Dropped {nulls_removed} rows containing null values.")
    else:
        logger.info("No null values found.")
        non_null_df = df.copy()
        nulls_removed = 0

    return non_null_df, nulls_removed


def filter_out_incomplete_urls(df):
    """
    Filters rows in a DataFrame based on the completeness of the 'repourl'
    URLs. A URL is considered complete if it contains at least five parts,
    including the protocol, empty segment (for '//'), domain, and at least
    two path segments, e.g., 'https://github.com/owner/repo'. Raises
    an error if the required column 'repourl' is missing.

    Args:
        df (pd.DataFrame): DataFrame containing URLs.

    Returns:
        pd.DataFrame: DataFrame with rows containing complete URLs.

    Raises:
        ValueError: If the 'repourl' column is missing from the DataFrame.
    """
    if "repourl" not in df.columns:
        logger.critical(
            "Critical: DataFrame columns are: {}".format(df.columns.tolist())
        )
        logger.critical(
            "DataFrame does not contain 'repourl' column. Aborting operation."
        )
        raise ValueError("DataFrame must contain a 'repourl' column.")

    # Helper function to determine if a URL is complete
    def is_complete_url(url):
        # Check if the url is not a string
        if not isinstance(url, str):
            return False

        # Example url: https://github.com/owner/repo
        parts = url.rstrip("/").split("/")
        return len(parts) >= 5

    # Identify rows with incomplete URLs using the helper function
    incomplete_urls = df[~df["repourl"].apply(is_complete_url)]

    # Log the incomplete URLs
    if not incomplete_urls.empty:
        logger.warning(
            f"{len(incomplete_urls)} incomplete GitHub URLs found and will not "
            f"be analysed:"
        )
        for url in incomplete_urls["repourl"]:
            logger.info(f"Excluding the repourl: {url}")

    # Filter out incomplete URLs using the helper function
    filtered_df = df[df["repourl"].apply(is_complete_url)]
    return filtered_df


def get_base_repo_url(url):
    """
    Extracts the base repository URL from various hosting platforms.
    Handles URLs ending with '.git', supports nested groups in GitLab,
    and adapts to different platform URL structures.

    Args:
      url (str): The full URL to a Git repository.

    Returns:
      str: The base repository URL if valid, otherwise returns None.
    """
    # Return None immediately if the URL is None or empty
    if not url:
        return None

    parsed_url = urlparse(url)
    path = parsed_url.path.strip("/")

    # Host-specific criteria for handling '.git'
    hosts_with_mandatory_git_suffix = [
        "git.savannah.gnu.org",
        "git.torproject.org",
        "git.taler.net",
    ]
    should_strip_git = not any(
        host in parsed_url.netloc for host in hosts_with_mandatory_git_suffix
    )

    if path.endswith(".git") and should_strip_git:
        path = path[:-4]  # Remove the last 4 characters, '.git'

    parts = path.split("/")
    print(f"parts: {parts}")

    # Check if the URL lacks specific repository details(owner/reponame)
    if len(parts) < 2:
        return None
        # Define platforms that use the complete path without slicing
    direct_path_platforms = {
        "gitlab.com",
        "gitlab.torproject.org",
        "codeberg.org",
        "framagit.org",
        "hydrillabugs.koszko.org",
        "git.replicant.us",
        "gerrit.osmocom.org",
    }

    # Determine the base path based on the hosting platform
    if any(host in parsed_url.netloc for host in direct_path_platforms):
        base_path = "/".join(parts)
    else:
        base_path = "/".join(parts[:2])  # Default handling for GitHub-like URLs

    return f"{parsed_url.scheme}://{parsed_url.netloc}/{base_path}"


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

    # Save the dataframe as a CSV file
    df.to_csv(output_dir / "original.csv", index=False)
    logger.info(
        f'Dataframe "original.csv" is created from the ".tsv" '
        f"file and saved in {output_dir} "
    )

    # Some of the URLs end with "/". I need to remove them.
    df["repourl"] = df["repourl"].str.rstrip("/")

    # Removing duplicate rows
    remove_duplicates(df)

    # Removing null value is any (There is no null values in the data at the
    # moment)
    remove_null_values(df)

    # replace http with https
    df["repourl"] = df["repourl"].str.replace(r"^http\b", "https", regex=True)

    # Extract the domain from the URL
    df["repodomain"] = df["repourl"].str.extract(r"https?://(www\.)?([^/]+)")[1]

    # Extracting the base repo url
    df["base_repo_url"] = df["repourl"].apply(get_base_repo_url)

    filter_out_incomplete_urls(df)

    # Remove any rows with invalid URLs
    df = df[df["base_repo_url"].notna()]

    # Remove any rows with invalid repodomain
    df = df[df["repodomain"].notna()]

    # Save the dataframe as a CSV file
    df.to_csv(output_dir / "original_massive_df.csv", index=False)
    logger.info(
        f'Dataframe "original_massive_df" is created from the '
        f'"original_df.csv" '
        f"file and saved in {output_dir} "
    )

    logger.info("Creating separate DataFrames for each domain: \n ")
    # Get the distinct repo domains
    distinct_domains = df["repodomain"].unique()

    # A dictionary comprehension is used to create a separate DataFrame for each
    # unique domain. For each domain in the list of unique domains, we filter
    # the original DataFrame to only include rows where the 'Domain' column
    # matches the current domain. We then drop the 'Domain' column since it's
    # no longer needed and reset the index to clean up the DataFrame.

    dfs_by_domain = {
        domain: df[df["repodomain"] == domain]
        .drop("repodomain", axis=1)
        .reset_index(drop=True)
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

    other_domains_df = pd.DataFrame(columns=df.columns)

    for domain, domain_df in dfs_by_domain.items():
        if len(domain_df) >= 10:
            domain_df.to_csv(
                data_folder / f"{domain.replace('/', '_').replace(':', '_')}.csv",
                index=False,
            )
            logger.info(
                f"Saved {domain} domain DataFrame with "
                f"{len(domain_df)} entries to {data_folder}"
            )

        # Append DataFrames with less than 10 repositories to the
        # other_domains_df
        else:
            other_domains_df = pd.concat(
                [other_domains_df, domain_df], ignore_index=True
            )

    # Save the DataFrame containing domains with less than 10 repositories
    if not other_domains_df.empty:
        other_domains_df.to_csv(data_folder / "other_domains.csv", index=False)
        logger.info(
            f"Saved DataFrame with domains having less than 10 repositories to: "
            f"{data_folder / 'other_domains.csv'}"
        )
