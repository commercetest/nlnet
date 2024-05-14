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
    Converts a pandas DataFrame to Turtle (TTL) RDF format, including additional
    repository details, and logs issues encountered when processing each row.

    The function processes each row in the DataFrame to generate RDF triples,
    which are serialised in Turtle format. The DataFrame must include specific
    columns listed in the REQUIRED_COLUMNS variable. If any required columns
    are missing, the function raises a ValueError. For each valid row, the
    function constructs an RDF graph, converts it to Turtle format, and appends
    the result to a list. Rows with errors are logged and skipped.
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
                if value is not None and value != -1:  # Check for valid values
                    # Using column name as predicate
                    predicate = project_namespace[column]
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
