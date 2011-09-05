# -*- coding: utf-8 -*-
__version__ = "0.4.3"
__useragent__ = ('ldtools-%s (http://github.com/dmr/ldtools, daniel@nwebs.de)'
                 % __version__)

import copy
import datetime
import logging
import mimetypes
import os
import rdflib
import socket;
import shutil
import urllib2
from rdflib.namespace import split_uri
from rdflib import compare
from urlparse import urlparse
from xml.sax._exceptions import SAXParseException

# TODO: find a better way to set socket timeout
socket.setdefaulttimeout(5)

# add n3 to known mimetypes
mimetypes.add_type("text/n3", ".n3")

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


def get_file_extension(filename):
    """
    >>> get_file_extension("test.xml")
    'xml'
    >>> get_file_extension("test.1234123.xml")
    'xml'
    >>> get_file_extension("test")
    ''
    """
    extension = filename.split(".")[1:][-1:]
    return str(extension[0]) if extension else ""


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


def reverse_dict(dct):
    # TODO rdflib.URIRef dict?
    res = {}
    for k,v in dct.iteritems():
        res[v] = k
    return safe_dict(res)


def predicate2pyattr(predicate, namespacedict):
    prefix, propertyname = split_uri(predicate)
    assert prefix
    assert propertyname
    #if not "_" in propertyname:
    #    logger.info("%s_%s may cause problems?" % (prefix, propertyname))
    if not prefix in namespacedict:
        logger.warning("%s cannot be shortened" % predicate)
        return predicate
    return u"%s_%s" % (namespacedict[prefix], propertyname)


def pyattr2predicate(pyattr, namespacedict):
    # TODO: build urirefdict instead of unicodedict?

    if pyattr.startswith(u"http://"):
        return rdflib.URIRef(pyattr)

    splitlist = pyattr.split("_")

    # HACK: are there constrains for namespace prefixes?
    if len(splitlist) > 2 and u"_".join(splitlist[0:2]) in namespacedict:
        # http://www.geonames.org/ontology# defines 'wgs84_pos' --> \
        # 'wgs84_pos_lat' cannot be solved with approach we took until now
        prefix = u"_".join(splitlist[0:2])
        property_name = u"_".join(splitlist[2:])
    else:
        prefix = splitlist[0]
        property_name = u"_".join(splitlist[1:])

    assert prefix, pyattr
    assert property_name, pyattr
    assert namespacedict[prefix], pyattr
    return rdflib.URIRef(u"%s%s" % (namespacedict[prefix], property_name))


def check_shortcut_consistency():
    """Checks every known Origin for inconsistent namespacemappings"""
    global_namespace_dict = {}
    for origin in Origin.objects.all():
        if hasattr(origin, "_graph"):
            for k, v in dict(origin._graph.namespace_manager\
                        .namespaces()).items():
                print k,v
                if k in global_namespace_dict:
                    assert global_namespace_dict[k] == v
                else:
                    global_namespace_dict[k] = v


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


######### Backends #########

class Backend(object):
    """ Abstract Backend to demonstrate API
    """
    def GET(self, uri):
        raise NotImplementedError
    def PUT(self):
        raise NotImplementedError

    @staticmethod
    def build_filename_from_uri(uri):
        file_name = uri.lstrip("http://").replace(".","_")\
            .replace("/","__").replace("?","___").replace("&","____")

        # TODO: hacky
        folder = os.path.abspath("cache")
        if not os.path.exists(folder):
            os.mkdir(folder)

        return os.path.join(folder, file_name)


class RestBackend(Backend):

    def GET(self, uri):
        """lookup URI"""
        # TODO: friendly crawling: use robots.txt speed limitation definitions

        if not hasattr(self, "uri"):
            self.uri = uri
        else:
            if not self.uri == uri:
                raise Exception("You cannot pass different uris to the same "
                                "backend")

        headers = {'User-agent': __useragent__,
                   'Accept':('application/rdf+xml,text/rdf+n3;q=0.9,'
                             'application/xhtml+xml;q=0.5, */*;q=0.1')}

        request = urllib2.Request(url=self.uri, headers=headers)

        opener = urllib2.build_opener() #SmartRedirectHandler())
        result_file = opener.open(request)

        self.content_type = result_file.headers['Content-Type'].split(";")[0]

        # Many servers don't do content negotiation: if one of the following
        # content_types are returned by server, assume the mapped type
        content_type_mapping = {
            "text/plain": "application/rdf+xml"
        }

        if self.content_type in content_type_mapping:
            self.content_type = content_type_mapping[self.content_type]

        file_extension = mimetypes.guess_extension(self.content_type)
        if file_extension:
            format = file_extension.strip(".")
            if format in ["rdf", "ksh"]:
                format = "xml"
            self.format = format
        else:
            logger.warning("%s not supported by ldtools. Trying 'xml'..."
                           % result_file.headers['Content-Type'])
            self.format = "xml"
            self.content_type = mimetypes.types_map[".%s" % self.format]

        content = result_file.read()
        return content

    def PUT(self, graph):
        assert self.uri, "GET has to be called before PUT possible"

        data = graph.serialize(format=self.format)

        # TODO: authentication? oauth?
        #h = httplib2.Http()
        #h.add_credentials('name', 'password')
        #resp, content = h.request(uri, "PUT", body=data, headers=headers)
        #if resp.status != 200: raise Error(resp.status, errmsg, headers)
        #return resp, content
        headers={"content-type": self.content_type,
                 "User-Agent": __useragent__,
                 "Content-Length": str(len(data))}

        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(self.uri,
                                  data=data,
                                  headers=headers)
        request.get_method = lambda: 'PUT'
        response = opener.open(request)


class SingleFileBackend(Backend):
    """Manages one xml file --> Uri that the user wants to "PUT" to is not
    flexible!
    """

    def __init__(self, filename, format=None):
        assert os.path.exists(filename)
        self.filename = filename

        # TODO: assert format in rdflib.parserplugins
        if format:
            self.format = format
        else:
            file_extension = filename.split(".")[-1]
            if filename != file_extension:
                self.format = file_extension
            else:
                self.format = "xml"

    def GET(self, uri):
        if not hasattr(self, "uri"):
            self.uri = uri
        else:
            if not self.uri == uri:
                raise Exception("You cannot pass different uris to the same "
                                "backend")

        with open(self.filename, "r") as f:
            data = f.read()
        return data

    def PUT(self, graph):
        assert self.uri, "GET has to be called before PUT possible"

        if os.path.exists(self.filename):
            # File already exists. Make backup copy
            now = datetime.datetime.strftime(datetime.datetime.utcnow(),
                                             '%Y%m%d-%H%M%S')
            file_extension = get_file_extension(self.filename)
            if file_extension:
                old_version = u"%s.%s.%s" % (self.filename.strip(file_extension),
                                             now, file_extension)
            else:
                old_version = u"%s_%s" % (self.filename, now)
            shutil.copy(self.filename, old_version)

        data = graph.serialize(format=self.format)
        with open(self.filename, "w") as f:
            f.write(data)
        self.old_version = old_version

    def revert_to_old_version(self):
        if hasattr(self, "old_version"):
            logger.info("Reverting to version before last saved version")
            shutil.copy(self.old_version, self.filename)
            os.remove(self.old_version)
            delattr(self, "old_version")


class SimpleMemoryBackend(Backend):
    def __init__(self, data=None, format="xml"):
        self.data = data if data else ""
        self.format = format

    def GET(self, uri):
        return self.data

    def PUT(self, graph):
        self.data = graph.serialize(format=self.format)


######### Model definitions #########

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
        for attr_name, field in self._meta.fields.iteritems():
            attr = kwargs.pop(attr_name)
            value = field.to_python(attr)
            setattr(self, attr_name, value)
        if kwargs:
            # TODO ValueError is raised on object creation with kwargs.
            # inconsistent: after that, no checks performed.
            raise ValueError('%s are not part of the schema for %s'
                % (', '.join(kwargs.keys()), self.__class__.__name__))

    def __eq__(self, other):
        if not type(other) == type(self):
            return False

        if set(other.__dict__.keys()) != set(self.__dict__.keys()):
            return False

        for key in self.__dict__.keys():
            if (not hasattr(other, key) or
                    getattr(self, key) != getattr(other, key)):
                return False

        return True


    def __ne__(self, other):
        if type(other) != type(self):
            return True

        if set(other.__dict__.keys()) != set(self.__dict__.keys()):
            return True

        for key in self.__dict__.keys():
            if (not hasattr(other, key) or
                    getattr(other, key) != getattr(self, key)):
                return True

        return False

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
            """helper method for loop. Convenient but maybe hacky: checks
            if value is in attr or if iterable inside the iterable"""
            if hasattr(item, key):
                items_value = getattr(item, key)
                # TODO why can't we check for hasattr(items_value, "__iter__")?
                if type(items_value) in [list, set]:
                    if value in items_value:
                        return True
                else:
                    if unicode(items_value) == unicode(value):
                        return True
            return False

        for item in self.all():
            if all(map(check_if_equals_or_in_set, kwargs.items())):
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


######### Resource #########

class ResourceManager(Manager):

    def get_pk(self, origin_uri, uri):
        return origin_uri+uri

    def create(self, uri, origin, **kwargs):
        assert isinstance(origin, Origin), "Origin instance required"

        if uri.startswith("#"):
            assert not isinstance(uri, rdflib.BNode), \
                "bnode should not start with #"
            uri = rdflib.URIRef(origin.uri + uri)

        uri = canonalize_uri(uri)
        pk = self.get_pk(origin_uri=origin.uri, uri=uri)
        if isinstance(uri, rdflib.BNode):
            obj = super(ResourceManager, self).create(pk=pk, _uri=uri,
                                                      _origin=origin)
            assert isinstance(obj._uri, rdflib.BNode)
            assert not hasattr(obj, "_has_changes")
            return obj

        return super(ResourceManager, self).create(pk=pk, _uri=uri,
                                                   _origin=origin, **kwargs)

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
                "Origin. The Resource you are looking for is provided by: %s"
                % ", ".join([r._origin for r in filter_result]))

            return filter_result[0]


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

    def _add_property(self, predicate, object):
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

        predicate = predicate2pyattr(predicate, self._origin._nsshortdict)

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

    def __unicode__(self):
        str = u"%s" % self._uri
        if hasattr(self, 'foaf_name'):
            str += u' "%s"' % unicode(self.foaf_name)
            if len(self.foaf_name) > 1: str += u",..."
        if hasattr(self, "_origin") and isinstance(self._origin, Origin):
            str += u" [%r]" % self._origin.uri.encode("utf8")
        return str

    def _tripleserialize_iterator(self, namespace_dict):
        for property, values in self.__dict__.items():

            # skip internals
            if str(property).startswith("_") or property == "pk":
                continue

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
        assert self in Resource.objects.filter(_origin=self._origin,
            _has_changes=True)
        assert len(list(Resource.objects.filter(_origin=self._origin,
            _has_changes=True))) == 1

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
            "Resource.objects.create(...,auto_origin=True) is what you are "
            "looking for." % uri)

    def create(self, uri, BACKEND=None):
        uri = canonalize_uri(uri)
        self.create_hook(uri)
        backend = BACKEND if BACKEND else RestBackend()
        return super(OriginManager, self).create(pk=uri, uri=uri,
                                                 backend=backend)

    def get(self, uri):
        """Retrieves Origin object from Store"""
        uri = canonalize_uri(uri)
        return super(OriginManager, self).get(pk=uri)

    def get_or_create(self, uri, **kwargs):
        assert not kwargs, ("If you intend to use 'backend' please use "
            "Origin.objects.create() directly")
        uri = canonalize_uri(uri)
        assert str(uri) == str(hash_to_slash_uri(uri))
        try:
            return self.get(uri), False
        except self.model.DoesNotExist:
            return self.create(uri), True

    @catchKeyboardInterrupt
    def GET_all(self, depth=2, **kwargs):
        """Crawls or Re-Crawls all Origins. Passes Arguments to GET"""
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
        str += " %s" % self.backend.__class__.__name__
        if hasattr(self, 'errors'):
            for error in self.errors:
                str += u" %s" % error
        if hasattr(self, 'processed'):
            str += u" Processed"
        return str

    def GET(self,
            GRAPH_SIZE_LIMIT=25000,
            follow_uris=None,
            handle_owl_imports=False,
            skip_urls=None
            ):
        logger.info(u"GET %s..." % self.uri)

        assert not self.has_unsaved_changes(), ("Please save all changes "
            "before querying again. Merging not supported yet")

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
                return
            else:
                raise
        except urllib2.URLError as e:
            self.add_error("timeout")
            return
        assert self.backend.format, "format is needed later"

        if not data:
            self.processed = True
            return

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
            raise
        except rdflib.exceptions.ParserError:
            self.add_error("ParserError")
            logger.error("ParserError: %s" % self)
        except IOError as e:
            # TODO: why does this occur? guess: wrong protocol
            self.add_error("IOError")
            logger.error("IOError: %s" % self)

        if not graph:
            self.processed = True
            return

        if hasattr(self, "errors"):
            delattr(self, "errors")

        g_length = len(graph)
        if g_length > 3000:
            logger.warning("len(graph) == %s" % g_length)
            if g_length > GRAPH_SIZE_LIMIT:
                logger.error("Nope."); return

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
                my_graph_diff(self._graph, graph)

                for resource in self.get_resources():
                    resource.delete()

                delattr(self, "handled")

        if not hasattr(self, "handled"):
            self._graph = graph

            #namespace short hand notation reverse dict
            self._nsshortdict = reverse_dict(dict(self._graph\
                .namespace_manager.namespaces()))

            self.handle_graph(
                follow_uris=follow_uris,
                handle_owl_imports=handle_owl_imports,
            )

        def triples_per_second(triples, time): # TODO make this more accurate
            total_seconds = (time.microseconds+(time.seconds+\
                                      time.days*24*3600)*10**6)//10**6
            return triples / total_seconds if total_seconds > 0 else None

        if hasattr(self, '_graph'):
            triples = len(self._graph)
            tps = triples_per_second(triples, self.stats['graph_processing_time'])
            if tps:
                logger.info(
                    "Crawled %s: '%s' triples in '%s' seconds --> '%s' "
                    "triples/second" % (self.uri, triples,
                                        self.stats['graph_processing_time'], tps))
            else:
                logger.info("Crawled %s in '%s' seconds"
                % (self.uri, self.stats['graph_processing_time']))
            pass

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
                self.GET() # TODO: test for recursion?
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
        namespaces = dict(self._graph.namespace_manager\
                            .namespaces())
        for prefix, namespace in safe_dict(namespaces).items():
            graph.bind(prefix=prefix, namespace=namespace)
        new_ns = dict(graph.namespace_manager.namespaces())

        assert namespaces == new_ns, [(k, v) for k, v in
                  safe_dict(namespaces)\
                  .items() if not k in safe_dict(new_ns).keys()]

        for resource in self.get_resources():
            # TODO: better idea how to do this?
            # __dict__ converts rdflib.urirefs to strings -->
            # converts back to uriref
            # {'foaf': 'http:/....', ...}
            namespace_dict = dict(self._graph.namespace_manager.namespaces())

            for triple in resource._tripleserialize_iterator(namespace_dict):
                graph.add(triple)
        return graph

    def handle_graph(self, follow_uris, handle_owl_imports):
        assert hasattr(self, '_graph')
        assert not hasattr(self, "handled")
        if not list(self.get_resources()):
            logger.debug("Resources exist but no _graph --> Resources were "
                         "created locally")

        def create_origin(o, caused_by=None, # should be Origin object
                                process_now=False):

            if isinstance(o, rdflib.Literal):
                # if follow_uri is used to manipulate which urirefs to follow
                # this could be an error that occurs
                logging.error(u"%s is Literal! Only URIRefs are allowed as "
                              u"follow_uri destination" % o.encode('utf8'))
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

        def add_property_to_resource(origin, subject, predicate, object):
            resource, _created = Resource.objects.get_or_create(uri=subject,
                                                                origin=self)
            resource._add_property(predicate, object)

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
                    create_origin(o, caused_by=self, process_now=True)

            if follow_uris:
                if p in follow_uris:
                    create_origin(o, caused_by=self)
            #else:
            #    # follow every URIRef! this could take a long time!
            #    if type(o) == rdflib.URIRef:
            #        create_origin(o, caused_by=self)

            add_property_to_resource(self, s, p, o)

        for resource in self.get_resources():
            resource._has_changes = False

        self.stats['graph_processing_time'] = datetime.datetime.now() - start_time

        assert compare.to_isomorphic(self._graph) == \
               compare.to_isomorphic(self.graph()), \
               my_graph_diff(self._graph, self.graph())

        self.handled = True

    def has_unsaved_changes(self):
        if any(resource._has_changes for resource in self.get_resources()\
               if hasattr(resource, '_has_changes')): return True
        return False

    def PUT(self):
        assert hasattr(self, "_graph")
        if not self.has_unsaved_changes():
            logging.error("Nothing to PUT for %s!" % self.uri)
            return
        self.backend.PUT(graph=self.graph())
        # TODO OK
