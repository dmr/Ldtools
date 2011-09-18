# -*- coding: utf-8 -*-

import copy
import datetime
import logging
import mimetypes
import rdflib
import socket
import urlparse
from xml.sax._exceptions import SAXParseException

from rdflib.namespace import split_uri
from rdflib import compare

import helpers
import utils

# set socket timeout. URLError will occur if time passed
socket.setdefaulttimeout(30)

logger = logging.getLogger(__name__)


def safe_dict(d):
    """Recursively clone json structure with UTF-8 dictionary keys"""
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v))
                     for k,v in d.iteritems()])
    elif isinstance(d, list):
        return [safe_dict(x) for x in d]
    else:
        return d


def catchKeyboardInterrupt(func):
    def dec(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt, _e:
            print 'KeyboardInterrupt --> Cancelling %s' % func
    return dec


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


from backends import *
from models import *


class ResourceManager(Manager):

    def get_pk(self, origin_uri, uri):
        return origin_uri+uri

    def create(self, uri, origin, **kwargs):

        assert isinstance(origin, Origin), "Origin instance required"
        assert origin.processed, ("Origin has to be processed "
            "before creating more Resource objects: origin.GET()")

        uri = utils.get_rdflib_uriref(uri)

        pk = self.get_pk(origin_uri=origin.uri, uri=uri)
        return super(ResourceManager, self).create(
            pk=pk, _uri=uri, _origin=origin, **kwargs)

    def get_authoritative_resource(self, uri,
                                   create_nonexistent_origin=True):
        """Tries to return the Resource object from the authoritative origin"""

        uri = utils.get_rdflib_uriref(uri)
        origin_uri = utils.get_slash_url(uri)

        authoritative_origin = Origin.objects.filter(uri=origin_uri)
        authoritative_origin_list = list(authoritative_origin)
        if len(authoritative_origin_list) == 1:
            origin = authoritative_origin_list[0]
        else:
            if create_nonexistent_origin:
                origin, created = Origin.objects.get_or_create(uri=origin_uri)
            else:
                raise self.model.DoesNotExist("No authoritative "
                "Resource found for %s" %uri)

        if not origin.has_unsaved_changes():
            origin.GET(only_follow_uris=[], raise_errors=False)

        authoritative_resource = self.get(uri=uri, origin=origin)
        return authoritative_resource

    def get(self, uri, origin=None):
        """If the authoratative Origin to the Resource does not exist and no
        origin is given then DoesNotExist is returned. Assumption is
        to only trust validated sources.

        Alternative: this could point to source with most parameters given
        etc because user may want to just have the Resource with most
        content/know everything about a uri.
        --> If DoesNotExist occurs Resources with uri might still
        exist but no validated Resources exist.
        """

        uri = utils.get_rdflib_uriref(uri)

        if not origin:
            filter_result = list(self.filter(_uri=uri))

            if not filter_result:
                raise self.model.DoesNotExist

            if len(filter_result) == 1:
                # return only match
                return filter_result[0]
            else:
                raise self.model.DoesNotExist("Please pass the exact "
                    "Origin. The Resource you are looking for is "
                    "provided by the Origins: %s"
                    % ", ".join([unicode(r._origin.uri)
                                 for r in filter_result]))

        assert isinstance(origin, Origin), origin
        pk = self.get_pk(origin_uri=origin.uri, uri=uri)
        return super(ResourceManager, self).get(pk=pk)
        assert 0, "implement!"

    def get_or_create(self, uri, origin=None):
        uri = utils.get_rdflib_uriref(uri)
        try:
            return self.get(uri=uri, origin=origin), False
        except self.model.DoesNotExist:
            return self.create(uri=uri, origin=origin), True


class Resource(Model):

    _uri = URIRefField()
    _origin = ObjectField()
    objects = ResourceManager()

    def __unicode__(self):
        str = [u"%r" % self._uri.encode('utf8')]
        if hasattr(self, "_origin"):
            assert isinstance(self._origin, Origin)
            if self.is_authoritative_resource():
                str.append(u"*authoritative*")
            else:
                str.append(u"[%r]" % self._origin.uri.encode("utf8"))
        return " ".join(str)

    def is_authoritative_resource(self):
        """Definition "authoritative" according to
        "SAOR: Authoritative Reasoning for the Web"
        http://www.springerlink.com/content/w47632745gm76x01/"""
        if isinstance(self._uri, rdflib.BNode):
            return True

        if utils.get_slash_url(self._uri) == self._origin.uri:
            return True

    def _add_property(self, predicate, object,
                      namespace_short_notation_reverse_dict):

        assert isinstance(predicate, rdflib.URIRef),\
            "Not an URIRef: %s" % predicate
        assert hasattr(predicate, "n3"),\
            "property %s is not a rdflib object" % predicate

        # add Resource object directly instead of uriref
        # hash function is important for that!
        is_resource = False
        if isinstance(object, rdflib.BNode):
            is_resource = True
        elif isinstance(object, rdflib.URIRef):
            if not isinstance(object, rdflib.Literal):
                o = urlparse.urlparse(object)
                if o.scheme == "http":
                    is_resource = True
                else:
                    logger.debug("Not a Resource URI because not valid: %s "
                                 "--> should be rdflib.Literals?" % object)

        predicate = predicate2pyattr(predicate,
                                     namespace_short_notation_reverse_dict)

        if is_resource:
            logger.debug("%s . %s = Resource( %s )"
                         % (self._uri, predicate, object))
            object, _created = Resource.objects.get_or_create(
                uri=object, origin=self._origin)

            if not hasattr(object, "_reverse"):
                object._reverse = {}
            if predicate in object._reverse:
                if not isinstance(object._reverse[predicate], set):
                    object._reverse[predicate] = set(
                        [object._reverse[predicate]])
                object._reverse[predicate].add(self)
            else:
                object._reverse[predicate] = self

        if hasattr(self, predicate):
            attr = getattr(self, predicate)
            if not type(attr) == set:
                setattr(self, predicate, set([attr]))
                attr = getattr(self, predicate)
            attr.add(object)
            assert object in getattr(self, predicate)
        else:
            setattr(self, predicate, object)
            attr = getattr(self, predicate)

        assert str(predicate) in self.__dict__

    def __setattr__(self, key, value):
        if key == "_has_changes":
            Model.__setattr__(self, key, value)
            return

        if key in self._meta.fields:
            field = self._meta.fields.get(key)
            if field and value:
                value = field.to_python(value)
        elif not key.startswith("_") and not key == "pk":
            # Assumption: rdf attributes do not start with "_"
            pass

        Model.__setattr__(self, key, value)
        self._has_changes = True

    def delete(self):
        if hasattr(self, "pk") and self.pk is not None:
            self.__class__.objects._storage.__delitem__(self.pk)

    def save(self):
        created = not self.pk
        if created:
            assert 0, ("Please use Resource.objects.create() to create "
                       "Resource objects!")
        assert self in Resource.objects.filter(_origin=self._origin)
        #defined_values = dict((name, getattr(self, name)) for name in
        # self._meta.fields.iterkeys())
        self.update() #**values)

    def update(self):
        self._origin.PUT()
        self._has_changes = False


class OriginManager(Manager):

    def post_create_hook(self, origin):
        # hook to be overwritten but using application
        # origin.timedelta = datetime.timedelta(minutes=2)
        return origin

    def create(self, uri, BACKEND=None):

        uri = utils.get_rdflib_uriref(uri)
        if not uri == utils.get_slash_url(uri):
            msg = ("URI passed to Origin Manager was not a slash URI: %s. "
                   "Fixed now." % uri)
            logger.debug(msg)
            uri = utils.get_slash_url(uri)

        backend = BACKEND if BACKEND else RestBackend()
        origin = super(OriginManager, self).create(pk=uri, uri=uri,
                                                 backend=backend)
        return self.post_create_hook(origin)

    def get(self, uri, **kwargs):
        """Retrieves Origin object from Store"""
        uri = utils.get_rdflib_uriref(uri)
        return super(OriginManager, self).get(pk=uri)

    def get_or_create(self, uri,
                      **kwargs):

        uri = utils.get_rdflib_uriref(uri)
        if not uri == utils.get_slash_url(uri):
            msg = ("URI passed to Origin Manager was not a slash URI: %s. "
                   "Fixed now." % uri)
            logger.warning(msg)
            uri = utils.get_slash_url(uri)

        try:
            if kwargs: logger.warning("kwargs are ignored for get.")
            return self.get(uri), False
        except self.model.DoesNotExist:
            return self.create(uri, **kwargs), True

    @catchKeyboardInterrupt
    def GET_all(self, depth=2, **kwargs):
        """Crawls or Re-Crawls all Origins. Passes Arguments to GET"""
        func = lambda origin: True if not origin.processed else False
        for _i in range(depth):
            crawl = filter(func, self.all())
            if crawl:
                for origin in crawl:
                    origin.GET(raise_errors=False, **kwargs)


class Origin(Model):

    uri = URIRefField()
    objects = OriginManager()
    backend = ObjectField()
    
    def add_error(self, error):
        if not hasattr(self, 'errors'): self.errors = []
        self.errors.append(error)

    def __init__(self, pk=None, **kwargs):
        super(Origin, self).__init__(pk=pk, **kwargs)
        self.processed = False

    def __unicode__(self):
        str = [unicode(self.uri)]
        str.append(self.backend.__class__.__name__)
        if hasattr(self, 'errors'):
            for error in self.errors:
                str.append(unicode(error))
        if self.processed:
            str.append(u"Processed")
        return u" ".join(str)

    def GET(self,
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
        #self.timedelta = datetime.timedelta(minutes=1)
        if hasattr(self, "timedelta") and hasattr(self, 'last_processed'):
            time_since_last_processed = now - self.last_processed
            if (time_since_last_processed < self.timedelta):
                logger.info("Not processing %s again because was processed "
                "only %s ago" % (self.uri, time_since_last_processed))
                return

        self.last_processed = now

        try:
            data = self.backend.GET(self.uri,
                                    httphandler=httphandler)
        except urllib2.HTTPError as e:
            if e.code in [
                    401,
                    403,
                    503, # Service Temporarily Unavailable
                    404, # Not Found
                    ]:
                self.add_error(e.code)
            if raise_errors: raise e
            else: return
        except urllib2.URLError as e:
            self.add_error("timeout")
            if raise_errors: raise e
            else: return
        except ContentNegotiationError as e:
            logger.error(e.message)
            if raise_errors: raise e
            else: return

        graph = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        try:
            if data:
                # Important: Do not pass data=data without publicID=uri because
                # relative URIs (#deri) won't be an absolute uri in that case!
                publicID = self.uri

                reference_time = datetime.datetime.now()

                graph.parse(data=data,
                            publicID=publicID,
                            format=self.backend.format)

                now = datetime.datetime.now()
                self.graph_parse_time = now - reference_time

                # normal rdflib.compare does not work correctly with
                # ConjunctiveGraph, unless there is only one graph within that
        except SAXParseException as e:
            self.add_error("SAXParseException")
            logger.error("SAXParseException: %s" % self)
            if raise_errors: raise e
            else: return
        except rdflib.exceptions.ParserError as e:
            self.add_error("ParserError")
            logger.error("ParserError: %s" % self)
            if raise_errors: raise e
            else: return
        except IOError as e:
            self.add_error("IOError")
            logger.error("IOError: %s" % self)
            if raise_errors: raise e
            else: return

        self.processed = True

        if hasattr(self, "errors"):
            delattr(self, "errors")

        g_length = len(graph)

        if g_length > 0:
            assert len(list(graph.contexts())) == 1

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

            if compare.to_isomorphic(self._graph) == \
               compare.to_isomorphic(graph):
                return
            else:
                logging.warning("GET retrieved updates for %s!" % self.uri)
                helpers.my_graph_diff(self._graph, graph)

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
                              ".get_graph()"
                    % self.uri)
                return graph
            assert hasattr(self, "_graph"), ("graph has to be "
                "processed before executing get_graph()")

        # Problems with namespacemapping here:
        #  1) namespace bindings are not really necessary to validate
        #     isomorphic graphs but the resulting graph is is different
        #     if they miss
        #  2) doesn't detect duplicate definitions of namespaces
        namespace_dict = dict(self._graph.namespace_manager.namespaces())

        for prefix, namespace in safe_dict(namespace_dict).items():
            graph.bind(prefix=prefix, namespace=namespace)
        new_ns = dict(graph.namespace_manager.namespaces())

        assert namespace_dict == new_ns, [(k, v)
            for k, v in safe_dict(namespace_dict).items() \
                if not k in safe_dict(new_ns).keys()]


        def do_yield_triple(resource, property, v):
            if isinstance(v, resource.__class__):
                # If object is referenced in attribute, "de-reference"
                return ((resource._uri, property, v._uri))
            else:

                if not hasattr(v, "n3"):
                    # print only newly added values without the correct
                    # type are handled here

                    # float has no attribute startswith
                    if (hasattr(v, "startswith")
                        and v.startswith("http://")
                        ):
                        v = rdflib.URIRef(v)
                    else:
                        v = rdflib.Literal(v)

                return ((resource._uri, property, v))


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

                assert isinstance(property, rdflib.URIRef), \
                    "property %s is not a URIRef object" % property

                if isinstance(values, set):
                    for v in values:
                        graph.add( do_yield_triple(resource, property, v) )
                else:
                    v = values
                    graph.add( do_yield_triple(resource, property, v) )

        return graph

    def get_resources(self):
        return Resource.objects.filter(_origin=self)

    def has_unsaved_changes(self):
        # objects with changed attributes exist
        if any(resource._has_changes
                for resource in self.get_resources()\
                    if (hasattr(resource, '_has_changes')
                        and resource._has_changes == True)):
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
            for k, v in dict(origin._graph.namespace_manager\
                        .namespaces()).items():
                if k in global_namespace_dict:
                    assert global_namespace_dict[k] == v
                else:
                    global_namespace_dict[k] = v


class GraphHandler(object):
    def __init__(self, origin, only_follow_uris, handle_owl_imports):
        self.origin=origin

        self.handle_owl_imports=handle_owl_imports
        if only_follow_uris is not None:
            only_follow_uris = [rdflib.URIRef(u) if not\
                isinstance(u, rdflib.URIRef) else u for u in only_follow_uris]
        self.only_follow_uris=only_follow_uris

    def populate_resources(self, graph):
        namespace_short_notation_reverse_dict = reverse_dict(dict(graph\
            .namespace_manager.namespaces()))

        reference_time = datetime.datetime.now()

        for subject, predicate, obj_ect in graph:
            assert hasattr(subject, "n3")

            # workaround for rdflib's unicode problems
            assert predicate.encode('utf8')

            if self.handle_owl_imports:
                if (predicate == rdflib.OWL.imports
                    and type(obj_ect) == rdflib.URIRef):

                    uri = utils.get_slash_url(obj_ect)
                    origin, created = Origin.objects.get_or_create(uri=uri)

                    logger.info("Interrupting to process owl:imports %s"
                                "first" % (origin.uri))
                    origin.GET()

            if ((self.only_follow_uris is not None
                 and predicate in self.only_follow_uris)
                or self.only_follow_uris is None):

                if type(obj_ect) == rdflib.URIRef:
                    # wrong scheme mailto, tel, callto --> should be Literal?
                    if utils.is_valid_url(obj_ect):
                        obj_uriref = utils.get_slash_url(obj_ect)
                        Origin.objects.get_or_create(uri=obj_uriref)

            resource, _created = Resource.objects.get_or_create(uri=subject,
                                                        origin=self.origin)
            resource._add_property(predicate, obj_ect,
                                   namespace_short_notation_reverse_dict)

        now = datetime.datetime.now()
        self.origin.graph_handler_time = now - reference_time

        for resource in self.origin.get_resources():
            resource._has_changes = False
