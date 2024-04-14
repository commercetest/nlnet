"""
This script reads a TSV file into a Pandas DataFrame, performs data cleaning
and preprocessing steps, and saves the results as CSV files. The preprocessing
includes checking for null values and duplicate rows in the DataFrame.

Additionally, the script:
- Extracts the domain from each URL in the 'repourl' column to determine where
  the code is hosted.
- Separates the DataFrame into multiple DataFrames based on the unique domains,
  facilitating domain-specific analyses.
- Saves DataFrames that contain more than 10 entries into a structured directory
  format, specifically catering to repositories hosted under distinct domains.

"""

import pandas as pd
import numpy as np
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root
import os


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


git_working_dir = get_working_directory_or_git_root()
logger.info(f"git_working_dir is : {git_working_dir}")

# Loading the original tsv file provided by NLNET
df_path = git_working_dir / "data" / "project_repos_from_jos_2024-feb-22.tsv"
logger.info(f"df_path is : {df_path}")

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
df = pd.DataFrame({"projectref": a_values, "nlnetpage": b_values, "repourl": c_values})


# Save the dataframe as a CSV file
path_to_data_folder = git_working_dir / "data"

# Applying preprocessing steps
check_and_clean_data(df)

# I will keep the first occurrence of each duplicate row and remove the
# others:
df = df.drop_duplicates(keep="first")
df.to_csv(path_to_data_folder / "original.csv", index=False)


# Extract the domain from the URL
df["domain"] = df["repourl"].str.extract(r"https?://(www\.)?([^/]+)")[1]

# Get the distinct domains
distinct_domains = df["domain"].unique()

# Create separate DataFrames for each domain
# A dictionary comprehension is used to create a separate DataFrame for each
# unique domain. For each domain in the list of unique domains, we filter the
# original DataFrame to only include rows where the 'Domain' column matches the
# current domain. We then drop the 'Domain' column since it's no longer needed
# and reset the index to clean up the DataFrame.
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

for domain, count in sorted_repo_counts_by_domain.items():
    print(f"{domain}: {count}")

# Set the directory path for saving the DataFrames
data_folder = path_to_data_folder
output_dir = data_folder / "source_code_hosting_platform_dfs"

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

for domain, domain_df in dfs_by_domain.items():
    if len(domain_df) > 10:
        domain_df.to_csv(
            output_dir / f"{domain.replace('/', '_').replace(':', '_')}.csv",
            index=False,
        )
        logger.info(
            f"Saved {domain} domain DataFrame with {len(domain_df)} entries to {output_dir}"
        )
