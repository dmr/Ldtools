# -*- coding: utf-8 -*-
import datetime
import logging
import os
import pprint

import rdflib
from rdflib import compare

import ldtools
from ldtools import Resource, Origin

Origin.objects.reset_store()
Resource.objects.reset_store()

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

def pprint_origins_and_resources(authoritative_only=False):
    res = {}
    for s in ldtools.Origin.objects.all():
        for _ in range(3): print
        pprint.pprint(s); print
        for r in s.get_resources():
            if authoritative_only and not r.is_authoritative_resource():
                continue
            pprint_resource(r)

def get_resource_and_connected_resources(uri, depth=1, **kw):
    """Helper method to query uri and requery discovered Resouces.
    kw will be passed to GET and GET_all"""
    r,o = cnt()
    logger.info("BEFORE %s: %s Origins and %s Resources" % (uri, r, o))

    if not ldtools.utils.is_valid_url(uri):
        logger.error("Not a valid Uri: %s" % uri)
        return
    uri = ldtools.utils.get_rdflib_uriref(uri)
    origin_uri = ldtools.utils.hash_to_slash_uri(uri)
    origin, origin_created = Origin.objects.get_or_create(uri=origin_uri)
    origin.GET(**kw)

    r,o = cnt()
    logger.info("AFTER lookup %s: %s Origins and %s Resources" % (uri, r, o))

    res, res_created = ldtools.Resource.objects.get_or_create(uri=uri,
        origin=origin)

    if depth:
        Origin.objects.GET_all(depth=depth, **kw)

        r,o = cnt()
        logger.info("AFTER GET_all: %s Origins and %s Resources" % (r, o))
    return res
