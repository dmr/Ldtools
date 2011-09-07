# -*- coding: utf-8 -*-

import copy
import datetime
import logging
import mimetypes
import rdflib
import socket;
from rdflib.namespace import split_uri
from rdflib import compare
from urlparse import urlparse
from xml.sax._exceptions import SAXParseException

import utils

# TODO: find a better way to set socket timeout
socket.setdefaulttimeout(5)

logger = logging.getLogger(__name__)


class UriNotValid(Exception):
    "Given Uri is not valid"
    silent_variable_failure = True


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
            print 'KeyboardInterrupt --> %s cancelled' % func
    return dec


def canonalize_uri(uriref):
    """Returns Uri that is valid or raises Exception"""
    if not uriref:
        raise UriNotValid("uri is None")

    # TODO: if I would implement canonalization following rfc (cut port,
    # lowercase domain, http and https is equal then I couldn't compare graphs
    # anymore

    if isinstance(uriref, rdflib.BNode):
        return uriref

    assert not isinstance(uriref, rdflib.Literal)

    if not uriref.encode('utf8'):
        raise UriNotValid("Not valid: %s" % uriref)

    if not hasattr(uriref, "n3"):
        logger.debug(u"Not an URIRef: %s, fixing that." % uriref)
        uriref = rdflib.URIRef(uriref)

    if uriref.startswith('#'):
        raise UriNotValid("%s starts with '#'. Check your Parser" % uriref)

    return uriref


def hash_to_slash_uri(uri):
    """Converts Hash to Slash uri http://www.w3.org/wiki/HashURI"""
    # TODO: replace with urlparse
    assert isinstance(uri, rdflib.URIRef)
    if '#' in uri:
        real_uri, hash_value = uri.split("#")
        assert real_uri
        return real_uri
    return uri


def reverse_dict(dct):
    # TODO rdflib.URIRef dict?
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
    # TODO: build urirefdict instead of unicodedict?

    if pyattr.startswith(u"http://"):
        return rdflib.URIRef(pyattr)

    splitlist = pyattr.split("_")

    # HACK: are there constrains for namespace prefixes?
    splitlistlen = len(splitlist)
    if splitlistlen == 1:
        # attribute "homepage" --> check if "" in namespace_dict
        prefix = ""
        property_name = splitlist[0]
    elif (splitlistlen > 2 and
        u"_".join(splitlist[0:2]) in namespace_dict):
        # http://www.geonames.org/ontology# defines 'wgs84_pos' --> \
        # 'wgs84_pos_lat' cannot be solved with approach we took until now
        prefix = u"_".join(splitlist[0:2])
        property_name = u"_".join(splitlist[2:])
        assert prefix, pyattr
    else:
        prefix = splitlist[0]
        property_name = u"_".join(splitlist[1:])
        assert prefix, pyattr

    assert property_name, pyattr

    # timbl foaf defines foaf as "" --> mbox_sha1sum makes problems here
    if "" in namespace_dict:
        if not prefix in namespace_dict:
            logger.error("problem. %s, %s" % (prefix, pyattr))
            return rdflib.URIRef(u"%s%s"
        % (namespace_dict[""], pyattr))
    else:
        assert namespace_dict[prefix], (u"%s not in namespace_dict. Trying to "
            "solve %s") % (prefix, pyattr)

    return rdflib.URIRef(u"%s%s"
        % (namespace_dict[prefix], property_name))


from backends import *
from models import *

######### Resource #########

class ResourceManager(Manager):

    def get_pk(self, origin_uri, uri):
        return origin_uri+uri

    def create(self, uri, origin, **kwargs):
        assert isinstance(origin, Origin), "Origin instance required"
        #assert origin.processed, ("Origin has to be processed before creating "
        #    "more Resource objects: origin.GET()")

        if uri.startswith("#"):
            assert not isinstance(uri, rdflib.BNode), \
                "bnode should not start with #"
            uri = rdflib.URIRef(origin.uri + uri)

        uri = canonalize_uri(uri)
        pk = self.get_pk(origin_uri=origin.uri, uri=uri)

        obj = super(ResourceManager, self).create(
            pk=pk, _uri=uri, _origin=origin, **kwargs
        )

        # move to tests
        if isinstance(uri, rdflib.BNode):
            assert isinstance(obj._uri, rdflib.BNode)

        assert not hasattr(obj, "_has_changes")

        return obj


    def get(self, uri, origin=None, return_authoritative_resource=True):
        """If the authoratative Origin to the Resource does not exist and no
        origin is given then DoesNotExist is returned. Assumption is
        to only trust validated sources.

        Alternative: this could point to source with most parameters given
        etc because user may want to just have the Resource with most
        content/know everything about a uri.
        --> If DoesNotExist occurs Resources with uri might still
        exist but no validated Resources exist.
        """
        uri = canonalize_uri(uri)

        if not origin:
            filter_result = list(self.filter(_uri=uri))

            if not filter_result:
                raise self.model.DoesNotExist

            if len(filter_result) == 1:
                # return only match
                return filter_result[0]
            else:
                if return_authoritative_resource:
                    # try to return best match
                    authoritative_resource = None
                    for resource in filter_result:
                        if uri.startswith(resource._origin.uri):
                            authoritative_resource = resource
                            break
                    if authoritative_resource:
                        return authoritative_resource
                    else:
                        raise self.model.DoesNotExist("No authoritative "
                            "Resource found for %s" %uri)
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

    def get_or_create(self, uri, origin=None, auto_origin=False):
        uri = canonalize_uri(uri)
        if auto_origin:
            assert not origin, "Either origin or auto_origin, not both"
            origin_uri = hash_to_slash_uri(uri)
            origin, _origin_created = Origin.objects\
                .get_or_create(uri=origin_uri)

        try:
            return self.get(uri=uri, origin=origin), False
        except self.model.DoesNotExist:
            return self.create(uri=uri, origin=origin), True


class Resource(Model):

    _uri = URIRefField()
    _origin = ObjectField()
    objects = ResourceManager()

    def __unicode__(self):
        str = u"%s" % self._uri
        if hasattr(self, 'foaf_name'):
            str += u' "%s"' % unicode(self.foaf_name)
            if len(self.foaf_name) > 1: str += u",..."
        if hasattr(self, "_origin") and isinstance(self._origin, Origin):
            str += u" [%r]" % self._origin.uri.encode("utf8")
        return str

    def get_attributes(self):
        dct = copy.copy(self.__dict__)
        for attr in [u"pk",
            u"_origin",
            u"_uri",
            u"_reverse",
            u"_has_changes"]:
            if hasattr(self, attr):
                dct.pop(attr)
        return dct

    def _add_property(self, predicate, object,
                      namespace_short_notation_reverse_dict):
        assert isinstance(predicate, rdflib.URIRef),\
            "Not an URIRef: %s"%predicate
        assert hasattr(predicate, "n3"),\
            "property %s is not a rdflib object" % predicate

        # add Resource object directly instead of uriref
        # hash function is important for that!
        is_resource = False
        if isinstance(object, rdflib.BNode):
            is_resource = True
        elif isinstance(object, rdflib.URIRef):
            if not isinstance(object, rdflib.Literal):
                o = urlparse(object)
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
                    object._reverse[predicate] = set([object._reverse[predicate]])
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
            #assert attr == object

        # TODO: this might cause UnicodeDecodeErrors
        #logger.debug(u"Contribute_to_object %s: %s = %s"
        #    % (self, predicate.encode('utf8'), attr))
        
        # TODO: introduce rdflib.Literal dict or force_unicode when
        # reconverting from __dict__?
        assert str(predicate) in self.__dict__

    def _tripleserialize_iterator(self,
                                  namespace_dict):
        for property, values in self.__dict__.items():

            # skip internals
            if str(property).startswith("_") or property == "pk":
                continue

            if property.startswith("http://"):
                property = rdflib.URIRef(property)
            else:
                property = pyattr2predicate(property, namespace_dict)

            assert hasattr(property, "n3"), \
                "property %s is not a rdflib object" % property

            if isinstance(values, set):
                for v in values:
                    if isinstance(v, self.__class__):
                        # If object is referenced in attribute, "de-reference"
                        yield((self._uri, property, v._uri))
                    else:
                        yield((self._uri, property, v))
            else:
                v = values
                if isinstance(v, self.__class__):
                    # If object is referenced in attribute, "de-reference"
                    yield((self._uri, property, v._uri))
                else:
                    yield((self._uri, property, v))


    def __setattr__(self, key, value):
        # TODO: is there a better way to validate attributes?
        if key in self._meta.fields:
            field = self._meta.fields.get(key)
            if field and value:
                value = field.to_python(value)
        elif not key.startswith("_") and not key == "pk": # TODO: rename to_pk?
            # rdf properties here
            self._has_changes = True
        Model.__setattr__(self, key, value)

    def delete(self):
        if hasattr(self, "_has_changes"):
            assert not self._has_changes
        assert hasattr(self, "pk") and self.pk is not None
        # TODO: use Collector objects as django does
        self.__class__.objects._storage.__delitem__(self.pk)

    def save(self):
        # TODO: introduce "clean" to make sure only valid properties modified
        created = not self.pk
        if created:
            assert 0, ("Please use Resource.objects.create() to create Resource"
                       "objects!")
            #assert not self.__class__.objects.get(self.uri, self.origin)
            #self = self.__class__.objects.create(**self.get_attributes())

        # TODO: write tests for the following lines
        assert self in Resource.objects.filter(_origin=self._origin)

        if self in Resource.objects.filter(_origin=self._origin,
                _has_changes=True):
            assert len(list(Resource.objects.filter(_origin=self._origin,
                _has_changes=True))) == 1
        else:
            logging.info("New resource object was created")

        #values = dict((name, getattr(self, name)) for name in \
        #        self._meta.fields.iterkeys())
        self.update() #**values)

    def update(self):
        self._origin.PUT()
        self._has_changes = False


######### Origin #########

class OriginManager(Manager):

    def create_hook(self, uri):
        assert not '#' in uri, ("HashURI not allowed as Origin: %s. Maybe "
            "you are looking for "
            "Resource.objects.get_or_create(...,auto_origin=True)?" % uri)

    def create(self, uri, BACKEND=None):
        uri = canonalize_uri(uri)
        self.create_hook(uri)
        backend = BACKEND if BACKEND else RestBackend()
        return super(OriginManager, self).create(pk=uri, uri=uri,
                                                 backend=backend)

    def get(self, uri, **kwargs):
        """Retrieves Origin object from Store"""
        uri = canonalize_uri(uri)
        return super(OriginManager, self).get(pk=uri)

    def get_or_create(self, uri, **kwargs):
        uri = canonalize_uri(uri)
        assert str(uri) == str(hash_to_slash_uri(uri))
        try:
            if kwargs:
                logger.warning("kwargs not supportet in get")
            return self.get(uri), False
        except self.model.DoesNotExist:
            return self.create(uri, **kwargs), True

    @catchKeyboardInterrupt
    def GET_all(self, depth=2, **kwargs):
        """Crawls or Re-Crawls all Origins. Passes Arguments to GET"""
        # TODO: limit crawling speed
        assert depth<5
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
        self.stats = {}
        self.processed = False

    def __unicode__(self):
        str = u"%s" % unicode(self.uri)
        str += " %s" % self.backend.__class__.__name__
        if hasattr(self, 'errors'):
            for error in self.errors:
                str += u" %s" % error
        if self.processed:
            str += u" Processed"
        return str

    def GET(self,
            GRAPH_SIZE_LIMIT=30000,
            only_follow_uris=None,
            handle_owl_imports=False,
            skip_urls=None,
            raise_errors=True,
            ):

        if not self.uri:
            raise Exception("Please provide URI first")

        logger.info(u"GET %s..." % self.uri)

        if self.has_unsaved_changes():
            if self.processed:
                raise Exception("Please save all changes before querying "
                                "again. Merging not supported yet")
            else:
                logger.warning("There were Resource objects created before "
                               "processing the resource's origin.")

        if skip_urls is not None and str(self.uri) in skip_urls:
            self.add_error("Skipped")
            self.processed = True
            return

        self.stats['last_processed'] = datetime.datetime.now()

        try:
            data = self.backend.GET(self.uri)
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

        if not data:
            self.processed = True
            return

        assert self.backend.format, "format is needed later"

        graph = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        try:
            # Important: Do not pass data=data without publicID=uri because
            # relative URIs (#deri) won't be an absolute uri in that case!
            assert data
            graph.parse(data=data, publicID=self.uri,
                        format=self.backend.format)
        except SAXParseException:
            self.add_error("SAXParseException")
            logger.error("SAXParseException: %s" % self)
            if raise_errors: raise e
            else: return
        except rdflib.exceptions.ParserError:
            self.add_error("ParserError")
            logger.error("ParserError: %s" % self)
            if raise_errors: raise e
            else: return
        except IOError as e:
            # TODO: why does this occur? guess: wrong protocol
            self.add_error("IOError")
            logger.error("IOError: %s" % self)
            if raise_errors: raise e
            else: return

        self.processed = True
        if not graph:
            logger.warning("%s did not return any information" % self.uri)
            return

        if hasattr(self, "errors"): delattr(self, "errors")

        g_length = len(graph)
        if g_length > 5000:
            logger.warning("len(graph) == %s" % g_length)
            if g_length > GRAPH_SIZE_LIMIT:
                logger.error("Maximum graph size is set to %s. The aquired "
                             "graph exceeds that! Pass "
                             "GRAPH_SIZE_LIMIT to set it differently."
                             % GRAPH_SIZE_LIMIT);
                return

        # normal rdflib.compare does not work correctly with
        # conjunctiveGraph, unless there is only one graph within that
        assert len(list(graph.contexts())) == 1

        if hasattr(self, "_graph"):
            # we already assured that there are no unsaved_changes
            # --> graph() == _graph
            logger.info(u"Already crawled: %s. Comparing graphs..." % self.uri)

            if not compare.to_isomorphic(self._graph) == \
                   compare.to_isomorphic(graph):
                logging.warning("GET retrieved updates for %s!" % self.uri)
                utils.my_graph_diff(self._graph, graph)

                for resource in self.get_resources():
                    resource.delete()

                delattr(self, "handled")

        if hasattr(self, "handled"):
            return

        self._graph = graph

        if not list(self.get_resources()):
            logger.debug("Resources exist but no _graph --> Resources were "
                         "created locally")

        def create_origin(o, caused_by=None, # should be Origin object
                                process_now=False):
            if not type(o) == rdflib.URIRef:
                return

            uri = hash_to_slash_uri(o)
            origin, created = Origin.objects.get_or_create(uri=uri)
            if created:
                setattr(origin, '_created_by', caused_by)
            if process_now:
                logger.info("Interrupting to load %s because we need to "
                        "process owl:imports %s first" % (caused_by.uri,
                                                          origin.uri))
                origin.GET()

                
        namespace_short_notation_reverse_dict = reverse_dict(dict(graph\
            .namespace_manager.namespaces()))

        # TODO: pass only_follow_uris = [] to skip creating origins? --> find
        # a better way
        if only_follow_uris is not None:
            only_follow_uris = [rdflib.URIRef(u) if not\
                isinstance(u, rdflib.URIRef) else u for u in only_follow_uris]

        start_time = datetime.datetime.now()

        for subject, predicate, obj_ect in graph:
            assert hasattr(subject, "n3")
            #subject = canonalize_uri(subject)

            assert predicate.encode('utf8')

            if handle_owl_imports:
                if predicate == rdflib.OWL.imports:
                    create_origin(obj_ect, caused_by=self, process_now=True)

            if only_follow_uris is not None:
                if predicate in only_follow_uris:
                    create_origin(obj_ect, caused_by=self)
            else:
                # follow every URIRef! this could take a long time!
                create_origin(obj_ect, caused_by=self)

            resource, _created = Resource.objects.get_or_create(uri=subject,
                                                                origin=self)
            resource._add_property(predicate, obj_ect,
                                   namespace_short_notation_reverse_dict)

        self.stats['graph_processing_time'] = datetime.datetime.now() - start_time

        for resource in self.get_resources():
            resource._has_changes = False

        assert compare.to_isomorphic(graph) == \
               compare.to_isomorphic(self.graph()), \
               utils.my_graph_diff(graph, self.graph())

        self.handled = True


    def get_resources(self):
        return Resource.objects.filter(_origin=self)

    def graph(self):
        """Processes every Resource and Property related to 'self' and
        creates rdflib.ConjunctiveGraph because rdflib.Graph does not allow
        parsing plugins
        """
        # TODO: rdflib.graph() ?
        graph = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        if not hasattr(self, '_graph'):
            if len(self.errors) == 0:
                self.GET(raise_errors=False) # TODO: test for recursion?
            else:
                logging.error("Origin %s has Errors --> can't process .graph()"
                    % self.uri)
                return graph

        # TODO: find a better way to do this
        # Problems:
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

        for resource in self.get_resources():
            # TODO: better idea how to do this?
            # __dict__ converts rdflib.urirefs to strings -->
            # converts back to uriref
            # {'foaf': 'http:/....', ...}
            for triple in resource._tripleserialize_iterator(namespace_dict):
                graph.add(triple)
        return graph

    def has_unsaved_changes(self):
        # resource objects exist although not processed yet
        if not self.processed and len(list(self.get_resources())):
            return True

        # objects with changed attributes exist
        if any(resource._has_changes
                for resource in self.get_resources()\
                    if hasattr(resource, '_has_changes')):
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

        graph = self.graph()
        data = graph.serialize(format=self.backend.format)

        self.backend.PUT(data=data)
        # TODO return "OK"

    def get_statistics(self):
        def triples_per_second(triples, time): # TODO make this more accurate
            total_seconds = (time.microseconds+(time.seconds+\
                                      time.days*24*3600)*10**6)//10**6
            return triples / total_seconds if total_seconds > 0 else None

        if hasattr(self, '_graph'):
            triples = len(self._graph)
            tps = triples_per_second(triples,
                                     self.stats['graph_processing_time'])
            if tps:
                logger.info(
                    "Crawled %s: '%s' triples in '%s' seconds --> '%s' "
                    "triples/second"
                    % (self.uri, triples,
                       self.stats['graph_processing_time'], tps))
            else:
                logger.info("Crawled %s in '%s' seconds"
                % (self.uri, self.stats['graph_processing_time']))
            pass
        else:
            print "no statistics recorded"



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
