from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import XSD
from loguru import logger

# List of required columns
REQUIRED_COLUMNS = [
    "projectref",
    "nlnetpage",
    "repourl",
    "duplicate_flag",
    "null_value_flag",
    "repodomain",
    "domain_extraction_flag",
    "incomplete_url_flag",
    "base_repo_url",
    "base_repo_url_flag",
    "testfilecountlocal",
    "clone_status",
    "last_commit_hash",
    "explanation",
]


def dataframe_to_ttl(df):
    """
    Converts a pandas DataFrame to TTL RDF format, including additional
    repository details, and logs issues encountered when processing each row.

     Args:
       df: A pandas DataFrame with relevant columns.

    Returns:
       A list of strings, each representing the TTL RDF representation of
       a row.
    """
    # Validate the presence of required columns
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"DataFrame is missing required columns: {missing_columns}")

    ttl_strings = []
    base_uri = "https://nlnet.nl/project/"
    project_namespace = Namespace(base_uri)

    for index, row in df.iterrows():
        try:
            graph = Graph()
            subject_uri = URIRef(base_uri + str(row.get("projectref")))

            # Create triples for all fields
            for column in REQUIRED_COLUMNS:
                value = row.get(column)
                if value is not None and value != -1:  # Check for valid values,
                    # ignoring placeholder like -1
                    predicate = project_namespace[
                        column
                    ]  # Using column name as predicate
                    if isinstance(value, str) and value.startswith("http"):
                        graph.add(
                            (subject_uri, predicate, URIRef(value))
                        )  # Add as URIRef for URLs
                    else:
                        graph.add(
                            (
                                subject_uri,
                                predicate,
                                Literal(value, datatype=XSD.string),
                            )
                        )

            ttl_strings.append(graph.serialize(format="turtle"))

        except Exception as e:
            logger.error(f"Skipping row {index} due to an error: {e}")

    return ttl_strings
