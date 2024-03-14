from pathlib import Path

def git_codebase_root(path):
    """
    Find repository root from the path's parents.

    Returns the path if found, else None.
    
    Source of the underlying method is https://stackoverflow.com/a/67516092/340175
    The code has been tested interactively.
    """
    for path in Path(path).parents:
        # Check whether "path/.git" exists and is a directory
        git_dir = path / ".git"
        if git_dir.is_dir():
            return path
