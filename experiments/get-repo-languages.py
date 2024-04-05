import os
import requests
from loguru import logger


def get_github_repository_languages(token, repository_owner, repository_name):
    # GraphQL endpoint
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # GraphQL query to retrieve repository languages
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            node {
              name
            }
            size
          }
        }
      }
    }
    """

    variables = {"owner": repository_owner, "name": repository_name}

    # Sending the request to the GitHub GraphQL API
    response = requests.post(
        url, headers=headers, json={"query": query, "variables": variables}
    )
    if response.status_code == 200:
        # Parsing the response
        data = response.json()
        languages = data["data"]["repository"]["languages"]["edges"]
        language_dict = {lang["node"]["name"]: lang["size"] for lang in languages}
        return language_dict
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {response.text}"
        )


# Example usage
pat = os.getenv("MY_PAT")
if pat is None:
    logger.error(
        "MY_PAT environment variable needs setting with a valid Personal Access Token for github.com"
    )
    os._exit(os.EX_CONFIG)

repository_owner = "SeleniumHQ"
repository_name = "selenium"
languages = get_github_repository_languages(pat, repository_owner, repository_name)
print(languages)
