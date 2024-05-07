import re


def sanitise_directory_name(name):
    """Sanitise the directory name by removing or replacing non-alphanumeric
    characters."""
    # Replace periods and other non-alphanumeric characters with an underscore
    # This regex replaces all non-alphanumeric, non-hyphen characters with an
    # underscore
    sanitised_name = re.sub(r"[^\w-]", "_", name)
    return sanitised_name
