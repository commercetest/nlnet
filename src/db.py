"""
Supabase Database Interaction Script

This script demonstrates how to interact with a Supabase database using Python.
It utilises the `dotenv` library to load environment variables
from a `.env` file and the `supabase-py` library to perform database operations.
The script includes functions to write data to and read data from a Supabase
table.

Argparse Parameters:
- --logfile-path: Path to the logfile. Defaults to "supabase/write_to_db.log"
in the working directory or git root.

Environment Variables:
- SUPABASE_URL: The URL of the Supabase instance.
- SUPABASE_KEY: The API key for accessing the Supabase instance.

"""

import os
import platform
import logging
import argparse
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

from utils.git_utils import get_working_directory_or_git_root


def parse_args():
    parser = argparse.ArgumentParser(description="Supabase Database Interaction Script")
    parser.add_argument(
        "--logfile-path",
        type=str,
        default=str(
            Path(get_working_directory_or_git_root()) / "supabase" / "write_to_db.log"
        ),
        help="Path to the logfile",
    )
    return parser.parse_args()


args = parse_args()
log_file_path = args.logfile_path


# Configure logging
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


logging.info(f"Logfile wil be saved in : {log_file_path}")

# Load environment variables from .env file
load_dotenv()

# Project Settings -> API
SUPABASE_URL = os.getenv("SUPABASE_URL")

# Project Settings -> API -> Project API keys
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Check if all the required environment variables are set
required_env_vars = [SUPABASE_URL, SUPABASE_KEY]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_vars)}"
    )

# Initialising the Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def write_to_db(
    hosting_provider, repo_name, file_path, guessed_language, hostname=None
):
    """
    Writes a new record to the 'guessed_languages' table in the Supabase
    database.
    Parameters:
        hosting_provider (str): The hosting provider of the repository.
        repo_name (str): The name of the repository.
        file_path (str): The file path in the repository.
        guessed_language (str): The language guessed for the file.
        hostname (str, optional): The hostname of the machine. Defaults to the
        current platform's node name.
    """
    if hostname is None:
        hostname = platform.node()
    try:
        # Define data to be inserted
        data = {
            "hosting_provider": hosting_provider,
            "repo_name": repo_name,
            "file_path": file_path,
            "guessed_language": guessed_language,
            "hostname": hostname,
        }
        supabase.table("guessed_languages").insert(data).execute()

        # Log the successful data insertion
        logging.info("'Data inserted successfully'")

    except Exception as error:
        logging.error(f"Error: {error}")


def read_from_db():
    """
    Reads and returns distinct file paths from the 'guessed_languages' table in
    the Supabase database.

    Returns:
        set: A set of distinct file paths.
    """
    try:
        # Query the distinct file_path values from the guessed_languages table
        response = supabase.table("guessed_languages").select("file_path").execute()

        # Check if response.data is empty and handle it
        if not response.data:
            logging.info("No records found in the 'guessed_languages' table.")
            return set()

        # Extract the file_path values and return them as a set
        file_paths = set(record["file_path"] for record in response.data)

        return file_paths

    except Exception as error:
        logging.error(f"Error reading from the database: {error} ")
        return set()


if __name__ == "__main__":
    # Read the distinct file_path values
    processed_files = read_from_db()
    logging.info(f"Processed files: {processed_files}")
