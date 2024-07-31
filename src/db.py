"""
Supabase Database Interaction Script

This script demonstrates how to interact with a Supabase database using Python.
It utilises the `dotenv` library to load environment variables
from a `.env` file and the `supabase-py` library to perform database operations.
The script includes functions to write data to and read data from a Supabase
table.

Environment Variables:
- SUPABASE_URL: The URL of the Supabase instance.
- SUPABASE_KEY: The API key for accessing the Supabase instance.

"""

import os
import platform

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Project Settings -> API
SUPABASE_URL = os.getenv("SUPABASE_URL")

# Project Settings -> API -> Project API keys
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Check if all the required environment variables are set
required_env_vars = [SUPABASE_URL, SUPABASE_KEY]
missing_vars = [
    var
    for var in required_env_vars
    if var not in os.environ or os.environ.get(var) is None
]

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

        print("Data inserted successfully")

    except Exception as error:
        print(f"Error: {error}")


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

        # Extract the file_path values and return them as a set
        file_paths = set(record["file_path"] for record in response.data)

        return file_paths

    except Exception as error:
        print(f"Error: {error}")
        return set()


if __name__ == "__main__":
    # Read the distinct file_path values
    processed_files = read_from_db()
    print(f"Processed files: {processed_files}")
