from __future__ import print_function

import logging
import pprint
import datetime
import sys

import argparse

from ldtools.utils import (
    is_valid_url,
    get_slash_url,
    get_rdflib_uriref,
    urllib2,
)
from ldtools.helpers import set_colored_logger
from ldtools.backends import __version__
from ldtools.origin import Origin
from ldtools.resource import Resource

logger = logging.getLogger("ldtools.cli")


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--version', action='version', version='%(prog)s ' + __version__,
        help="Print current version")
    parser.add_argument(
        '-v', '--verbosity', action="store",
        help='Adjust verbosity. 1 for every detail, 5 for silent',
        default=2, type=int)
    parser.add_argument(
        '-d', '--depth', action="store", default=0, type=int,
        help="Crawl discovered Origins x times")

    follow_group = parser.add_mutually_exclusive_group()
    follow_group.add_argument(
        '--follow-all', action="store_true",
        help="Follow all URIs discovered")
    follow_group.add_argument(
        '--follow-uris',
        action="append", dest='follow_uris', default=[],
        help="Follow the URIs specified")

    print_group = parser.add_mutually_exclusive_group()
    print_group.add_argument(
        '--only-print-uris', action="store_true",
        help='Only prints a short representation of Resources')

    parser.add_argument(
        '--only-print-uri-content', action="store_true",
        help='Only prints data retrieved from URIs and exists')
    parser.add_argument(
        '--socket-timeout', action="store", type=int,
        help="Set the socket timeout")
    parser.add_argument(
        '-o', '--only-negotiate', action="store_true",
        help='Only do content negotiation for given URIs and print the '
             'response headers')
    parser.add_argument(
        '--GRAPH_SIZE_LIMIT', action="store", type=int,
        help="Set maximum graph size that will be processed")
    parser.add_argument('--print-all-resources', action="store_true")

    def check_uri(url):
        if not is_valid_url(url):
            raise argparse.ArgumentTypeError("%r is not a valid URL" % url)
        return url
    parser.add_argument(
        'origin_urls', action="store", nargs='+', type=check_uri,
        help="Pass a list of URIs. ldtools will crawl them one by one")
    return parser


def execute_ldtools(
    verbosity,
    origin_urls,
    depth,
    follow_all,
    follow_uris,
    socket_timeout,
    GRAPH_SIZE_LIMIT,
    print_all_resources,
    only_print_uris,
    only_print_uri_content,
    only_negotiate
):
    set_colored_logger(verbosity)

    # customize Origin.objects.post_create_hook for performance reasons
    def custom_post_create_hook(origin):
        origin.timedelta = datetime.timedelta(minutes=5)
        return origin
    Origin.objects.post_create_hook = custom_post_create_hook

    url_count = len(origin_urls)

    if url_count > 1:
        logger.info("Retrieving content of %s URLs" % url_count)

    if follow_all:
        only_follow_uris = None
        logging.info("Following all URIs")
    elif follow_uris:
        only_follow_uris = follow_uris
        logging.info("Following values matching: %s"
                     % ", ".join(only_follow_uris))
    else:
        only_follow_uris = []

    if socket_timeout:
        import socket
        logger.info("Setting socket timeout to %s" % socket_timeout)
        socket.setdefaulttimeout(socket_timeout)

    kw = dict(raise_errors=False)
    if GRAPH_SIZE_LIMIT:
        kw["GRAPH_SIZE_LIMIT"] = GRAPH_SIZE_LIMIT

    for url in origin_urls:
        url = get_slash_url(url)
        origin, created = Origin.objects.get_or_create(url)
        logger.info("Retrieving content of %s" % origin.uri)

        if only_negotiate or only_print_uri_content:
            try:
                data = origin.backend.GET(
                    uri=origin.uri,
                    httphandler=urllib2.HTTPHandler(debuglevel=1))
            except Exception as exc:
                print(exc)
                continue
            if only_print_uri_content:
                print('\n', data, '\n')
        else:
            origin.GET(only_follow_uris=only_follow_uris, **kw)

    if only_negotiate or only_print_uri_content:
        sys.exit(0)

    if depth:
        for round in range(depth):
            for origin in Origin.objects.all():
                origin.GET(only_follow_uris=only_follow_uris, **kw)

    for orig_url in origin_urls:
        url = get_slash_url(orig_url)
        origin = Origin.objects.get(url)
        for r in origin.get_resources():
            if r._uri == get_rdflib_uriref(orig_url):
                logger.info(u"Printing all available information "
                    "about {0}".format(r._uri))
                if hasattr(r, "_has_changes"):
                    delattr(r, "_has_changes")
                if hasattr(r, "pk"):
                    delattr(r, "pk")
                pprint.pprint(r.__dict__)

    if print_all_resources:
        all_resources = Resource.objects.all()
        if (only_print_uris):
            for resource in all_resources:
                print(resource)
        else:
            for r in all_resources:
                if hasattr(r, "_has_changes"):
                    delattr(r, "_has_changes")
                if hasattr(r, "pk"):
                    delattr(r, "pk")
                pprint.pprint(r.__dict__)


def main():
    execute_ldtools(**get_parser().parse_args().__dict__)
