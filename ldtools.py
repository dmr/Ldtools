# -*- coding: utf-8 -*-

__version__ = "0.1"
__useragent__ = ('ldtools-%s (http://github.com/dmr/ldtools, daniel@nwebs.de)'
                 % __version__)

import datetime
import rdflib
import urllib2
from rdflib import compare
from urlparse import urlparse
from xml.sax._exceptions import SAXParseException

import socket;
socket.setdefaulttimeout(5) # HACK, TODO: find a way to set this for request

import logging
logger = logging.getLogger(__name__)


class UriNotValid(Exception):
    "Given Uri is not valid"
    silent_variable_failure = True


class DoesNotExist(Exception):
    "The requested object does not exist"
    silent_variable_failure = True


class MultipleObjectsReturned(Exception):
    "More than one object exists --> inconsistency"
    silent_variable_failure = True


def safe_dict(d):
    """Recursively clone json structure with UTF-8 dictionary keys"""
    if isinstance(d, dict):
        return dict([(k.encode('utf-8'), safe_dict(v)) \
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
    """Returns Uri that is valid or raises Exception
    """
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
    """Converts Hash to Slash uri http://www.w3.org/wiki/HashURI
    """
    # TODO: replace with urlparse
    assert isinstance(uri, rdflib.URIRef)
    if '#' in uri:
        real_uri, hash_value = uri.split("#")
        assert real_uri
        return real_uri
    return uri


class Field(object):
    def to_db(self, value=None):
        if value is None:
            value = ''
        return value
    def to_python(self, value=None):
        return value


class StringField(Field):
    def to_python(self, value=None):
        return unicode(value) or u""

class URIRefField(Field):
    def to_python(self, value=None):
        if value:
            assert not isinstance(value, rdflib.Literal)
            assert isinstance(value, (rdflib.URIRef,
                rdflib.BNode)), "please pass uriref!"
            #value = rdflib.URIRef(unicode(value))
        else:
            value = rdflib.URIRef(u'')
        return value

class ObjectField(Field):
    def to_python(self, value=None):
        return value


class Options(object):

    def __init__(self, meta, attrs):
        fields = []
        for obj_name, obj in attrs.iteritems():
            if isinstance(obj, Field):
                fields.append((obj_name, obj))
        self.fields = dict(fields)


class ModelMeta(type):

    def __new__(cls, name, bases, attrs):
        super_new = super(ModelMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, ModelMeta)]
        if not parents:
            # If this isn't a subclass of Model, don't do anything special.
            return super_new(cls, name, bases, attrs)

        module = attrs.pop('__module__')

        new_cls = super_new(cls, name, bases, {'__module__': module})

        attr_meta = attrs.pop('Meta', None)
        if not attr_meta:
            meta = getattr(new_cls, 'Meta', None)
        else:
            meta = attr_meta
        setattr(new_cls, '_meta', Options(meta, attrs))

        # Add all attributes to the class.
        for obj_name, obj in attrs.iteritems():
            if isinstance(obj, Manager):
                obj.contribute_to_class(new_cls, obj_name)
            else:
                setattr(new_cls, obj_name, obj)

        if not hasattr(new_cls, "__unicode__"):
            new_cls.__unicode__ = lambda self: self.pk
        if not hasattr(new_cls, '__str__'):
            new_cls.__str__ = lambda self: self.__unicode__()
        new_cls.__repr__ = lambda self: u'<%s: %s>' % (
                self.__class__.__name__, self.__unicode__())
        return new_cls


class Model(object):

    __metaclass__ = ModelMeta
    MultipleObjectsReturned = MultipleObjectsReturned
    DoesNotExist = DoesNotExist

    def __init__(self, pk=None, **kwargs):
        self.pk = pk
        for attrname, field in self._meta.fields.iteritems():
            attr = kwargs.pop(attrname)
            value = field.to_python(attr)
            setattr(self, attrname, value)
        if kwargs:
            raise ValueError('%s are not part of the schema for %s'
                % (', '.join(kwargs.keys()), self.__class__.__name__))

    def __eq__(self, other):
        return (type(other) == type(self) and
                other.__dict__.keys() == self.__dict__.keys() and
                all(getattr(other, key) == getattr(self, key)
                    for key in self.__dict__.keys()))
    def __ne__(self, other):
        if type(other) != type(self):
            return True
        if any(getattr(other, key) != getattr(self, key) \
                   for key in self.__dict__.keys()):
            return True

    def __hash__(self):
        # It is wrong to really compare the object here. This case is
        # important to work with references in set() instances for instance
        return hash(self.pk)


class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance != None:
            raise AttributeError("Manager isn't accessible via %s instances"
                                 % type.__name__)
        return self.manager


class Manager(object):

    def __init__(self):
        self.model = None
        self.reset_store()

    def contribute_to_class(self, model, name):
        self.model = model
        setattr(model, name, ManagerDescriptor(self))

    def reset_store(self):
        self._storage = {}

    def all(self):
        return self._storage.values()

    def filter_has_key(self, key):
        key = unicode(key)
        func = lambda obj: key in [unicode(k) for k in \
                                        obj.__dict__.keys()]
        return filter(func, self.all())

    def filter(self, **kwargs):
        def check_if_equals_or_in_set((key, value)):
            if hasattr(item, key):
                items_value = getattr(item, key)
                # TODO: inconsistent: can handle lists and strings!!! again,
                # this is convenient but ugly
                if type(items_value) in (set, list):
                    if value in items_value:
                        return True
                else:
                    if unicode(items_value) == unicode(value):
                        return True
            return False

        # TODO: this is ugly but it works ;-)
        for item in self.all():
            if all(map(check_if_equals_or_in_set, kwargs.items())):
                #logger.info("Found %s in %s" % (kwargs.items(), item))
                yield item

    def create(self, pk, **kwargs):
        instance = self.model(pk=pk, **kwargs)
        assert not pk in self._storage, ("%s object with pk %s already exists!"
            % (self.model, pk))
        self._storage[pk] = instance
        return instance

    def get(self, pk):
        if pk in self._storage:
            return self._storage[pk]
        else:
            raise self.model.DoesNotExist


class ResourceManager(Manager):

    def get_pk(self, uri1, uri2):
        return uri1+uri2

    def create(self, uri, origin):
        assert isinstance(origin, Origin), "Origin instance required"

        if uri.startswith("#"):
            assert not isinstance(uri, rdflib.BNode), \
                "bnode should not start with #"
            uri = rdflib.URIRef(origin.uri + uri)

        uri = canonalize_uri(uri)
        pk = self.get_pk(origin.uri, uri)
        if isinstance(uri, rdflib.BNode):
            obj = super(ResourceManager, self).create(pk=pk, _uri=uri,
                                                      _origin=origin)
            assert isinstance(obj._uri, rdflib.BNode)
            return obj
        return super(ResourceManager, self).create(pk=pk, _uri=uri,
                                                   _origin=origin)

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
        uri = canonalize_uri(uri)

        # TODO: make origin optional? explicit > implicit --> no. but still
        # convenient...
        if not origin: # TODO: make guessing origin explicit in get()
            filter_result = list(self.filter(_uri=uri))

            if not filter_result:
                raise self.model.DoesNotExist

            assert len(filter_result) == 1, ("Please pass the exact "
                "Origin. The Resource you are looking for is provided by: %s"\
                % ", ".join([r._origin for r in filter_result]))

            return filter_result[0]


        assert isinstance(origin, Origin), origin
        pk = self.get_pk(origin.uri, uri)
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

    def add_property(self, predicate, object):
        assert isinstance(predicate, rdflib.URIRef),\
            "Not an URIRef: %s"%predicate
        # TODO remove?
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

        if not hasattr(self, predicate):
            setattr(self, predicate, set())

        attr = getattr(self, predicate)
        assert type(attr) == set

        if is_resource:
            logger.debug("%s . %s = Resource( %s )"
                         % (self._uri, predicate, object))
            object, _created = Resource.objects.get_or_create(uri=object,
                                                      origin=self._origin)

        attr.add(object)

        logger.debug(u"Contribute_to_object %s: %s = %s"
            % (self, predicate.encode('utf8'),
               ", ".join([unicode(v) for v in attr])))

        assert object in getattr(self, predicate)

        assert isinstance(predicate, rdflib.URIRef)

        # --> TODO: force_unicode when reconverting from __dict__?
        assert str(predicate) in self.__dict__

    def __unicode__(self):
        str = u"%s" % self._uri
        if hasattr(self, 'foaf_name'):
            str += u' "%s"' % unicode(self.foaf_name)
            if len(self.foaf_name) > 1: str += u",..."
        assert isinstance(self._origin, Origin)
        str += u" [origin: %s]" % self._origin.uri
        if hasattr(self, rdflib.RDF.type):
            rdf_type = list(getattr(self, rdflib.RDF.type))
            str += (u" rdf:type %s" % unicode(rdf_type[0]))
            if len(rdf_type) > 1: str += u",..."
        return str

    def tripleserialize_iterator(self):
        # TODO: self.get_property_dict() instead?
        for property, values in self.__dict__.items():

            # skip internals
            if str(property).startswith("_") or property == "pk":
                continue

            assert isinstance(values, set), property

            # TODO: better idea how to do this?
            # __dict__ converts rdflib.urirefs to strings -->
            # converts back to uriref
            property = rdflib.URIRef(property)

            assert hasattr(property, "n3"), \
                "property %s is not a rdflib object" % property

            for v in values:
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
        elif not key.startswith("_"):
            # rdf properties here
            self._has_changes = True
        Model.__setattr__(self, key, value)

    def delete(self):
        if hasattr(self, "_has_changes"):
            assert not self._has_changes
        assert hasattr(self, "pk") and self.pk is not None
        # TODO: use Collector objects as django does
        self.__class__.objects._storage.__delitem__(self.pk)

class Backend(object):
    """ Abstract Backend to demonstrate API
    """
    def GET(self):
        raise NotImplementedError
    def PUT(self):
        raise NotImplementedError

class RestBackend(Backend):
    def GET(self, uri, origin): # TODO remove origin
        try:
            data = get_uri_content(uri)
        except urllib2.HTTPError as e:
            if not e.code in (401, 403, 404, 503):
                raise
            origin.add_error(str(e.code))
            return
        except urllib2.URLError as e:
            origin.add_error("timeout")
            return
        return data

class FileBackend(Backend):
    def __init__(self, filename):
        import os
        assert os.path.exists(filename)
        self.filename = filename

    def GET(self):
        with open(self.filename, "r") as f:
            data = f.read()
        return data

class OriginManager(Manager):

    def create_hook(self, uri):
        assert not '#' in uri, ("HashURI not allowed as Origin: %s. Maybe "
            "Resource.objects.create(...,auto_origin=True) is what you are "
            "looking for." % uri)

    def create(self, uri, BACKEND=RestBackend()):
        uri = canonalize_uri(uri)
        self.create_hook(uri)
        backend = BACKEND
        return super(OriginManager, self).create(pk=uri, uri=uri,
                                                 backend=backend)

    def get(self, uri):
        """Retrieves Origin object from Store"""
        uri = canonalize_uri(uri)
        return super(OriginManager, self).get(pk=uri)

    def get_or_create(self, uri):
        uri = canonalize_uri(uri)
        assert str(uri) == str(hash_to_slash_uri(uri))
        try:
            return self.get(uri), False
        except self.model.DoesNotExist:
            return self.create(uri), True

    @catchKeyboardInterrupt
    def GET_all(self, depth=2, **kwargs):
        """ Crawls or Re-Crawls all Origins.
        Passes Arguments to GET"""
        # TODO: limit crawling speed
        for _i in range(depth):
            for origin in self.all():
                origin.GET(**kwargs)

    @catchKeyboardInterrupt
    def GET_uncrawled(self, depth=2, **kwargs):
        func = lambda origin: True if not hasattr(origin, "_graph") else False
        for _i in range(depth):
            crawl = filter(func, self.all())
            if crawl:
                for origin in crawl:
                    origin.GET(**kwargs)

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

    def __unicode__(self):
        str = u"%s" % unicode(self.uri)
        if hasattr(self, 'errors'):
            for error in self.errors: str += u" %s" % error
        if hasattr(self, 'processed'):
            str += u" Processed"
            if hasattr(self, 'stats'):
                if hasattr(self, 'handle_graph'):
                    str += u" (%s)" % self.stats['handle_graph']
                else:
                    raise NotImplementedError
        return str

    def has_unsaved_changes(self):
        if any(o._has_changes for o in self.get_resources()\
               if hasattr(o, '_has_changes')): return True
        return False

    def get_resources(self):
        return [r for r in Origin.objects.all() if self == r._origin]

    def GET(self,
            GRAPH_SIZE_LIMIT=25000,
            follow_uris=None,
            handle_owl_imports=False,
            skip_urls=None
            ):
        logger.info(u"GET %s..." % self.uri)

        assert not self.has_unsaved_changes(), ("Please save all changes "
            "before querying again. Merging not supported yet")

        # http://www.infoq.com/news/2008/04/cool-uris-rest
        if skip_urls is not None and str(self.uri) in skip_urls:
            self.add_error("Skipped")
            self.processed = True
            return

        g = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        data = self.backend.GET(uri=self.uri, origin=self)
        if not data:
            self.processed = True
            return

        try:
            # Important: Do not pass data=data without publicID=uri because
            # relative URIs (#deri) won't be an absolute uri in that case!
            assert data
            g.parse(data=data, publicID=self.uri)
        except SAXParseException:
            self.add_error("SAXParseException")
            logger.error("SAXParseException: %s" % self)
        except rdflib.exceptions.ParserError:
            self.add_error("ParserError")
            logger.error("ParserError: %s" % self)
        except IOError as e:
            # TODO: why does this occur? guess: wrong protocol
            self.add_error("IOError")
            logger.error("IOError: %s" % self)
            print e

        if not g:
            self.processed = True
            return

        g_length = len(g)
        if g_length > 3000:
            logger.warning("len(g) == %s" % g_length)
            if g_length > GRAPH_SIZE_LIMIT:
                logger.error("Nope."); return

        # normal rdflib.compare does not work correctly with
        # conjunctiveGraph, unless there is only one graph within that
        assert len(list(g.contexts())) == 1

        if hasattr(self, "_graph"):
            # at this point we know that all changes are saved --> graph() == _graph
            logger.info(u"Already crawled: %s. Comparing graphs..." % self.uri)

            if not compare.to_isomorphic(self._graph) == \
                   compare.to_isomorphic(g):
                logging.warning("GET retrieved updates for %s!" % self.uri)
                my_graph_diff(self._graph, g)

                for resource in self.get_resources():
                    resource.delete()

                delattr(self, "handled")
            else:
                logging.info("GET %s still the same, boring" %self.uri) # TODO: remove later

        if not hasattr(self, "handled"):
            self._graph = g

            self.handle_graph(
                follow_uris=follow_uris,
                handle_owl_imports=handle_owl_imports,
                skip_urls=skip_urls
            )

        def triples_per_second(triples, time):
            # TODO: should be more accurate
            td = time
            total_seconds = (td.microseconds+(td.seconds+\
                                              td.days*24*3600)*10**6)//10**6
            if total_seconds > 0:
                triples_per_second = triples / total_seconds
                return triples_per_second
            else: return
        if hasattr(self, '_graph'):
            triples = len(self._graph)
            tps = triples_per_second(triples, self.stats['handle_graph'])
            if tps:
                logger.info(
                    "Crawled %s: '%s' triples in '%s' seconds --> '%s' "
                    "triples/second" % (self.uri, triples,
                                        self.stats['handle_graph'], tps))
            else:
                logger.info("Crawled %s in '%s' seconds"
                % (self.uri, self.stats['handle_graph']))
            pass


    def handle_graph(self, follow_uris, handle_owl_imports, skip_urls):
        assert hasattr(self, '_graph')
        assert not hasattr(self, "handled")
        assert not list(self.get_resources())

        def handle_follow_uri(o):
            if isinstance(o, rdflib.Literal):
                logging.error(u"%s is Literal! Only URIRefs are allowed as "
                              u"follow_uri destination" % o.encode('utf8'))
                return

            uri = hash_to_slash_uri(o)

            origin, created = Origin.objects.get_or_create(uri=uri)
            if created:
                setattr(origin, '_created_by', self)

        def handle_owl_imports(o):
            # TODO: owl:imports is always Origin? or could it be a Resource?

            uri = hash_to_slash_uri(o)
            origin, created = Origin.objects.get_or_create(uri)
            if created:
                setattr(origin, '_created_by', self)

            # TODO: possible improvement: check whether origin already crawled

            logger.info("Interrupting to load %s because we need to "
                    "process owl:imports %s first" % (self.uri, origin.uri))
            origin.GET()

        def handle_properties(origin, subject, predicate, object):
            resource, _created = Resource.objects.get_or_create(uri=subject,
                                                                origin=self)
            resource.add_property(predicate, object)

        handlers = []
        to_handle = {}

        to_handle[handle_follow_uri] = []
        handlers.append((handle_follow_uri, to_handle[handle_follow_uri]))

        if handle_owl_imports:
            to_handle[handle_owl_imports] = []
            handlers.append((handle_owl_imports,
                             to_handle[handle_owl_imports]))

        to_handle[handle_properties] = []
        handlers.append((handle_properties, to_handle[handle_properties]))

        if follow_uris:
            follow_uris = [rdflib.URIRef(u) if not\
                isinstance(u, rdflib.URIRef) else u for u in follow_uris]

        start_time = datetime.datetime.now()

        for s, p, o in self._graph:
            assert hasattr(s, "n3")
            #s = canonalize_uri(s)

            assert p.encode('utf8')

            if handle_owl_imports:
                if p == rdflib.OWL.imports:
                    to_handle[handle_owl_imports].append(o)

            if follow_uris:
                if p in follow_uris:
                    to_handle[handle_follow_uri].append(o)

            to_handle[handle_properties].append((self, s, p, o))

        for handler, items in handlers:
            if items:
                for item in items:
                    if isinstance(item, tuple):
                        handler(*item)
                    else:
                        handler(item)

        for resource in self.get_resources():
            resource._has_changes = False

        self.stats['handle_graph'] = datetime.datetime.now() - start_time

        assert compare.to_isomorphic(self._graph) == \
               compare.to_isomorphic(self.graph()), \
               my_graph_diff(self._graph, self.graph())

        self.handled = True



    def graph(self):
        """Processes every Resource and Property related to 'self' and
        creates rdflib.ConjunctiveGraph because rdflib.Graph does not allow
        parsing plugins
        """
        # TODO: rdflib.graph() ?
        g = rdflib.graph.ConjunctiveGraph(identifier=self.uri)

        if not hasattr(self, '_graph'):
            if len(self.errors) == 0:
                self.GET() # TODO: test for recursion?
            else:
                logging.error("Origin %s has Errors --> can't process .graph()"
                    % self.uri)
                return g

        # TODO: find a better way to do this
        # Problems:
        #  1) namespace bindings are not really necessary to validate
        #     isomorphic graphs but the resulting graph is is different
        #     if they miss
        #  2) doesn't detect duplicate definitions of namespaces
        namespaces = dict(self._graph.namespace_manager\
                            .namespaces())
        for prefix, namespace in safe_dict(namespaces).items():
            g.bind(prefix=prefix, namespace=namespace)
        new_ns = dict(g.namespace_manager.namespaces())

        assert namespaces == new_ns, [(k, v) for k, v in
                  safe_dict(namespaces)\
                  .items() if  not k in safe_dict(new_ns).keys()]

        for resource in self.get_resources():
            for triple in resource.tripleserialize_iterator():
                g.add(triple)

        return g

    def get_resources(self):
        return Resource.objects.filter(_origin=self)


def get_uri_content(uri):
    """lookup URI"""
    # TODO: friendly crawling: use robots.txt
    # crawling speed limitations in robots.txt.

    # TODO: rdf browser accept header literature?
    headers = {'User-agent': __useragent__,
               'Accept':('application/rdf+xml,text/rdf+n3;q=0.9,'
                         'application/xhtml+xml;q=0.5, */*;q=0.1')}

    try:
        request = urllib2.Request(url=uri, headers=headers)
    except urllib2.HTTPError as e:
        if e.code == 401:
            logger.error("Authorization Required: %s" % uri)
        raise

    try:
        opener = urllib2.build_opener() #SmartRedirectHandler())
        result_file = opener.open(request)
        #print 'The original headers where', result_file.headers

        if result_file.headers['Content-Type'] not in [
            "application/rdf+xml",
            "application/rdf+xml; charset=UTF-8",
            "application/rdf+xml; qs=0.9",
            "text/n3",
            "text/xml",
            "application/xml; charset=UTF-8",
            "application/rdf+xml;charset=UTF-8",
            #"application/json",
            ]:
            logger.warning("%s not supported by ldtools. %s response maybe "
                "in wrong format or Content Negotiation of server wring"
                % (result_file.headers['Content-Type'], uri))

        #print 'The Redirect Code was', result_file.status
        #assert result_file.status == 200

    except urllib2.HTTPError as e:
        if e.code == 403:
            logger.error("Forbidden: %s" % uri)
        elif e.code == 503: #"Service Temporarily Unavailable"
            logger.error("Service Temporarily Unavailable: %s" % uri)
        raise

    except urllib2.URLError as e:
        logger.error("Timeout: %s" % uri)
        raise

    content = result_file.read()


    # cache file for further investigazion --> TODO: delete later?
    if "DEBUG" in globals():
        def build_filename(uri):
            return uri.lstrip("http://").replace(".","_")\
                .replace("/","__").replace("?","___").replace("&","____")
        import os
        folder = os.path.abspath("cache")
        if not os.path.exists(folder):
            os.mkdir(folder)
        filename = os.path.join(folder, build_filename(uri))
        with open(filename, "w") as f:
            f.write(content)


    return content


# TODO: this is just for convenience --> remove once stable
def my_graph_diff(graph1, graph2):
    """Compares graph2 to graph1 and highlights everything that changed.
    Colored if pygments available"""

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
