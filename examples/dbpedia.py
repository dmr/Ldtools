# -*- coding: utf-8 -*-
from __future__ import print_function

import pprint

import rdflib

from ldtools.origin import Origin
from ldtools.resource import Resource
from ldtools.utils import get_slash_url
from ldtools.helpers import set_colored_logger

logger = set_colored_logger(2)


count_things = lambda: (len(Origin.objects.all()), len(Resource.objects.all()))


GET_kw = dict(
    only_follow_uris=[rdflib.RDFS.seeAlso, rdflib.OWL.sameAs],
    handle_owl_imports=True,
)


from functools import wraps


def log_resource_n_origin_diff(func):
    """
    Logs hwo the storage's content changed during operation
    """
    @wraps(func)
    def new_func(*args, **kwargs):
        r1, o1 = count_things()
        ret = func(*args, **kwargs)
        r2, o2 = count_things()
        logger.info(
            "{0} more Origins and {1} more Resources".format(o2-o1, r2-r1)
        )
        return ret
    return new_func


@log_resource_n_origin_diff
def get_resource_and_connected_resources(uri):
    origin_uri = get_slash_url(uri)
    origin, origin_created = Origin.objects.get_or_create(uri=origin_uri)
    origin.GET(**GET_kw)
    res, res_created = Resource.objects.get_or_create(uri=uri, origin=origin)
    return res


karlsruhe_uri = "http://dbpedia.org/resource/Karlsruhe"
karlsruhe = get_resource_and_connected_resources(uri=karlsruhe_uri)
print("Print Karlsruhe Resource object --> Number of properties:", len(karlsruhe.__dict__.keys()))

print("Karlsruhe rdf:type s:")
for typ in list(karlsruhe.rdf_type):
    print(typ)

log_resource_n_origin_diff(Origin.objects.GET_all(depth=1, **GET_kw))
