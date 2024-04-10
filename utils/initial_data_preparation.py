"""
This script reads a TSV file into a Pandas DataFrame, performs data cleaning
and preprocessing steps, and saves the results as CSV files. It also checks for
null values and duplicate rows in the DataFrame.

In addition to this, the rows from the original df where the
code is hosted in the github.com domain is extracted and saved.

"""

import pandas as pd
import numpy as np
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root


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

# Extracting the rows which host the code on github.com domain
original_github_df = df[df["repourl"].str.contains("github.com")]
original_github_df.to_csv(path_to_data_folder / "original_github_df.csv", index=False)
