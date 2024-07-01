"""
This script analyses Python test files within cloned repositories.
It converts a list of test files into a DataFrame, merges it with
a DataFrame containing Python file information, and performs
analysis on the test files to extract relevant metrics.
"""

import pandas as pd
from utils.git_utils import get_working_directory_or_git_root
from loguru import logger
import ast


def convert_test_file_list_to_df(file_path):
    """
    Converts a text file containing repository URLs and file paths into a DataFrame.

    Args:
        file_path (str): The path to the text file.

    Returns:
        pd.DataFrame: A DataFrame with columns 'repo_url' and 'file_path'.
    """
    data = []
    current_repo = None
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("Repository URL:"):
                current_repo = line.split(": ")[1]
            elif current_repo:
                data.append((current_repo, line))
    return pd.DataFrame(data, columns=["repo_url", "file_path"])


def extract_repo_name(url):
    """
    Extracts the repository name from a URL.

    Args:
        url (str): The repository URL.

    Returns:
        str: The repository name.
    """
    return url.split("/")[-1]


def analyse_test_file(file_path):
    """
    Analyses a Python test file to extract the number of test cases,
    assertions, presence of setup and teardown methods, and the complexity
    of the test file. This function reads the file content and parses it
    into an Abstract Syntax Tree (AST) using the ast module. The AST
    represents the structure of the code in a tree format.

    Args:
        file_path (str): The path to the test file.

    Returns:
        dict: A dictionary containing the analysis results.
    """

    if not file_path.endswith(".py"):
        logger.info(f"Skipping non-Python file {file_path}")
        return {
            "num_test_cases": 0,
            "num_assertions": 0,
            "has_setup": False,
            "has_teardown": False,
            "complexity": 0,
        }

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
        logger.info(f"Error processing the file {file_path}: {e}")
        return {
            "num_test_cases": 0,
            "num_assertions": 0,
            "has_setup": False,
            "has_teardown": False,
            "complexity": 0,
        }

    num_test_cases = 0
    num_assertions = 0
    has_setup = False
    has_teardown = False
    complexity = 0

    for node in ast.walk(tree):  # Walks through all nodes in the AST
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("test_"):
                num_test_cases += 1
                complexity += 1  # Basic complexity, 1 per function

                for body_node in node.body:  # Iterates over the body of the
                    # function
                    if isinstance(body_node, ast.If):
                        complexity += 1  # Each 'if' branch increases complexity

                    if isinstance(body_node, ast.Expr) and isinstance(
                        body_node.value, ast.Call
                    ):  #  Checks if the node
                        # is an expression and a function call.
                        if (
                            isinstance(body_node.value.func, ast.Name)
                            and body_node.value.func.id == "assert"
                        ):  # Checks
                            # if the function call is an assertion.
                            num_assertions += 1

            if node.name in ("setUp", "tearDown"):
                has_setup = has_setup or node.name == "setUp"
                has_teardown = has_teardown or node.name == "tearDown"

    return {
        "num_test_cases": num_test_cases,
        "num_assertions": num_assertions,
        "has_setup": has_setup,
        "has_teardown": has_teardown,
        "complexity": complexity,
    }


if __name__ == "__main__":
    working_directory = get_working_directory_or_git_root()
    logger.info(f"Working directory: {working_directory}")

    clone_directory = working_directory / "data" / "clone_repos"
    logger.info(f"Clone directory : {clone_directory}")

    df = pd.read_csv(
        working_directory / "data" / "for_test_merged_df_with_languages.csv"
    )
    df_language_python = df[df["detected_language"] == "Python"]

    logger.info("Converting the test_files_list.txt into a dataframe")
    test_file_list_df = convert_test_file_list_to_df(
        str(working_directory / "data" / "test_files_list.txt")
    )

    # Deduplicate test_file_list_df based on file_path
    test_file_list_df = test_file_list_df.drop_duplicates(subset=["file_path"])

    logger.info('Merging "df_language_python" and "test_file_list_df"')
    merged_df = pd.merge(
        df_language_python, test_file_list_df, on="file_path", how="inner"
    )

    logger.info("Apply the analysis to each test file")
    merged_df["analysis"] = merged_df["file_path"].apply(analyse_test_file)

    # Expand the analysis into separate columns
    analysis_df = merged_df["analysis"].apply(pd.Series)

    # Concatenate the analysis results with the original DataFrame
    final_df = pd.concat([merged_df, analysis_df], axis=1)

    # Drop the original 'analysis' column as it's now expanded
    final_df.drop(columns=["analysis"], inplace=True)
