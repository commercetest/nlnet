"""
This code was initially generated using ChatGPT4 and then manually modified.

The main aim is to experiment with creating a suitable data structure for the
results to communicate with NLnet.

The Efficacy Metric would be an internal metric to compare the suitability of
the various interrogation methods.

MethodUsed emerged from the work in https://github.com/commercetest/nlnet/issues/7
Manual means a person sought the information using similar heuristics to those
described in issue 7 e.g. by using github's online search facility then
reviewing those search results.

ChatGPT history: https://chat.openai.com/share/a01e8f98-74be-4c33-a8e0-1e6887b06a98
"""
import pandas as pd
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD

from pathlib import Path

# get parent directory
curr_dir = Path(__file__).parent.parent
path_to_data_folder = str(curr_dir) + '/data'

# Sample data
data = {
    'CommitHash': ['516722647ae474746a84c197127e323135907d57', '516722647ae474746a84c197127e323135907d57', '516722647ae474746a84c197127e323135907d57', '3efd6e0f03c3dabbbc9acbb52b058e0482d146ad', '3efd6e0f03c3dabbbc9acbb52b058e0482d146ad'],
    'MethodUsed': ['manual', 'filesystem', 'githubAPI', 'GitPython', 'GitShell'],
    'TestFileCount': [10, 12, 11, 8, 9],  # Counts obtained by each method
    'EfficacyMetric': [0.95, 0.90, 0.92, 0.88, 0.91]  # Hypothetical metric, if relevant
}

df = pd.DataFrame(data)

repo_uri = 'https://github.com/spring-projects/spring-petclinic/'
# Initialize a graph
g = Graph()

# Define your namespace
mv = Namespace("http://example.org/myvocab/")
g.bind("mv", mv)

# Iterate over DataFrame rows and convert each row to RDF triples
for index, row in df.iterrows():
    # Unique identifier for each observation
    observation_uri = URIRef(f"{repo_uri}{row['CommitHash']}/{row['MethodUsed']}")

    # Reference to the commit and the method
    # Commit URIs are of the form: https://github.com/spring-projects/spring-petclinic/commit/516722647ae474746a84c197127e323135907d57
    commit_uri = URIRef(f"{repo_uri}commit/{row['CommitHash']}")
    method_uri = mv[row['MethodUsed']]

    # Define the observation as an instance of a collection effort
    g.add((observation_uri, RDF.type, mv.Observation))
    g.add((observation_uri, mv.commit, commit_uri))
    g.add((observation_uri, mv.methodUsed, method_uri))
    g.add((observation_uri, mv.testFileCount, Literal(row['TestFileCount'], datatype=XSD.integer)))

# Serialize the graph to a Turtle file
g.serialize(f"{path_to_data_folder}/example_commit_data.ttl", format="turtle")
