"""
Test framework detection script.
Analyses repository files to detect various testing frameworks.
Top programming languages in repositories:
1. .php (18,536 files)
2. .go (15,705 files)
3. .js (14,516 files)
4. .ts (13,532 files)
5. .py (12,939 files)
6. .java (11,069 files)
7. .c (8,058 files)
8. .cpp (7,893 files)
9. .rs (7,781 files)
10. .kt (4,978 files)
11. .rb (4,292 files)
"""

import os
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Set
import subprocess
from tqdm import tqdm
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger

from utils.git_utils import get_working_directory_or_git_root


BATCH_SIZE = 50

# Configuration
EXCLUDE_EXTENSIONS = {
    # Images
    '.png', '.svg', '.jpg', '.gif', '.webp',
    # Fonts
    '.woff', '.woff2', '.eot', '.ttf', '.otf',
    # Documents
    '.pdf', '.odt', '.txt', '.md', '.rst', '.mdx',
    # Binary/Compiled
    '.pack', '.tar', '.lib', '.bcmap',
    # Other assets
    '.css', '.scss', '.less',
    # Generated files
    '.map', '.lock', '.sample',
    # Data files
    '.po', '.graphml', '.pbf'
}

FRAMEWORK_PATTERNS = {
    # High Priority (>10K files)
    "phpunit": {
        "dependency_patterns": ["phpunit/phpunit"],
        "config_files": ["phpunit.xml", "phpunit.xml.dist"],
        "file_patterns": ["Test.php", "TestCase.php"],
        "content_patterns": ["extends TestCase", "extends PHPUnit", "@test"]
    },
    "go_test": {
        "dependency_patterns": ["testing"],
        "config_files": [],
        "file_patterns": ["_test.go"],
        "content_patterns": ["func Test", "t *testing.T"]
    },
    "jest": {
        "dependency_patterns": ["jest", "@types/jest"],
        "config_files": ["jest.config.js", "jest.config.ts"],
        "file_patterns": [".test.js", ".test.ts", ".spec.js", ".spec.ts"],
        "content_patterns": ["describe(", "test(", "it(", "expect("]
    },
    "mocha": {
        "dependency_patterns": ["mocha"],
        "config_files": [".mocharc", "mocha.opts"],
        "file_patterns": [".test.js", ".spec.js"],
        "content_patterns": ["describe(", "it(", "beforeEach("]
    },
    "pytest": {
        "dependency_patterns": ["pytest"],
        "config_files": ["pytest.ini", "conftest.py"],
        "file_patterns": ["test_*.py", "*_test.py"],
        "content_patterns": ["import pytest", "@pytest", "def test_"]
    },
    "unittest": {
        "dependency_patterns": [],  # Part of Python standard library
        "config_files": [],
        "file_patterns": ["test_*.py", "*_test.py"],
        "content_patterns": ["import unittest", "unittest.TestCase",
                             "def test_"]
    },
    "junit": {
        "dependency_patterns": ["junit", "org.junit.jupiter"],
        "config_files": ["pom.xml", "build.gradle"],
        "file_patterns": ["*Test.java", "*Tests.java"],
        "content_patterns": ["@Test", "extends TestCase", "org.junit"]
    },

    # Second Priority (>5K files)
    "gtest": {
        "dependency_patterns": ["gtest", "googletest"],
        "config_files": ["CMakeLists.txt"],
        "file_patterns": ["_test.cpp", "_test.cc", "test_.cpp", "test_.cc"],
        "content_patterns": ["TEST(", "TEST_F(", "#include <gtest/gtest.h>"]
    },
    "catch2": {
        "dependency_patterns": ["catch2"],
        "config_files": ["CMakeLists.txt"],
        "file_patterns": ["_test.cpp", "_test.cc", "test_.cpp", "test_.cc"],
        "content_patterns": ["#include <catch2/catch.hpp>", "SCENARIO(",
                             "TEST_CASE("]
    },
    "rust_test": {
        "dependency_patterns": ["test"],
        "config_files": [],
        "file_patterns": ["_test.rs"],
        "content_patterns": ["#[test]", "use test;"]
    },
    "kotlin_test": {
        "dependency_patterns": ["org.jetbrains.kotlin:kotlin-test"],
        "config_files": ["build.gradle", "build.gradle.kts"],
        "file_patterns": ["*Test.kt", "*Tests.kt"],
        "content_patterns": ["@Test", "assertThat", "kotlin.test"]
    }
}

def setup():
    """Initialise Supabase client and logging."""
    load_dotenv()
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def get_unprocessed_files(supabase, page_start: int = 0) -> list:
    """Get a batch of unprocessed files."""
    try:
        response = supabase.table('cloned_files')\
            .select('id, repository_id, file_path, file_extension')\
            .is_('framework_detection_processed_at', 'null')\
            .range(page_start, page_start + BATCH_SIZE - 1)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching files batch starting at {page_start}: {e}")
        return []


def get_total_unprocessed_count(supabase) -> int:
    """Get total count of unprocessed files."""
    try:
        response = supabase.table('cloned_files')\
            .select('id', count='exact')\
            .is_('framework_detection_processed_at', 'null')\
            .execute()
        return response.count
    except Exception as e:
        logger.error(f"Error getting total count: {e}")
        return 0


def check_file_content(file_path: Path, patterns: List[str]) -> bool:
    """Check if file contains any of the patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return any(pattern in content for pattern in patterns)
    except Exception as e:
        logger.warning(f"Error reading file {file_path}: {e}")
        return False


def check_dependency_files(repo_path: Path, framework_patterns: Dict) -> Set[
    str]:
    """Check dependency files for framework patterns across different ecosystems."""
    detected_frameworks = set()

    # PHP - composer.json
    composer_json = repo_path / 'composer.json'
    if composer_json.exists():
        try:
            with open(composer_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_deps = {
                    **data.get('require', {}),
                    **data.get('require-dev', {})
                }
                for framework, patterns in framework_patterns.items():
                    if any(dep in all_deps for dep in
                           patterns['dependency_patterns']):
                        detected_frameworks.add(framework)
        except Exception as e:
            logger.warning(f"Error parsing composer.json in {repo_path}: {e}")

    # Go - go.mod
    go_mod = repo_path / 'go.mod'
    if go_mod.exists():
        try:
            with open(go_mod, 'r', encoding='utf-8') as f:
                content = f.read()
                for framework, patterns in framework_patterns.items():
                    if any(dep in content for dep in
                           patterns['dependency_patterns']):
                        detected_frameworks.add(framework)
        except Exception as e:
            logger.warning(f"Error parsing go.mod in {repo_path}: {e}")

    # JavaScript/TypeScript - package.json
    package_json = repo_path / 'package.json'
    if package_json.exists():
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_deps = {
                    **data.get('dependencies', {}),
                    **data.get('devDependencies', {})
                }
                for framework, patterns in framework_patterns.items():
                    if any(dep in all_deps for dep in
                           patterns['dependency_patterns']):
                        detected_frameworks.add(framework)
        except Exception as e:
            logger.warning(f"Error parsing package.json in {repo_path}: {e}")

    # Python - requirements.txt, setup.py, pyproject.toml
    python_files = ['requirements.txt', 'setup.py', 'pyproject.toml']
    for py_file in python_files:
        file_path = repo_path / py_file
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for framework, patterns in framework_patterns.items():
                        if any(dep in content for dep in
                               patterns['dependency_patterns']):
                            detected_frameworks.add(framework)
            except Exception as e:
                logger.warning(f"Error parsing {py_file} in {repo_path}: {e}")

    # Java/Kotlin - pom.xml, build.gradle
    java_files = ['pom.xml', 'build.gradle', 'build.gradle.kts']
    for java_file in java_files:
        file_path = repo_path / java_file
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for framework, patterns in framework_patterns.items():
                        if any(dep in content for dep in
                               patterns['dependency_patterns']):
                            detected_frameworks.add(framework)
            except Exception as e:
                logger.warning(f"Error parsing {java_file} in {repo_path}: {e}")

    # C/C++ - CMakeLists.txt
    cmake_lists = repo_path / 'CMakeLists.txt'
    if cmake_lists.exists():
        try:
            with open(cmake_lists, 'r', encoding='utf-8') as f:
                content = f.read()
                for framework, patterns in framework_patterns.items():
                    if any(dep in content for dep in
                           patterns['dependency_patterns']):
                        detected_frameworks.add(framework)
        except Exception as e:
            logger.warning(f"Error parsing CMakeLists.txt in {repo_path}: {e}")

    # Rust - Cargo.toml
    cargo_toml = repo_path / 'Cargo.toml'
    if cargo_toml.exists():
        try:
            with open(cargo_toml, 'r', encoding='utf-8') as f:
                content = f.read()
                for framework, patterns in framework_patterns.items():
                    if any(dep in content for dep in
                           patterns['dependency_patterns']):
                        detected_frameworks.add(framework)
        except Exception as e:
            logger.warning(f"Error parsing Cargo.toml in {repo_path}: {e}")

    return detected_frameworks


def process_file(file_info: dict, repo_path: Path,
                 framework_patterns: Dict) -> dict:
    """Process a single file to detect test frameworks."""
    results = {
        'has_test_framework': False,
        'detected_frameworks': set(),
        'detection_methods': set()
    }

    file_path = repo_path / file_info['file_path']
    if not file_path.exists() or file_info[
        'file_extension'] in EXCLUDE_EXTENSIONS:
        return results

    # Check each framework's patterns
    for framework, patterns in framework_patterns.items():
        # Check file patterns
        if any(file_info['file_path'].endswith(pattern) for pattern in
               patterns['file_patterns']):
            results['detected_frameworks'].add(framework)
            results['detection_methods'].add('pattern')

        # Check file content
        if check_file_content(file_path, patterns['content_patterns']):
            results['detected_frameworks'].add(framework)
            results['detection_methods'].add('content')

    results['has_test_framework'] = len(results['detected_frameworks']) > 0
    return results


def update_database(supabase, file_id: str, detection_results: dict):
    """Update database with framework detection results."""
    update_data = {
        'has_test_framework': detection_results['has_test_framework'],
        'detected_test_framework': list(
            detection_results['detected_frameworks']),
        'framework_detected_by_pattern': 'pattern' in detection_results[
            'detection_methods'],
        'framework_detected_by_content': 'content' in detection_results[
            'detection_methods'],
        'framework_detection_processed_at': datetime.utcnow().isoformat()
    }

    # Update specific framework flags
    for framework in FRAMEWORK_PATTERNS.keys():
        update_data[f'{framework}_framework'] = framework in detection_results[
            'detected_frameworks']

    try:
        supabase.table('cloned_files') \
            .update(update_data) \
            .eq('id', file_id) \
            .execute()
        logger.info(f"Updated framework detection for file {file_id}")
    except Exception as e:
        logger.error(f"Error updating database for file {file_id}: {e}")


def process_repositories(supabase):
    """Process repositories in batches to avoid timeouts"""
    clone_directory = (get_working_directory_or_git_root() / "Data" /
                       "repos_cloned" / "repositories")

    # Get total count for progress bar
    total_files = get_total_unprocessed_count(supabase)
    if total_files == 0:
        logger.info("No files to process")
        return

    logger.info(f"Total files to process: {total_files}")

    # Create progress bar
    with tqdm(total=total_files, desc="Processing files") as pbar:
        processed_count = 0
        current_repo_id = None
        detected_deps = set()

        while processed_count < total_files:
            batch = get_unprocessed_files(supabase, processed_count)
            if not batch:
                logger.warning(
                    f"No files returned for batch starting at {processed_count}")
                break

            # Process files in the batch
            for file in batch:
                repo_id = file['repository_id']
                repo_path = clone_directory / repo_id

                # Check dependencies only when switching to a new repository
                if repo_id != current_repo_id:
                    current_repo_id = repo_id
                    if repo_path.exists():
                        detected_deps = check_dependency_files(repo_path,
                                                               FRAMEWORK_PATTERNS)
                    else:
                        logger.warning(
                            f"Repository path not found: {repo_path}")
                        detected_deps = set()

                if repo_path.exists():
                    # Process file
                    results = process_file(file, repo_path, FRAMEWORK_PATTERNS)

                    # Add dependency-detected frameworks
                    results['detected_frameworks'].update(detected_deps)
                    if detected_deps:
                        results['detection_methods'].add('dependency')

                    try:
                        update_database(supabase, file['id'], results)
                    except Exception as e:
                        logger.error(f"Error updating file {file['id']}: {e}")
                        continue

                pbar.update(1)
                processed_count += 1


def main():
    git_working_dir = get_working_directory_or_git_root()
    log_path = git_working_dir / "logs" / "test_framework_detection.log"
    logger.add(log_path, rotation="1 day", level="INFO")

    try:
        logger.info("Starting test framework detection process")
        supabase = setup()
        process_repositories(supabase)
        logger.info("Completed test framework detection process")
    except Exception as e:
        logger.error(f"Error in main process: {e}")


if __name__ == "__main__":
    main()