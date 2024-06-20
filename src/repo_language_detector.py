import pandas as pd
from pathlib import Path
import os
import json
from loguru import logger
from tqdm import tqdm
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound
from utils.git_utils import get_working_directory_or_git_root

logger.add("script.log", rotation="500 MB")

PROGRAMMING_EXTENSIONS = {
    ".py",
    ".java",
    ".c",
    ".cpp",
    ".cs",
    ".js",
    ".ts",
    ".rb",
    ".php",
    ".go",
    ".rs",
    ".swift",
    ".m",
    ".h",
    ".sh",
    ".scss",
    ".json",
    ".xml",
    ".yml",
    ".yaml",
    ".md",
}


def detect_language(file_path):
    """
    Detects the programming language of a given file.
    Args:
        file_path (str): The path to the file.
    Returns:
        str: The name of the detected programming language.
    """
    logger.debug(f"Analysing file: {file_path}")
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' not found.")

            # Check if file extension is in the list of programming-related
            # extensions
        extension = os.path.splitext(file_path)[1]
        if extension not in PROGRAMMING_EXTENSIONS:
            logger.debug(f"Skipping non-programming file: {file_path}")
            return "Unknown"

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        try:
            # Attempt to identify the programming language of a string of
            # code or text. It returns a lexer object that it determines to be
            # the best fit based on lexical patterns and keywords present in
            # the content.
            lexer = guess_lexer(content)
            language = lexer.name
            logger.debug(f"Detected language from content: {language}")
            return language
        except ClassNotFound:
            logger.debug(f"Failed to detect language from content for {file_path}.")
            # Fall back to using the file extension to guess the language
            try:
                # The primary purpose is to identify the appropriate lexer for
                # a given file based on its filename extension. It returns a
                # lexer object that matches the file extension (for instance
                # PythonLexer). If no appropriate lexer is found, it typically
                # falls back to a generic lexer suitable for plain text or
                # returns TextLexer.

                # lexer = get_lexer_for_filename(file_path)
                # language = lexer.name
                # logger.debug(f"Detected language from file extension: {language}")
                # return language

                language = PROGRAMMING_EXTENSIONS.get(extension, "Unknown")
                logger.debug(f"Detected language from file extension: {language}")
                return language
            except ClassNotFound:
                logger.debug(f"Could not detect language for {file_path}")
                return "Unknown"

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return "Unknown"


def extract_languages(cloned_repos_base_path, df, df_path):
    """
    Extracts the programming languages used in each repository.
    Args:
        cloned_repos_base_path (str): The base path to the cloned repositories.
        df (DataFrame): The DataFrame to update with language information.
        df_path (str): Path to save the DataFrame periodically.
    Returns:
        DataFrame: The updated DataFrame with language information.
    """
    org_paths = list(Path(cloned_repos_base_path).glob("*"))
    logger.info(f"Found {len(org_paths)} organisations")

    for org_path in tqdm(org_paths, desc="Analysing organisations", unit="org"):
        if org_path.is_dir():
            repo_paths = list(org_path.glob("*"))
            logger.info(f"Found {len(repo_paths)} repositories in {org_path.name}")

            for repo_path in tqdm(
                repo_paths,
                desc=f"Analysing repositories in {org_path.name}",
                unit="repo",
                leave=False,
            ):
                if repo_path.is_dir():
                    repo_name = repo_path.name
                    logger.info(f"Processing repository: {repo_name}")

                    # Skip already processed repositories
                    if (
                        df[df["repourl"].str.contains(repo_name)]["languages"]
                        .notna()
                        .any()
                    ):
                        logger.info(
                            f"Skipping already processed repository: {repo_name}"
                        )
                        continue

                    repo_languages = set()
                    file_paths = list(repo_path.rglob("*"))
                    logger.info(f"Found {len(file_paths)} files in {repo_name}")

                    for file_path in tqdm(
                        file_paths,
                        desc=f"Analysing files in {repo_path.name}",
                        unit="file",
                        leave=False,
                    ):
                        if file_path.is_file():
                            language = detect_language(str(file_path))
                            if language != "Unknown":
                                repo_languages.add(language)

                    # Update the DataFrame
                    df.loc[df["repourl"].str.contains(repo_name), "languages"] = (
                        json.dumps(list(repo_languages))
                    )
                    logger.info(
                        f"Updated languages for {repo_name}: {list(repo_languages)}"
                    )

                    # Save the DataFrame periodically
                    df.to_csv(df_path, index=False)

    return df


if __name__ == "__main__":
    # Path to the log file
    working_directory = get_working_directory_or_git_root()
    logger.info(f"Working Directory: {working_directory}")

    input_file_path = working_directory / Path("data/merged_df.csv")
    logger.info(f"Input file path: {input_file_path}")

    if os.path.exists(working_directory / "data/merged_df_with_languages.csv"):
        logger.info("Resuming from previously saved progress.")
        df = pd.read_csv(working_directory / "data/merged_df_with_languages.csv")
    else:
        df = pd.read_csv(input_file_path)
        logger.info(
            "Column 'languages' not found. Creating and prefilling it with None."
        )
        if "languages" not in df.columns:
            df["languages"] = None

    # Base path to the cloned repositories
    cloned_repos_base_path = working_directory / "data/cloned_repos"

    # Extract languages from the cloned repositories
    logger.info("Extracting languages from cloned repositories")
    df_path = working_directory / "data/merged_df_with_languages.csv"
    df = extract_languages(cloned_repos_base_path, df, df_path)

    # Save the updated DataFrame
    df.to_csv(df_path, index=False)

    logger.info(f"Saved the DataFrame with languages to {df_path}")
