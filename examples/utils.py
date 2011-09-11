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

# overwrites sys.excepthook
import ipdb #; ipdb.set_trace()

# setup logging
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
        #The background is set with 40 plus the number of the color, and
        # the foreground with 30
        #These are the sequences need to get colored ouput
        RESET_SEQ = "\033[0m"
        COLOR_SEQ = "\033[1;%dm"
        BOLD_SEQ = "\033[1m"
        COLORS = {'DEBUG': BLUE,'INFO': MAGENTA,
            'WARNING': YELLOW,'CRITICAL': YELLOW,'ERROR': RED}
        if record.levelname in COLORS:
            record.levelname = COLOR_SEQ % (30 + COLORS[record.levelname]) + \
                              record.levelname + RESET_SEQ
        record.msg = unicode(record.msg)
        record.msg = COLOR_SEQ % (30 + GREEN) + record.msg + RESET_SEQ
        return logging.Formatter.format(self, record)
formatter = ColoredFormatter("%(asctime)s %(name)s %(funcName)s:%(lineno)d"
                             " %(levelname)s: %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger()
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)


cnt = lambda: (len(ldtools.Origin.objects.all()),
               len(ldtools.Resource.objects.all()))

def one(set):
    l = list(set)
    assert len(l) == 1
    return l[0]

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
        for _ in range(5): print
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
