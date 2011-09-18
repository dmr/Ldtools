import rdflib
import logging
import urlparse

logger = logging.getLogger("ldtools")


def is_valid_url(uri):
    if not uri:
        raise UriNotValid("An empty url is not valid")

    parsed = urlparse.urlparse(uri)

    if not parsed.scheme in ["http", "https"]:
        logger.error("Not a URL. scheme is wrong: %s" % parsed.scheme)
        return False

    # TODO: implement canonalization of URI. Problem: graph comparison not
    # trivial

    uri = urlparse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                         parsed.params, parsed.query,""))

    if not "http" in uri:
        return False
    return True


class UriNotValid(Exception):
    "Given Uri is not valid"
    silent_variable_failure = True


def get_rdflib_uriref(uri):
    """Returns Uri that is valid and canonalized or raises Exception"""

    if isinstance(uri, rdflib.BNode):
        return uri

    elif isinstance(uri, rdflib.Literal):
        raise UriNotValid("Cannot convert Literals")

    elif isinstance(uri, rdflib.URIRef):
        uriref = uri

    else:
        if logger:
            logger.debug(u"Converting %s to URIRef" % uri)
        uriref = rdflib.URIRef(uri)

    # check for rdflib encoding bug
    if not uriref.encode('utf8'):
        raise UriNotValid("Not valid: %s" % uriref)

    # check for parser errors
    if uriref.startswith('#'):
        raise UriNotValid("%s starts with '#'. Check your Parser" % uriref)

    return uriref


def get_slash_url(uri):
    """Converts Hash to Slash uri http://www.w3.org/wiki/HashURI"""

    assert is_valid_url(uri)
    if not isinstance(uri, rdflib.URIRef):
        uri = get_rdflib_uriref(uri)

    parsed = urlparse.urlparse(uri)
    uri = urlparse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                         parsed.params, parsed.query,""))
    return rdflib.URIRef(uri)
