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

from typing import Dict, Tuple, Optional, Any, Union, List
import argparse
import ast
import hashlib
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache
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
        logger.debug(f"Skipping non-python file {file_path}")
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


def get_parsed_arg(file_path):
    """
    Get AST tree and content from file, raising ValueError if parsing fails.
    """
    parsed_file = read_and_parse_file(file_path)
    if parsed_file is None:
        logger.error(f"Failed to parse file: {file_path}")
        raise ValueError(f"Could not parse file: {file_path}")
    return parsed_file


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

    # Dictionary to collect debug information
    debug_info = {
        "test_cases": [],
        "if_locations": [],
        "assertion_locations": [],
    }

    tree, _ = get_parsed_arg(file_path)

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
                debug_info["test_cases"].append(node.name)

                for body_node in node.body:  # Iterates over the body of the
                    # function
                    if isinstance(body_node, ast.If):
                        # Each 'if' branch increases complexity
                        result["complexity"] = (
                            result["complexity"] + 1 if result["complexity"] >= 0 else 1
                        )
                        debug_info["if_locations"].append(f"'if' in {node.name}")

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
                            debug_info["assertion_locations"].append(
                                f"assertion in {node.name}"
                            )

            if node.name == "setUp":
                result["has_setup"] = True
                logger.debug(f"Found setup method: {node.name}")

            if node.name == "tearDown":
                result["has_teardown"] = True
                logger.debug(f"Found teardown method: {node.name}")

    logger.debug(
        f"Analysis results for {file_path}:\n"
        f"Test cases found ({len(debug_info['test_cases'])}): {', '.join(debug_info['test_cases'])}\n"
        f"If statements found ({len(debug_info['if_locations'])}): {', '.join(debug_info['if_locations'])}\n"
        f"Assertions found ({len(debug_info['assertion_locations'])}): {', '.join(debug_info['assertion_locations'])}\n"
        f"Setup method: {'present' if result['has_setup'] else 'absent'}\n"
        f"Teardown method: {'present' if result['has_teardown'] else 'absent'}\n"
        f"Total complexity: {result['complexity']}"
    )

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
        "cyclomatic_complexity": -1,
        "lines_of_code": -1,
        "num_functions": -1,
    }

    # Dictionary to collect debug information
    debug_info = {"function_complexities": [], "file_stats": {}}

    tree, content = get_parsed_arg(file_path)

    # Initialise lines of code directly from content
    result["lines_of_code"] = len(content.splitlines())

    try:
        visitor = PathGraphingAstVisitor()
        visitor.preorder(tree, visitor)
    except Exception as e:
        logger.error(f"Failed to analyse complexity for {file_path}: {str(e)}")
        raise ValueError(f"Failed to analyse complexity: {str(e)}")

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

        result["num_functions"] = (
            result["num_functions"] + 1 if result["num_functions"] >= 0 else 1
        )

        complexity = graph.complexity()
        result["cyclomatic_complexity"] = (
            result["cyclomatic_complexity"] + complexity
            if result["cyclomatic_complexity"] >= 0
            else complexity
        )

        # Collect debug information
        debug_info["function_complexities"].append(
            f"{graph.name}: " f"complexity:{complexity}"
        )

        # Collect file statistics for debug info
        debug_info["file_stats"] = {
            "total_lines": result["lines_of_code"],
            "total_functions": result["num_functions"],
            "avg_complexity": (
                result["cyclomatic_complexity"] / result["num_functions"]
                if result["num_functions"] > 0
                else 0
            ),
        }

    return result


if __name__ == "__main__":
    args = parse_args()
    input_file = args.input
    output_file = args.output

    working_directory = get_working_directory_or_git_root()
    logger.info(f"Working directory: {working_directory}")

    df = pd.read_csv(input_file)
    df_language_python = df[df["guessed_language"] == "Python"]

    # Initialize or load the final DataFrame
    if Path(output_file).exists():
        final_df = pd.read_csv(output_file)
        logger.info(f"Loaded existing final DataFrame from {output_file}")
    else:
        final_df = pd.DataFrame()

    # Extract already processed file paths
    processed_files = (
        set(final_df["file_path"].unique()) if not final_df.empty else set()
    )
    logger.info(f"Found {len(processed_files)} already processed files.")

    # Get unprocessed files
    unprocessed_files = [
        Path(row["file_path"])
        for _, row in df_language_python.iterrows()
        if row["file_path"] not in processed_files
    ]

    if not unprocessed_files:
        logger.info("No new files to process.")
        exit(0)

    logger.info(f"Processing {len(unprocessed_files)} files in parallel...")

    # Create MetricsCollector instance
    collector = MetricsCollector()

    # Process files in parallel
    results = process_files_parallel(unprocessed_files)

    # Convert results to DataFrame
    if results:
        batch_df = pd.DataFrame(results)
        final_df = pd.concat([final_df, batch_df], ignore_index=True)

        # Remove duplicates and save
        final_df.drop_duplicates(subset=["file_path"], keep="last", inplace=True)
        final_df.to_csv(output_file, index=False)
        logger.info(f"Saved analysis results for {len(results)} files")

    logger.info(f"Final dataframe saved to {output_file}")

    @lru_cache(maxsize=1000)
    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Get hash of file contents for caching."""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _process_test_function(
        self, node: ast.FunctionDef, result: Dict[str, Any]
    ) -> None:
        """Process a test function node to extract metrics."""
        for body_node in ast.walk(node):
            if isinstance(body_node, ast.If):
                result["complexity"] += 1
            elif (
                isinstance(body_node, ast.Expr)
                and isinstance(body_node.value, ast.Call)
                and isinstance(body_node.value.func, ast.Name)
                and body_node.value.func.id == "assert"
            ):
                result["num_assertions"] += 1

    def analyse_test_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyses a Python test file to extract metrics.

        Args:
            file_path: Path to the Python test file

        Returns:
            Dictionary containing extracted metrics
        """
        logger.info(f"Starting analysis of test file: {file_path}")

        # Check cache first
        file_hash = self._get_file_hash(file_path)
        if file_hash in self._metrics_cache:
            return self._metrics_cache[file_hash]

        result = {
            "num_test_cases": 0,
            "num_assertions": 0,
            "has_setup": False,
            "has_teardown": False,
            "complexity": 0,
        }

        parsed = read_and_parse_file(file_path)
        if not parsed:
            return result

        tree, _ = parsed

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    result["num_test_cases"] += 1
                    result["complexity"] += 1
                    self._process_test_function(node, result)
                elif node.name in ("setUp", "tearDown"):
                    result[f"has_{node.name.lower()}"] = True

        # Cache the result
        self._metrics_cache[file_hash] = result
        return result

    def analyse_code_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Analyses a Python code file to extract metrics.

        Args:
            file_path: Path to the Python code file

        Returns:
            Dictionary containing extracted metrics
        """
        logger.info(f"Starting analysis of code file: {file_path}")

        # Check cache first
        file_hash = self._get_file_hash(file_path)
        if file_hash in self._metrics_cache:
            return self._metrics_cache[file_hash]

        result = {
            "cyclomatic_complexity": 0,
            "lines_of_code": 0,
            "num_functions": 0,
        }

        parsed = read_and_parse_file(file_path)
        if not parsed:
            return result

        tree, content = parsed

        # Calculate lines of code
        result["lines_of_code"] = len(content.splitlines())

        try:
            visitor = PathGraphingAstVisitor()
            visitor.preorder(tree, visitor)

            for graph in visitor.graphs.values():
                result["num_functions"] += 1
                result["cyclomatic_complexity"] += graph.complexity()

        except Exception as e:
            logger.error(f"Failed to analyse complexity for {file_path}: {str(e)}")

        # Cache the result
        self._metrics_cache[file_hash] = result
        return result


def process_files_parallel(
    file_paths: List[Path], num_workers: int = 4
) -> List[Dict[str, Any]]:
    """
    Process multiple files in parallel using a process pool.

    Args:
        file_paths: List of paths to process
        num_workers: Number of parallel workers

    Returns:
        List of results dictionaries
    """
    collector = MetricsCollector()
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_path = {
            executor.submit(collector.analyse_test_file, path): path
            for path in file_paths
        }

        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                result = future.result()
                results.append({"file_path": str(path), **result})
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")
                results.append({"file_path": str(path), "error": str(e)})

    return results
