"""
This script performs analysis on a dataset containing information about various
code hosting platform repositories and visualises the results using a Sankey
diagram.


Variables:
    - working_directory: Path to the working directory or Git root directory.
    - df: DataFrame containing the original data read from a CSV file.
    - test_file_categories: Dictionary categorising test file counts into bins.
    - domain_counts: Series containing the count of repositories per domain.
    - domains_more_than_ten: List of domains with more than ten repositories.
    - domains_less_than_ten_count: Total count of repositories across domains
    with ten or fewer repositories.
    - node_dict: Dictionary mapping node names to numerical indices for Sankey
    diagram visualisation.
    - sources, targets, values: Lists storing sources, targets, and values for
    Sankey diagram links.
"""

import pandas as pd
from loguru import logger
from utils.git_utils import get_working_directory_or_git_root
import plotly.graph_objects as go
import re
from collections import defaultdict


def add_node(node_name):
    global counter
    if node_name not in node_dict:
        node_dict[node_name] = counter
        counter += 1


# Function to parse the test_runners column and return a dict of test runners
# and their counts
def parse_test_runners(runners_str):
    """Parses the 'test_runners' column in the dataset to extract test runners
    and their counts."""

    if pd.isna(runners_str) or runners_str in ["nan", "None detected"]:
        return {}
    runners = defaultdict(int)
    parts = runners_str.split(",")
    for part in parts:
        match = re.match(r"(\w+):\s*(\d+)", part.strip())
        if match:
            runners[match.group(1)] += int(match.group(2))
    return dict(runners)


# Setting up the working directory and logger
working_directory = get_working_directory_or_git_root()
logger.info(f"Working directory is: {working_directory}")

# Reading the original data
df = pd.read_csv(working_directory / "data" / "updated_local_github_df_test_count.csv")

# Clone status updated for null values as 'not cloned'
df["clone_status"] = df["clone_status"].fillna("not cloned")
df["Repos Not Cloned"] = df["clone_status"] == "not cloned"
df["Repos Cloned"] = df["clone_status"] == "successful"

# Apply the parsing function to the test_runners column
df["parsed_test_runners"] = df["test_runners"].apply(parse_test_runners)

# Sum test runners for cloned repositories
test_runner_counts = defaultdict(int)
for index, row in df[df["Repos Cloned"]].iterrows():
    for runner, count in row["parsed_test_runners"].items():
        test_runner_counts[runner] += count

# Test file counts categorized
bins = [-1, 0, 9, 99, 999, float("inf")]
labels = [
    "0 test files",
    "1 - 9 test files",
    "10 - 99 test files",
    "100 - 999 test files",
    "More than 1000 test files",
]
df["Test File Categories"] = pd.cut(
    df["testfilecountlocal"], bins=bins, labels=labels, right=True
)

# Categories for test files
test_file_categories = {
    "0 test files": (0, 0),
    "1 - 9 test files": (1, 9),
    "10 - 99 test files": (10, 99),
    "100 - 999 test files": (100, 999),
    "More than 1000 test files": (1000, float("inf")),  # Renamed for clarity
}

# Prepare domain counts
domain_counts = df["repodomain"].value_counts()
domains_more_than_ten = domain_counts[domain_counts > 10].index.tolist()
domains_less_than_ten_count = domain_counts[domain_counts <= 10].sum()

# Node dictionary for indexing
node_dict = {}
counter = 0

# Initialise source, target, and value lists for Sankey
sources = []
targets = []
values = []

# Add nodes
add_node("Original Data")
for domain in domains_more_than_ten:
    add_node(domain)
add_node("Domains with < 10 Repos")
add_node("Duplicates")
add_node("Incomplete URLs")
add_node("Base Repo URL Issues")
add_node("Repos not Cloned")
add_node("Repos Cloned")


for category in test_file_categories.keys():
    add_node(category)

# Add nodes and links for test runners
for runner, count in test_runner_counts.items():
    add_node(runner)  # Create a node for each test runner

# Link from 'Original Data' to individual domains and grouped node
sources.append(node_dict["Original Data"])
targets.append(node_dict["Domains with < 10 Repos"])
values.append(domains_less_than_ten_count)

for domain in domains_more_than_ten:
    sources.append(node_dict["Original Data"])
    targets.append(node_dict[domain])
    values.append(domain_counts[domain])

    # Link domains to Duplicates if applicable
    domain_duplicates_count = df[
        (df["repodomain"] == domain) & df["duplicate_flag"]
    ].shape[0]
    if domain_duplicates_count > 0:
        sources.append(node_dict[domain])
        targets.append(node_dict["Duplicates"])
        values.append(domain_duplicates_count)

    # Link domain to Incomplete URLs if applicable, excluding duplicates
    domain_incomplete_urls_count = df[
        (df["repodomain"] == domain) & df["incomplete_url_flag"] & ~df["duplicate_flag"]
    ].shape[0]
    if domain_incomplete_urls_count > 0:
        sources.append(node_dict[domain])
        targets.append(node_dict["Incomplete URLs"])
        values.append(domain_incomplete_urls_count)

    # Link domain to Base Repo URL Issues if applicable, excluding duplicates
    # and Incomplete URLs
    domain_base_repo_url_issues_count = df[
        (df["repodomain"] == domain)
        & df["base_repo_url_flag"]
        & ~df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
    ].shape[0]
    if domain_base_repo_url_issues_count > 0:
        sources.append(node_dict[domain])
        targets.append(node_dict["Base Repo URL Issues"])
        values.append(domain_base_repo_url_issues_count)

    # Link domain to Repos Not Cloned if applicable, excluding duplicates,
    # Incomplete URLs, Base Repo URL Issues
    domain_repos_not_cloned_count = df[
        (df["repodomain"] == domain)
        & df["Repos Not Cloned"]
        & ~df["base_repo_url_flag"]
        & ~df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
    ].shape[0]
    if domain_repos_not_cloned_count > 0:
        sources.append(node_dict[domain])
        targets.append(node_dict["Repos not Cloned"])
        values.append(domain_repos_not_cloned_count)

    # Link domain to Repos Cloned if applicable, excluding duplicates,
    # Incomplete URLs, Base Repo URL Issues
    domain_repos_cloned_count = df[
        (df["repodomain"] == domain)
        & df["Repos Cloned"]
        & ~df["base_repo_url_flag"]
        & ~df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
    ].shape[0]
    if domain_repos_cloned_count > 0:
        sources.append(node_dict[domain])
        targets.append(node_dict["Repos Cloned"])
        values.append(domain_repos_cloned_count)

# Link 'Domains with < 10 Repos' to Duplicates if applicable
less_than_ten_duplicates_count = df[
    (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
    & df["duplicate_flag"]
].shape[0]
if less_than_ten_duplicates_count > 0:
    sources.append(node_dict["Domains with < 10 Repos"])
    targets.append(node_dict["Duplicates"])
    values.append(less_than_ten_duplicates_count)

# Link 'Domains with < 10 Repos' to Incomplete URLs if applicable, excluding duplicates
less_than_ten_incomplete_urls_count = df[
    (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
    & df["incomplete_url_flag"]
    & ~df["duplicate_flag"]
].shape[0]
if less_than_ten_incomplete_urls_count > 0:
    sources.append(node_dict["Domains with < 10 Repos"])
    targets.append(node_dict["Incomplete URLs"])
    values.append(less_than_ten_incomplete_urls_count)

# Link 'Domains with < 10 Repos' to Base Repo URL Issues if applicable, excluding duplicates and Incomplete URLs
less_than_ten_base_repo_url_issues_count = df[
    (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
    & df["base_repo_url_flag"]
    & ~df["incomplete_url_flag"]
    & ~df["duplicate_flag"]
].shape[0]
if less_than_ten_base_repo_url_issues_count > 0:
    sources.append(node_dict["Domains with < 10 Repos"])
    targets.append(node_dict["Base Repo URL Issues"])
    values.append(less_than_ten_base_repo_url_issues_count)

# Link 'Domains with < 10 Repos' to Repos Not Cloned if applicable, excluding
# duplicates, Incomplete URLs, Base Repo URL Issues
less_than_ten_repos_not_cloned_count = df[
    (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
    & df["Repos Not Cloned"]
    & ~df["base_repo_url_flag"]
    & ~df["incomplete_url_flag"]
    & ~df["duplicate_flag"]
].shape[0]
if less_than_ten_repos_not_cloned_count > 0:
    sources.append(node_dict["Domains with < 10 Repos"])
    targets.append(node_dict["Repos not Cloned"])
    values.append(less_than_ten_repos_not_cloned_count)

# Link 'Domains with < 10 Repos' to Repos Cloned if applicable, excluding
# duplicates, Incomplete URLs, Base Repo URL Issues
less_than_ten_repos_cloned_count = df[
    (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
    & df["Repos Cloned"]
    & ~df["base_repo_url_flag"]
    & ~df["incomplete_url_flag"]
    & ~df["duplicate_flag"]
].shape[0]
if less_than_ten_repos_cloned_count > 0:
    sources.append(node_dict["Domains with < 10 Repos"])
    targets.append(node_dict["Repos Cloned"])
    values.append(less_than_ten_repos_cloned_count)


# Link from 'Repos Cloned' to the test file categories
repos_cloned_index = node_dict["Repos Cloned"]
for category, (lower_bound, upper_bound) in test_file_categories.items():
    # Filter df to find counts within bounds for cloned repos
    count = df[
        (df["Repos Cloned"])
        & (df["testfilecountlocal"] >= lower_bound)
        & (df["testfilecountlocal"] <= upper_bound)
    ].shape[0]
    if count > 0:
        sources.append(repos_cloned_index)
        targets.append(node_dict[category])
        values.append(count)

# Link from 'Repos Cloned' to the test runners
for runner, count in test_runner_counts.items():
    if count > 0:
        sources.append(repos_cloned_index)
        targets.append(node_dict[runner])
        values.append(count)


# Visualise the Sankey Diagram including the Duplicates layer
fig = go.Figure(
    data=[
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=[k for k in node_dict.keys()],
            ),
            link=dict(source=sources, target=targets, value=values),
        )
    ]
)
fig.update_layout(
    title_text="Extended Project Analysis Sankey Diagram with " "Test Runners",
    font_size=12,
)
fig.show()
