"""
This is based on the example in:
   https://rdflib.readthedocs.io/en/stable/intro_to_parsing.html
   and updated as the card for Tim Berners-Lee is no longer on the w3 site
   It is on archive.org at:
   https://web.archive.org/web/20120226191514/http://www.w3.org/People/Berners-Lee/card
   The contents were saved into a local file for ease of parsing here;
   they're in n3 notation.
"""

from rdflib import Graph
import os
import pprint

g = Graph()
# NB: the following path is hard-coded relative to the runtime folder. For the
# moment this isn't worth fixing as the fix is more complex than editing here.
g.parse(os.getcwd() + "/experiments/data_for_experiments/tbl.n3")

print(len(g))

for stmt in g:
    pprint.pprint(stmt)
