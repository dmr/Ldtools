# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

try:
    unicode
except NameError:
    basestring = unicode = str  # Python 3

import datetime
import rdflib
from xml.sax._exceptions import SAXParseException
import logging

from rdflib import compare

from ldtools.backends import RestBackend, ContentNegotiationError
from ldtools.resource import Resource
from ldtools.metamodels import Manager, Model
from ldtools.models import URIRefField, ObjectField
from ldtools.utils import (
    get_rdflib_uriref, get_slash_url,
    catchKeyboardInterrupt, is_valid_url, reverse_dict, safe_dict,
    pyattr2predicate,
    urllib2
)
from ldtools.helpers import my_graph_diff

logger = logging.getLogger(__name__)


class OriginManager(Manager):
    def post_create_hook(self, origin):
        # hook to be overwritten but using application
        # origin.timedelta = datetime.timedelta(minutes=2)
        return origin

    def create(self, uri, BACKEND=None):
        uri = get_rdflib_uriref(uri)
        if not uri == get_slash_url(uri):
            msg = ("URI passed to Origin Manager was not a slash URI: %s. "
                   "Fixed now." % uri)
            logger.debug(msg)
            uri = get_slash_url(uri)

        backend = BACKEND if BACKEND else RestBackend()
        origin = super(OriginManager, self).create(
            pk=uri, uri=uri,
            backend=backend)
        return self.post_create_hook(origin)

    def get(self, uri, **kwargs):
        """Retrieves Origin object from Store"""
        uri = get_rdflib_uriref(uri)
        return super(OriginManager, self).get(pk=uri)

    def get_or_create(self, uri, **kwargs):

        uri = get_rdflib_uriref(uri)
        if not uri == get_slash_url(uri):
            msg = ("URI passed to Origin Manager was not a slash URI: %s. "
                   "Fixed now." % uri)
            logger.warning(msg)
            uri = get_slash_url(uri)

        try:
            if kwargs:
                logger.warning("kwargs are ignored for get.")
            return self.get(uri), False
        except self.model.DoesNotExist:
            return self.create(uri, **kwargs), True

    @catchKeyboardInterrupt
    def GET_all(self, depth=2, **kwargs):
        """Crawls or Re-Crawls all Origins. Passes Arguments to GET"""
        func = lambda origin: True if not origin.processed else False
        for _i in range(depth):
            crawl = filter(func, self.all())
            if not isinstance(crawl, list):  # py3
                crawl = list(crawl)
            if crawl:
                for origin in crawl:
                    origin.GET(raise_errors=False, **kwargs)


def triple_yield(resource, property, v):
    if isinstance(v, resource.__class__):
        # If object is referenced in attribute, "de-reference"
        return ((resource._uri, property, v._uri))
    else:
        if not hasattr(v, "n3"):
            # print only newly added values without the correct
            # type are handled here

            # float has no attribute startswith
            if (hasattr(v, "startswith") and v.startswith("http://")):
                v = rdflib.URIRef(v)
            else:
                v = rdflib.Literal(v)
        return ((resource._uri, property, v))


class Origin(Model):
    uri = URIRefField()
    objects = OriginManager()
    backend = ObjectField()

    def add_error(self, error):
        if not hasattr(self, 'errors'):
            self.errors = []
        self.errors.append(error)

    def __init__(self, pk=None, **kwargs):
        super(Origin, self).__init__(pk=pk, **kwargs)
        self.processed = False

    def __unicode__(self):
        extras = []
        if hasattr(self, 'errors'):
            for error in self.errors:
                extras.append(unicode(error))
        if self.processed:
            extras.append(u"Processed")

        return u" ".join([
            unicode(self.uri),
            self.backend.__class__.__name__,
        ] + extras)

    def GET(
        self,
        GRAPH_SIZE_LIMIT=30000,
        only_follow_uris=None,
        handle_owl_imports=False,
        raise_errors=True,
        skip_urls=None,
        httphandler=None,
    ):

        if not self.uri:
            raise Exception("Please provide URI first")

        if skip_urls is not None and self.uri.encode("utf8") in skip_urls:
            self.add_error("Skipped")
            self.processed = True
            return

        logger.info(u"GET %s..." % self.uri)

        if self.has_unsaved_changes():
            if self.processed:
                raise Exception("Please save all changes before querying "
                                "again. Merging not supported yet")
            else:
                logger.warning("There were Resource objects created before "
                               "processing the resource's origin.")

        now = datetime.datetime.now()
        # self.timedelta = datetime.timedelta(minutes=1)
        if hasattr(self, "timedelta") and hasattr(self, 'last_processed'):
            time_since_last_processed = now - self.last_processed
            if (time_since_last_processed < self.timedelta):
                logger.info(
                    "Not processing %s again because was processed only %s ago" % (self.uri, time_since_last_processed))
                return
            self.last_processed = now

        try:
            data = self.backend.GET(self.uri, httphandler=httphandler)
        except urllib2.HTTPError as e:
            if e.code in [
                401,
                403,
                503,  # Service Temporarily Unavailable
                404,  # Not Found
            ]:
                self.add_error(e.code)
            if raise_errors:
                raise e
            else:
                return
        except urllib2.URLError as e:
            self.add_error("timeout")
            if raise_errors:
                raise e
            else:
                return
        except ContentNegotiationError as e:
            logger.error(e.message)
            if raise_errors:
                raise e
            else:
                return

        graph = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        try:
            if data:
                # Important: Do not pass data=data without publicID=uri because
                # relative URIs (#deri) won't be an absolute uri in that case!
                publicID = self.uri

                reference_time = datetime.datetime.now()

                graph.parse(data=data, publicID=publicID, format=self.backend.format)

                now = datetime.datetime.now()
                self.graph_parse_time = now - reference_time

                # normal rdflib.compare does not work correctly with
                # ConjunctiveGraph, unless there is only one graph within that
        except SAXParseException as e:
            self.add_error("SAXParseException")
            logger.error("SAXParseException: %s" % self)
            if raise_errors:
                raise e
            else:
                return
        except rdflib.exceptions.ParserError as e:
            self.add_error("ParserError")
            logger.error("ParserError: %s" % self)
            if raise_errors:
                raise e
            else:
                return
        except IOError as e:
            self.add_error("IOError")
            logger.error("IOError: %s" % self)
            if raise_errors:
                raise e
            else:
                return

        self.processed = True

        if hasattr(self, "errors"):
            delattr(self, "errors")

        g_length = len(graph)

        if g_length > 0:
            if len(list(graph.contexts())) > 1:
                # detect problems with graph contexts: rdflib can only
                # compare graphs with one context. If a graph has more
                # contexts this might result in wrong comparisons of graphs
                # Still ignored here as ldtools is more robust by doing so.
                logger.error("The graph has more than one context. This"
                             "might cause problems comparing the graphs!")

        if g_length > GRAPH_SIZE_LIMIT:
            logger.error("Maximum graph size exceeded. Thr graph is %s "
                         "triples big. Limit is set to %s. The aquired "
                         "graph exceeds that! Pass GRAPH_SIZE_LIMIT to set it "
                         "differently." % (g_length, GRAPH_SIZE_LIMIT))
            return

        if hasattr(self, "_graph"):
            # we already assured that there are no unsaved_changes
            # --> get_graph() == _graph

            logger.info(u"Already crawled: %s. Comparing graphs..." % self.uri)

            if compare.to_isomorphic(self._graph) ==\
               compare.to_isomorphic(graph):
                return
            else:
                logging.warning("GET retrieved updates for %s!" % self.uri)
                my_graph_diff(self._graph, graph)

                for resource in self.get_resources():
                    resource.delete()
                delattr(self, "handled")

        if hasattr(self, "handled"):
            return

        self._graph = graph

        graph_handler = GraphHandler(
            only_follow_uris=only_follow_uris,
            handle_owl_imports=handle_owl_imports,
            origin=self)
        graph_handler.populate_resources(graph=graph)

        self.handled = True

    def get_graph(self):
        """Processes every Resource and Property related to 'self'"""
        #rdflib.ConjunctiveGraph because rdflib.Graph does not allow
        # usage of parsing plugins
        graph = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        if not hasattr(self, '_graph'):
            if hasattr(self, 'errors') and len(self.errors) != 0:
                logging.error("Origin %s has Errors --> can't process "
                              ".get_graph()" % self.uri)
                return graph
            assert hasattr(self, "_graph"), ("graph has to be processed before executing get_graph()")

        # Problems with namespacemapping here:
        #  1) namespace bindings are not really necessary to validate
        #     isomorphic graphs but the resulting graph is is different
        #     if they miss
        #  2) doesn't detect duplicate definitions of namespaces
        namespace_dict = safe_dict(dict(self._graph.namespace_manager.namespaces()))

        for prefix, namespace in safe_dict(namespace_dict).items():
            graph.bind(prefix=prefix, namespace=namespace)
        new_ns = dict(graph.namespace_manager.namespaces())

        assert namespace_dict == new_ns, [(k, v) for k, v in safe_dict(namespace_dict).items() if not k in safe_dict(new_ns).keys()]

        for resource in self.get_resources():
            # __dict__ converts rdflib.urirefs to strings for keys -->
            # convert back the dict's items back to uriref
            # {'foaf': 'http:/....', ...}

            for property, values in resource.__dict__.items():

                # skip internals
                if str(property).startswith("_") or property == "pk":
                    continue

                if property.startswith("http://"):
                    property = rdflib.URIRef(property)
                else:
                    property = pyattr2predicate(property, namespace_dict)

                assert isinstance(property, rdflib.URIRef), "property %s is not a URIRef object" % property

                if isinstance(values, set):
                    for v in values:
                        graph.add(triple_yield(resource, property, v))
                else:
                    v = values
                    graph.add(triple_yield(resource, property, v))

        return graph

    def get_resources(self):
        return Resource.objects.filter(_origin=self)

    def has_unsaved_changes(self):
        # objects with changed attributes exist
        if any(
            resource._has_changes
            for resource in self.get_resources()
            if (hasattr(resource, '_has_changes') and
                resource._has_changes is True)
        ):
            return True
        return False

    def PUT(self):
        assert self.processed
        if hasattr(self, "errors"):
            assert not self.errors, ("There were errors fetching the "
                                     "resource. PUT not possible")

        if not self.has_unsaved_changes():
            logging.error("Nothing to PUT for %s!" % self.uri)
            return

        graph = self.get_graph()
        data = graph.serialize(format=self.backend.format)

        self.backend.PUT(data=data)

        for resource in Resource.objects.filter(_has_changes=True):
            resource._has_changes = False

        assert not self.has_unsaved_changes(), "something went wrong"


def check_shortcut_consistency():
    """Checks every known Origin for inconsistent namespacemappings"""
    global_namespace_dict = {}
    for origin in Origin.objects.all():
        if hasattr(origin, "_graph"):
            for k, v in safe_dict(origin._graph.namespace_manager.namespaces()):
                if k in global_namespace_dict:
                    assert global_namespace_dict[k] == v
                else:
                    global_namespace_dict[k] = v


class GraphHandler(object):
    def __init__(self, origin, only_follow_uris, handle_owl_imports):
        self.origin = origin
        self.handle_owl_imports = handle_owl_imports
        if only_follow_uris is not None:
            only_follow_uris = [
                rdflib.URIRef(u) if not
                isinstance(u, rdflib.URIRef) else u for u in only_follow_uris
            ]
        self.only_follow_uris = only_follow_uris

    def populate_resources(self, graph):
        namespace_short_notation_reverse_dict = {
            unicode(rdflib_url): prefix
            for rdflib_url, prefix in reverse_dict(
                safe_dict(dict(graph.namespace_manager.namespaces()))
            ).items()
        }
        reference_time = datetime.datetime.now()

        for subject, predicate, obj_ect in graph:
            assert hasattr(subject, "n3")

            # workaround for rdflib's unicode problems
            assert predicate.encode('utf8')

            if self.handle_owl_imports:
                if (predicate == rdflib.OWL.imports and type(obj_ect) == rdflib.URIRef):
                    uri = get_slash_url(obj_ect)
                    origin, created = Origin.objects.get_or_create(uri=uri)

                    logger.info("Interrupting to process owl:imports %s"
                                "first" % (origin.uri))
                    origin.GET()

            if ((
                self.only_follow_uris is not None and predicate in self.only_follow_uris
            ) or self.only_follow_uris is None):
                if type(obj_ect) == rdflib.URIRef:
                    # wrong scheme mailto, tel, callto --> should be Literal?
                    if is_valid_url(obj_ect):
                        obj_uriref = get_slash_url(obj_ect)
                        Origin.objects.get_or_create(uri=obj_uriref)

            resource, _created = Resource.objects.get_or_create(uri=subject, origin=self.origin)
            resource._add_property(predicate, obj_ect, namespace_short_notation_reverse_dict)

        now = datetime.datetime.now()
        self.origin.graph_handler_time = now - reference_time

        for resource in self.origin.get_resources():
            resource._has_changes = False
