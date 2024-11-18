"""
This script analyses Python test files within cloned repositories to extract
relevant metrics and perform various analyses. The script processes both test
files and general Python code files, extracting metrics such as:

- Number of test cases (functions starting with 'test_')
- Number of assertions (using 'assert' statements)
- Presence of setup and teardown methods (e.g., setUp, tearDown)
- Complexity of the test file (measured by counting functions and branches)
- Cyclomatic complexity of the code : sum of all functions' complexities where
cyclomatic complexity of that function, is a measure of how many independent
paths or 'decision points' exist in the function. Cyclomatic complexity
generally increases with the number of branches, loops, and conditional
statements in the function.
- Lines of code (LOC) : Counts lines by splitting the file content into lines.
- Number of functions : Counts each function encountered.

The script saves the results of these analyses to a specified CSV file,
updating the file in batches as multiple files are processed.

Notes about the input and output files of this script:
- Input file : This is the output of the Supabase database after running the
script `guesslang_to_db.py`. This dataframe contains the repository `file_
path` and 'guessed_language' amongst other columns like `hosting_provider` and
`repo_name`.
- output file: is a dataframe which contains information about testing
techniques and code complexity. Some columns are `num_assertions`,
`cyclomatic_complexity`, and `lines_of_code`.

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
logger.add("metrics_extraction.log", rotation="500 MB", level="INFO")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyse Python test files and general Python code files "
        "and extract metrics."
    )

    parser.add_argument(
        "--input",
        type=str,
        default=Path(
            get_working_directory_or_git_root() / "data" / "guessed_languages_rows.csv"
        ),
        help="Path to the input CSV file exported from Supabase with "
        "file_path, guessed_language, and more.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=Path(
            get_working_directory_or_git_root()
            / "data"
            / "test_metrics_df_guesslang.csv"
        ),
        help="Path to the output CSV file with data on testing techniques and "
        "code complexity.",
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
        "num_test_cases": -1,
        "num_assertions": -1,
        "has_setup": False,
        "has_teardown": False,
        "complexity": -1,
    }

    parsed_file = read_and_parse_file(file_path)
    if parsed_file is None:
        logger.warning(f"Analysis skipped for file: {file_path}")
        return result

    tree, _ = parsed_file

    # Initialise counters to 1 on first find (since they start at -1)
    for node in ast.walk(tree):  # Walks through all nodes in the AST
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("test_"):
                # For first test case, set to 1; for subsequent ones, increment
                result["num_test_cases"] = (
                    result["num_test_cases"] + 1 if result["num_test_cases"] >= 0 else 1
                )
                # Basic complexity, 1 per function
                result["complexity"] = (
                    result["complexity"] + 1 if result["complexity"] >= 0 else 1
                )
                logger.debug(f"Found test case: {node.name}")

                for body_node in node.body:  # Iterates over the body of the
                    # function
                    if isinstance(body_node, ast.If):
                        # Each 'if' branch increases complexity
                        result["complexity"] = (
                            result["complexity"] + 1 if result["complexity"] >= 0 else 1
                        )
                        logger.debug(
                            f"Incrementing complexity for 'if' in" f" {node.name}"
                        )

                    if isinstance(body_node, ast.Expr) and isinstance(
                        body_node.value, ast.Call
                    ):  # Checks if the node is an expression and a function
                        # call.
                        if (
                            isinstance(body_node.value.func, ast.Name)
                            and body_node.value.func.id == "assert"
                        ):  # Checks if the function call is an assertion.
                            result["num_assertions"] = (
                                result["num_assertions"] + 1
                                if result["num_assertions"] >= 0
                                else 1
                            )
                            logger.debug(f"Found assertion in {node.name}")

            if node.name == "setUp":
                result["has_setup"] = True
                logger.debug(f"Found setup method: {node.name}")

            if node.name == "tearDown":
                result["has_teardown"] = True
                logger.debug(f"Found teardown method: {node.name}")

    return result


def analyse_code_file(file_path):
    """
    Analyses a Python code file to extract code metrics such as cyclomatic
    complexity, lines of code, and the number of functions.

    Args:
        file_path (str): The path to the code file.

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
        # Each graph in `visitor.graphs.values()` represents the control flow
        # graph (CFG) of a single function, which is used to compute its
        # cyclomatic complexity.
        # `PathGraphingAstVisitor' processes the Abstract Syntax Tree (AST)
        # of the code and generates a control flow graph for each function it
        # encounters, storing these graphs in 'visitor.graphs'. Each entry in
        # 'visitor.graphs' corresponds to one function, so iterating over it
        # and counting with 'num_functions += 1' accurately captures the
        # function count.

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

    # Initialise or load the final Dataframe
    if Path(output_file).exists():
        final_df = pd.read_csv(output_file)
        logger.info(f"Loaded existing final Dataframe from {output_file}")

    else:
        final_df = pd.DataFrame()

    # Extract already processed file paths
    processed_files = (
        set(final_df["file_path"].unique()) if not final_df.empty else set()
    )
    logger.info(f"Found {len(processed_files)} already processed files.")

    batch_results = []

    for idx, row in df_language_python.iterrows():
        file_path = row["file_path"]

        # Skip files already processed
        if file_path in processed_files:
            logger.debug(f"Skipping already processed file: {file_path}")
            continue

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
            final_df.to_csv(output_file, index=False)
            logger.info(f"Saved analysis results for {len(batch_results)} files")

            # Clear the batch results after saving
            batch_results.clear()

    # Save any remaining results after the loop
    if batch_results:
        batch_df = pd.DataFrame(batch_results)
        final_df = pd.concat([final_df, batch_df], ignore_index=True)

        # Remove duplicates before saving
        final_df.to_csv(output_file, index=False)
        logger.info(
            f"Saved final batch of analysis results for {len(batch_results)}" f"files"
        )

    logger.info(f"Final dataframe saved to {output_file}")
