# -*- coding: utf-8 -*-
import pprint

import rdflib

from ldtools.origin import Origin
from ldtools.resource import Resource
from ldtools.utils import get_slash_url
from ldtools.helpers import set_colored_logger

logger = set_colored_logger(2)


def get_resource_and_connected_resources(uri, depth=1, **kw):
    """Helper method to query uri and requery discovered Resouces.
    kw will be passed to GET and GET_all"""

    cnt = lambda: (len(Origin.objects.all()), len(Resource.objects.all()))

    r,o = cnt()
    logger.info("BEFORE %s: %s Origins and %s Resources" % (uri, r, o))

    origin_uri = get_slash_url(uri)
    origin, origin_created = Origin.objects.get_or_create(uri=origin_uri)
    origin.GET(**kw)

    r,o = cnt()
    logger.info("AFTER lookup %s: %s Origins and %s Resources" % (origin_uri, r, o))

    res, res_created = Resource.objects.get_or_create(uri=uri,
        origin=origin)

    if depth:
        Origin.objects.GET_all(depth=depth, **kw)

        r,o = cnt()
        logger.info("AFTER GET_all: %s Origins and %s Resources" % (r, o))
    return res


uri = "http://dbpedia.org/resource/Karlsruhe"
karlsruhe = get_resource_and_connected_resources(
    uri=uri,
    depth=0,
    only_follow_uris=[rdflib.RDFS.seeAlso, rdflib.OWL.sameAs],
    handle_owl_imports=True,
)


print "Print Karlsruhe Resource object"
pprint.pprint(karlsruhe)

print

print "Karlsruhe rdf:type s:"
for type in list(karlsruhe.rdf_type):
    print type
