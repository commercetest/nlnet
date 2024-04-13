from rdflib import Graph, Literal, URIRef, RDF, Namespace
from rdflib.namespace import FOAF, XSD, RDFS
import pandas as pd
from loguru import logger


def dataframe_to_ttl(df):
    """
    Converts a pandas DataFrame to TTL RDF format, including additional
    repository details, and logs issues encountered when processing each row.

    Args:
        df: A pandas DataFrame with columns 'projectref', 'nlnetpage',
        'repourl', 'testfilecountlocal', and 'last_commit_hash'.

    Returns:
        A list of strings, each representing the TTL RDF representation of
        a row.
    """
    ttl_strings = []
    base_uri = "https://nlnet.nl/project/"
    project_namespace = Namespace(base_uri)

    for index, row in df.iterrows():
        try:
            graph = Graph()
            project_ref = row["projectref"]
            nlnet_page = row["nlnetpage"]
            repo_url = row["repourl"]
            test_file_count = row["testfilecountlocal"]
            last_commit_hash = row["last_commit_hash"]

            # Check for necessary data completeness
            if (
                pd.isna(project_ref)
                or pd.isna(nlnet_page)
                or pd.isna(repo_url)
                or pd.isna(test_file_count)
                or pd.isna(last_commit_hash)
            ):
                raise ValueError(
                    "Missing required data fields for RDF " "serialization."
                )

            subject_uri = URIRef(base_uri + project_ref)
            graph.add((subject_uri, RDF.type, FOAF.Project))
            graph.add((subject_uri, FOAF.homepage, URIRef(nlnet_page)))
            graph.add((subject_uri, RDFS.seeAlso, URIRef(repo_url)))
            graph.add(
                (
                    subject_uri,
                    project_namespace.testFileCount,
                    Literal(test_file_count, datatype=XSD.integer),
                )
            )
            # Add last commit hash
            graph.add(
                (
                    subject_uri,
                    project_namespace.lastCommitHash,
                    Literal(last_commit_hash, datatype=XSD.string),
                )
            )

            # Serialize the RDF graph to a string in TTL format and add to list
            ttl_strings.append(graph.serialize(format="turtle"))

        except Exception as e:
            logger.error(f"Skipping row {index} due to an error: {e}")

    return ttl_strings
