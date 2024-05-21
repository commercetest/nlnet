"""
This script processes a TSV file to create a DataFrame, performs data
cleaning, and organises entries into separate DataFrames based on the domain
extracted from URLs. Each domain-specific DataFrame is saved as a CSV file if
it contains more than 10 records. It also performs detailed data cleaning by
removing rows with null values and duplicates, and ensures URLs are complete
and well-formed before extracting the domain for analysis.

Features:
- **Data Input and Cleaning**: Reads a user-specified TSV file to create a
DataFrame, checks for null values and duplicates, and ensures that URLs are
complete and well-formed. The script also converts HTTP URLs to HTTPS and
removes trailing slashes to standardise URL formats.
- **Domain Extraction and Organisation**: Extracts domains from URLs and
organises the data into separate DataFrames based on these domains.
- **Data Output**: Saves DataFrames that contain more than 10 entries as CSV
in a structured directory format, catering to repositories hosted under distinct
domains. Additionally, it outputs the count of repositories for each domain
into a text file for easy reference and further analysis.
- **Command Line Flexibility**: Supports command-line arguments that allow users
to specify custom paths for the input TSV file and the output directory.

Command Line Arguments:
- --input-file: Specifies the path to the input TSV file.
- --output-folder: Specifies the directory where output CSV files and other
  results will be saved. Defaults to 'data/'.

Functions:
- parse_args(): Parses command-line arguments to customise input and output paths.
- mark_duplicates(df): Marks duplicate rows in the DataFrame.
- mark_null_values(df): Marks rows with null values in the DataFrame.
- extract_and_flag_domains(df): Extracts domains from URLs and flags rows with unsupported URL schemes.
- mark_incomplete_urls(df): Identifies incomplete URLs in the DataFrame.
- get_base_repo_url(df): Extracts the base repository URL from various hosting platforms.


Usage:
To run the script with default paths:
    python initial_data_preparation.py

To specify custom paths:
    python initial_data_preparation.py --input-file path/to/input_file.tsv
                                       --output-folder path/to/output_directory
"""

import pandas as pd
import argparse
from pathlib import Path
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root
from utils.string_utils import sanitise_directory_name
import os
from urllib.parse import urlparse

# Constants for URL validation
EXPECTED_URL_PARTS = 5


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


def mark_duplicates(df):
    """
    Adds a 'duplicate_flag' column to the DataFrame to indicate duplicate rows.

    Parameters:
        df (pd.DataFrame): The DataFrame in which to mark duplicates.

    Returns:
        pd.DataFrame: The DataFrame with an added 'duplicate_flag' column.
    """

    logger.info("Marking duplicate rows.")

    # 'duplicate_flag' is `False` for the first occurrence, and it is `True`
    # for the duplicate row
    df["duplicate_flag"] = df.duplicated(keep="first")
    duplicates_count = df["duplicate_flag"].sum()

    logger.info(f"Marked {duplicates_count} duplicate rows.")

    return df


def mark_null_values(d):
    """
    Adds a 'null_value_flag' column to the DataFrame to indicate rows with null
    values.

    Parameters:
        df (pd.DataFrame): The DataFrame in which to mark null values.

    Returns:
        pd.DataFrame: The DataFrame with an added 'null_value_flag' column.
    """
    logger.info("Marking rows with null values.")
    df["null_value_flag"] = False  # Initialise all rows to False
    non_duplicate_rows = ~df["duplicate_flag"]  # Identify non-duplicate rows
    # Set 'null_value_flag' to True only for non-duplicate rows with any null values
    df.loc[non_duplicate_rows & df.isnull().any(axis=1), "null_value_flag"] = True
    nulls_count = df["null_value_flag"].sum()

    logger.info(f"Marked {nulls_count} rows with null values.")

    return df


# Define a function to extract domain and flag errors
def extract_and_flag_domains(df):
    """
    Extracts domains from URLs and flags rows with unsupported URL schemes.

    Parameters:
        df (pd.DataFrame): DataFrame containing the 'repourl' column with URLs.

    Returns:
        pd.DataFrame: Updated DataFrame with 'repodomain' and 'unsupported_url_scheme' columns.
    """

    def get_domain(url):
        parsed_url = urlparse(url)
        if parsed_url.scheme in ["http", "https", "git"]:
            return parsed_url.hostname
        else:
            return None

    # Apply the domain extraction function on non-duplicate rows
    non_duplicate_rows = ~df["duplicate_flag"]  # Identify non-duplicate rows
    df.loc[non_duplicate_rows, "repodomain"] = df.loc[
        non_duplicate_rows, "repourl"
    ].apply(get_domain)

    # Flag rows where the domain could not be extracted
    # (i.e., unsupported schemes)
    df["unsupported_url_scheme"] = df["repodomain"].isnull()
    # Count problematic rows (excluding duplicate rows) and log them
    unsupported_count = df.loc[non_duplicate_rows, "unsupported_url_scheme"].sum()

    logger.info(f"Found {unsupported_count} rows with unsupported domains")

    return df


def mark_incomplete_urls(df):
    """
    Identifies incomplete URLs in the DataFrame by adding a new boolean column
    `incomplete_url_flag`.A URL is considered complete if it contains at
    least five parts, including the protocol, empty segment (for '//'),
    domain, and at least two path segments, e.g.,
    'https://github.com/owner/repo'. Raises an error if the required column
    'repourl' is missing. Logs the process in a JSONLines file.

    Args:
        df (pd.DataFrame): DataFrame containing URLs.

    Returns:
        pd.DataFrame: The original DataFrame with the new
        `incomplete_url_flag` column.

    Raises:
        ValueError: If the 'repourl' column is missing from the DataFrame.
    """
    if "repourl" not in df.columns:
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
        parts = url.split("/")
        return len(parts) >= EXPECTED_URL_PARTS

    # Identify rows with incomplete URLs using the helper function
    non_duplicate_rows = ~df["duplicate_flag"]  # Identify non-duplicate rows
    domain_extraction_successful = ~df[
        "unsupported_url_scheme"
    ]  # Check for successful domain extraction
    # Apply the incomplete URL flag condition on non-duplicate and unsuccessful domain extraction rows
    df["incomplete_url_flag"] = ~df.loc[
        non_duplicate_rows & domain_extraction_successful, "repourl"
    ].apply(is_complete_url)
    df["incomplete_url_flag"] = df["incomplete_url_flag"].astype(bool)
    incomplete_count = df["incomplete_url_flag"].sum()
    logger.info(f"Found {incomplete_count} incomplete " f"URLs.")

    return df


def get_base_repo_url(df):
    """
    Extracts the base repository URL from various hosting platforms and logs
    the process. Adds a 'base_repo_url_flag' column to indicate success or
    failure of extraction.

    Args:
       df (pd.DataFrame): DataFrame containing URLs.

    Returns:
      pd.DataFrame: The updated DataFrame with 'base_repo_url' and
      'base_repo_url_flag' columns.
    """

    # Return None immediately if the URL is None or empty
    def extract_url(url):
        if not url:
            return None, True  # Return None for URL, True for unsuccessful flag

        parsed_url = urlparse(url)
        path = parsed_url.path

        parts = path.split("/")

        # Define platforms that use the complete path without slicing
        direct_path_platforms = {
            "gitlab.com",
            "gitlab.torproject.org",
            "codeberg.org",
            "framagit.org",
            "hydrillabugs.koszko.org",
            "git.replicant.us",
            "gerrit.osmocom.org",
            "git.taler.net",
        }

        # Determine the base path based on the hosting platform
        if any(host in parsed_url.netloc for host in direct_path_platforms):
            base_path = path  # Use the whole path for these platforms
        elif len(parts) < 2:
            return None, True  # URL lacks sufficient parts, flag as unsuccessful
        else:
            base_path = "/".join(parts[:2])  # Standard handling for most URLs

        return f"{parsed_url.scheme}://{parsed_url.netloc}/{base_path}", False

    # Filter DataFrame based on specified conditions
    filtered_rows = (
        ~df["duplicate_flag"]
        & ~df["unsupported_url_scheme"]
        & ~df["incomplete_url_flag"]
    )
    results = df.loc[filtered_rows, "repourl"].apply(extract_url)

    # Apply results to the DataFrame
    df.loc[filtered_rows, "base_repo_url"] = results.apply(lambda x: x[0])
    df.loc[filtered_rows, "base_repo_url_flag"] = results.apply(lambda x: x[1])

    flagged_count = df["base_repo_url_flag"].sum()
    logger.info(
        f"Getting Base Repo URL: Found {flagged_count} rows with URL "
        f"extraction issues."
    )

    return df


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

    # Strip leading '+' characters, then remove trailing slashes, and strip
    # leading / trailing spaces,
    df["repourl"] = df["repourl"].str.lstrip("+").str.rstrip("/").str.strip()

    # Marking duplicate rows and Null values
    df = mark_duplicates(df)
    df = mark_null_values(df)

    # replace http with https
    df["repourl"] = df["repourl"].str.replace(r"^http\b", "https", regex=True)

    # Extracts domains from URLs and flags rows with unsupported URL schemes.
    # unsupported_url_flag: A boolean flag that is True for rows where the
    # domain extraction returned None
    df = extract_and_flag_domains(df)

    # Identifies incomplete URLs in the DataFrame by adding a new boolean column
    # `incomplete_url_flag`.
    df = mark_incomplete_urls(df)

    # Extracting the base repo url
    df = get_base_repo_url(df)

    # Save the dataframe as a CSV file
    df.to_csv(output_dir / "original_massive_df.csv", index=False)
    logger.info(
        f'Dataframe "original_massive_df.csv" has been created from the '
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
                data_folder / f"{sanitise_directory_name(domain)}.csv",
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
