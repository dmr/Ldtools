import urlparse
import logging
logger = logging.getLogger(__name__)

import rdflib
from rdflib.namespace import split_uri


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


def catchKeyboardInterrupt(func):
    def dec(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt, _e:
            print 'KeyboardInterrupt --> Cancelling %s' % func
    return dec


def safe_dict(d):
    """Recursively clone json structure with UTF-8 dictionary keys"""
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v))
        for k,v in d.iteritems()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d


def reverse_dict(dct):
    res = {}
    for k,v in dct.iteritems():
        res[v] = k
    return safe_dict(res)


def predicate2pyattr(predicate, namespace_short_notation_reverse_dict):
    prefix, propertyname = split_uri(predicate)
    assert prefix
    assert propertyname

    #if not "_" in propertyname:
    #    logger.info("%s_%s may cause problems?" % (prefix, propertyname))

    if not prefix in namespace_short_notation_reverse_dict:
        logger.warning("%s cannot be shortened" % predicate)
        return predicate

    if namespace_short_notation_reverse_dict[prefix] == "":
        return propertyname
    else:
        return u"%s_%s" % (namespace_short_notation_reverse_dict[prefix],
                           propertyname)


def pyattr2predicate(pyattr, namespace_dict):
    if pyattr.startswith(u"http://"):
        return rdflib.URIRef(pyattr)

    splitlist = pyattr.split("_")

    # this code ckecks pyattr for namespace prefix limitations
    splitlistlen = len(splitlist)
    if splitlistlen == 1:
        # attribute "homepage" --> check if "" in namespace_dict
        prefix = ""
        property_name = splitlist[0]
    elif (splitlistlen > 2 and
          u"_".join(splitlist[0:2]) in namespace_dict):
        # manually handle 'wgs84_pos_lat'
        # http://www.geonames.org/ontology#
        prefix = u"_".join(splitlist[0:2])
        property_name = u"_".join(splitlist[2:])
        assert prefix, pyattr
    else:
        prefix = splitlist[0]
        property_name = u"_".join(splitlist[1:])
        assert prefix, pyattr

    assert property_name, pyattr

    # i.e.: foaf defined as "" --> manually handle 'mbox_sha1sum'
    if "" in namespace_dict:
        if not prefix in namespace_dict:
            logger.error("problem. %s, %s" % (prefix, pyattr))
            return rdflib.URIRef(u"%s%s"
            % (namespace_dict[""], pyattr))
    else:
        assert namespace_dict[prefix], (u"%s not in namespace_dict") % prefix

    return rdflib.URIRef(u"%s%s" % (namespace_dict[prefix], property_name))
