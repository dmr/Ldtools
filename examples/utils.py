# -*- coding: utf-8 -*-
import datetime
import logging
import os
import pprint

import rdflib
from rdflib import compare

import ldtools
from ldtools import Resource, Origin
Origin.objects.reset_store(); Resource.objects.reset_store()
import ipdb #; ipdb.set_trace() # overwrites sys.excepthook
logger = ldtools.utils.set_logger(2)
cnt = lambda: (len(Origin.objects.all()), len(Resource.objects.all()))

def pprint_resource(resource):
    import copy
    c = copy.copy(resource)
    delattr(c, "pk")
    if hasattr(c, "_reverse"): delattr(c, "_reverse")
    if hasattr(c, "_has_changes"): delattr(c, "_has_changes")
    dct = ldtools.safe_dict(c.__dict__)
    try:
        pprint.pprint(dct)
    except UnicodeEncodeError as e:
        logger.error("UnicodeEncodeError occurred during print")
        print c

def pprint_origins_and_resources():
    res = {}
    for s in ldtools.Origin.objects.all():
        for _ in range(3): print
        pprint.pprint(s)
        print
        for r in s.get_resources():
            pprint_resource(r)


def get_resource_and_connected_resources(uri, depth=1, **kw):
    """Helper method to query uri and requery discovered Resouces.
    kw will be passed to GET and GET_all"""
    r,o = cnt()
    logger.info("BEFORE %s: %s Origins and %s Resources" % (uri, r, o))

    origin_uri = ldtools.hash_to_slash_uri(rdflib.URIRef(uri))

    origin, origin_created = Origin.objects.get_or_create(uri=origin_uri,
    )
    origin.GET(**kw)

    r,o = cnt()
    logger.info("AFTER lookup %s: %s Origins and %s Resources" % (uri, r, o))

    res, res_created = ldtools.Resource.objects.get_or_create(uri=uri,
        origin=origin
    )

    if depth:
        Origin.objects.GET_all(depth=depth, **kw)

        r,o = cnt()
        logger.info("AFTER GET_all: %s Origins and %s Resources" % (r, o))

    return res
