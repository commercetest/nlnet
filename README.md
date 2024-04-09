# nlnet
Analysis of the opensource codebases of NLnet sponsored projects.

[![Tests Status](./reports/junit/tests-badge.svg?dummy=8484744)](./reports/junit/report.html)

## Objectives
The main objective is to be able to identify characteristics of existing and current testing practices recorded in the opensource repos of projects that have received funding from NLnet foundation. These details may then enable us to identify ways to help distill approaches that may help several of these projects in tandem (concurrently).

## Data structure
The columns are: `project code, public page, code repository`

Some projects have multiple repos, these are on their own row in the dataset.

The source file is in TSV (Tab Separated Values) format.

## Structure of this repo
In general, much of the work will be identified in this repo's https://github.com/commercetest/nlnet/issues, and various more general notes will be recorded in Wiki pages at https://github.com/commercetest/nlnet/wiki

## Runtime environment
I'm using miniforge to manage the python environment including packages.

```
conda create --name commercetest-nlnet python=3.10 pandas
conda activate commercetest-nlnet
pip install -r requirements.txt
```

For GitHub API queries this project uses a Personal Access Token (PAT).

Generated a PAT for authentication with the Github API (Expiration 90 days Scopes → public_repo)

Chose the endpoints:
- Repositories Endpoint: To get information about repositories.
- Contents Endpoint: To access the file structure of a repository.
- Search Code Endpoint: To search within repositories for specific words or phrases.

https://github.com/settings/tokens?type=beta


## Checking the quality of our code
We'd like to learn by doing, this includes experimenting with various code quality tools and techniques. Currently we're experimenting with `ruff`, pre-commit checks, and using `pytest` to generate test reports which are then post-processed to provide a coverage badge.

```
pytest --junit-xml=reports/junit/junit.xml --html=reports/junit/report.html
genbadge tests --output-file reports/junit/tests-badge.svg
```

## Scripts

1. github_repo_request_local.py :

   #### Overview
   
   This Python script automates the cloning and analysis of GitHub repositories. Designed for robustness, it handles interruptions by
   saving progress, allowing for resumption without data loss. It provides the flexibility to exclude specific file types and to set
   a custom directory for repository clones.

    #### Key Features
   
     - **Cloning Automation**: Clone repositories from a list provided in a CSV file.
     - **Test File Counting**: Count the number of 'test' files within each repository, ignoring files with user-defined extensions.
     - **Progress Tracking**: Save and resume progress, ideal for long-running processes.
     - **Customizability**: Specify file extensions to exclude and designate a custom directory for cloned repositories via command-            line arguments.
     - **Clean-up Option**: Choose whether to keep or remove cloned repositories after processing.


3. github_repo_requests.py

   #### Overview

   This script facilitates the analysis of GitHub repositories by interfacing with the GitHub API. It processes a CSV file containing
   repository URLs, counts the number of test files within each repository, fetches the latest commit information, and updates this data
   back into the CSV file.

   #### Key Features
   
      -  **CSV File Processing**: Load and validate data from a CSV file, checking for null values and duplicates.
      -  **GitHub Interaction**: Interface with the GitHub API to perform searches within repositories and retrieve commit information.
      -  **Rate Limiting**: Respect GitHub API rate limits with built-in delay and retry logic.
      -  **Data Enrichment**: Update the original CSV file with the count of test files and the latest commit data for each repository.


## Related projects
Work on the data analysis of NLnet projects is also maintained in: https://codeberg.org/NGI0Review/harvest (and the test coverage tracked online at https://artifacts.nlnet.nl/harvest/main/coverage/). In future some or all of this repo's work may migrate there, for the moment this repo facilitates exploration and experimentation.
