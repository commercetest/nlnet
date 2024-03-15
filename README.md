# nlnet
Analysis of the opensource codebases of NLnet sponsored projects.

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
```

For GitHub API queries this project uses a Personal Access Token (PAT).

Generated a PAT for authentication with the Github API (Expiration 90 days Scopes → public_repo)

Chose the endpoints:
- Repositories Endpoint: To get information about repositories.
- Contents Endpoint: To access the file structure of a repository.
- Search Code Endpoint: To search within repositories for specific words or phrases.

https://github.com/settings/tokens?type=beta


## Related projects
Work on the data analysis of NLnet projects is also maintained in: https://codeberg.org/NGI0Review/harvest (and the test coverage tracked online at https://artifacts.nlnet.nl/harvest/main/coverage/). In future some or all of this repo's work may migrate there, for the moment this repo facilitates exploration and experimentation.
