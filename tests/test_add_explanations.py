import pandas as pd
import pytest
from src.github_repo_request_local import add_explanations


def test_add_explanations_empty_df():
    """Test the add_explanations function with an empty DataFrame."""
    df = pd.DataFrame()
    result = add_explanations(df)
    assert result.empty and "explanation" in result.columns, (
        "Should handle " "empty DataFrame " "by adding an " "explanation " "column."
    )


# Define a test function that takes multiple parameters
@pytest.mark.parametrize(
    "data, expected",
    [
        (
            {
                "duplicate_flag": False,
                "null_value_flag": True,
                "base_repo_url_flag": False,
                "incomplete_url_flag": True,
                "repourl": "http://example.com",
                "domain_extraction_flag": False,
                "testfilecountlocal": -1,
                "clone_status": "failed",
                "last_commit_hash": None,
            },
            "Row contains null values.",
        ),
        (
            {
                "duplicate_flag": True,
                "null_value_flag": False,
                "base_repo_url_flag": True,
                "incomplete_url_flag": False,
                "repourl": "http://incomplete",
                "domain_extraction_flag": True,
                "testfilecountlocal": 0,
                "clone_status": None,
                "last_commit_hash": "abc123",
            },
            "Row is marked as a duplicate of another entry.",
        ),
        # All flags false
        (
            {
                "duplicate_flag": False,
                "null_value_flag": False,
                "base_repo_url_flag": False,
                "incomplete_url_flag": False,
                "repourl": "http://complete.com",
                "domain_extraction_flag": False,
                "testfilecountlocal": 10,
                "clone_status": "successful",
                "last_commit_hash": "def456",
            },
            "No issues detected.",
        ),
        (
            {
                "duplicate_flag": False,
                "null_value_flag": False,
                "base_repo_url_flag": None,
                "incomplete_url_flag": False,
                "repourl": "http://complete.com/oener/repo",
                "domain_extraction_flag": False,
                "testfilecountlocal": -1,
                "clone_status": None,
                "last_commit_hash": None,
            },
            "Clone status unknown.",
        ),
    ],
)
def test_add_explanations_with_flags(data, expected):
    """Test with various flags set to ensure explanations are added
    correctly."""
    df = pd.DataFrame([data])
    result = add_explanations(df)
    assert result.loc[0, "explanation"] == expected, (
        "Explanation does not " "match expected output."
    )
