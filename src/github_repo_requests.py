import os
import time

from loguru import logger
import pandas as pd
from requests_ratelimiter import LimiterSession
from utils.git_utils import git_codebase_root


def load_data(filepath):
    try:
        df = pd.read_csv(filepath)
        logger.info(f"Dataframe shape: {df.shape}")
        logger.info(f"Dataframe columns: {df.columns.tolist()}")
        df.info()
        return df

    except Exception as e:
        logger.error(f"Error Loading data from path {filepath} with exception" f" {e}")
    return None


def extract_owner_and_repo_names(repourl):
    parts = repourl.split("/")
    logger.info(parts)

    # Not all repourls are correct, some point to just the user and others to
    # the issues page
    index_of_github = parts.index("github.com")
    if len(parts) <= index_of_github + 2:
        logger.warning(
            f"repopath: {repourl} Does not contain both the owner and repo names"
        )
        return ""

    repo_path = "/".join(parts[index_of_github + 1 : index_of_github + 3])
    return repo_path


def get_test_file_count(repo_path, headers):
    session = LimiterSession(per_minute=5)
    test_files = []
    page = 1
    more_pages = True

    while more_pages:
        # Construct the search query with pagination
        search_url = (
            f"https://api.github.com/search/code?q=test+in:path+"
            f"-filename:.txt+-filename:.md+-filename:.html+-filename:.xml+"
            f"-filename:.json+repo:{repo_path}&page={page}"
        )
        logger.debug(f"Search Url: {search_url}")

        response = make_github_request(url=search_url, session=session, headers=headers)
        if response:
            search_results = response.json()
            if "items" not in search_results:
                logger.error(
                    f"Unable to find 'items' in search_results. Got "
                    f"{search_results}"
                )
            else:
                test_files.extend(search_results["items"])
                for item in search_results["items"]:
                    logger.debug(f'File Name: {item["name"]}, Path: {item["path"]}')
                if "next" in response.links:
                    page += 1
                else:
                    more_pages = False  # Exit loop if there are no more pages

    test_file_count = len(test_files)
    return test_file_count


def get_latest_commit_info(repo_path, headers):
    session = LimiterSession(per_minute=5)
    # Get the commit hash
    # As per: https://docs.github.com/en/rest/commits/
    # commits?apiVersion=2022-11-28
    # "https://api.github.com/repos/OWNER/REPO/commits"
    commit_url = f"https://api.github.com/repos/{repo_path}/commits"
    logger.debug(f"Commit Url: {commit_url}")
    commit_response = make_github_request(
        url=commit_url, session=session, headers=headers
    )
    if commit_response:
        commit_results = commit_response.json()
        # Note: there are 2 commits returned, not sure why...
        #     commits = len(commit_results)
        if "sha" not in commit_results[0]:
            logger.error(
                f"Unable to find commit 'sha' in the first commit results."
                f" Got {commit_results[0]}"
            )
        else:
            html_url = commit_results[0]["html_url"]
            sha = commit_results[0]["sha"]
            logger.debug(f"sha: {sha}, html_url: {html_url}")
            return sha, html_url


def make_github_request(url, session, headers, attempt_num=1):
    if attempt_num > 10:
        logger.error(f"Reached max attempt count of 10 for {url}.")
        return

    logger.info(f"Making attempt num: {attempt_num} for the url: {url}")
    response = session.get(url, headers=headers)
    if response.status_code != 200:
        time_to_pause = attempt_num * 2
        logger.warning(
            f"Received status: {response.status_code} for {url}. "
            f"Response text: {response.text} "
            f"Sleeping for {time_to_pause} seconds."
        )
        time.sleep(time_to_pause)
        return make_github_request(url, session, headers, attempt_num + 1)

    return response


def main():
    codebase_root = str(git_codebase_root())
    github_df_file_path = codebase_root + "/data/github_df.csv"
    logger.info(f" github_df_file_path is : { github_df_file_path}")

    # Accessing the environmental variable (PAT)
    pat = os.getenv("MY_PAT")
    if pat is None:
        logger.error(
            "MY_PAT environment variable needs setting with a valid Personal "
            "Access Token for github.com"
        )
        os._exit(os.EX_CONFIG)

    # Make the authenticated request
    headers = {"Authorization": f"token {pat}", "X-GitHub-Api-Version": "2022-11-28"}

    if os.path.exists(github_df_file_path):
        logger.info(f"Found existing file at: {github_df_file_path}")
        github_df = pd.read_csv(github_df_file_path)

    else:
        logger.info(
            f"Could not find existing file at '{github_df_file_path}', creating"
            f" a new file."
        )
        data_path = codebase_root + "/data/original_github_df.csv"
        # Loading the dataframe
        github_df = load_data(data_path)

        # Some of the URLs end with "/". I need to remove them.
        github_df["repourl"] = github_df["repourl"].str.rstrip("/")
        github_df.to_csv(github_df_file_path, index=False)

    # replace http with https
    github_df["repourl"] = github_df["repourl"].str.replace(
        r"^http\b", "https", regex=True
    )

    # replace www.github.com with github.com
    github_df["repourl"] = github_df["repourl"].str.replace(
        r"https?://(www\.)?", "https://", regex=True
    )

    if "testfilecount" not in github_df.columns:
        logger.info(
            f"Column 'testfilecount' not found in '{github_df_file_path}',"
            f" adding it."
        )
        github_df["testfilecount"] = -1
    else:
        complete = github_df[github_df["testfilecount"] != -1]
        logger.info(
            f"Resuming processing, out of {len(github_df)} rows {len(complete)}"
            f" are complete. leaving {len(github_df) - len(complete)} to"
            f" process."
        )

    for index, row in github_df.iterrows():
        if github_df.loc[index, "testfilecount"] == -1:
            repourl = row["repourl"]
            logger.info(f"Analysing repo {repourl}")
            repo_path = extract_owner_and_repo_names(repourl)
            sha, html_url = get_latest_commit_info(repo_path, headers)
            logger.info(f"Latest git commit {sha} at {html_url}")
            # TODO save in the data array
            test_file_count = get_test_file_count(repo_path, headers)
            github_df.at[index, "testfilecount"] = test_file_count
            github_df.to_csv(github_df_file_path, index=False)
        else:
            continue

    return github_df


if __name__ == "__main__":
    github_df = main()
