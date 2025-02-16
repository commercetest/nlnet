import os
from datetime import datetime
from pathlib import Path
import subprocess
import time
from tqdm import tqdm
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root

BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 5  #seconds
SUB_BATCH_SIZE = 20  # For database updates

# Exclusions to exclude from language detection (this is based on the query
# on the 'file_extension' column of the 'cloned_files' table in Supabase)
EXCLUDE_EXTENSIONS = {
    # Images
    '.png', '.svg', '.jpg', '.gif', '.webp',

    # Documentation
    '.txt', '.md', '.rst', '.pdf', '.mdx', '.odt',

    # Fonts and Web Assets
    '.woff', '.woff2', '.eot', '.ttf', '.otf',

    # Build/Binary files
    '.pack', '.tar', '.lib', '.bcmap',

    # Other assets
    '.css', '.scss', '.less',  # Stylesheets
    '.map',  # Source maps
    '.lock', '.sample',  # Generated files
    '.po', '.graphml', '.pbf',  # Data files

    # Configuration and templates
    '.properties', '.conf', '.tpl', '.tmpl', '.snap',

    # Documentation and license files
    '.license', '.patch', '.in'
}

# Language mapping based on the data frequencies
LANGUAGE_EXTENSIONS = {
    # Most common languages (>5000 files)
    '.php': 'PHP',  # 18536 files
    '.go': 'Go',  # 15705 files
    '.js': 'JavaScript',  # 14516 files
    '.ts': 'TypeScript',  # 13532 files
    '.py': 'Python',  # 12939 files
    '.java': 'Java',  # 11069 files
    '.c': 'C',  # 8058 files
    '.cpp': 'C++',  # 7893 files
    '.rs': 'Rust',  # 7781 files
    '.kt': 'Kotlin',  # 4978 files

    # Common languages (1000-5000 files)
    '.rb': 'Ruby',  # 4292 files
    '.sh': 'Shell',  # 3187 files
    '.tsx': 'TypeScript',  # 2818 files
    '.hpp': 'C++',  # 1800 files
    '.vue': 'Vue',  # 1668 files
    '.lua': 'Lua',  # 1619 files
    '.sql': 'SQL',  # 1461 files
    '.scala': 'Scala',  # 889 files
    '.cc': 'C++',  # 887 files
    '.swift': 'Swift',  # 798 files

    # Configuration and markup
    '.json': 'JSON',  # 14636 files
    '.xml': 'XML',  # 12296 files
    '.html': 'HTML',  # 10159 files
    '.yaml': 'YAML',  # 5372 files
    '.yml': 'YAML',  # 3680 files
    '.toml': 'TOML',  # 1051 files

    # Special cases
    '.h': 'C/C++ Header',  # 15190 files
    '.jsx': 'JavaScript',  # 477 files
    '.m': 'Objective-C',  # 405 files
    '.dart': 'Dart'  # 306 files

}

def setup():
    load_dotenv()
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def retry_on_timeout(func):
    """Decorator to handle retries on timeout."""
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if 'statement timeout' in str(e).lower():
                    retries += 1
                    if retries < MAX_RETRIES:
                        logger.warning(f"Timeout occurred. Retry {retries}/{MAX_RETRIES} after {RETRY_DELAY} seconds")
                        time.sleep(RETRY_DELAY)
                        continue
                logger.error(f"{'Max retries reached' if retries == MAX_RETRIES else 'Error'}: {str(e)}")
                raise
    return wrapper


@retry_on_timeout
def get_unprocessed_count(supabase) -> int:
    """Get total count of unprocessed files."""
    response = supabase.table('cloned_files')\
        .select('id', count='exact')\
        .is_('language_detection_processed_at', 'null')\
        .execute()
    return response.count


@retry_on_timeout
def get_unprocessed_batch(supabase, start: int, size: int) -> list:
    """Get a batch of unprocessed files."""
    response = supabase.table('cloned_files')\
        .select('id, file_path, file_extension, file_name')\
        .is_('language_detection_processed_at', 'null')\
        .range(start, start + size - 1)\
        .execute()
    return response.data


@retry_on_timeout
def update_database_batch(supabase, updates):
    """Update database in batches."""
    if not updates:
        return

    for i in range(0, len(updates), SUB_BATCH_SIZE):
        sub_batch = updates[i:i + SUB_BATCH_SIZE]
        try:
            # Only update records that have all required fields
            valid_updates = [update for update in sub_batch if update.get(
                'file_name') is not None]
            if valid_updates:
                supabase.table('cloned_files')\
                .upsert(valid_updates)\
                .execute()
            logger.info(f"Updated batch of {len(valid_updates)} files")
            # Small delay between sub-batches
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error updating batch: {e}")
            raise


def extract_file_name_from_path(file_path):
    """Extract file name from path."""
    if not file_path:
        return None
    return Path(file_path).name


def process_file_2(file) -> dict:
    """Process a single file and return update data."""
    try:
        # Ensure we have a file_name
        file_name = file.get('file_name') or extract_file_name_from_path(
            file.get('file_path'))
        if not file_name:
            logger.warning(f"Skipping file {file['id']} - Cannot determone "
                           f"file_name")
            return None

        # Handle null/none extension
        if file['file_extension'] is None:
            return {
                'id': file['id'],
                'file_name': file_name,
                'file_language': None,
                'language_detection_processed_at': datetime.utcnow().isoformat()
            }

        # Handle file extensions
        if isinstance(file['file_extension'], list):
            logger.debug(
                f"File {file['id']} has list extension: {file['file_extension']}")
            file_extension = file['file_extension'][0] if file[
                'file_extension'] else ''
        else:
            file_extension = file['file_extension'].lower() if isinstance(
                file['file_extension'], str) else ''

        # Handle empty extension
        if not file_extension:
            return {
                'id': file['id'],
                'file_name': file_name,
                'file_language': None,
                'language_detection_processed_at': datetime.utcnow().isoformat()
            }

        # Handle excluded extensions
        if file_extension in EXCLUDE_EXTENSIONS:
            return {
                'id': file['id'],
                'file_language': None,
                'file_name' : file_name,
                'language_detection_processed_at': datetime.utcnow().isoformat()
            }

        # Detect language
        language = LANGUAGE_EXTENSIONS.get(file_extension, 'Unknown')

        return {
            'id': file['id'],
            'file_name': file_name,
            'file_language': language,
            'language_detection_processed_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing file {file['id']}: {e}")
        return None

def detect_language(supabase):
    """Main language detection function with improved batch processing."""
    try:
        # Get total count with retry
        total_files = get_unprocessed_count(supabase)
        if total_files == 0:
            logger.info("No files to process for language detection")
            return

        logger.info(f"Starting language detection for {total_files} files")

        # Statistics tracking
        language_stats = {}
        processed_count = 0
        error_count = 0
        max_errors = 5 # Maximum number of consecutive errors before aborting

        # Process files in batches with progress bar
        with tqdm(total=total_files, desc="Detecting languages") as pbar:
            while processed_count < total_files:
                try:
                    # Get batch of files with retry
                    batch = get_unprocessed_batch(supabase, processed_count, BATCH_SIZE)
                    if not batch:
                        logger.warning("No more files to process.")
                        break

                    batch_updates = []
                    valid_files = 0

                    # Process each file in batch
                    for file in batch:
                        update_data = process_file_2(file)
                        if update_data:
                            batch_updates.append(update_data)
                            if update_data['file_language']:
                                language_stats[update_data['file_language']] = \
                                    language_stats.get(update_data['file_language'], 0) + 1
                            valid_files += 1

                    # Update database with retry
                    if batch_updates:
                        update_database_batch(supabase, batch_updates)
                        error_count = 0 # Reset error count on successful update


                    # Update progress
                    processed_count += len(batch)
                    pbar.update(len(batch))

                    # Log progress periodically
                    if processed_count % 1000 == 0:
                        logger.info(f"Processed {processed_count}/{total_files} files")
                        logger.info(f"Current language distribution: {language_stats}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing batch at "
                                 f"{processed_count}: {e}")

                    if error_count >= max_errors:
                        logger.error(f"Exceeded maximum consecutive errors ("
                                     f"{max_errors}). Aborting.")
                        break

                    # Wait before retrying
                    time.sleep(RETRY_DELAY)

        # Log final statistics
        logger.info("Language detection completed!")
        logger.info(f"Total files processed: {processed_count}")
        logger.info("Language statistics:")
        for language, count in sorted(language_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"{language}: {count} files")

    except Exception as e:
        logger.error(f"Error in language detection process: {e}")
        raise


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
    # log_path = git_working_directory / "logs" / "retrieve_last_commit_hash.log"
    # logger.add(log_path, level="INFO", rotation="1 day")

    # try:
    #     logger.info(f"Starting commit hash retrieval process")
    #     supabase = setup()
    #     process_repositories(supabase)
    #     logger.info(f"Completed commit hash retrieval process")
    # except Exception as e:
    #     logger.error(f"Error in main process: {e}")

    # Setup logging for language detection
    log_path = git_working_directory / "logs" / "language_detection.log"
    logger.add(log_path, rotation='1 day', level="INFO")

    try:
        logger.info("Starting language detection processed (based on file "
                    "extensions)")
        supabase = setup()
        detect_language(supabase)
        logger.info("Finished language detection processed (based on file "
                    "extensions)")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
if __name__ == "__main__":
    main()

