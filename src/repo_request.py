import pandas as pd
import numpy as np
import os
import requests
import json
from loguru import logger

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

def construct_search_request(repo_path):
    # constructing the search query
    search_query = f'test in:path -filename:.txt -filename:.md repo:{repo_path}'
    payload = {'q': search_query, 'type': 'code'}
    # The URL for the Search Code endpoint
    search_url = f'https://api.github.com/search/code'
    return payload, search_url

def extract_reponame_and_username(repo_path):
    parts = repo_path.split('/')
    logger.info(parts)
    repo_path = '/'.join(parts[-2:])  # This joins the last two parts using '/'
    return repo_path

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
        'Authorization' : f'token {pat}',
        'X-GitHub-Api-Version': '2022-11-28'
               }
    # Some of the URLs end with "/". I need to remove them.
    github_df['repourl'] = github_df['repourl'].str.rstrip('/')
    df.to_csv('../data/github_df.csv', index=False)

    # I'm focusing on one repo for now
    index_for_manual_check = 11
    repo_path = github_df['repourl'][index_for_manual_check]
    logger.info(f'repo_path is :  {repo_path}')

    # Extracting the 'username/repository':
    repo_path = extract_reponame_and_username(repo_path)

    # Constructing the search request
    payload, search_url = construct_search_request(repo_path)

    # Sending the GET request to the Github API
    response = requests.get(search_url, headers=headers, params=payload)

    if response.status_code == 200:
        search_results = response.json()
        count_test_files = len(search_results['items'])
        logger.info(f'Number of "test" files found: {count_test_files}')

        for item in search_results['items']:
            logger.info(f'File Name: {item["name"]}, Path: {item["path"]}')
    else:
        logger.info(f'Failed to search, status code: {response.status_code}')
        logger.info("Response text:", response.text)

    logger.info("X-RateLimit-Limit:", response.headers.get("X-RateLimit-Limit"))
    logger.info("X-RateLimit-Remaining:", response.headers.get("X-RateLimit-Remaining"))
    logger.info("X-RateLimit-Reset:", response.headers.get("X-RateLimit-Reset"))


if __name__ == '__main__':
    main()
