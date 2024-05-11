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
from utils.string_utils import sanitise_directory_name
import os
from urllib.parse import urlparse
import json
from json import JSONEncoder
import time


class NumpyEncoder(JSONEncoder):
    """Custom encoder for numpy data types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return JSONEncoder.default(self, obj)


# Define a custom error class
class UnsupportedURLError(ValueError):
    pass


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


def mark_duplicates(df, output_path):
    """
    Adds a 'duplicate_flag' column to the DataFrame to indicate duplicate rows,
    and logs the process in a JSONLines file.

    Parameters:
        df (pd.DataFrame): The DataFrame in which to mark duplicates.
        output_path (str): The file path to write the JSONLines output.

    Returns:
        pd.DataFrame: The DataFrame with an added 'duplicate_flag' column.
    """
    logger.info("Marking duplicate rows.")
    start_time = int(time.time() * 1000)

    # 'duplicate_flag' is `False` for the first occurrence, and it is `True`
    # for the duplicate row
    df["duplicate_flag"] = df.duplicated(keep="first")
    duplicates_count = df["duplicate_flag"].sum()

    end_time = int(time.time() * 1000)
    duration = end_time - start_time

    logger.info(f"Marked {duplicates_count} duplicate rows.")

    # Create JSONLine entry
    jsonline = {
        "step_name": "Marking Duplicates",
        "execution_start": start_time,
        "execution_end": end_time,
        "duration_millis": duration,
        "errors_encountered": False,
        "data": {
            "total_rows": len(df),
            "duplicates_marked": duplicates_count,
            "example_duplicate": df[df["duplicate_flag"]].head(1).to_dict("records")[0]
            if duplicates_count
            else {},
        },
    }

    # Write to JSONLines file
    with open(output_path, "a") as f:
        f.write(json.dumps(jsonline, cls=NumpyEncoder) + "\n")

    return df


def mark_null_values(df, output_path):
    """
    Adds a 'null_value_flag' column to the DataFrame to indicate rows with null
    values, and logs the process in a JSONLines file.

    Parameters:
        df (pd.DataFrame): The DataFrame in which to mark null values.
        output_path (str): The file path to write the JSONLines output.

    Returns:
        pd.DataFrame: The DataFrame with an added 'null_value_flag' column.
    """
    logger.info("Marking rows with null values.")
    start_time = int(time.time() * 1000)

    # Create a flag column for rows containing null values
    df["null_value_flag"] = df.isnull().any(axis=1)
    nulls_count = df["null_value_flag"].sum()

    end_time = int(time.time() * 1000)
    duration = end_time - start_time

    logger.info(f"Marked {nulls_count} rows with null values.")

    # Create JSONLine entry
    jsonline = {
        "step_name": "Marking Null Values",
        "execution_start": start_time,
        "execution_end": end_time,
        "duration_millis": duration,
        "errors_encountered": False,
        "data": {
            "total_rows": len(df),
            "nulls_marked": nulls_count,
            "example_null_row": df[df["null_value_flag"]].head(1).to_dict("records")[0]
            if nulls_count
            else {},
        },
    }

    # Write to JSONLines file
    with open(output_path, "a") as f:
        f.write(json.dumps(jsonline, cls=NumpyEncoder) + "\n")

    return df


# Define a function to extract domain and flag errors
def extract_and_flag_domains(df):
    """
    Extracts domains from URLs and flags rows with unsupported URL schemes.

    Parameters:
        df (pd.DataFrame): DataFrame containing the 'repourl' column with URLs.

    Returns:
        pd.DataFrame: Updated DataFrame with 'repodomain' and 'unsupported_url_flag' columns.
    """

    def get_domain(url):
        parsed_url = urlparse(url)
        if parsed_url.scheme in ["http", "https", "git"]:
            return parsed_url.hostname
        else:
            return None

    # Apply the domain extraction function
    df["repodomain"] = df["repourl"].apply(get_domain)

    # Flag rows where the domain could not be extracted
    # (i.e., unsupported schemes)
    df["domain_extraction_flag"] = df["repodomain"].isnull()
    # Count problematic rows and log them
    unsupported_count = df["domain_extraction_flag"].sum()

    logger.info(f"Found {unsupported_count} rows with unsupported domains")

    return df


def filter_out_incomplete_urls(df, output_path):
    """
    Identifies incomplete URLs in the DataFrame by adding a new boolean column
    `incomplete_url_flag`.A URL is considered complete if it contains at
    least five parts, including the protocol, empty segment (for '//'),
    domain, and at least two path segments, e.g.,
    'https://github.com/owner/repo'. Raises an error if the required column
    'repourl' is missing. Logs the process in a JSONLines file.

    Args:
        df (pd.DataFrame): DataFrame containing URLs.
        output_path (str): The file path to write the JSONLines output.

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
        parts = url.rstrip("/").split("/")
        return len(parts) >= 5

    # Identify rows with incomplete URLs using the helper function
    df["incomplete_url_flag"] = ~df["repourl"].apply(is_complete_url)
    incomplete_count = df["incomplete_url_flag"].sum()
    logger.info(
        f"Filtering Out Incomplete URLs: Found {incomplete_count} incomplete " f"URLs."
    )
    # Log the processing step
    start_time = int(time.time() * 1000)
    incomplete_count = df["incomplete_url_flag"].sum()
    end_time = int(time.time() * 1000)

    jsonline = {
        "step_name": "Filter Incomplete URLs",
        "execution_start": start_time,
        "execution_end": end_time,
        "duration_millis": end_time - start_time,
        "errors_encountered": incomplete_count > 0,
        "data": {"total_urls_processed": len(df), "incomplete_urls": incomplete_count},
    }

    # Write to JSONLines file
    with open(output_path, "a") as f:
        f.write(json.dumps(jsonline, cls=NumpyEncoder) + "\n")

    return df


def get_base_repo_url(df, output_path):
    """
    Extracts the base repository URL from various hosting platforms and logs
    the process. Adds a 'base_repo_url_flag' column to indicate success or
    failure of extraction.

    Args:
       df (pd.DataFrame): DataFrame containing URLs.
       output_path (str): The file path to write the JSONLines output.

    Returns:
      pd.DataFrame: The updated DataFrame with 'base_repo_url' and
      'base_repo_url_flag' columns.
    """

    # Return None immediately if the URL is None or empty
    def extract_url(url):
        if not url:
            return None, True

        parsed_url = urlparse(url)
        path = parsed_url.path.strip("/")

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
            base_path = "/".join(parts)
        elif len(parts) < 2:
            # Check if the URL lacks specific repository details(owner/reponame)
            return None, True  # URL lacks sufficient parts
        else:
            base_path = "/".join(parts[:2])  # Default handling for GitHub-like
            # URLs

        return f"{parsed_url.scheme}://{parsed_url.netloc}/{base_path}", False

    # Apply the function to extract URL and flag
    result = df["repourl"].apply(lambda x: extract_url(x))
    df["base_repo_url"] = result.apply(lambda x: x[0])
    df["base_repo_url_flag"] = result.apply(lambda x: x[1])

    flagged_count = df["base_repo_url_flag"].sum()
    logger.info(
        f"Getting Base Repo URL: Found {flagged_count} rows with URL "
        f"extraction "
        f"issues."
    )

    # Log the operation
    start_time = int(time.time() * 1000)
    flagged_count = df["base_repo_url_flag"].sum()
    end_time = int(time.time() * 1000)

    jsonline = {
        "step_name": "Extract Base Repo URL",
        "execution_start": start_time,
        "execution_end": end_time,
        "duration_millis": end_time - start_time,
        "errors_encountered": flagged_count > 0,
        "data": {
            "total_urls_processed": len(df),
            "urls_flagged_as_incomplete": flagged_count,
        },
    }

    # Write to JSONLines file
    with open(output_path, "a") as f:
        f.write(json.dumps(jsonline, cls=NumpyEncoder) + "\n")

    return df


def add_explanations(df):
    """
    Adds an 'explanation' column to the DataFrame, which contains detailed
    descriptions of any flags or conditions that affect each row.

    Args:
        df (pd.DataFrame): The DataFrame containing the data and flags.

    Returns:
        pd.DataFrame: The updated DataFrame with an 'explanation' column added.
    """

    def get_explanation(row):
        explanations = []
        if row.get("duplicate_flag", False):
            explanations.append("Row is marked as a duplicate of another entry.")
        if row.get("null_value_flag", False):
            explanations.append("Row contains null values.")
        if row.get("base_repo_url_flag", False):
            explanations.append("Unable to extract base repository URL.")
        if row.get("incomplete_url_flag", False):
            url_parts = row["repourl"].rstrip("/").split("/")
            if len(url_parts) < 5:
                missing_parts = 5 - len(url_parts)
                explanations.append(
                    f"URL is incomplete; missing {missing_parts}"
                    f" parts (expects protocol, domain, and "
                    f"path)."
                )
        if row.get("domain_extraction_flag", False):
            explanations.append(
                "Domain could not be extracted due to " "unsupported or malformed URL."
            )

        return " | ".join(explanations) if explanations else "No issues detected."

    # Apply the get_explanation function to each row
    df["explanation"] = df.apply(get_explanation, axis=1)

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

    # Strip leading '+' characters, then strip leading/trailing spaces, and
    # remove trailing slashes
    df["repourl"] = df["repourl"].str.lstrip("+").str.rstrip("/").str.strip()

    output_json_path = str(output_dir / "process_log.jsonl")
    # Marking duplicate rows
    df = mark_duplicates(df, output_json_path)
    df = mark_null_values(df, output_json_path)

    # replace http with https
    df["repourl"] = df["repourl"].str.replace(r"^http\b", "https", regex=True)

    # Extracts domains from URLs and flags rows with unsupported URL schemes.
    # unsupported_url_flag: A boolean flag that is True for rows where the
    # domain extraction returned None
    df = extract_and_flag_domains(df)

    # Identifies incomplete URLs in the DataFrame by adding a new boolean column
    # `incomplete_url_flag`.
    df = filter_out_incomplete_urls(df, output_json_path)

    # Extracting the base repo url
    df = get_base_repo_url(df, output_json_path)

    # Adding an explanation column
    df = add_explanations(df)

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
