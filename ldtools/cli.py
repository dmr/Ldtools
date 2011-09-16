import argparse
import logging
import urllib2
import rdflib
import pprint
import datetime
import logging
import sys

from ldtools.utils import set_logger, is_valid_url, hash_to_slash_uri
from ldtools.backends import __version__
from ldtools import Origin, Resource

logger = logging.getLogger("ldtools.cli")

def get_parser():
    parser = argparse.ArgumentParser()

    version_str = '%(prog)s ' + __version__
    parser.add_argument('--version', action='version', version=version_str,
        help="Print current version")

    parser.add_argument('-v', '--verbosity', action="store",
        help='Adjust verbosity. 1 for every detail, 5 for silent',
        default=2, type=int)

    parser.add_argument('--depth', action="store", default=0, type=int,
        help="Crawl discovered Origins x times")

    follow_group = parser.add_mutually_exclusive_group()
    follow_group.add_argument('--follow-all', action="store_true",
        help="Follow all URIs discovered")
    follow_group.add_argument('--follow-uris',
        action="append", dest='follow_uris', default=[],
        help="Follow the URIs specified")

    print_group = parser.add_mutually_exclusive_group()
    print_group.add_argument('--only-print-uris', action="store_true",
        help='Only prints a short representation of Resources')
    print_group.add_argument('--print-detailled-resources-limit',
        action="store",
        help=('If more resources are discovered, only short representations '
              'will be printed'),
        default=300, type=int)

    parser.add_argument('--sockettimeout', action="store", type=int,
        help="Set the socket timeout")

    parser.add_argument('-o', '--only-negotiate', action="store_true",
        help='Only do content negotiation for given URIs and print the '
             'response headers')

    def check_uri(url):
        if not is_valid_url(url):
            raise argparse.ArgumentTypeError("%r is not a valid URL" % url)
        return url
    parser.add_argument('url', action="store", nargs='+', type=check_uri,
        help="Pass a list of URIs. ldtools will crawl them one by one")

    return parser


def main():
    parser = get_parser()
    results = parser.parse_args()

    set_logger(results.verbosity)

    # customize Origin.objects.post_create_hook for performance reasons
    def custom_post_create_hook(origin):
        origin.timedelta = datetime.timedelta(minutes=5)
        return origin
    Origin.objects.post_create_hook = custom_post_create_hook

    url_count = len(results.url)

    if url_count > 1:
        logger.info("Retrieving content of %s URLs" % url_count)

    if results.follow_all:
        only_follow_uris = None
        logging.info("Following all URIs")
    elif results.follow_uris:
        only_follow_uris = results.follow_uris
        logging.info("Following values matching: %s"
                     % ", ".join(only_follow_uris))
    else:
        only_follow_uris = []

    if results.sockettimeout:
        import socket
        logger.info("Setting socket timeout to %s" % results.sockettimeout)
        socket.setdefaulttimeout(results.sockettimeout)


    for url in results.url:
        url = hash_to_slash_uri(rdflib.URIRef(url))
        logger.info("Retrieving content of %s" % url)
        origin, created = Origin.objects.get_or_create(url)

        if results.only_negotiate:
            try:
                import urllib2
                data = origin.backend.GET(uri=origin.uri,
                    backend_httphandler=urllib2.HTTPHandler(debuglevel=1))
            except Exception as e:
                print e.message
        else:
            origin.GET(only_follow_uris=only_follow_uris, raise_errors=False)

    if results.only_negotiate:
        sys.exit(0)

    if results.depth:
        for round in range(results.depth):
            for origin in Origin.objects.all():
                origin.GET(only_follow_uris=only_follow_uris,
                           raise_errors=False)

    all_resources = Resource.objects.all()
    if (len(all_resources) > results.print_detailled_resources_limit
        or results.only_print_uris):
        logger.warning("ldtools discovered more than %s Resource objects, "
            "only printing titles" % results.print_detailled_resources_limit)
        for resource in all_resources:
            print resource
    else:
        print
        for r in all_resources:
            if hasattr(r, "_has_changes"): delattr(r, "_has_changes")
            if hasattr(r, "pk"): delattr(r, "pk")
            pprint.pprint(r.__dict__); print
