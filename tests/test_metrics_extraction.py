import pytest
from pathlib import Path
import ast
from src.DS.metrics_extraction import (
    MetricsCollector,
    read_and_parse_file,
    process_files_parallel,
)


# Fixtures
@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file with known content."""
    file_content = """
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42
        
    def test_something(self):
        assert self.value == 42
        if self.value > 0:
            assert True
            
    def test_another(self):
        assert True
        
    def tearDown(self):
        self.value = None
"""
    test_file = tmp_path / "test_example.py"
    test_file.write_text(file_content)
    return test_file


@pytest.fixture
def metrics_collector():
    """Create a MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def complex_test_file(tmp_path):
    """Create a test file with more complex test patterns."""
    file_content = """
import pytest
import unittest

class TestComplex(unittest.TestCase):
    def setUp(self):
        self.data = [1, 2, 3]
        
    def test_nested_conditions(self):
        for item in self.data:
            if item > 1:
                if item > 2:
                    assert item == 3
                else:
                    assert item == 2
            else:
                assert item == 1
                
    def test_multiple_assertions(self):
        assert len(self.data) == 3
        assert sum(self.data) == 6
        assert max(self.data) == 3
        
    def tearDown(self):
        self.data = None
"""
    test_file = tmp_path / "test_complex.py"
    test_file.write_text(file_content)
    return test_file


# Basic Functionality Tests
def test_read_and_parse_file(temp_test_file):
    """Test file parsing functionality."""
    result = read_and_parse_file(temp_test_file)
    assert result is not None
    tree, content = result
    assert isinstance(tree, ast.AST)
    assert isinstance(content, str)
    assert "class TestExample" in content


def test_read_and_parse_file_nonexistent():
    """Test handling of nonexistent files."""
    result = read_and_parse_file(Path("nonexistent.py"))
    assert result is None


def test_metrics_collector_analyse_test_file(metrics_collector, temp_test_file):
    """Test analysis of a test file."""
    result = metrics_collector.analyse_test_file(temp_test_file)

    assert result["num_test_cases"] == 2
    assert result["num_assertions"] == 3
    assert result["has_setup"] is True
    assert result["has_teardown"] is True
    assert result["complexity"] == 3  # 2 test functions + 1 if statement


def test_complex_test_analysis(metrics_collector, complex_test_file):
    """Test analysis of complex test patterns."""
    result = metrics_collector.analyse_test_file(complex_test_file)

    assert result["num_test_cases"] == 2
    assert result["num_assertions"] == 6  # Total assertions across all tests
    assert result["has_setup"] is True
    assert result["has_teardown"] is True
    assert result["complexity"] >= 5  # Base complexity + nested conditions


# Caching Tests
def test_metrics_collector_caching(metrics_collector, temp_test_file):
    """Test that caching works correctly."""
    # First call
    result1 = metrics_collector.analyse_test_file(temp_test_file)

    # Second call should use cache
    result2 = metrics_collector.analyse_test_file(temp_test_file)

    assert result1 == result2
    assert metrics_collector._get_file_hash.cache_info().hits == 1


def test_cache_invalidation(metrics_collector, tmp_path):
    """Test cache invalidation when file content changes."""
    test_file = tmp_path / "changing_test.py"

    # First version of file
    test_file.write_text("def test_one(): assert True")
    result1 = metrics_collector.analyse_test_file(test_file)

    # Modified version of file
    test_file.write_text("def test_one(): assert True\ndef test_two(): assert False")
    result2 = metrics_collector.analyse_test_file(test_file)

    assert result1 != result2
    assert result2["num_test_cases"] == 2


# Parallel Processing Tests
def test_parallel_processing(tmp_path):
    """Test parallel processing of multiple files."""
    files = []
    for i in range(3):
        file_content = f"""
def test_func_{i}():
    assert True
"""
        test_file = tmp_path / f"test_{i}.py"
        test_file.write_text(file_content)
        files.append(test_file)

    results = process_files_parallel(files, num_workers=2)

    assert len(results) == 3
    for result in results:
        assert result["num_test_cases"] == 1
        assert result["num_assertions"] == 1


def test_parallel_processing_with_errors(tmp_path):
    """Test parallel processing with some invalid files."""
    files = [
        (tmp_path / "valid.py", "def test_valid(): assert True"),
        (tmp_path / "invalid.py", "def invalid_syntax:"),
        (tmp_path / "another_valid.py", "def test_another(): assert False"),
    ]

    for file_path, content in files:
        file_path.write_text(content)

    results = process_files_parallel([f[0] for f in files], num_workers=2)
    assert len(results) == 3  # Should still get 3 results

    # Check that valid files were processed correctly
    valid_results = [r for r in results if r["num_test_cases"] > 0]
    assert len(valid_results) == 2


# Error Handling Tests
def test_metrics_collector_error_handling(metrics_collector, tmp_path):
    """Test handling of invalid Python files."""
    invalid_file = tmp_path / "invalid.py"
    invalid_file.write_text("def invalid_syntax:")

    result = metrics_collector.analyse_test_file(invalid_file)

    assert result["num_test_cases"] == 0
    assert result["num_assertions"] == 0
    assert result["complexity"] == 0


def test_non_test_file_analysis(metrics_collector, tmp_path):
    """Test analysis of non-test Python file."""
    regular_file = tmp_path / "regular.py"
    regular_file.write_text("""
def regular_function():
    pass
""")

    result = metrics_collector.analyse_test_file(regular_file)
    assert result["num_test_cases"] == 0
    assert not result["has_setup"]
    assert not result["has_teardown"]


# Parameterized Tests
@pytest.mark.parametrize(
    "file_content,expected_metrics",
    [
        (
            """
def test_simple():
    assert True
""",
            {"num_test_cases": 1, "num_assertions": 1, "complexity": 1},
        ),
        (
            """
def test_complex():
    if True:
        assert True
    else:
        assert False
""",
            {"num_test_cases": 1, "num_assertions": 2, "complexity": 2},
        ),
        (
            """
class TestClass:
    def test_method(self):
        assert True
    def test_another(self):
        assert False
""",
            {"num_test_cases": 2, "num_assertions": 2, "complexity": 2},
        ),
    ],
)
def test_various_test_patterns(
    metrics_collector, tmp_path, file_content, expected_metrics
):
    """Test analysis of various test patterns."""
    test_file = tmp_path / "parameterized_test.py"
    test_file.write_text(file_content)

    result = metrics_collector.analyse_test_file(test_file)

    for metric, expected in expected_metrics.items():
        assert result[metric] == expected


import pytest
import time
from pathlib import Path
import ast
from src.DS.metrics_extraction import (
    MetricsCollector,
    read_and_parse_file,
    process_files_parallel
)

@pytest.fixture
def sample_repo(tmp_path):
    """Create a sample repository structure with test files."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    
    test_files = {
        "test_basic.py": """
def test_simple():
    assert True
""",
        "test_complex.py": """
import unittest

class TestComplex(unittest.TestCase):
    def setUp(self):
        self.value = 42
        
    def test_value(self):
        assert self.value == 42
        if self.value > 0:
            assert True
            
    def tearDown(self):
        self.value = None
""",
        "not_a_test.py": """
def regular_function():
    pass
"""
    }
    
    for filename, content in test_files.items():
        (repo_dir / filename).write_text(content)
    
    return repo_dir

@pytest.fixture
def metrics_collector():
    """Create a MetricsCollector instance with caching enabled."""
    return MetricsCollector(enable_caching=True)

def test_batch_processing(sample_repo, metrics_collector):
    """Test processing multiple files in a batch."""
    results = metrics_collector.process_directory(sample_repo)
    assert len(results) == 3
    
    # Check test file metrics
    test_files = [r for r in results if r["file_path"].name.startswith("test_")]
    assert len(test_files) == 2
    
    # Verify complex test file metrics
    complex_test = next(r for r in results if "complex" in r["file_path"].name)
    assert complex_test["num_test_cases"] == 1
    assert complex_test["has_setup"] is True
    assert complex_test["has_teardown"] is True

def test_cache_effectiveness(sample_repo, metrics_collector):
    """Test that caching improves performance on repeated analysis."""
    # First run
    start_time = time.time()
    first_results = metrics_collector.process_directory(sample_repo)
    first_duration = time.time() - start_time
    
    # Second run (should use cache)
    start_time = time.time()
    second_results = metrics_collector.process_directory(sample_repo)
    second_duration = time.time() - start_time
    
    # Cache should make second run faster
    assert second_duration < first_duration
    # Results should be identical
    assert first_results == second_results

def test_read_and_parse_file(sample_repo):
    """Test file parsing functionality."""
    test_file = sample_repo / "test_basic.py"
    result = read_and_parse_file(test_file)
    assert result is not None
    tree, content = result
    assert isinstance(tree, ast.AST)
    assert isinstance(content, str)
    assert "test_simple" in content

def test_error_handling(tmp_path):
    """Test handling of invalid files."""
    # Test non-existent file
    assert read_and_parse_file(tmp_path / "nonexistent.py") is None
    
    # Test invalid Python syntax
    invalid_file = tmp_path / "invalid.py"
    invalid_file.write_text("def invalid_syntax:")
    assert read_and_parse_file(invalid_file) is None

import pytest
from pathlib import Path
import ast
import time
import tempfile
import shutil
from src.DS.metrics_extraction import (
    MetricsCollector,
    read_and_parse_file,
    process_files_parallel
)

@pytest.fixture
def sample_repo(tmp_path):
    """Create a sample repository structure with test files."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    
    # Create test files
    test_files = {
        "test_basic.py": """
def test_simple():
    assert True
""",
        "test_complex.py": """
import unittest

class TestComplex(unittest.TestCase):
    def setUp(self):
        self.value = 42
        
    def test_value(self):
        assert self.value == 42
        if self.value > 0:
            assert True
            
    def tearDown(self):
        self.value = None
""",
        "not_a_test.py": """
def regular_function():
    pass
"""
    }
    
    for filename, content in test_files.items():
        (repo_dir / filename).write_text(content)
    
    return repo_dir

@pytest.fixture
def metrics_collector():
    """Create a MetricsCollector instance with caching enabled."""
    return MetricsCollector(enable_caching=True)

def test_batch_processing(sample_repo, metrics_collector):
    """Test processing multiple files in a batch."""
    results = metrics_collector.process_directory(sample_repo)
    assert len(results) == 3
    
    # Check test file metrics
    test_files = [r for r in results if r["file_path"].name.startswith("test_")]
    assert len(test_files) == 2
    
    # Verify complex test file metrics
    complex_test = next(r for r in results if "complex" in r["file_path"].name)
    assert complex_test["num_test_cases"] == 1
    assert complex_test["has_setup"] is True
    assert complex_test["has_teardown"] is True

def test_cache_effectiveness(sample_repo, metrics_collector):
    """Test that caching improves performance on repeated analysis."""
    # First run
    start_time = time.time()
    first_results = metrics_collector.process_directory(sample_repo)
    first_duration = time.time() - start_time
    
    # Second run (should use cache)
    start_time = time.time()
    second_results = metrics_collector.process_directory(sample_repo)
    second_duration = time.time() - start_time
    
    # Cache should make second run faster
    assert second_duration < first_duration
    # Results should be identical
    assert first_results == second_results