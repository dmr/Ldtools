# -*- coding: utf-8 -*-
from utils import *

uri = "http://dbpedia.org/resource/Karlsruhe"
karlsruhe = get_resource_and_connected_resources(
    uri=uri,
    depth=0,
    only_follow_uris=[rdflib.RDFS.seeAlso, rdflib.OWL.sameAs],
    handle_owl_imports=True,
)

print "Print Karlsruhe Resource object"
pprint_resource(karlsruhe)

print

print "Karlsruhe rdf:type s:"
for type in list(karlsruhe.rdf_type):
    print type
