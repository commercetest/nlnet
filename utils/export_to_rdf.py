from rdflib import Graph, Literal, URIRef, RDF, Namespace
from rdflib.namespace import FOAF, XSD, RDFS


def dataframe_row_to_ttl(row):
    """
    Converts a pandas DataFrame row to TTL RDF format, following the client's specifications.

    Args:
        row: A pandas DataFrame row.

    Returns:
        A string representing the TTL RDF representation of the row.
    """

    # Create a new RDF graph
    graph = Graph()

    # Define the base URI for the project
    base_uri = "https://nlnet.nl/project/"
    project_namespace = Namespace(base_uri)

    # Extract data from the row
    project_ref = row["projectref"]
    nlnet_page = row["nlnetpage"]
    repo_url = row["repourl"]
    test_file_count = row["testfilecountlocal"]

    # Create RDF subject (URI) based on base_uri and project_ref
    subject_uri = URIRef(base_uri + project_ref)

    # Add RDF triples (subject, predicate, object)
    # Type for the project could be a specific class if you have one, here I'm using FOAF.Project
    graph.add((subject_uri, RDF.type, FOAF.Project))

    # Add homepage link to the project's NLnet page
    graph.add((subject_uri, FOAF.homepage, URIRef(nlnet_page)))

    # Add seeAlso link to the project's GitHub repository URL
    graph.add((subject_uri, RDFS.seeAlso, URIRef(repo_url)))

    # Add literal for test file count
    graph.add(
        (
            subject_uri,
            project_namespace.testFileCount,
            Literal(test_file_count, datatype=XSD.integer),
        )
    )

    # Serialize the RDF graph to a string in TTL format
    ttl_string = graph.serialize(format="turtle")

    return ttl_string
