import pytest
from src.github_repo_request_local import get_base_repo_url, filter_incomplete_urls
import pandas as pd


def test_get_base_repo_url():
    # Empty or null input
    assert get_base_repo_url("") is None
    assert get_base_repo_url(None) is None

    # Valid URLs
    assert (
        get_base_repo_url("https://github.com/getdnsapi/stubby")
        == "https://github.com/getdnsapi/stubby"
    )

    assert get_base_repo_url("https://github.com/namecoin") is None

    assert (
        get_base_repo_url("https://github.com/osresearch/heads/issues/540")
        == "https://github.com/osresearch/heads"
    )

    # URLs from other code hosting platforms
    assert (
        get_base_repo_url("https://git.sr.ht/~dvn/boxen")
        == "https://git.sr.ht/~dvn/boxen"
    )

    assert (
        get_base_repo_url(
            "https://redmine.replicant.us/projects/replicant"
            "/wiki/Tasks_funding#Graphics-acceleration"
        )
        == "https://redmine.replicant.us/projects/replicant"
    )

    # Checking the `repourls` which ends with `.git`
    assert (
        get_base_repo_url("https://github.com/stalwartlabs/mail-server.git")
        == "https://github.com/stalwartlabs/mail-server"
    )

    assert (
        get_base_repo_url("https://github.com/tdf/odftoolkit.git")
        == "https://github.com/tdf/odftoolkit"
    )

    # Invalid URL formats
    assert get_base_repo_url("just-a-string") is None
    assert get_base_repo_url("http:///a-bad-url.com") is None

    # URLs with query parameters or fragments
    assert (
        get_base_repo_url("https://github.com/getdnsapi/stubby.git#readme")
        == "https://github.com/getdnsapi/stubby"
    )

    assert (
        get_base_repo_url("https://github.com/getdnsapi/stubby.git?branch=main")
        == "https://github.com/getdnsapi/stubby"
    )


@pytest.mark.parametrize(
    "data, expected_length, expected_urls",
    [
        # Test with an empty DataFrame
        ({"repourl": []}, 0, []),
        # DataFrame without the 'repourl' column
        ({"other_column": ["data1", "data2"]}, 2, []),
        # DataFrame with various types of URLs including None and empty strings
        (
            {
                "repourl": [
                    "https://github.com/user/repo",
                    None,
                    "https://github.com/user",
                    "",
                ]
            },
            1,
            ["https://github.com/user/repo"],
        ),
        # All valid URLs
        (
            {
                "repourl": [
                    "https://github.com/user/repo",
                    "https://github.com/user2/repo2",
                ]
            },
            2,
            ["https://github.com/user/repo", "https://github.com/user2/repo2"],
        ),
        # All incomplete URLs
        ({"repourl": ["https://github.com/user", "https://github.com"]}, 0, []),
        # Mixed completeness in URLs
        (
            {"repourl": ["https://github.com/user/repo", "https://github.com/user"]},
            1,
            ["https://github.com/user/repo"],
        ),
    ],
)
def test_filter_incomplete_urls(data, expected_length, expected_urls):
    df = pd.DataFrame(data)
    result = filter_incomplete_urls(df)
    assert len(result) == expected_length, (
        "The number of returned rows does not match " "the expected value."
    )
    for url in expected_urls:
        assert url in result["repourl"].values, f"{url} should be in the result set."
