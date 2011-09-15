import rdflib
from rdflib import compare
import logging
import urlparse

logger = logging.getLogger("ldtools")

def my_graph_diff(graph1, graph2):
    """Compares graph2 to graph1 and highlights everything that changed.
    Colored if pygments available"""

    logger = logging.getLogger("ldtools")
    import difflib

    # quick fix for wrong type
    if not type(graph1) == type(graph2) == rdflib.Graph:
        if type(graph1) == rdflib.ConjunctiveGraph:
            g1contexts = list(graph1.contexts())
            assert len(g1contexts) == 1
            graph1 = g1contexts[0]
        if type(graph2) == rdflib.ConjunctiveGraph:
            g2contexts = list(graph2.contexts())
            assert len(g2contexts) == 1
            graph2 = g2contexts[0]


    # Return if both graphs are isomorphic
    iso1 = compare.to_isomorphic(graph1)
    iso2 = compare.to_isomorphic(graph2)

    if graph1.identifier == graph2.identifier:
        str_bit = u"The 2 '%s' Graphs" % graph1.identifier
    else:
        str_bit = (u"Graphs '%s' and '%s'"
                   % (graph1.identifier, graph2.identifier))

        # TODO remove later
        assert not are_isomorphic(graph1, graph2)

    if iso1 == iso2:
        logger.debug(u"%s are isomorphic" % str_bit)
        return

    print u"Differences between %s." % str_bit

    in_both, in_first, in_second = compare.graph_diff(iso1, iso2)

    def dump_nt_sorted(g):
        return sorted(g.serialize(format='nt').splitlines())

    sorted_first = dump_nt_sorted(in_first)
    sorted_second = dump_nt_sorted(in_second)

    diff = difflib.unified_diff(
        sorted_first,
        sorted_second,
        u'Original',
        u'Current',
        lineterm=''
    )

    try:
        from pygments import highlight
        from pygments.formatters import terminal
        from pygments.lexers import web

        lexer = web.XmlLexer()
        formatter = terminal.TerminalFormatter()
        print highlight(u'\n'.join(diff), lexer, formatter)
    except ImportError:
        logger.info("Install pygments for colored diffs")
        print u'\n'.join(diff)
    except UnicodeDecodeError:
        print u"Only in first", unicode(sorted_first)
        print u"Only in second", unicode(sorted_second)


def set_logger(verbosity_level):
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
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(handler)


    logger2 = logging.getLogger("ldtools._add_property")
    logger2.setLevel(logging.INFO)


    mapper = {1: logging.DEBUG,
              2: logging.INFO,
              3: logging.WARNING,
              4: logging.ERROR,
              5: None}
    try:
        log_level = mapper[verbosity_level]
    except KeyError:
        log_level = mapper[2]
    if log_level:
        logger.setLevel(log_level)
    return logger


def is_valid_url(uri):
    parsed = urlparse.urlparse(uri)

    if not parsed.scheme in ["http", "https"]:
        logging.error("wrong scheme %s" % parsed.scheme)
        return False

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
    if not uri:
        raise UriNotValid("uri is None")

    # TODO: implement canonalization: cut port 80, lowercase domain,
    # http and https is equal. Problem: graph comparison

    # Workaround for rdflib's handling of BNodes
    if isinstance(uri, rdflib.BNode):
        return uri

    if isinstance(uri, rdflib.Literal):
        raise UriNotValid("Cannot convert Literals")

    if isinstance(uri, rdflib.URIRef):
        uriref = uri
    else:
        if logger:
            logger.debug(u"Converting %s to URIRef" % uri)
        uriref = rdflib.URIRef(uri)

    # check if uri is valid
    # TODO: maybe not constrain here but at export?
    # TODO: move to "is_valid_uri" and delete here
    if not uriref.encode('utf8'):
        raise UriNotValid("Not valid: %s" % uriref)
    if uriref.startswith('#'):
        raise UriNotValid("%s starts with '#'. Check your Parser" % uriref)

    return uriref


def hash_to_slash_uri(uri):
    """Converts Hash to Slash uri http://www.w3.org/wiki/HashURI"""
    assert isinstance(uri, rdflib.URIRef)

    parsed = urlparse.urlparse(uri)

    assert parsed.scheme in ["http", "https"], parsed.scheme

    uri = urlparse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                         parsed.params, parsed.query,""))
    assert is_valid_url(uri)
    return rdflib.URIRef(uri)


def build_absolute_url(url, fragment):
    assert fragment.startswith("#"), fragment
    assert isinstance(url, rdflib.URIRef)

    parsed = urlparse.urlparse(url)
    print parsed
    if parsed.fragment:
        raise ValueError("Cannot add fragment to HashURI: %s + %s?"
                         % (url, fragment))
    url = urlparse.urlunparse((parsed.scheme, parsed.netloc,
        parsed.path if parsed.path else "/",
        parsed.params, parsed.query, fragment.strip("#")))
    assert is_valid_url(url)
    return rdflib.URIRef(url)