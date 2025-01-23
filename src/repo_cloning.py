"""
Repository cloning and file tracking script.
Issue: #93
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path
import shutil
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root

# Setup
load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def clone_repository(repo_url: str, clone_dir: Path) -> tuple[bool, str]:
    """Clone repository and return success status with error message."""
    try:
        logger.info(f"Attempting to clone {repo_url} into {clone_dir}")
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(clone_dir)],
            check=True,
            capture_output=True,
            text=True,
            env={"GIT_TERMINAL_PROMPT": "0"}
        )
        logger.info(f"Successfully cloned {repo_url}")
        return True, ""
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        logger.error(f"Failed to clone {repo_url}. Error: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error cloning {repo_url}. Error: {error_msg}")
        return False, error_msg


def get_repository_files(clone_dir: Path) -> list:
    """Get all files in the repository."""
    files = []
    for item in clone_dir.rglob('*'):
        if item.is_file():
            files.append({
                'file_path': str(item.relative_to(clone_dir)),
                'file_name': item.name,
                'file_extension': item.suffix if item.suffix else None
            })
    return files


def process_single_repository(repo_id: str, repo_url: str):
    """Process a single repository."""
    base_clone_dir = Path('repositories')
    clone_dir = clone_directory / base_clone_dir / repo_id
    clone_dir.parent.mkdir(exist_ok=True)
    base_clone_dir.mkdir(exist_ok=True)

    # Skip if already cloned
    if clone_dir.exists():
        logger.info(f"Repository already exists at {clone_dir}")
        return

    try:
        success, error_msg = clone_repository(repo_url, clone_dir)

        cloning_data = {
            'repository_id': repo_id,
            'clone_status': 'successful' if success else 'failed',
            'cloned_at': datetime.utcnow().isoformat(),
            'error_message': error_msg if error_msg else None
        }
        supabase.table('repository_cloning').insert(cloning_data).execute()

        if success:
            files = get_repository_files(clone_dir)
            for file_data in files:
                file_data['repository_id'] = repo_id
                supabase.table('cloned_files').insert(file_data).execute()

    except Exception as e:
        logger.error(f"Error processing repository {repo_url}: {str(e)}")
        # Only cleanup on error
        if clone_dir.exists():
            shutil.rmtree(clone_dir)



def main():
    """Main function to process repositories."""
    try:
        response = supabase.table('repositories').select(
            'id, repo_url').execute()
        for repo in response.data:
            logger.info(f"Processing repository: {repo['repo_url']}")
            process_single_repository(repo['id'], repo['repo_url'])

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")


if __name__ == "__main__":
    git_working_dir = get_working_directory_or_git_root()
    logger.info(f"git_working_dir is : {git_working_dir}")

    clone_directory = (get_working_directory_or_git_root() / "Data"/
                       "repos_cloned")
    clone_directory.mkdir(exist_ok=True, parents=True)
    # Configure logging
    logger.add(get_working_directory_or_git_root()/"logs"/"repo_cloning.log",
               rotation="1 day")

    main()