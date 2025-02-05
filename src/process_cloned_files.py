import os
from datetime import datetime
from pathlib import Path
import subprocess
from tqdm import tqdm
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root

BATCH_SIZE = 5

def setup():
    load_dotenv()
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))



def process_files(supabase):
    while True:
        try:
            response = supabase.table('cloned_files')\
                        .select('id, file_path, file_name')\
                        .is_('processed_at','null')\
                        .limit(BATCH_SIZE)\
                        .execute()

            if not response.data:
                logger.info(f"No data for response_id : {response.id}")
                break

            for file in response.data:
                try:
                    has_test = 'test' in file['file_path'].lower()
                    supabase.table('cloned_files')\
                    .update({
                        'has_test_in_name_or_path' : has_test,
                        'processed_at' : datetime.utcnow().isoformat()
                    })\
                    .eq('id', file['id'])\
                    .execute()
                    logger.info(f"Processed file {file['id']}")

                except Exception as e:
                    logger.error(f"Error processing file {file['id']} : {e}")
                    continue

        except Exception as e:
            logger.error(f"Batch error: {e}")
            continue


def get_last_commit_hash(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting last commit hash for {repo_path}:"
                     f" {e.stderr}")
        return None


def process_repositories(supabase):
    # Get repositories with successful clones but no commit hash
    response = supabase.table('repository_cloning')\
        .select('id, repository_id')\
        .eq('clone_status', 'successful')\
        .is_('last_commit_hash', 'null')\
        .execute()

    if not response.data:
        logger.info("No repositories to process")
        return

    clone_directory = (get_working_directory_or_git_root() / "Data" /
                       "repos_cloned" / "repositories")

    # Creating a progress bar
    pbar = tqdm(response.data, desc="Processing repositories")

    for repo in pbar:
        repo_path = clone_directory / repo['repository_id']
        if not repo_path.exists():
            logger.warning(f"Repository path not found: {repo_path}")
            continue

        pbar.set_description(f"Processing repository {repo['repository_id']}")
        commit_hash = get_last_commit_hash(repo_path)

        if commit_hash:
            try:
                supabase.table('repository_cloning')\
                    .update({'last_commit_hash' : commit_hash})\
                    .eq('id', repo['id'])\
                    .execute()
                logger.info(f"Updated commit hash for repository"
                            f" {repo['repository_id']}")
            except Exception as e:
                logger.error(f"Error updating commit hash on database for "
                             f"repository {repo['repository_id']}: {e}")




def main():

    # 1. Checking for 'test' in filenames/file path
    # logger.add("logs/process_cloned_files.log", level="INFO", rotation="1 day")
    # try:
    #     supabase = setup()
    #     process_files(supabase)
    # except Exception as e:
    #     logger.error(f"Error: {e}")

    # 2. Getting the last commit hash for each repository
    git_working_directory = get_working_directory_or_git_root()
    log_path = git_working_directory / "logs" / "retrieve_last_commit_hash.log"
    logger.add(log_path, level="INFO", rotation="1 day")

    try:
        logger.info(f"Starting commit hash retrieval process")
        supabase = setup()
        process_repositories(supabase)
        logger.info(f"Completed commit hash retrieval process")
    except Exception as e:
        logger.error(f"Error in main process: {e}")


if __name__ == "__main__":
    main()

