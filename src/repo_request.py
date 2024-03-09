import logging
import os

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
    repo_path = '/'.join(parts[-2:])  # This joins the last two parts using '/'
    return repo_path


def get_test_file_count(repo_path, headers):
    session = LimiterSession(per_second=0.2)
    test_files = []
    page = 1
    repo_path = extract_reponame_and_username(repo_path)
    more_pages = True

    while more_pages:
        # Construct the search query with pagination
        search_url = f"https://api.github.com/search/code?q=test+in:path+" \
                     f"-filename:.txt+-filename:.md+-filename:.html+-filename:.xml+" \
                     f"-filename:.json+repo:{repo_path}&page={page}"
        logger.debug(f"Search Url: {search_url}")
        response = session.get(search_url, headers=headers)

        if response.status_code == 200:
            search_results = response.json()
            test_files.extend(search_results['items'])
            for item in search_results['items']:
                logger.info(f'File Name: {item["name"]}, Path: {item["path"]}')

            # Check for the 'next' link in the response headers for more pages
            if 'next' in response.links:
                page += 1
            else:
                more_pages = False  # Exit loop if there are no more pages
        else:
            logger.error(f"Failed to search, status code: {response.status_code}")
            logger.error("Response text:", response.text)
            more_pages = False
    test_file_count = len(test_files)
    return test_file_count, test_files, response


def main():
    data_path = '../data/df'
    # Loading the dataframe
    df = load_data(data_path)

    # Checking the Null and duplicate values
    check_and_clean_data(df)

    # I will keep the first occurrence of each duplicate row and remove the others:
    df = df.drop_duplicates(keep='first')

    # I will only consider github.com domain
    github_df = df[df['repourl'].str.contains('github.com')]

    # Accessing the environmental variable (PAT)
    pat = os.getenv('MY_PAT')

    # Make the authenticated request
    headers = {
        'Authorization': f'token {pat}',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    # Some of the URLs end with "/". I need to remove them.
    github_df['repourl'] = github_df['repourl'].str.rstrip('/')
    df.to_csv('../data/github_df.csv', index=False)

    # Creating a new column is the github_df to store the test file counts:
    github_df['testfilecount'] = -1

    for index, row in github_df.head(3).iterrows():
        repo_path = row['repourl']
        logger.info(f'Analysing repo {repo_path}')
        test_file_count, _, _ = get_test_file_count(repo_path, headers)
        github_df.at[index, 'testfilecount'] = test_file_count
        df.to_csv('../data/github_df.csv', index=True)

    return github_df, test_file_count


if __name__ == '__main__':
    github_df, test_file_count = main()
