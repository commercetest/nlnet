import pandas as pd
from pathlib import Path
import os
from loguru import logger
from tqdm import tqdm
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound
from utils.git_utils import get_working_directory_or_git_root

logger.add("language_detector_log", rotation="500 MB")

PROGRAMMING_EXTENSIONS = {
    ".py": "Python",
    ".pyc": "Compiled Python",
    ".pyo": "Compiled Python",
    ".pyd": "Compiled Python",
    ".java": "Java",
    ".class": "Compiled Java",
    ".jar": "Java Archive",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".js": "JavaScript",
    ".spec.js": "JavaScript",
    ".test.js": "JavaScript",
    ".ts": "TypeScript",
    ".spec.ts": "TypeScript",
    ".test.ts": "TypeScript",
    ".rb": "Ruby",
    ".spec.rb": "Ruby",
    ".test.rb": "Ruby",
    ".php": "PHP",
    ".go": "Go",
    ".rs": "Rust",
    ".swift": "Swift",
    ".m": "Objective-C",
    ".h": "C/C++ Header",
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".zsh": "Shell Script",
    ".ksh": "Shell Script",
    ".scss": "Sass",
    ".json": "JSON",
    ".xml": "XML",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".md": "Markdown",
    ".hs": "Haskell",
    ".ocaml": "OCaml",
    ".pl": "Perl",
    ".groovy": "Groovy",
    ".cf": "ColdFusion",
    ".cfm": "ColdFusion",
    ".tf": "Terraform",
    ".side": "Selenium",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".clj": "Clojure",
    ".cljs": "ClojureScript",
    ".cljc": "Clojure",
    ".lua": "Lua",
    ".r": "R",
    ".jl": "Julia",
    ".f90": "Fortran",
    ".f95": "Fortran",
    ".f03": "Fortran",
    ".f08": "Fortran",
    ".vhdl": "VHDL",
    ".vhd": "VHDL",
    ".v": "Verilog",
    ".vh": "Verilog",
    ".adb": "Ada",
    ".ads": "Ada",
    ".toml": "TOML",
    "Dockerfile": "Dockerfile",
    "Makefile": "Makefile",
    ".ini": "INI",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".log": "Log",
    ".github/workflows/*.yml": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
}

# List of problematic files
PROBLEMATIC_FILES = [
    "/Users/tannazmnjm/PycharmProjects/nlnet/data/cloned_repos/"
    "github_com/wikirate/mod/wikirate/data/fixtures/test/"
    "card_actions.yml",
    "/Users/tannazmnjm/PycharmProjects/nlnet/data/cloned_repos/"
    "github_com/wikirate/mod/wikirate/data/fixtures/test/card_acts.yml",
    "/Users/tannazmnjm/PycharmProjects/nlnet/data/cloned_repos/"
    "git_irde_st/irdest/utils/eris-rs/res/eris-test-vectors/"
    "eris-test-vector-12.json",
    "/Users/tannazmnjm/PycharmProjects/nlnet/data/cloned_repos/"
    "git_irde_st/irdest/utils/eris-rs/res/eris-test-vectors/"
    "eris-test-vector-11.json",
]


def detect_language(file_path):
    """
    Detects the programming language of a given file.
    Args:
        file_path (str): The path to the file.
    Returns:
        str: The name of the detected programming language.
    """

    logger.debug(f"Analysing file: {file_path}")

    # Skip the specific problematic file
    if file_path in PROBLEMATIC_FILES:
        logger.info(f"Skipping problematic file: {file_path}")
        return "Unknown"

    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File '{file_path}' not found.")
        return "Unknown"

    # Check if file extension is in the list of programming-related extensions
    _, extension = os.path.splitext(file_path)
    if extension not in PROGRAMMING_EXTENSIONS:
        logger.debug(f"Skipping non-programming file: {file_path}")
        return "Unknown"

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        try:
            lexer = guess_lexer(content)
            language = lexer.name
            logger.debug(f"Detected language from content: {language}")
            return language
        except ClassNotFound:
            logger.debug(
                f"Failed to detect language from content for "
                f"{file_path}. Fall back to using the file extension "
                f"to guess the language"
            )
            language = PROGRAMMING_EXTENSIONS.get(extension, "Unknown")
            logger.debug(f"Detected language from file extension: {language}")
            return language

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return "Unknown"


def extract_languages(cloned_repos_base_path, df_path):
    """
    Extracts the programming languages used in each repository and updates the
     DataFrame.
    Args:
        cloned_repos_base_path (str): The base path to the cloned repositories.
        df_path (str): Path to save the DataFrame periodically.
    Returns:
        DataFrame: The updated DataFrame with language information.
    """
    df = pd.DataFrame(columns=["file_path", "detected_language"])
    org_paths = list(Path(cloned_repos_base_path).glob("*"))
    logger.info(f"Found {len(org_paths)} organizations")

    file_count = 0  # Counter to limit the number of files processed

    for org_path in tqdm(org_paths, desc="Analyzing organizations", unit="org"):
        if org_path.is_dir():
            repo_paths = list(org_path.glob("*"))
            logger.info(f"Found {len(repo_paths)} repositories in {org_path.name}")

            for repo_path in tqdm(
                repo_paths,
                desc=f"Analyzing repositories in {org_path.name}",
                unit="repo",
                leave=False,
            ):
                if repo_path.is_dir():
                    repo_name = repo_path.name
                    logger.info(f"Processing repository: {repo_name}")

                    file_paths = list(repo_path.rglob("*"))
                    logger.info(f"Found {len(file_paths)} files in {repo_name}")

                    for file_path in tqdm(
                        file_paths,
                        desc=f"Analyzing files in {repo_path.name}",
                        unit="file",
                        leave=False,
                    ):
                        if file_path.is_file():
                            language = detect_language(str(file_path))
                            new_row = pd.DataFrame(
                                [
                                    {
                                        "file_path": str(file_path),
                                        "detected_language": language,
                                    }
                                ]
                            )
                            df = pd.concat([df, new_row], ignore_index=True)

                            file_count += 1
                            if file_count >= 100500:  # Stop after processing 10
                                # files
                                logger.info(
                                    "Processed 2500 files. Stopping early for "
                                    "testing."
                                )
                                df.to_csv(df_path, index=False)
                                return df

                    # Save the DataFrame periodically
                    df.to_csv(df_path, index=False)
                    logger.info(f"DataFrame saved at {df_path}")

    return df


if __name__ == "__main__":
    # Path to the log file
    working_directory = get_working_directory_or_git_root()
    logger.info(f"Working Directory: {working_directory}")

    input_file_path = working_directory / Path("data/merged_df.csv")
    logger.info(f"Input file path: {input_file_path}")

    df_path = working_directory / "data/merged_df_with_languages.csv"

    if os.path.exists(working_directory / "data/merged_df_with_languages.csv"):
        logger.info("Resuming from previously saved progress.")
        df = pd.read_csv(df_path)
    else:
        df = pd.DataFrame(columns=["file_path", "detected_language"])

    # Base path to the cloned repositories
    cloned_repos_base_path = working_directory / "data/cloned_repos"

    # Extract languages from the cloned repositories
    logger.info("Extracting languages from cloned repositories")
    df = extract_languages(cloned_repos_base_path, df_path)

    # Save the updated DataFrame
    df.to_csv(df_path, index=False)

    logger.info(f"Saved the DataFrame with languages to {df_path}")
