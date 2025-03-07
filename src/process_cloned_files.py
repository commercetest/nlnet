import os
import re
from datetime import datetime
from pathlib import Path
import subprocess
import time

from pkg_resources import non_empty_lines
from tqdm import tqdm
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root

# Configuration
BATCH_SIZE = 5
MAX_RETRIES = 3
RETRY_DELAY = 5  #seconds
SUB_BATCH_SIZE = 1  # For database updates

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

EXCLUDE_EXTENSIONS_METRIC_EXTRACTION = {
    # Images
    '.png', '.svg', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.bmp',

    # Fonts
    '.woff', '.woff2', '.eot', '.ttf', '.otf',

    # Documents/Text
    '.txt', '.md', '.rst', '.pdf', '.doc', '.docx', '.odt', '.mdx',

    # Binary/Compiled
    '.bin', '.zip', '.gz', '.tar', '.exe', '.dll', '.so', '.dylib',
    '.class', '.pyc', '.pack', '.lib', '.bcmap',

    # Styles/Assets
    '.css', '.scss', '.less',

    # Generated files
    '.map', '.lock', '.sample', '.min.js', '.min.css',

    # Configuration/Data files
    '.po', '.properties', '.patch', '.graphml', '.pbf', '.in',
    '.conf', '.tpl', '.tmpl', '.snap'
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
    """Decorator to handle retries on timeout. This is a decorator function
    that takes another function (func) as input. It wraps func with retry
    logic when it is called."""
    def wrapper(*args, **kwargs):
        """ The inner function (wrapper) allows the decorated function to
        accept any number of arguments (*args, **kwargs)."""
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs) # Try to execute the function
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
def get_unprocessed_count_metrics_extraction(supabase) -> int:
    """Get total count of unprocessed files for metric extraction."""
    response = supabase.table('cloned_files')\
        .select('id', count='exact')\
        .is_('metrics_processed_at', 'null')\
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


def get_unprocessed_batch_metrics_extraction(supabase, start: int,
                                             size: int)-> list:
    """Get a batch of unprocessed files for metrics."""
    logger.info(f"start: {start}, size: {size}")
    response = supabase.table('cloned_files')\
        .select('id, repository_id, file_path, file_extension, file_language')\
        .is_('metrics_processed_at', 'null')\
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


@retry_on_timeout
def update_database_batch_metrics_extraction(supabase, updates):
    """Update database with metrics in batches."""
    if not updates:
        return

    for i in range(0, len(updates), SUB_BATCH_SIZE):
        sub_batch = updates[i:i + SUB_BATCH_SIZE]
        try:
            valid_updates = [update for update in sub_batch if update.get('id') is not None]
            if valid_updates:
                supabase.table('cloned_files')\
                .upsert(valid_updates)\
                .execute()
            logger.info(f"Updated batch of {len(valid_updates)} files with metrics")
            # Small delay between sub-batches
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error updating batch with metrics: {e}")
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

def count_lines_of_code(file_content):
    """Count non-empty, non-comment lines of code."""
    if not file_content:
        return 0

    lines = file_content.split('\n')
    # Remove empty lines and simple comment lines
    non_empty_lines = [line for line in lines if line.strip() and not
    line.strip().startswith(('#', '//', '/*', '*', '*/'))]
    return len(non_empty_lines)


def count_functions_in_file(file_content, file_extension):
    """Count the number of functions in a file based on the language."""
    if not file_content:
        return 0

    # Define language-specific regex patterns for function detection
    patterns = {
        # Python functions and methods
        '.py': [
            r'def\s+[a-zA-Z0-9_]+\s*\(',  # Regular functions
            r'async\s+def\s+[a-zA-Z0-9_]+\s*\('  # Async functions
        ],
        # JavaScript/TypeScript functions
        '.js': [
            r'function\s+[a-zA-Z0-9_]+\s*\(',  # Named functions
            r'[a-zA-Z0-9_]+\s*=\s*function\s*\(',  # Function assignments
            r'[a-zA-Z0-9_]+\s*:\s*function\s*\(',  # Object methods
            r'[a-zA-Z0-9_]+\s*=\s*\([^\)]*\)\s*=>',
            # Arrow functions with params
            r'[a-zA-Z0-9_]+\s*=\s*\w+\s*=>',  # Simple arrow functions
        ],
        '.ts': [
            r'function\s+[a-zA-Z0-9_]+\s*\(',  # Named functions
            r'[a-zA-Z0-9_]+\s*=\s*function\s*\(',  # Function assignments
            r'[a-zA-Z0-9_]+\s*:\s*function\s*\(',  # Object methods
            r'[a-zA-Z0-9_]+\s*\([^\)]*\)\s*:\s*[a-zA-Z0-9_<>\\[\\]]+\s*{',
            # TypeScript methods with return type
            r'[a-zA-Z0-9_]+\s*=\s*\([^\)]*\)\s*=>',
            # Arrow functions with params
            r'[a-zA-Z0-9_]+\s*=\s*\w+\s*=>',  # Simple arrow functions
        ],
        # Java/Kotlin methods
        '.java': [
            r'(public|private|protected|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])'
        ],
        '.kt': [
            r'fun\s+[a-zA-Z0-9_]+\s*\(',  # Kotlin functions
        ],
        # Go functions
        '.go': [
            r'func\s+[a-zA-Z0-9_]+\s*\(',  # Go functions
            r'func\s+\([^)]+\)\s+[a-zA-Z0-9_]+\s*\('  # Go methods
        ],
        # PHP functions and methods
        '.php': [
            r'function\s+[a-zA-Z0-9_]+\s*\(',  # Functions
            r'public|private|protected\s+function\s+[a-zA-Z0-9_]+\s*\('
            # Methods
        ],
        # C/C++ functions
        '.c': [
            r'[a-zA-Z0-9_]+\s+[a-zA-Z0-9_]+\s*\([^;]+\)\s*\{'
        ],
        '.cpp': [
            r'[a-zA-Z0-9_:]+\s+[a-zA-Z0-9_]+\s*\([^;]+\)\s*\{',
            r'[a-zA-Z0-9_]+::[a-zA-Z0-9_]+\s*\([^;]+\)\s*\{'  # Class methods
        ],
        '.h': [
            r'[a-zA-Z0-9_]+\s+[a-zA-Z0-9_]+\s*\([^;]+\)\s*\{'
        ],
        # Rust functions
        '.rs': [
            r'fn\s+[a-zA-Z0-9_]+\s*\(',  # Rust functions
            r'impl\s+.+\s*\{[^}]*fn\s+[a-zA-Z0-9_]+\s*\('
            # Rust implementation methods
        ],
        # Ruby methods
        '.rb': [
            r'def\s+[a-zA-Z0-9_?!]+',
            # Ruby methods (including those with ? or !)
        ]
    }

    # Generic pattern for other languages
    generic_patterns = [
        r'function\s+[a-zA-Z0-9_]+\s*\(',  # Common function pattern
        r'def\s+[a-zA-Z0-9_]+\s*\(',  # Python-like function pattern
        r'func\s+[a-zA-Z0-9_]+\s*\('  # Go-like function pattern
    ]

    # Get appropriate patterns for the file extension
    extension = file_extension.lower() if file_extension else ''
    # Retrieve the value for a given key `extension` if not return the
    # generic_patterns
    function_patterns = patterns.get(extension, generic_patterns)

    count = 0
    for pattern in function_patterns:
        # search for all occurrences of a `pattern` in `file_content`.
        matches = re.findall(pattern, file_content)
        count += len(matches)

    return count


def count_test_cases(file_content, file_extension):
    """Count the number of test case functions in the file."""
    if not file_content:
        return 0

        # Define language-specific patterns for test functions
    test_patterns = {
        # Python test patterns
        '.py': [
            r'def\s+test_[a-zA-Z0-9_]+\s*\(',  # unittest and pytest style
            r'@pytest\.mark\.parametrize',  # Parametrized tests
            r'class\s+Test[a-zA-Z0-9_]+\('  # Test classes
        ],
        # JavaScript/TypeScript test patterns
        '.js': [
            r'test\s*\(\s*[\'"][^\'"]+[\'"]\s*,',  # Jest/Mocha test functions
            r'it\s*\(\s*[\'"][^\'"]+[\'"]\s*,',  # BDD style tests
            r'describe\s*\(\s*[\'"][^\'"]+[\'"]\s*,',  # Test suites
        ],
        '.ts': [
            r'test\s*\(\s*[\'"][^\'"]+[\'"]\s*,',
            r'it\s*\(\s*[\'"][^\'"]+[\'"]\s*,',
            r'describe\s*\(\s*[\'"][^\'"]+[\'"]\s*,',
        ],
        # Java/Kotlin test patterns
        '.java': [
            r'@Test',  # JUnit annotations
            r'public\s+void\s+test[a-zA-Z0-9_]+\s*\(',  # Test methods
            r'class\s+[a-zA-Z0-9_]*Test[a-zA-Z0-9_]*\s+',  # Test classes
        ],
        '.kt': [
            r'@Test',  # JUnit annotations
            r'fun\s+test[a-zA-Z0-9_]+\s*\(',  # Test methods
            r'class\s+[a-zA-Z0-9_]*Test[a-zA-Z0-9_]*\s+',  # Test classes
        ],
        # Go test patterns
        '.go': [
            r'func\s+Test[A-Z][a-zA-Z0-9_]*\s*\(',  # Go test functions
            r'func\s+Benchmark[A-Z][a-zA-Z0-9_]*\s*\('  # Go benchmark functions
        ],
        # PHP test patterns
        '.php': [
            r'function\s+test[A-Z][a-zA-Z0-9_]*\s*\(',  # PHPUnit test methods
            r'class\s+[a-zA-Z0-9_]*Test\s+',  # Test classes
            r'@test'  # PHPUnit @test annotation
        ],
        # C++ test patterns
        '.cpp': [
            r'TEST\s*\(',  # GoogleTest or Catch2 test
            r'TEST_F\s*\(',  # GoogleTest fixture test
            r'SCENARIO\s*\(',  # Catch2 BDD-style tests
            r'TEST_CASE\s*\('  # Catch2 test cases
        ],
        # Rust test patterns
        '.rs': [
            r'#\[test\]',  # Rust test annotation
            r'#\[cfg\(test\)\]',  # Rust test config
        ],
        # Ruby test patterns
        '.rb': [
            r'def\s+test_[a-zA-Z0-9_]+',  # Test methods
            r'describe\s+[\'"][^\'"]+[\'"]\s+do',  # RSpec describe blocks
            r'it\s+[\'"][^\'"]+[\'"]\s+do'  # RSpec it blocks
        ]
    }

    # Generic test patterns for other languages
    generic_test_patterns = [
        r'test[A-Z][a-zA-Z0-9_]*\s*\(',  # TestXxx function names
        r'[a-zA-Z0-9_]*[tT]est[a-zA-Z0-9_]*\s*\(',  # Contains "test" anywhere
        r'assert[A-Z][a-zA-Z0-9_]*\s*\('  # Assertion functions
    ]

    # Get appropriate patterns for the file extension
    extension = file_extension.lower() if file_extension else ''
    patterns = test_patterns.get(extension, generic_test_patterns)

    count = 0
    for pattern in patterns:
        matches = re.findall(pattern, file_content)
        count += len(matches)

    return count


def count_assertions(file_content, file_extension):
    """Count the number of assertion statements in the file."""
    if not file_content:
        return 0

    # Define language-specific patterns for assertions
    assertion_patterns = {
        # Python assertions
        '.py': [
            r'assert\s+',  # assert statement
            r'self\.assert[A-Za-z]+\s*\(',
            # unittest assertions (assertEqual, etc)
            r'pytest\.raises\s*\(',  # pytest exception assertion
            r'assert_[a-z_]+\s*\('  # nose/pytest assertion helpers
        ],
        # JavaScript/TypeScript assertions
        '.js': [
            r'assert\.[a-zA-Z]+\s*\(',  # Node.js assert
            r'expect\s*\([^\)]*\)\.[a-z]+',  # Jest/Chai expectations
            r'should\.[a-z]+\s*\(',  # Should.js
            r'assert\s*\('  # Plain assert
        ],
        '.ts': [
            r'assert\.[a-zA-Z]+\s*\(',
            r'expect\s*\([^\)]*\)\.[a-z]+',
            r'should\.[a-z]+\s*\(',
            r'assert\s*\('
        ],
        # Java/Kotlin assertions
        '.java': [
            r'assert[A-Z][a-zA-Z]+\s*\(',  # JUnit/AssertJ assertions
            r'[aA]ssert\.[a-zA-Z]+\s*\(',  # Static assertions
            r'[aA]ssert(True|False|Equals|NotNull)'  # Various assertions
        ],
        '.kt': [
            r'assert[A-Z][a-zA-Z]+\s*\(',
            r'[aA]ssert\.[a-zA-Z]+\s*\(',
            r'[aA]ssert(True|False|Equals|NotNull)'
        ],
        # Go assertions
        '.go': [
            r't\.(Fatal|Error|Equal|NotEqual|True|False)[a-zA-Z]*\s*\(',
            # testing.T assertions
            r'require\.(NoError|Error|Equal|NotEqual|True|False)[a-zA-Z]*\s*\('
            # testify assertions
        ],
        # PHP assertions
        '.php': [
            r'assert[A-Z][a-zA-Z]+\s*\(',  # PHPUnit assertions
            r'this->assert[A-Z][a-zA-Z]+\s*\('
            # PHPUnit assertions within object context
        ],
        # C++ assertions
        '.cpp': [
            r'ASSERT_[A-Z_]+\s*\(',  # GoogleTest ASSERT macros
            r'EXPECT_[A-Z_]+\s*\(',  # GoogleTest EXPECT macros
            r'CHECK\s*\(',  # Various check macros
            r'REQUIRE\s*\('  # Catch2 REQUIRE
        ],
        # Rust assertions
        '.rs': [
            r'assert!',  # Rust assert macro
            r'assert_eq!',  # Equality assertion
            r'assert_ne!'  # Inequality assertion
        ],
        # Ruby assertions
        '.rb': [
            r'assert_[a-z_]+\s',  # Test::Unit/Minitest assertions
            r'expect\s*\([^\)]*\)\.(to|not_to|to_not)',  # RSpec expectations
            r'\.must_'  # Minitest expectations
        ]
    }

    # Generic assertion patterns for other languages
    generic_assertion_patterns = [
        r'assert[A-Za-z]*\s*\(',  # Generic assert functions
        r'expect\s*\([^\)]*\)\.[a-z]+',  # Generic expectations
        r'should\.[a-z]+\s*\('  # Generic should assertions
    ]

    # Get appropriate patterns for the file extension
    extension = file_extension.lower() if file_extension else ''
    patterns = assertion_patterns.get(extension, generic_assertion_patterns)

    count = 0
    for pattern in patterns:
        matches = re.findall(pattern, file_content)
        count += len(matches)

    return count


def detect_setup_teardown(file_content, file_extension):
    """Detect if the file contains setup/teardown methods."""
    if not file_content:
        return False

    # Define language-specific patterns for setup/teardown
    setup_teardown_patterns = {
        # Python setup/teardown
        '.py': [
            r'def\s+setUp\s*\(',  # unittest setUp
            r'def\s+tearDown\s*\(',  # unittest tearDown
            r'def\s+setup_[a-z_]+\s*\(',  # pytest setup
            r'def\s+teardown_[a-z_]+\s*\(',  # pytest teardown
            r'@pytest\.fixture'  # pytest fixtures
        ],
        # JavaScript/TypeScript setup/teardown
        '.js': [
            r'beforeEach\s*\(',  # Jest/Mocha beforeEach
            r'afterEach\s*\(',  # Jest/Mocha afterEach
            r'beforeAll\s*\(',  # Jest/Mocha beforeAll
            r'afterAll\s*\('  # Jest/Mocha afterAll
        ],
        '.ts': [
            r'beforeEach\s*\(',
            r'afterEach\s*\(',
            r'beforeAll\s*\(',
            r'afterAll\s*\('
        ],
        # Java/Kotlin setup/teardown
        '.java': [
            r'@Before',  # JUnit 4 Before
            r'@After',  # JUnit 4 After
            r'@BeforeEach',  # JUnit 5 BeforeEach
            r'@AfterEach',  # JUnit 5 AfterEach
            r'@BeforeClass',  # JUnit 4 BeforeClass
            r'@AfterClass'  # JUnit 4 AfterClass
        ],
        '.kt': [
            r'@Before',
            r'@After',
            r'@BeforeEach',
            r'@AfterEach',
            r'@BeforeClass',
            r'@AfterClass'
        ],
        # Go setup/teardown
        '.go': [
            r'func\s+setUp\s*\(',
            r'func\s+tearDown\s*\(',
            r'func\s+TestMain\s*\('  # TestMain for setup/teardown
        ],
        # PHP setup/teardown
        '.php': [
            r'function\s+setUp\s*\(',
            r'function\s+tearDown\s*\(',
            r'protected\s+function\s+setUp\s*\(',
            r'protected\s+function\s+tearDown\s*\('
        ],
        # C++ setup/teardown
        '.cpp': [
            r'SetUp\s*\(\s*\)',  # GoogleTest SetUp
            r'TearDown\s*\(\s*\)',  # GoogleTest TearDown
            r'SETUP\s*\(',  # Catch2 SETUP
            r'TEST_SETUP',  # Various setup macros
            r'TEST_TEARDOWN'  # Various teardown macros
        ],
        # Rust setup/teardown
        '.rs': [
            r'fn\s+setup\s*\(',
            r'fn\s+teardown\s*\('
        ],
        # Ruby setup/teardown
        '.rb': [
            r'def\s+setup\s',
            r'def\s+teardown\s',
            r'before\s+\(?\s*:each',  # RSpec before each
            r'after\s+\(?\s*:each'  # RSpec after each
        ]
    }

    # Generic setup/teardown patterns for other languages
    generic_setup_teardown_patterns = [
        r'setup\s*\(',
        r'teardown\s*\(',
        r'set_up\s*\(',
        r'tear_down\s*\(',
        r'setUp\s*\(',
        r'tearDown\s*\('
    ]

    # Get appropriate patterns for the file extension
    extension = file_extension.lower() if file_extension else ''
    patterns = setup_teardown_patterns.get(extension,
                                           generic_setup_teardown_patterns)

    for pattern in patterns:
        if re.search(pattern, file_content):
            return True

    return False


def calculate_complexity_score(file_content):
    """Calculate a basic complexity score for the file.

    This is a simple heuristic based on:
    - Number of conditional statements (if, else, switch, case)
    - Number of loops (for, while, do-while)
    - Number of exception handling blocks (try/catch)
    """
    if not file_content:
        return 0

    # Count conditional statements
    conditional_patterns = [
        r'\sif\s*\(', r'\selse\s+if', r'\selse\s*{',
        r'\sswitch\s*\(', r'\scase\s+[^:]+:'
    ]

    # Count loops
    loop_patterns = [
        r'\sfor\s*\(', r'\swhile\s*\(', r'\sdo\s*{',
        r'\.forEach\s*\(', r'\.map\s*\(', r'\.filter\s*\('
    ]

    # Count exception handling
    exception_patterns = [
        r'\stry\s*{', r'\scatch\s*\(', r'\sfinally\s*{',
        r'\sexcept\s+', r'\sraise\s+'
    ]

    # Calculate base score
    conditional_score = sum(
        len(re.findall(pattern, file_content)) for pattern in
        conditional_patterns)
    loop_score = sum(len(re.findall(pattern, file_content)) for pattern in
                     loop_patterns) * 2  # Loops weighted more
    exception_score = sum(len(re.findall(pattern, file_content)) for pattern in
                          exception_patterns)

    # Calculate nesting score - a rough approximation of nested code blocks
    # Count the number of opening braces followed by another opening brace without a closing brace
    nesting_score = 0
    brace_level = 0
    for char in file_content:
        if char == '{':
            brace_level += 1
            if brace_level > 1:
                nesting_score += brace_level - 1  # Higher score for deeper nesting
        elif char == '}':
            brace_level = max(0, brace_level - 1)  # Ensure we don't go negative

    # Combine scores with weights
    total_score = conditional_score + loop_score + exception_score + nesting_score

    return total_score


def calculate_cyclomatic_complexity(file_content):
    """Calculate the cyclomatic complexity of the file.

    Cyclomatic complexity is calculated as:
    M = E - N + 2P

    Where:
    - E = number of edges in the control flow graph
    - N = number of nodes in the control flow graph
    - P = number of connected components (usually 1 for a single method)

    For a simplified calculation, we'll count:
    - Number of decision points (if, else if, case, for, while, etc.)
    - Add 1 for the base path
    """
    if not file_content:
        return 1  # Minimum complexity

    # Decision point patterns (each represents a branch in the code)
    decision_patterns = [
        r'\sif\s*\(', r'\selse\s+if',
        r'\scase\s+[^:]+:', r'\sdefault\s*:',
        r'\sfor\s*\(', r'\swhile\s*\(', r'\sdo\s*{',
        r'\scatch\s*\(', r'\s&&\s', r'\s\|\|\s',
        r'(?<=[^?])(\?)[^?]',  # Ternary operator ? but not ?? (null coalescing)
        r'\.forEach\s*\(', r'\.map\s*\(', r'\.filter\s*\(',
        # Higher-order functions
    ]

    # Count decision points
    decision_count = sum(
        len(re.findall(pattern, file_content)) for pattern in decision_patterns)

    # Basic cyclomatic complexity is decision count + 1
    return decision_count + 1


def process_file_for_metrics(file_info, repo_path):
    """Process a single file to extract metrics."""
    file_path = repo_path / file_info['file_path']
    if not file_path.exists() or file_info.get(
            'file_extension') in EXCLUDE_EXTENSIONS_METRIC_EXTRACTION:
        return {
            'id': file_info['id'],
            'file_name': file_info.get('file_name') or
                     extract_file_name_from_path(
                         file_info.get('file_path', '')),
            'lines_of_code': 0,
            'number_of_functions': 0,
            'number_of_test_cases': 0,
            'number_of_assertions': 0,
            'has_setup_teardown': False,
            'complexity_score': 0,
            'cyclomatic_complexity': 0,
            'metrics_processed_at': datetime.utcnow().isoformat()
        }

    metrics = {
        'id': file_info['id'],
        'file_name': file_info.get('file_name') or
                     extract_file_name_from_path(
                         file_info.get('file_path', '')),
        'lines_of_code': 0,
        'number_of_functions': 0,
        'number_of_test_cases': 0,
        'number_of_assertions': 0,
        'has_setup_teardown': False,
        'complexity_score': 0,
        'cyclomatic_complexity': 0,
    }

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            file_extension = file_info.get('file_extension', '')

            # Count Lines of Code
            metrics['lines_of_code'] = count_lines_of_code(content)

            # Count Functions
            metrics['number_of_functions'] = count_functions_in_file(
                content, file_extension
            )

            # Count the Test Cases
            metrics['number_of_test_cases'] = count_test_cases(content, file_extension)

            # Count Assertions
            metrics['number_of_assertions'] = count_assertions(content, file_extension)

            # Detect Setup/Teardown Methods
            metrics['has_setup_teardown'] = detect_setup_teardown(content, file_extension)

            # Calculate Complexity Score
            metrics['complexity_score'] = calculate_complexity_score(content)

            # Calculate Cyclomatic Complexity
            metrics['cyclomatic_complexity'] = calculate_cyclomatic_complexity(content)

    except Exception as e:
        logger.warning(f"Error reading or processing file in function "
                       f"process_file_for_metrics : {e}"
                       f" {file_path}: {e}")

    # Add timestamp
    metrics['metrics_processed_at'] = datetime.utcnow().isoformat()
    return metrics


def process_repositories_for_metrics(supabase):
    """Process repositories to extract metrics from files."""
    clone_directory = (get_working_directory_or_git_root() / "Data" /
                       "repos_cloned" / "repositories")
    logger.info(f"clone_directory path: {clone_directory}")

    # Get total count for progress bar
    total_files = get_unprocessed_count_metrics_extraction(supabase)
    if total_files == 0:
        logger.info("No files to process for metrics extraction")
        return

    logger.info(f"Total files to process for metrics: {total_files}")

    # Create progress bar for overall process
    with tqdm(total=total_files, desc="Processing files for metrics") as pbar:
        processed_count = 0
        error_count = 0
        max_errors = 3  # Maximum consecutive errors before aborting
        # repo_stats = {}  # Keep track of metrics per repository

        while processed_count < total_files:
            try:
                # Get batch of files
                logger.info(f"Getting a batch of files. processed_count: "
                            f"{processed_count}")
                batch = get_unprocessed_batch_metrics_extraction(supabase,
                                                            processed_count,
                                                                 BATCH_SIZE)
                if not batch:
                    logger.warning(
                        f"No files returned for batch starting at {processed_count}")
                    break
                logger.info(f"Batch is:\n{batch}")
                batch_updates = []
                # logger.info(f"Batch updates:\n{batch_updates}")
                current_repo_id = None
                repo_files_processed = 0

                # Process files in the batch with nested progress bar
                with tqdm(total=len(batch), desc="Current batch",
                          leave=False) as batch_pbar:
                    for file in batch:
                        repo_id = file['repository_id']
                        logger.info(f"repo_id is: {repo_id}")

                        # Track repository changes for logging purposes
                        if repo_id != current_repo_id:
                            if current_repo_id is not None:
                                logger.info(
                                    f"Completed {repo_files_processed} files "
                                    f"for repository {current_repo_id}")
                            current_repo_id = repo_id
                            repo_files_processed = 0

                        repo_path = clone_directory / repo_id
                        logger.info(f"repo_path: {repo_path}")
                        if not repo_path.exists():
                            logger.warning(
                                f"Repository path not found: {repo_path}")
                            # Still mark as processed to avoid getting stuck
                            metrics = {
                                'id': file['id'],
                                'file_name': file.get('file_name') or
                                             extract_file_name_from_path(
                                                 file.get('file_path', '')),
                                'metrics_processed_at': datetime.utcnow(

                                ).isoformat()
                            }
                        else:
                            # Extract metrics from file
                            metrics = process_file_for_metrics(file, repo_path)
                            logger.info(f"metrics is: {metrics}")

                        batch_updates.append(metrics)
                        repo_files_processed += 1
                        batch_pbar.update(1)

                # Update database
                try:
                    update_database_batch_metrics_extraction(supabase,
                                                             batch_updates)
                    error_count = 0  # Reset error count on successful update
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error updating database for batch: {e}")
                    if error_count >= max_errors:
                        logger.error(
                            f"Exceeded maximum consecutive errors "
                            f"({max_errors}). Aborting.")
                        break

                processed_count += len(batch)
                pbar.update(len(batch))

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing batch at {processed_count}: {e}")

                if error_count >= max_errors:
                    logger.error(f"Exceeded maximum consecutive errors "
                                 f"({max_errors}). Aborting.")
                    break

                # Wait before retrying
                time.sleep(RETRY_DELAY)

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
    logger.info(f"Working directory: {git_working_directory}")
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
    # log_path = git_working_directory / "logs" / "language_detection.log"
    log_path = git_working_directory / "logs" / "file_metrics_extraction.log"
    logger.add(log_path, rotation='1 day', level="INFO")

    try:
        # logger.info("Starting language detection processed (based on file "
        #             "extensions)")
        logger.info("Starting file metrics extraction process")
        supabase = setup()
        # detect_language(supabase)
        process_repositories_for_metrics(supabase)
        logger.info("Completed file metrics extraction process")
        # logger.info("Finished language detection processed (based on file "
        #             "extensions)")
    except Exception as e:
        # logger.error(f"Error in main process: {e}")
        logger.error(f"Error in main metrics extraction process: {e}")

if __name__ == "__main__":
    main()

