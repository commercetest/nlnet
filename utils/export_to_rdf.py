from rdflib import Graph, Literal, URIRef, RDF, Namespace
from rdflib.namespace import FOAF, XSD, RDFS
from loguru import logger

# List of required columns
REQUIRED_COLUMNS = [
    "projectref",
    "nlnetpage",
    "repourl",
    "repodomain",
    "base_repo_url",
    "testfilecountlocal",
    "clone_status",
    "last_commit_hash",
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

            # Extracting column values using `.get` for safety
            project_ref = row.get("projectref")
            nlnet_page = row.get("nlnetpage")
            repo_url = row.get("repourl")
            repo_domain = row.get("repodomain")
            base_repo_url = row.get("base_repo_url")
            test_file_count = row.get("testfilecountlocal")
            clone_status = row.get("clone_status")
            last_commit_hash = row.get("last_commit_hash")

            subject_uri = URIRef(base_uri + project_ref)

            # Basic triples
            graph.add((subject_uri, RDF.type, FOAF.Project))
            if nlnet_page:
                graph.add((subject_uri, FOAF.homepage, URIRef(nlnet_page)))
            if repo_url:
                graph.add((subject_uri, RDFS.seeAlso, URIRef(repo_url)))

            # Additional triples
            if repo_domain:
                graph.add(
                    (
                        subject_uri,
                        project_namespace.repoDomain,
                        Literal(repo_domain, datatype=XSD.string),
                    )
                )
            if base_repo_url:
                graph.add(
                    (subject_uri, project_namespace.baseRepoURL, URIRef(base_repo_url))
                )
            if test_file_count is not None:
                graph.add(
                    (
                        subject_uri,
                        project_namespace.testFileCount,
                        Literal(test_file_count, datatype=XSD.integer),
                    )
                )
            if clone_status:
                graph.add(
                    (
                        subject_uri,
                        project_namespace.cloneStatus,
                        Literal(clone_status, datatype=XSD.string),
                    )
                )
            if last_commit_hash:
                graph.add(
                    (
                        subject_uri,
                        project_namespace.lastCommitHash,
                        Literal(last_commit_hash, datatype=XSD.string),
                    )
                )

            # Serialise the RDF graph to a string in TTL format and add to list
            ttl_strings.append(graph.serialize(format="turtle"))

        except Exception as e:
            logger.error(f"Skipping row {index} due to an error: {e}")

    return ttl_strings
