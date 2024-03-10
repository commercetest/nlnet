import logging
import os
import time

import json
import numpy as np
from loguru import logger
import pandas as pd
from requests_ratelimiter import LimiterSession
import requests


def load_data(filepath):
    try:
        df = pd.read_csv(filepath)
        logger.info(f'Dataframe shape: {df.shape}')
        logger.info(f'Dataframe columns: {df.columns.tolist()}')
        df.info()
        return df

    except Exception as e:
        logger.error(f'Error Loading data from path {filepath} with exception {e}')
    return None


def check_and_clean_data(df):
    # Checking for null values
    null_counts = df.isnull().sum()
    if np.any(null_counts):
        logger.info("Null values found:")
        logger.info(null_counts[null_counts > 0])
    else:
        logger.info("No null values found.")

    # Checking for duplicates
    duplicates = df.duplicated().sum()
    if duplicates:
        logger.info(f"Number of duplicate rows: {duplicates}")
    else:
        logger.info("No duplicate rows found.")


def extract_reponame_and_username(repo_path):
    parts = repo_path.split('/')
    logger.info(parts)

    # Not all repourls are correct, some point to just the user and others to the issues page
    index_of_github = parts.index('github.com')
    if len(parts) <= index_of_github + 2:
        logger.warning(f'repopath: {repo_path} does not contain a username and repo')
        return ""

    repo_path = '/'.join(parts[index_of_github + 1: index_of_github + 3])
    return repo_path


def get_test_file_count(repourl, headers):
    session = LimiterSession(per_minute=5)
    test_files = []
    page = 1
    repo_path = extract_reponame_and_username(repourl)
    more_pages = True
    if not repo_path:
        logger.warning(f"Repo: {repourl} doesn't have a username and reponame, skipping.")
        more_pages = False

    while more_pages:
        # Construct the search query with pagination
        search_url = f"https://api.github.com/search/code?q=test+in:path+" \
                     f"-filename:.txt+-filename:.md+-filename:.html+-filename:.xml+" \
                     f"-filename:.json+repo:{repo_path}&page={page}"
        logger.debug(f"Search Url: {search_url}")

        response = make_github_request(search_url=search_url, session=session, headers=headers)
        if response:
            search_results = response.json()
            if 'items' not in search_results:
                logger.error(f"Unable to find 'items' in search_results. Got {search_results}")
            else:
                test_files.extend(search_results['items'])
                for item in search_results['items']:
                    logger.info(f'File Name: {item["name"]}, Path: {item["path"]}')
                if 'next' in response.links:
                    page += 1
                else:
                    more_pages = False  # Exit loop if there are no more pages

    test_file_count = len(test_files)
    return test_file_count


def make_github_request(search_url, session, headers, attempt_num=0):
    if attempt_num > 10:
        logger.error(f"Reached max attempt count of 10 for {search_url}.")
        return

    logger.info(f'Making attempt num: {attempt_num} for the url: {search_url}')
    response = session.get(search_url, headers=headers)
    if response.status_code != 200:
        logger.warning(f'Received status: {response.status_code} for {search_url}. '
                       f'Response text: {response.text} '
                       f'Sleeping for 30 seconds.')
        time.sleep(61)
        return make_github_request(search_url, session, headers, attempt_num + 1)

    return response

def main():
    github_df_file_path = '../data/github_df.csv'

    # Accessing the environmental variable (PAT)
    pat = os.getenv('MY_PAT')

    # Make the authenticated request
    headers = {
        'Authorization': f'token {pat}',
        'X-GitHub-Api-Version': '2022-11-28'
              }

    if os.path.exists(github_df_file_path):
        logger.info(f"Found existing file at: {github_df_file_path}")
        github_df = pd.read_csv(github_df_file_path)

    else:
        logger.info(f"Could not find existing file at '{github_df_file_path}', creating a new file.")
        data_path = '../data/df'
        # Loading the dataframe
        df = load_data(data_path)

        # Checking the Null and duplicate values
        check_and_clean_data(df)

        # I will keep the first occurrence of each duplicate row and remove the others:
        df = df.drop_duplicates(keep='first')

        # I will only consider github.com domain
        github_df = df[df['repourl'].str.contains('github.com')]

        # Some of the URLs end with "/". I need to remove them.
        github_df['repourl'] = github_df['repourl'].str.rstrip('/')
        github_df.to_csv(github_df_file_path, index=True)


    if 'testfilecount' not in github_df.columns:
        logger.info(f"Column 'testfilecount' not found in '{github_df_file_path}', adding it.")
        github_df['testfilecount'] = -1
    else:
        complete = github_df[github_df['testfilecount'] != -1]
        logger.info(f"Resuming processing, out of {len(github_df)} rows {len(complete)} are complete "
                    f"leaving {len(github_df) - len(complete)} to process.")

    for index, row in github_df.iterrows():
        if github_df.loc[index,'testfilecount'] == -1:
            repourl = row['repourl']
            logger.info(f'Analysing repo {repourl}')
            test_file_count = get_test_file_count(repourl, headers)
            github_df.at[index, 'testfilecount'] = test_file_count
            github_df.to_csv(github_df_file_path, index=True)

        else:
            continue


    return github_df


if __name__ == '__main__':
    github_df = main()
