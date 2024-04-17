from src.github_repo_request_local import get_base_repo_url


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
