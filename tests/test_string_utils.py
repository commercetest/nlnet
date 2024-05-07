import pytest
from utils.string_utils import sanitise_directory_name


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("example_directory", "example_directory"),
        ("example directory", "example_directory"),
        ("example_directory@2024!", "example_directory_2024_"),
        ("example.directory.com", "example_directory_com"),
        ("", ""),
        ("@#$%^&*()!", "__________"),
        ("123@#$", "123___"),
        ("well-named-directory", "well-named-directory"),
        ("!directory-name!", "_directory-name_"),
    ],
)
def test_sanitise_directory_name(input_str, expected):
    assert (
        sanitise_directory_name(input_str) == expected
    ), f"Failed for input: {input_str}"


# To handle non-string inputs and ensure the function raises an error:
def test_sanitise_non_string_input():
    with pytest.raises(TypeError):
        sanitise_directory_name(123)
