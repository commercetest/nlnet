"""
This script imports repository data from a CSV file into a Supabase database.
It's part of the repository analysis pipeline that processes and stores
repository information for further analysis.

The script:
- Reads repository data from a CSV file
- Connects to Supabase using environment variables
- Imports repository data into the 'repositories' table
- Logs the import process and any errors

Requirements:
    - A .env file with SUPABASE_URL and SUPABASE_KEY
    - CSV file with repository data
    - Supabase database with the repositories table schema

Issue: #93

"""
import os
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger
from pathlib import Path

from utils.git_utils import get_working_directory_or_git_root

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise EnvironmentError(
        "Supabase credentials not found in environment variables")

supabase = create_client(supabase_url, supabase_key)


def import_repositories_from_csv(csv_path: str) -> None:
    """
    Import repository data from CSV into Supabase repositories table.

    Args:
        csv_path (str): Path to the CSV file containing repository data

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        Exception: For other errors during import process
    """
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        logger.info(f"Read {len(df)} rows from CSV")

        # Process each row
        for _, row in df.iterrows():
            # Prepare data for insertion
            repo_data = {
                'project_ref': row['projectref'],
                'nlnet_page': row['nlnetpage'],
                'repo_url': row['repourl'],
                'repo_domain': row['repodomain'],
                'base_repo_url': row['base_repo_url'],
                'duplicate_flag': row['duplicate_flag'],
                'null_value_flag': row['null_value_flag'],
                'unsupported_url_scheme': row['unsupported_url_scheme'],
                'incomplete_url_flag': row['incomplete_url_flag'],
                'base_repo_url_flag': row['base_repo_url_flag'],
                'clone_status': 'pending'
            }

            try:
                # Insert into Supabase
                result = supabase.table('repositories').insert(
                    repo_data).execute()
                logger.info(
                    f"Successfully inserted repository: {row['repourl']}")

            except Exception as e:
                logger.error(
                    f"Error inserting repository {row['repourl']}: {str(e)}")

    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
        raise
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        raise


if __name__ == "__main__":
    git_working_dir = get_working_directory_or_git_root()
    logger.info(f"git_working_dir is : {git_working_dir}")

    # Configure logging
    logger.add(get_working_directory_or_git_root()/"logs"/"repo_import_to_supabase.log", rotation="1 day")

    # Path to your CSV file
    csv_path = get_working_directory_or_git_root()/"data"/"original_massive_df.csv"

    logger.info("Starting repository import")
    import_repositories_from_csv(csv_path)
    logger.info("Import completed")