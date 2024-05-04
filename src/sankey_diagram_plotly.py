"""
Script for processing domain-specific data and generating a Sankey diagram of
the analysis.

This script reads an original data file, processes domain-specific data, and
visualises the analysis results using a Sankey diagram. The processing involves
the following steps:
1. Removing duplicates from domain-specific data.
2. Filtering out entries with incomplete URLs.
3. Dropping rows with null values.

The script sets up the working directory and logger, reads the original data
file, and filters the data to include only domains with more than four
occurrences. It then calculates various metrics for each domain, including the
 number of duplicates, incomplete URLs, and null values.

Based on the processed data, the script constructs a Sankey diagram to
visualise the flow of data analysis, including transitions from the original
data to domain-specific data, and from domains to outcome nodes
representing duplicates, entries with incomplete URLs, and rows with null values.

The generated Sankey diagram is saved as an HTML file in the
'reports/graphs/sankey-diagram-of-analysis' directory.
"""

import pandas as pd
import plotly.graph_objects as go
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root
from utils.initial_data_preparation import (
    filter_out_incomplete_urls,
    remove_duplicates,
)


def process_domain_df(domain_df):
    # Removing duplicates
    unique_df, num_duplicates = remove_duplicates(domain_df)

    # Filtering out incomplete URLs
    complete_df = filter_out_incomplete_urls(unique_df)
    num_incomplete_urls = len(unique_df) - len(complete_df)

    # Dropping null values
    no_null_df = complete_df.dropna()
    num_null_values = len(complete_df) - len(no_null_df)

    return {
        "duplicates_count": num_duplicates,
        "incomplete_urls_count": num_incomplete_urls,
        "null_values_count": num_null_values,
    }


# Setting up the working directory and logger
working_directory = get_working_directory_or_git_root()
logger.info(f"Working directory is: {working_directory}")


# Reading the original data
original_df = pd.read_csv(working_directory / "data" / "original.csv")
initial_row_count = original_df.shape[0]

original_df["repodomain"] = original_df["repourl"].str.extract(
    r"https?://(www\.)?([^/]+)"
)[1]
repodomain_counts = original_df["repodomain"].value_counts()

domains_with_more_than_four = repodomain_counts[repodomain_counts > 6].index


# Filter the original DataFrame
filtered_original_df = original_df[
    original_df["repodomain"].isin(domains_with_more_than_four)
]
repodomain_counts = filtered_original_df["repodomain"].value_counts()

# Nodes for Sankey Diagram
node_labels = [
    # 0
    "Original Data",
    # 1-3
    *repodomain_counts.index.tolist(),
    # 4
    "Duplicates",
    # 5
    "No Repo Name",
    # 6
    "Null values",
]

# Links for Sankey Diagram
# Initialise the indices for sources and targets
source_indices = []
target_indices = []
values = []

# Original Data to domains
for i, domain in enumerate(repodomain_counts.index, start=1):
    source_indices.append(0)
    target_indices.append(i)
    values.append(repodomain_counts[domain])


# Calculate domain results and aggregate to outcome nodes
domain_results = {}
duplicates_total = 0
incomplete_urls_total = 0
null_values_total = 0

for domain in repodomain_counts.index:
    domain_df = filtered_original_df[filtered_original_df["repodomain"] == domain]
    result = process_domain_df(domain_df)
    domain_results[domain] = result
    duplicates_total += result["duplicates_count"]
    incomplete_urls_total += result["incomplete_urls_count"]
    null_values_total += result["null_values_count"]

# Adding links from each domain to the outcome nodes
duplicate_index = len(repodomain_counts) + 1
incomplete_url_index = duplicate_index + 1
null_value_index = incomplete_url_index + 1

for i, domain in enumerate(repodomain_counts.index, start=1):
    # Link to Duplicates
    source_indices.append(i)
    target_indices.append(duplicate_index)
    values.append(domain_results[domain]["duplicates_count"])

    # Link to Incomplete URLs
    source_indices.append(i)
    target_indices.append(incomplete_url_index)
    values.append(domain_results[domain]["incomplete_urls_count"])

    # Link to Null Values
    source_indices.append(i)
    target_indices.append(null_value_index)
    values.append(domain_results[domain]["null_values_count"])


# Creating the Sankey Diagram
fig = go.Figure(
    data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=node_labels,
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                # Adding labels for each link indicating the number of excluded rows
                label=[f"{v} rows excluded" for v in values],
            ),
        )
    ]
)


fig.write_html(
    working_directory
    / "reports"
    / "graphs"
    / "sankey-diagram-of-analysis"
    / "sankey-diagram-plotly.html"
)

fig.show()
