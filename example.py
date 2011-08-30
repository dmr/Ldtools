from ldtools import Resource, Origin
import rdflib

import ldtools; ldtools.DEBUG=True

# First, we define the Resource object and thereby its Origin object
uri = "http://dbpedia.org/resource/Karlsruhe"
r, created = Resource.objects.get_or_create(uri, auto_origin=True)

assert len(Resource.objects.all()) == 1
assert len(Origin.objects.all()) == 1

# Process it, hopefully discovering more Origins in there (rdfs:seeAlso, owl:sameAs...)
# process it
r._origin.GET(
    GRAPH_SIZE_LIMIT=25000,
    follow_uris=[rdflib.RDFS.seeAlso, rdflib.OWL.sameAs],
    handle_owl_imports=True)

assert len(Resource.objects.all()) > 1, Resource.objects.all()[0].__dict__
assert len(Origin.objects.all()) > 1

Origin.objects.GET_all()

#import pprint
#pprint.pprint(r.__dict__)
#print

print "Crawled %s Origins and collected %s Resources" % (
    len(list(Origin.objects.filter(processed=True))), len(list(Resource.objects.all())))

