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
   
   This script automates the process of cloning GitHub repositories listed in a CSV file, counts the number of test files in each repository, and saves both the count and the last    commit hash back to the CSV. Additionally, it writes the repository URL followed by the names of all test files found within that repository to a specified text file,              facilitating detailed record-keeping and auditing of test file existence across repositories. The script is designed to handle interruptions and errors more robustly by            independently verifying the completion of each critical operation including cloning, commit hash retrieval, test file counting, and the writing of test file records. It saves      progress incrementally and can resume where it left off, ensuring that data from previous runs is properly managed.

   #### Enhancements

   This script includes several enhancements to improve its functionality:
   
   - **GitHub URL Parsing:** Ensures only repository roots are targeted by parsing and correcting GitHub URLs.
   - **File Extension Exclusion:** Allows exclusion of specific file extensions during the test file count to tailor the data collection.
   - **Retention of Clones:** Optional retention of cloned repositories post-processing, which can be useful for subsequent manual reviews or further automated tasks.
   - **Batch Processing:** Manages large sets of data efficiently and saves progress periodically.
   - **Turtle Format Conversion:** Converts the final data collection to Turtle (TTL) format for RDF compliant data storage, with the ability to specify the output location.
   - **Auditing and Verification:** Writes repository URLs and associated test file names to a text file for easy auditing and verification. The location of this text file can be       specified via command-line arguments.

   #### Configuration

   Users can customize their experience with the script through several command-line arguments:
   
   - `--exclude`: Specify file extensions to exclude from test file counts.
   - `--clone-dir`: Set a custom directory for cloning the repositories.
   - `--keep-clones`: Option to retain cloned repositories after processing.
   - `--input-file`: Path to the input CSV file.
   - `--output-file`: Path to the output CSV file that includes test file counts and last commit hashes.
   - `--test-file-list`: Path to the text file for recording repository URLs and test file names.
   - `--ttl-file`: Path to save the Turtle (TTL) format file.

   #### Usage
   
   To use this script, you can specify all necessary command line arguments based on your requirements. For example:

   ```bash
   python 1. github_repo_request_local.py --input-file path/to/input.csv --output-file path/to/output.csv



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
