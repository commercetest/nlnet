import pytest
from utils.initial_data_preparation import mark_incomplete_urls, get_base_repo_url
import pandas as pd


def test_get_base_repo_url():
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
            ],
            "duplicate_flag": [False] * 23,
            "unsupported_url_scheme": [False] * 23,
            "incomplete_url_flag": [False] * 23,
        }
    )
    data.loc[10:11, "unsupported_url_scheme"] = True  # Invalid URL formats

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
    ]

    # Checking results
    for expected, actual in zip(expected_urls, result_df["base_repo_url"].tolist()):
        # Check if both values are missing values
        if pd.isna(expected) and pd.isna(actual):
            continue  # This treats both None and nan as equivalent for the
            # purpose of the test
        assert expected == actual, f"Expected {expected}, got {actual}"


@pytest.mark.parametrize(
    "data, expected_length, expected_urls",
    [
        # Test with an empty DataFrame
        ({"repourl": []}, 0, []),
        # DataFrame with various types of URLs including None and empty strings
        (
            {
                "repourl": [
                    "https://github.com/owner/repo",
                    None,
                    "https://github.com/owner",
                    "",
                ]
            },
            1,
            ["https://github.com/owner/repo"],
        ),
        # All valid URLs
        (
            {
                "repourl": [
                    "https://github.com/owner1/repo",
                    "https://github.com/owner2/repo2",
                ]
            },
            2,
            ["https://github.com/owner1/repo", "https://github.com/owner2/repo2"],
        ),
        # All incomplete URLs
        ({"repourl": ["https://github.com/owner", "https://github.com"]}, 0, []),
        # Mixed completeness in URLs
        (
            {"repourl": ["https://github.com/owner/repo", "https://github.com/owner"]},
            1,
            ["https://github.com/owner/repo"],
        ),
    ],
)
def test_filter_incomplete_urls(data, expected_length, expected_urls):
    df = pd.DataFrame(data)
    result = mark_incomplete_urls(df)
    assert len(result) == expected_length, (
        "The number of returned rows does not match " "the expected value."
    )
    for url in expected_urls:
        assert url in result["repourl"].values, f"{url} should be in the " f"result set"


@pytest.mark.parametrize(
    "data, expected_length",
    [
        # Testing different data types
        (
            {
                "repourl": [
                    None,
                    "https://github.com/owner/repo",
                    12345,
                    987.654,
                    True,
                    pd.Timestamp("20230101"),
                ]
            },
            1,
        ),
        # Test with all entries being non-string types
        ({"repourl": [12345, 67890, False, pd.Timestamp("20240101"), 987.654]}, 0),
        # Test with mixed valid URLs and non-string types
        (
            {
                "repourl": [
                    "https://github.com/owner/repo",
                    "https://github.com/owner/repo2",
                    12345,
                    "",
                ]
            },
            2,
        ),
    ],
)
def test_filter_urls_with_various_data_types(data, expected_length):
    df = pd.DataFrame(data)
    result = mark_incomplete_urls(df)
    assert len(result) == expected_length, (
        "The number of returned rows does " "not match the expected value."
    )
    if expected_length > 0:
        for url in result["repourl"]:
            assert isinstance(url, str), (
                "All returned 'repourl' values should " "be strings."
            )


@pytest.mark.parametrize(
    "url, is_valid",
    [
        # Properly formatted URL with a query string, follows the correct
        # structure for HTTP URLs including parameters.
        ("https://example.com/over/there?name=ferret", True),
        # Single quotes are unsafe and should be encoded; Potentially
        # problematic or unsafe
        ("http://example.com/special'chars", False),
        # Angle brackets are invalid in URLs unless encoded because they could
        # be misinterpreted as HTML tags, so this is False. Invalid characters
        # in domain
        ("http://<notvalid>.com", False),
        # Not a HTTP/HTTPS URL
        ("ftp://example.com/resource", False),
        # Contains an unencoded space, which can cause issues in URL parsing
        # and is generally not secure or standard, resulting in False.
        ("https://example.com/sub dir", False),
        # Includes unencoded double quotes, which are unsafe and should be
        # encoded in URLs to prevent breaking out of URL contexts in HTML or
        # JavaScript, therefore False.
        ('https://example.com/"quotes"', False),  # Quotes not encoded
    ],
)
def test_url_with_special_characters(url, is_valid):
    df = pd.DataFrame({"repourl": [url]})
    result = mark_incomplete_urls(df)
    assert (len(result) == 1) == is_valid, f"URL '{url}' validation failed."


@pytest.mark.parametrize(
    "data, expected_exception",
    [
        # Expect a ValueError for DataFrame without the 'repourl' column
        ({"other_column": ["data1", "data2"]}, ValueError),
    ],
)
def test_filter_incomplete_urls_exceptions(data, expected_exception):
    df = pd.DataFrame(data)
    with pytest.raises(expected_exception):
        mark_incomplete_urls(df)
