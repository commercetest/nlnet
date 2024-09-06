"""
This script analyses Python test files within cloned repositories to extract
relevant metrics and perform various analyses. The script processes both test
files and general Python code files, extracting metrics such as:

- Number of test cases (functions starting with 'test_')
- Number of assertions (using 'assert' statements)
- Presence of setup and teardown methods (e.g., setUp, tearDown)
- Complexity of the test file (measured by counting functions and branches)
- Cyclomatic complexity of the code
- Lines of code (LOC)
- Number of functions

The script saves the results of these analyses to a specified CSV file,
updating the file in batches as multiple files are processed.

### Usage:
To run the script, specify the input and output CSV file paths using the
command-line arguments `--input` and `--output`. By default, the script
assumes input and output files are located in the 'data' directory of the
repository's root.

Example:
    python script_name.py --input path/to/input.csv --output path/to/output.csv

"""

import argparse
import ast
import pandas as pd
from mccabe import PathGraphingAstVisitor
from loguru import logger
from pathlib import Path

from utils.git_utils import get_working_directory_or_git_root

BATCH_SIZE = 100  # Number of files to process before saving to disk

# Configure logger
logger.add("metrics_extraction_log", rotation="500 MB", level="INFO")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyse Python test files and extract metrics."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=Path(
            get_working_directory_or_git_root() / "data" / "guessed_languages_rows.csv"
        ),
        help="Path to the input CSV file.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=Path(
            get_working_directory_or_git_root()
            / "data"
            / "test_metrics_df_guesslang.csv"
        ),
        help="Path to the output CSV file.",
    )

    return parser.parse_args()


def read_and_parse_file(file_path):
    """
    Reads and parses a Python file into an AST.

    Args:
        file_path (str): The path to the Python file.

    Returns:
        tuple: A tuple containing the AST tree and the file content, or
        None if there's an error.
    """
    logger.debug(f"Attempting to read and parse: {file_path}")
    if not file_path.endswith(".py"):
        logger.info(f"Skipping non-python file {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            tree = ast.parse(content, filename=file_path)
            logger.debug(f"Successfully parsed file: {file_path}")
            return tree, content
    except SyntaxError as e:
        logger.error(f"Syntax error in file {file_path}: {e}")
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error in file {file_path}: {e}")
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {e}")

    return None


def analyse_test_file(file_path):
    """
    Analyses a Python test file to extract the number of test cases,
    assertions, presence of setup and teardown methods, and the complexity
    of the test file.

    Args:
        file_path (str): The path to the test file.

    Returns:
           dict: A dictionary containing the analysis results.
    """
    logger.info(f"Starting analysis of test file: {file_path}")

    result = {
        "num_test_cases": 0,
        "num_assertions": 0,
        "has_setup": False,
        "has_teardown": False,
        "complexity": 0,
    }

    parsed_file = read_and_parse_file(file_path)
    if parsed_file is None:
        logger.warning(f"Analysis skipped for file: {file_path}")
        return result

    tree, _ = parsed_file

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
                logger.debug(f"Found test case: {node.name}")

                for body_node in node.body:  # Iterates over the body of the
                    # function
                    if isinstance(body_node, ast.If):
                        complexity += 1  # Each 'if' branch increases complexity
                        logger.debug(f"Incrementing complexity for 'if' in {node.name}")

                    if isinstance(body_node, ast.Expr) and isinstance(
                        body_node.value, ast.Call
                    ):  #  Checks if the node is an expression and a function
                        # call.
                        if (
                            isinstance(body_node.value.func, ast.Name)
                            and body_node.value.func.id == "assert"
                        ):  # Checks if the function call is an assertion.
                            num_assertions += 1
                            logger.debug(f"Found assertion in {node.name}")

            if node.name in ("setUp", "tearDown"):
                has_setup = has_setup or node.name == "setUp"
                has_teardown = has_teardown or node.name == "tearDown"
                logger.debug(f"Found setup/teardown method: {node.name}")

    result.update(
        {
            "num_test_cases": num_test_cases,
            "num_assertions": num_assertions,
            "has_setup": has_setup,
            "has_teardown": has_teardown,
            "complexity": complexity,
        }
    )

    return result


def analyse_code_file(file_path, max_complexity=10):
    """
    Analyses a Python code file to extract code metrics such as cyclomatic
    complexity, lines of code, and the number of functions.

    Args:
        file_path (str): The path to the code file.
        max_complexity (int): The maximum allowed complexity for a function.

    Returns:
        dict: A dictionary containing the code metrics.
    """

    logger.info(f"Starting analysis of code file: {file_path}")

    result = {
        "cyclomatic_complexity": 0,
        "lines_of_code": 0,
        "num_functions": 0,
    }

    parsed_file = read_and_parse_file(file_path)
    if parsed_file is None:
        logger.warning(f"Analysis skipped for file: {file_path}")
        return result

    tree, content = parsed_file

    num_functions = 0
    lines_of_code = len(content.splitlines())
    cyclomatic_complexity = 0

    visitor = PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)

    for graph in visitor.graphs.values():
        num_functions += 1
        complexity = graph.complexity()
        cyclomatic_complexity += complexity
        logger.debug(f"Function {graph.name} has complexity {complexity}")

    result.update(
        {
            "cyclomatic_complexity": cyclomatic_complexity,
            "lines_of_code": lines_of_code,
            "num_functions": num_functions,
        }
    )

    return result


if __name__ == "__main__":
    args = parse_args()
    input_file = args.input
    output_file = args.output

    working_directory = get_working_directory_or_git_root()
    logger.info(f"Working directory: {working_directory}")

    df = pd.read_csv(input_file)
    df_language_python = df[df["guessed_language"] == "Python"]

    final_df_path = output_file
    logger.info("Apply the analysis to each test file")

    # Initialise or load the final Dataframe
    if Path(final_df_path).exists():
        final_df = pd.read_csv(final_df_path)
        logger.info(f"Loaded existing final Dataframe from {final_df_path}")

    else:
        final_df = pd.DataFrame()

    batch_results = []

    for idx, row in df_language_python.iterrows():
        file_path = row["file_path"]
        test_file_analysis = analyse_test_file(file_path)
        code_file_analysis = analyse_code_file(file_path)

        # Combine the analysis results with the original data
        analysis_result = {
            "file_path": file_path,
            **test_file_analysis,  # This unpacks the dictionary test_file_
            # analysis and includes all its key-value pairs in the analysis_
            # result dictionary.
            **code_file_analysis,
        }

        batch_results.append(analysis_result)

        # Save the batch results every BATCH_SIZE files
        if len(batch_results) >= BATCH_SIZE:
            batch_df = pd.DataFrame(batch_results)
            final_df = pd.concat([final_df, batch_df], ignore_index=True)
            final_df.to_csv(final_df_path, index=False)
            logger.info(f"Saved analysis results for {len(batch_results)} files")
            batch_results.clear()  # Clear the batch results after saving

    # Save any remaining results after the loop
    if batch_results:
        batch_df = pd.DataFrame(batch_results)
        final_df = pd.concat([final_df, batch_df], ignore_index=True)
        final_df.to_csv(final_df_path, index=False)
        logger.info(
            f"Saved final batch of analysis results for " f"{len(batch_results)} files"
        )

    logger.info(f"Final dataframe saved to {final_df_path}")
