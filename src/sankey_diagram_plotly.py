"""
This script visualises the usage of various test runners across cloned
repositories. It scans repositories for test patterns and dependencies, and
visualises the data using a Sankey diagram in a web browser.

Usage:
    The script is intended to be run with command line arguments specifying
    paths for input data and output:
    Command line usage example:
        python sankey_diagram_plotly.py --clone-dir=data/cloned_repos
        --input-file=data/input.csv --output-file=data/output.csv`
"""

import sys
import argparse
from pathlib import Path
from enum import Enum

import pandas as pd
import plotly.graph_objects as go
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root


class Node(Enum):
    ORIGINAL_DATA = "Original Data"
    DOMAINS_LESS_THAN_10 = "Domains with < 10 Repos"
    DUPLICATES = "Duplicates"
    INCOMPLETE_URLS = "Incomplete URLs"
    REPOS_NOT_CLONED = "Repos not Cloned"
    REPOS_CLONED = "Repos Cloned"
    JUNIT = "JUnit"
    PYTEST = "pytest"
    MOCHA = "Mocha"
    NO_TEST_RUNNER_DETECTED = "No test runner detected"


class TestCategory(Enum):
    ZERO_TEST_FILES = "0 test files"
    ONE_TO_NINE_TEST_FILES = "1 - 9 test files"
    TEN_TO_NINETY_NINE_TEST_FILES = "10 - 99 test files"
    HUNDRED_TO_NINE_NINE_NINE_TEST_FILES = "100 - 999 test files"
    MORE_THAN_THOUSAND_TEST_FILES = "More than 1000 test files"


def parse_args():
    """
    Parses and returns command line arguments specifying paths for input and
    output file, and clone directories.
    """
    parser = argparse.ArgumentParser(description="Repository clone directory")
    parser.add_argument(
        "--clone-dir",
        type=str,
        default=str(
            Path(get_working_directory_or_git_root()) / "data" / "cloned_repos"
        ),
        help="Defaults to a subdirectory within the project's data folder",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=str(Path("data/updated_local_github_df_test_count.csv")),
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=str(Path("data/ready_for_sankey.csv")),
        help="Path to the output CSV file.",
    )
    return parser.parse_args()


def load_data(file_path):
    logger.info(f"Loading data from {file_path}")
    return pd.read_csv(file_path)


def prepare_sankey_data(df):
    """
    Processes a DataFrame containing repository data to prepare the source,
    target, and value lists for generating a Sankey diagram. The function
    categorises repositories based on the number of test files and aggregates
    data on test runner usage.
    """

    # Test file counts categorised
    bins = [-1, 0, 9, 99, 999, float("inf")]
    labels = [category.value for category in TestCategory]

    df["Test File Categories"] = pd.cut(
        df["testfilecountlocal"], bins=bins, labels=labels, right=True
    )

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

    # Calculate sums for each test runner's file patterns
    logger.info("Calculate sums for each test runner's file patterns")
    df["JUnit_total"] = df["JUnit_file_patterns"]
    df["pytest_total"] = df["pytest_file_patterns"]
    df["Mocha_total"] = df["Mocha_file_patterns"]

    # Calculate 'No test runner detected'
    df["No_test_runner_detected"] = (
        (df["JUnit_total"] == 0) & (df["pytest_total"] == 0) & (df["Mocha_total"] == 0)
    ).astype(int)

    def add_node(node_enum):
        """
        Add a node to the Sankey graph.
        This function creates a node for the Sankey graph and assigns it a
        unique identifier.
        If the input is an Enum, it extracts the Enum's value; otherwise, it
        uses the input string directly.
        """
        nonlocal counter
        # Check if the input is an Enum, extract value; if not, use the string directly
        node_value = node_enum.value if isinstance(node_enum, Enum) else node_enum
        if node_value not in node_dict:
            node_dict[node_value] = counter
            counter += 1

    # Add nodes using enums
    logger.info("Adding nodes for Sankey Diagram")
    for node in Node:
        add_node(node)

    for category in TestCategory:
        add_node(category)

    # Add domain nodes dynamically
    for domain in domains_more_than_ten:
        add_node(domain)  # Ensure domain names are added to node_dict

    logger.info("Defining links between nodes")
    # Link from 'Original Data' to individual domains and grouped node
    sources.append(node_dict[Node.ORIGINAL_DATA.value])
    targets.append(node_dict[Node.DOMAINS_LESS_THAN_10.value])
    values.append(domains_less_than_ten_count)

    # Link original data to Duplicates
    domain_duplicates_count = df[df["duplicate_flag"]].shape[0]
    if domain_duplicates_count > 0:
        sources.append(node_dict[Node.ORIGINAL_DATA.value])
        targets.append(node_dict[Node.DUPLICATES.value])
        values.append(domain_duplicates_count)

    # Define connections and calculate sums
    for domain in domains_more_than_ten:
        sources.append(node_dict[Node.ORIGINAL_DATA.value])
        targets.append(node_dict[domain])
        values.append(domain_counts[domain])

        # Handle specific conditions and link to nodes
        for condition, target_node in [
            (
                df["incomplete_url_flag"] & ~df["duplicate_flag"],
                Node.INCOMPLETE_URLS.value,
            ),
            (
                (df["clone_status"] == "failed")
                & ~df["incomplete_url_flag"]
                & ~df["duplicate_flag"],
                Node.REPOS_NOT_CLONED.value,
            ),
            (
                (df["clone_status"] == "successful")
                & ~df["incomplete_url_flag"]
                & ~df["duplicate_flag"],
                Node.REPOS_CLONED.value,
            ),
        ]:
            count = df[(df["repodomain"] == domain) & condition].shape[0]
            if count > 0:
                sources.append(node_dict[domain])
                targets.append(node_dict[target_node])
                values.append(count)

    # Link 'Domains with < 10 Repos' to Incomplete URLs if applicable, excluding
    # duplicates
    less_than_ten_incomplete_urls_count = df[
        (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
        & df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
    ].shape[0]
    if less_than_ten_incomplete_urls_count > 0:
        sources.append(node_dict[Node.DOMAINS_LESS_THAN_10.value])
        targets.append(node_dict[Node.INCOMPLETE_URLS.value])
        values.append(less_than_ten_incomplete_urls_count)

    # Link 'Domains with < 10 Repos' to Repos Not Cloned if applicable, excluding
    # duplicates, Incomplete URLs, Base Repo URL Issues
    less_than_ten_repos_not_cloned_count = df[
        (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
        & ~df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
        & (df["clone_status"] == "failed")
    ].shape[0]
    if less_than_ten_repos_not_cloned_count > 0:
        sources.append(node_dict[Node.DOMAINS_LESS_THAN_10.value])
        targets.append(node_dict[Node.REPOS_NOT_CLONED.value])
        values.append(less_than_ten_repos_not_cloned_count)

    # Link 'Domains with < 10 Repos' to Repos Cloned if applicable, excluding
    # duplicates, Incomplete URLs, Base Repo URL Issues
    less_than_ten_repos_cloned_count = df[
        (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
        & ~df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
        & (df["clone_status"] == "successful")
    ].shape[0]
    if less_than_ten_repos_cloned_count > 0:
        sources.append(node_dict[Node.DOMAINS_LESS_THAN_10.value])
        targets.append(node_dict[Node.REPOS_CLONED.value])
        values.append(less_than_ten_repos_cloned_count)

    # Determine the primary test runner for each repository
    logger.info("Determine the primary test runner for each repository")
    df["primary_runner"] = df[
        ["JUnit_file_patterns", "pytest_file_patterns", "Mocha_file_patterns"]
    ].idxmax(axis=1)

    # Replace column names with runner names using enums
    df["primary_runner"] = df["primary_runner"].replace(
        {
            "JUnit_file_patterns": Node.JUNIT.value,
            "pytest_file_patterns": Node.PYTEST.value,
            "Mocha_file_patterns": Node.MOCHA.value,
        }
    )
    # Handling cases where all runners have zero files (if necessary)
    df.loc[
        df[["JUnit_file_patterns", "pytest_file_patterns", "Mocha_file_patterns"]].sum(
            axis=1
        )
        == 0,
        "primary_runner",
    ] = "No test runner detected"

    # For each runner, calculate the number of repositories that primarily use
    # it
    logger.info(
        "For each runner, calculate the number of repositories that "
        "primarily uses it."
    )

    for runner_enum in [Node.JUNIT, Node.PYTEST, Node.MOCHA]:
        runner_repo_count = df[
            (df["primary_runner"] == runner_enum.value)
            & (df["clone_status"] == "successful")
        ].shape[0]

        if runner_repo_count > 0:
            sources.append(node_dict[Node.REPOS_CLONED.value])
            targets.append(node_dict[runner_enum.value])
            values.append(runner_repo_count)

    no_runner_count = df[
        (df["primary_runner"] == Node.NO_TEST_RUNNER_DETECTED.value)  # Use enum value
        & (df["clone_status"] == "successful")
    ].shape[0]

    if no_runner_count > 0:
        sources.append(node_dict[Node.REPOS_CLONED.value])  # Use enum value
        targets.append(node_dict[Node.NO_TEST_RUNNER_DETECTED.value])  # Use enum value
        values.append(no_runner_count)

    # Calculate how many repositories primarily using each test runner fall
    # into each test file category.
    # (pass the count of repositories in each category.)
    logger.info("Pass the count of repositories in each category")
    for runner_enum in [
        Node.JUNIT,
        Node.PYTEST,
        Node.MOCHA,
        Node.NO_TEST_RUNNER_DETECTED,
    ]:
        for category_enum in TestCategory:
            # Calculate the number of repositories for each runner in each test file category
            category_count = df[
                (df["primary_runner"] == runner_enum.value)
                & (df["Test File Categories"] == category_enum.value)
                & (df["clone_status"] == "successful")
            ].shape[0]
            if category_count > 0:
                sources.append(node_dict[runner_enum.value])
                targets.append(node_dict[category_enum.value])
                values.append(category_count)

    return node_dict, sources, targets, values


args = parse_args()
input_file = args.input_file
clone_directory = args.clone_dir
output_file = args.output_file

# Setting up the working directory and logger
working_directory = get_working_directory_or_git_root()
logger.info(f"Working directory is: {working_directory}")

input_file_path = working_directory / input_file
logger.info(f"Input file path: {input_file_path}")
try:
    df = load_data(working_directory / input_file)
except FileNotFoundError:
    logger.error("Input file not found at: " + str(input_file_path))
    sys.exit(1)
except pd.errors.EmptyDataError:
    logger.error("Input file is empty at: " + str(input_file_path))
    sys.exit(1)
except Exception as e:
    logger.error(f"An error occurred while loading the data: {str(e)}")
    sys.exit(1)


logger.info(f"Repositories Clone Directory: {working_directory / clone_directory}")
beginning_clone_dir = str(working_directory / clone_directory) + "/"
logger.info(f"Beginning_clone_dir: {beginning_clone_dir}")

node_dict, sources, targets, values = prepare_sankey_data(df)

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
    title_text="Extended Project Analysis Sankey Diagram with Test Runners",
    font_size=12,
)

fig.show()
