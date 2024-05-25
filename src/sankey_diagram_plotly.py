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

import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root


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
        default=str(Path("data/ready_for_sankey.csv ")),
        help="Path to the output CSV file.",
    )

    return parser.parse_args()


def prepare_sankey_data(df):
    """
    Processes a DataFrame containing repository data to prepare the source,
    target, and value lists for generating a Sankey diagram. The function
    categorises repositories based on the number of test files and aggregates
    data on test runner usage.
    """
    # Test file counts categorised
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
        "More than 1000 test files": (1000, float("inf")),
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

    # Calculate sums for each test runner's file patterns
    logger.info("Calculate sums for each test runner's file patterns")
    df["JUnit_total"] = df["JUnit_file_patterns"]
    df["pytest_total"] = df["pytest_file_patterns"]
    df["Mocha_total"] = df["Mocha_file_patterns"]

    # Calculate 'No test runner detected'
    df["No_test_runner_detected"] = (
        (df["JUnit_total"] == 0) & (df["pytest_total"] == 0) & (df["Mocha_total"] == 0)
    ).astype(int)

    # Sum up counts for the new Sankey layer
    test_runner_sums = {
        "JUnit": df["JUnit_total"].sum(),
        "pytest": df["pytest_total"].sum(),
        "Mocha": df["Mocha_total"].sum(),
        "No test runner detected": df["No_test_runner_detected"].sum(),
    }

    def add_node(node_name):
        nonlocal counter
        if node_name not in node_dict:
            node_dict[node_name] = counter
            counter += 1

    # Add nodes
    logger.info("Adding nodes for Sankey Diagram")
    add_node("Original Data")
    for domain in domains_more_than_ten:
        add_node(domain)
    add_node("Domains with < 10 Repos")
    add_node("Duplicates")
    add_node("Incomplete URLs")
    add_node("Repos not Cloned")
    add_node("Repos Cloned")

    for category in test_file_categories.keys():
        add_node(category)

    # Add nodes for the test runners
    for runner in test_runner_sums.keys():
        add_node(runner)

    logger.info("Defining links between nodes")
    # Link from 'Original Data' to individual domains and grouped node
    sources.append(node_dict["Original Data"])
    targets.append(node_dict["Domains with < 10 Repos"])
    values.append(domains_less_than_ten_count)

    # Link original data to Duplicates
    domain_duplicates_count = df[df["duplicate_flag"]].shape[0]
    if domain_duplicates_count > 0:
        sources.append(node_dict["Original Data"])
        targets.append(node_dict["Duplicates"])
        values.append(domain_duplicates_count)

    for domain in domains_more_than_ten:
        sources.append(node_dict["Original Data"])
        targets.append(node_dict[domain])
        values.append(domain_counts[domain])

        # Link domain to Incomplete URLs if applicable, excluding duplicates
        domain_incomplete_urls_count = df[
            (df["repodomain"] == domain)
            & df["incomplete_url_flag"]
            & ~df["duplicate_flag"]
        ].shape[0]
        if domain_incomplete_urls_count > 0:
            sources.append(node_dict[domain])
            targets.append(node_dict["Incomplete URLs"])
            values.append(domain_incomplete_urls_count)

        # Link domain to Repos not Cloned if applicable
        domain_repos_not_cloned_count = df[
            ~df["incomplete_url_flag"]
            & ~df["duplicate_flag"]
            & (df["clone_status"] == "failed")
            & (df["repodomain"] == domain)
        ].shape[0]
        if domain_repos_not_cloned_count > 0:
            sources.append(node_dict[domain])
            targets.append(node_dict["Repos not Cloned"])
            values.append(domain_repos_not_cloned_count)

        # Link domain to Repos Cloned if applicable, excluding duplicates,
        # Incomplete URLs, Base Repo URL Issues
        domain_repos_cloned_count = df[
            ~df["incomplete_url_flag"]
            & ~df["duplicate_flag"]
            & (df["clone_status"] == "successful")
            & (df["repodomain"] == domain)
        ].shape[0]

        if domain_repos_cloned_count > 0:
            sources.append(node_dict[domain])
            targets.append(node_dict["Repos Cloned"])
            values.append(domain_repos_cloned_count)

    # Link 'Domains with < 10 Repos' to Incomplete URLs if applicable, excluding
    # duplicates
    less_than_ten_incomplete_urls_count = df[
        (df["repodomain"].isin(domain_counts[domain_counts <= 10].index))
        & df["incomplete_url_flag"]
        & ~df["duplicate_flag"]
    ].shape[0]
    if less_than_ten_incomplete_urls_count > 0:
        sources.append(node_dict["Domains with < 10 Repos"])
        targets.append(node_dict["Incomplete URLs"])
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
        sources.append(node_dict["Domains with < 10 Repos"])
        targets.append(node_dict["Repos not Cloned"])
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
        sources.append(node_dict["Domains with < 10 Repos"])
        targets.append(node_dict["Repos Cloned"])
        values.append(less_than_ten_repos_cloned_count)

    # Determine the primary test runner for each repository
    logger.info("Determine the primary test runner for each repository")
    df["primary_runner"] = df[
        ["JUnit_file_patterns", "pytest_file_patterns", "Mocha_file_patterns"]
    ].idxmax(axis=1)

    # Replace column names with runner names
    df["primary_runner"] = df["primary_runner"].replace(
        {
            "JUnit_file_patterns": "JUnit",
            "pytest_file_patterns": "pytest",
            "Mocha_file_patterns": "Mocha",
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

    # For each runner, calculate the number of repositories that primarily use it
    logger.info(
        "For each runner, calculate the number of repositories that " "primarily use it"
    )
    for runner in ["JUnit", "pytest", "Mocha"]:
        runner_repo_count = df[
            (df["primary_runner"] == runner) & (df["clone_status"] == "successful")
        ].shape[0]
        if runner_repo_count > 0:
            sources.append(node_dict["Repos Cloned"])
            targets.append(node_dict[runner])
            values.append(runner_repo_count)

    no_runner_count = df[
        (df["primary_runner"] == "No test runner detected")
        & (df["clone_status"] == "successful")
    ].shape[0]
    if no_runner_count > 0:
        sources.append(node_dict["Repos Cloned"])
        targets.append(node_dict["No test runner detected"])
        values.append(no_runner_count)

    # Calculate how many repositories primarily using each test runner fall
    # into each test file category.
    # (pass the count of repositories in each category.)
    logger.info("Pass the count of repositories in each category")
    for runner in ["JUnit", "pytest", "Mocha", "No test runner detected"]:
        for category in test_file_categories.keys():
            # Calculate the number of repositories for each runner in each test file category
            category_count = df[
                (df["primary_runner"] == runner)
                & (df["Test File Categories"] == category)
                & (df["clone_status"] == "successful")
            ].shape[0]
            if category_count > 0:
                sources.append(node_dict[runner])
                targets.append(node_dict[category])
                values.append(category_count)

    return node_dict, sources, targets, values


args = parse_args()
input_file = args.input_file
clone_directory = args.clone_dir
output_file = args.output_file

# Setting up the working directory and logger
working_directory = get_working_directory_or_git_root()
logger.info(f"Working directory is: {working_directory}")

logger.info(f"Input file path : {working_directory / input_file}")
df = pd.read_csv(working_directory / input_file)

logger.info(f"Repositories Clone Directory : {working_directory / clone_directory}")
beginning_clone_dir = str(working_directory / clone_directory) + "/"
logger.info(f"Beginning_clone_dir : {beginning_clone_dir}")

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
    title_text="Extended Project Analysis Sankey Diagram with " "Test Runners",
    font_size=12,
)

fig.show()
