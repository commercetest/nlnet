import unittest
import pandas as pd
from hamcrest import assert_that, equal_to, is_, contains_string, not_
from utils.initial_data_preparation import (
    get_domain,
    is_complete_url,
    extract_url,
    convert_http_to_https,
)


# Tests for the function `get_domain(df)`
class TestGetDomain(unittest.TestCase):
    def test_with_supported_schemes(self):
        # Test with supported schemes and expect the correct domain
        urls_with_expected_domains = [
            ("http://example.com", "example.com"),
            ("https://www.example.com", "www.example.com"),
            ("git://github.com/user/repo.git", "github.com"),
        ]

        for url, expected in urls_with_expected_domains:
            with self.subTest(url=url):
                result = get_domain(url)
                assert_that(result, is_(equal_to(expected)), f"Failed for URL: {url}")

    def test_with_unsupported_schemes(self):
        # Test with unsupported schemes and expect None
        urls_with_unsupported_schemes = [
            "ftp://example.com",
            "file:///tmp/test",
            "mailto:user@example.com",
        ]

        for url in urls_with_unsupported_schemes:
            with self.subTest(url=url):
                result = get_domain(url)
                assert_that(result, is_(None), f"Failed for URL: {url}")

    def test_with_malformed_urls(self):
        malformed_urls = ["", "http:///example.com", None]
        for url in malformed_urls:
            with self.subTest(url=url):
                result = get_domain(url)
                assert_that(result, is_(equal_to(None)), f"Failed for URL: {url}")


# Tests for the function `is_complete_url`
EXPECTED_URL_PARTS = 5


class TestIsCompleteURL(unittest.TestCase):
    def test_complete_urls(self):
        # Test with a URL that meets the expected part count
        url = "https://github.com/owner/repo"
        assert_that(is_complete_url(url), is_(True))

    def test_incomplete_urls(self):
        # Test with URLs that do not meet the expected part count
        incomplete_urls = [
            "https://github.com/owner",  # Only 4 parts
            "http://github.com",  # Only 3 parts
            "github.com/owner/repo",
        ]  # Only 3 parts

        for url in incomplete_urls:
            with self.subTest(url=url):
                assert_that(is_complete_url(url), is_(False))

    def test_non_string_input(self):
        # Test with non-string inputs. Expect the result to be False
        non_strings = [123, None, [], {}]
        for non_string in non_strings:
            with self.subTest(input=non_string):
                assert_that(is_complete_url(non_string), is_(False))

    def test_with_edge_cases(self):
        # Test with an empty string
        assert_that(is_complete_url(""), is_(False))


# Tests for the function `extract_url`
class TestExtractURL(unittest.TestCase):
    def test_empty_input(self):
        result, flag = extract_url("")
        assert_that(result, is_(None))
        assert_that(flag, is_(True))

        result, flag = extract_url(None)
        assert_that(result, is_(None))
        assert_that(flag, is_(True))

    def direct_path_platforms(self):
        # Test URLs from specific platforms that require using the
        # complete path without any truncation
        direct_path_urls = [
            "https://framagit.org/incommon.cc",
            "https://gitlab.com/technostructures/kazarma/kazarma",
            "https://git.taler.net/taler-ios.git",
        ]
        for url in direct_path_urls:
            with self.subTest(url=url):
                result, flag = extract_url(url)
                assert_that(result, equal_to(url))
                assert_that(flag, is_(False))

    def test_standard_path_slicing(self):
        # Test standard URL handling
        result, flag = extract_url("https://github.com/user/project")
        assert_that(result, is_("https://github.com/user/project"))
        assert_that(flag, is_(False))

        result, flag = extract_url("https://example.com/deeply/nested/path")
        assert_that(result, is_("https://example.com/deeply/nested"))
        assert_that(flag, is_(False))

    def test_insufficient_path_parts(self):
        # Test URLs with insufficient path parts
        result, flag = extract_url("https://example.com/")
        assert_that(result, is_(None))
        assert_that(flag, is_(True))

        result, flag = extract_url("https://justadomain.com")
        assert_that(result, is_(None))
        assert_that(flag, is_(True))


# Tests for the function `convert_http_to_https`
class TestConvertHttpToHttps(unittest.TestCase):
    def test_basic_conversion(self):
        # Create a DataFrame with HTTP URLs
        df = pd.DataFrame({"repourl": ["http://example.com", "http://example.org"]})
        convert_http_to_https(df)
        # Check all URLs are converted to HTTPS
        for url in df["repourl"]:
            assert_that(url, contains_string("https://"))

    def test_already_https(self):
        # Create a DataFrame with HTTPS URLs
        df = pd.DataFrame({"repourl": ["https://example.com", "https://example.org"]})
        convert_http_to_https(df)
        # Check that no URLs contain "http://"
        for url in df["repourl"]:
            assert_that(url, not_(contains_string("http://")))

    def test_missing_repourl_column(self):
        # Create a DataFrame without the 'repourl' column
        df = pd.DataFrame({"other_column": ["value1", "value2"]})
        # Test that the function raises a ValueError when 'repourl' is missing
        with self.assertRaises(ValueError):
            convert_http_to_https(df)

    def test_non_http_urls(self):
        # Create a DataFrame with non-HTTP URLs
        df = pd.DataFrame({"repourl": ["ftp://example.com", "telnet://example.org"]})
        original_urls = df["repourl"].tolist()  # Store original URLs to
        # compare later
        convert_http_to_https(df)
        # Check URLs remain unchanged
        for original, modified in zip(original_urls, df["repourl"]):
            self.assertEqual(original, modified)
        convert_http_to_https(df)

    def test_empty_dataframe(self):
        # Create an empty DataFrame with the 'repourl' column
        df = pd.DataFrame({"repourl": pd.Series(dtype=str)})
        convert_http_to_https(df)
        # Check DataFrame remains empty
        self.assertTrue(df.empty)  # Directly using assertTrue to check if the
        # DataFrame is empty
