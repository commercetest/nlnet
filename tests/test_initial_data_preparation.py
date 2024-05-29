"""
This script contains a suite of tests for URL processing functions within a
data preparation utility.
These functions are designed to manage, validate, and transform repository URLs
from a dataset. Tests cover the following functionalities:

1. `get_base_repo_url`: Extracts the base repository URL from a more complex
URL structure.
2. `mark_incomplete_urls`: Flags URLs based on their completeness and the
presence of unsupported URL schemes.
3. `extract_and_flag_domains`: Extracts domains from URLs and flags unsupported
 URL schemes.

Each function uses Pytest for setting up test conditions and checking the
assertions.
"""

import pytest
import pandas as pd
from utils.initial_data_preparation import (
    mark_incomplete_urls,
    get_base_repo_url,
    extract_and_flag_domains,
)


def test_get_base_repo_url():
    """Verifies that the base repository URL is correctly extracted from a set
    of test URLs."""
    # Test data setup
    data = pd.DataFrame(
        {
            "repourl": [
                None,  # Test for None input
                "https://github.com/getdnsapi/stubby",
                "https://github.com/namecoin",
                "https://github.com/osresearch/heads/issues/540",
                "https://git.sr.ht/~dvn/boxen",
                "https://redmine.replicant.us/projects/replicant/wiki/"
                "Tasks_funding#Graphics-acceleration",
                "https://github.com/tdf/odftoolkit.git",
                "https://git.savannah.gnu.org/git/mes.git",
                "https://git.taler.net/git/libtalerutil.git",
                "https://git.taler.net/taler-ios.git",
                "just-a-string",
                "http:///a-bad-url.com",
                "https://github.com/getdnsapi/stubby.git#readme",
                "https://github.com/getdnsapi/stubby.git?branch=main",
                "https://gitlab.com/technostructures/kazarma/kazarma",
                "https://gitlab.torproject.org/tpo/network-heal",
                "https://codeberg.org/interpeer",
                "https://codeberg.org/openEngiadina/geopub",
                "https://codeberg.org/librEDA",
                "https://framagit.org/incommon.cc",
                "https://hydrillabugs.koszko.org/projects/haketilo/repository",
                "https://git.replicant.us/replicant",
                "https://gerrit.osmocom.org/plugins/gitiles/ims",
                "http://git.savannah.gnu.org/cgit/gnucap.git",
            ],
            "duplicate_flag": [False] * 24,
            "unsupported_url_scheme": [False] * 24,
            "incomplete_url_flag": [False] * 24,
        }
    )
    data.loc[10:11, "unsupported_url_scheme"] = True  # Invalid URL formats.
    # Align with the entries "just-a-string", and "http:///a-bad-url.com"

    # Run the function
    result_df = get_base_repo_url(data)

    # Expected results setup
    expected_urls = [
        None,  # None input
        "https://github.com/getdnsapi/stubby",
        None,  # URL leading to a user page, no specific repo
        "https://github.com/osresearch/heads",
        "https://git.sr.ht/~dvn/boxen",
        "https://redmine.replicant.us/projects/replicant",
        "https://github.com/tdf/odftoolkit.git",
        "https://git.savannah.gnu.org/git/mes.git",
        "https://git.taler.net/git/libtalerutil.git",
        "https://git.taler.net/taler-ios.git",
        None,  # Invalid format
        None,  # Invalid format
        "https://github.com/getdnsapi/stubby.git",
        "https://github.com/getdnsapi/stubby.git",
        "https://gitlab.com/technostructures/kazarma/kazarma",
        "https://gitlab.torproject.org/tpo/network-heal",
        "https://codeberg.org/interpeer",
        "https://codeberg.org/openEngiadina/geopub",
        "https://codeberg.org/librEDA",
        "https://framagit.org/incommon.cc",
        "https://hydrillabugs.koszko.org/projects/haketilo/repository",
        "https://git.replicant.us/replicant",
        "https://gerrit.osmocom.org/plugins/gitiles/ims",
        "http://git.savannah.gnu.org/cgit/gnucap.git",
    ]

    # Checking results
    for expected, actual in zip(expected_urls, result_df["base_repo_url"].tolist()):
        # Check if both values are missing values
        if pd.isna(expected) and pd.isna(actual):
            continue  # This treats both None and nan as equivalent for the
            # purpose of the test
        assert expected == actual, f"Expected {expected}, got {actual}"


#  Writing test cases for the function `mark_incomplete_urls`
def test_missing_repourl_column_raises_error():
    """Checks that a ValueError is raised if the 'repourl' column is missing."""
    # Create a DataFrame without the 'repourl' column
    data = {"some_other_column": ["https://github.com/owner/repo"]}
    df = pd.DataFrame(data)

    # Expect a ValueError to be raised due to the missing 'repourl' column
    with pytest.raises(ValueError) as exc_info:
        mark_incomplete_urls(df)

    # Check that the error message is as expected
    assert (
        str(exc_info.value) == "DataFrame must contain a 'repourl' column."
    ), "Error message does not match the expected output."


# A URL is considered complete (incomplete_url_flag would be False) if it
# contains at least five parts, including the protocol, an empty segment
# (for '//'),domain, and at least two path segments, e.g.,
# 'https://github.com/owner/repo'
@pytest.mark.parametrize(
    "data, expected_flags",
    [
        # DataFrame with various types of URLs including None and empty strings
        (
            {
                "repourl": [
                    # Expected to be flagged as complete(False) as it has all
                    # the required 5 parts
                    "https://github.com/owner/repo",
                    # Expected to be flagged as incomplete(True) as it has none
                    # of the required 5 parts
                    None,
                    # Expected to be flagged as incomplete(True) as it misses
                    # 1 part (repository name)
                    "https://github.com/owner",
                    # Expected to be flagged as incomplete(True) as it does not
                    # have all the required 5 parts
                    "",
                    # Expected to be flagged as incomplete(True) as it does not
                    # have the required 5 parts
                    12345,
                    # Expected to be flagged as incomplete(True) as it does not
                    # have the required 5 parts
                    987.654,
                    # Expected to be flagged as incomplete(True) as it does not
                    # have the required 5 parts
                    True,
                    pd.Timestamp("20230101"),
                    # Expected to be flagged as incomplete
                ],
                "duplicate_flag": [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                "unsupported_url_scheme": [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
            },
            [False, True, True, True, True, True, True, True],
        ),
        # All incomplete URLs
        (
            {
                "repourl": ["https://github.com/owner", "https://github.com"],
                "duplicate_flag": [False, False],
                "unsupported_url_scheme": [False, False],
            },
            [True, True],
        ),
        # Test with unsupported URL schemes
        (
            {
                "repourl": [
                    "ftp://github.com/owner/repo",
                    "https://github.com/owner/repo",
                ],
                "duplicate_flag": [False, False],
                "unsupported_url_scheme": [True, False],
            },
            [True, False],
        ),
    ],
)
def test_mark_incomplete_urls(data, expected_flags):
    df = pd.DataFrame(data)
    result = mark_incomplete_urls(df)
    assert (
        list(result["incomplete_url_flag"]) == expected_flags
    ), "The incomplete URL flags do not match expected results."


@pytest.mark.parametrize(
    "url, duplicate_flag, unsupported_url_scheme, expected_flag",
    [
        # Properly formatted URL with a query string, follows the complete
        # structure including parameters. The presence of a query does not
        # affect completeness.
        ("https://example.com/over/there?name=ferret", False, False, False),
        # URL contains special characters but still has the necessary parts.
        ("http://example.com/owner/special'chars", False, False, False),
        ("http://example.com/owner/repo<abcde>", False, True, True),
        # FTP URL; not HTTP/HTTPS but has the necessary structure for
        # completeness.
        ("ftp://example.com/owner/resource", False, True, True),
        # Contains an unencoded space, but still structured correctly.
        ("https://example.com/owner/sub dir", False, False, False),
        # Includes unencoded double quotes, but structured with necessary parts.
        ('https://example.com/owner/"quotes"', False, False, False),
    ],
)
def test_url_completeness_with_special_characters(
    url, duplicate_flag, unsupported_url_scheme, expected_flag
):
    """Tests URL completeness check with special characters and schemes."""
    df = pd.DataFrame(
        {
            "repourl": [url],
            "duplicate_flag": [duplicate_flag],
            "unsupported_url_scheme": [unsupported_url_scheme],
        }
    )
    result = mark_incomplete_urls(df)
    assert (
        result["incomplete_url_flag"].iloc[0] == expected_flag
    ), f"Completeness check for URL '{url}' failed."


@pytest.mark.parametrize(
    "data, expected_exception",
    [
        # Expect a ValueError for DataFrame without the 'repourl' column
        ({"other_column": ["data1", "data2"]}, ValueError),
    ],
)
def test_filter_incomplete_urls_exceptions(data, expected_exception):
    """Verifies that the correct exception is raised for dataframes lacking
    'repourl'."""
    df = pd.DataFrame(data)
    with pytest.raises(expected_exception):
        mark_incomplete_urls(df)


# Writing test cases for the function `extract_and_flag_domains`
@pytest.mark.parametrize(
    "data, expected_domains, expected_flags",
    [
        # Test with various supported and unsupported URL schemes
        (
            {
                "repourl": [
                    "https://github.com/openai",
                    "http://example.com",
                    "git://example.org/repo.git",
                    "ftp://example.net/resource",
                    "smb://fileserver/home",
                ],
                "duplicate_flag": [False, False, False, False, False],
            },
            [
                pd.NA if domain is None else domain
                for domain in ["github.com", "example.com", "example.org", None, None]
            ],
            [False, False, False, True, True],
        ),
        # Test with a mix of duplicate and non-duplicate entries
        (
            {
                "repourl": [
                    "https://github.com/ownwe/openai",
                    # ftp is not a list of accepted schemes ["http", "https",
                    # "git"]
                    "ftp://example.net/owner/resource",
                    "https://github.com/owner/openai",
                    "git://example.org/repo.git",
                ],
                "duplicate_flag": [False, False, True, False],
            },
            [
                pd.NA if domain is None else domain
                for domain in ["github.com", None, None, "example.org"]
            ],  # Expect None for the
            # duplicate as it's not processed
            [False, True, True, False],
            # Duplicates are ignored for processing
        ),
    ],
)
def test_extract_and_flag_domains(data, expected_domains, expected_flags):
    """Confirms that domain extraction and flagging for unsupported schemes are
    accurate."""
    df = pd.DataFrame(data)
    result = extract_and_flag_domains(df)
    pd.testing.assert_series_equal(
        result["repodomain"],
        pd.Series(expected_domains, dtype="object"),
        check_names=False,
    )
    assert (
        list(result["unsupported_url_scheme"]) == expected_flags
    ), "Unsupported URL scheme flagging failed."
