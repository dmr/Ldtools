# -*- coding: utf-8 -*-
import logging
import rdflib

from ldtools.metamodels import Manager, Model
from ldtools.models import URIRefField, ObjectField
from ldtools.utils import (
    get_rdflib_uriref,
    get_slash_url,
    predicate2pyattr,
    urlparse
)

logger = logging.getLogger(__name__)


class ResourceManager(Manager):
    def get_pk(self, origin_uri, uri):
        return origin_uri + uri

    def create(self, uri, origin, **kwargs):

        # from ldtools.origin import Origin <-- import circle problem
        # assert isinstance(origin, Origin), "Origin instance required"
        assert origin is not None
        assert origin.processed, ("Origin has to be processed before creating more Resource objects: origin.GET()")

        uri = get_rdflib_uriref(uri)

        pk = self.get_pk(origin_uri=origin.uri, uri=uri)
        return super(ResourceManager, self).create(
            pk=pk, _uri=uri, _origin=origin, **kwargs)

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

        uri = get_rdflib_uriref(uri)

        if not origin:
            filter_result = list(self.filter(_uri=uri))

            if not filter_result:
                raise self.model.DoesNotExist

            if len(filter_result) == 1:
                # return only match
                return filter_result[0]
            else:
                raise self.model.DoesNotExist(
                    "Please pass the exact "
                    "Origin. The Resource you are looking for is "
                    "provided by the Origins: %s"
                    % ", ".join([unicode(r._origin.uri) for r in filter_result])
                )

        pk = self.get_pk(origin_uri=origin.uri, uri=uri)
        return super(ResourceManager, self).get(pk=pk)
        assert 0, "implement!"

    def get_or_create(self, uri, origin=None):
        uri = get_rdflib_uriref(uri)
        try:
            return self.get(uri=uri, origin=origin), False
        except self.model.DoesNotExist:
            return self.create(uri=uri, origin=origin), True


class Resource(Model):
    _uri = URIRefField()
    _origin = ObjectField()
    objects = ResourceManager()

    def __unicode__(self):
        extras = []
        if hasattr(self, "_origin"):
            if self.is_authoritative_resource():
                extras.append(u"*authoritative*")
            else:
                extras.append(u"[%r]" % self._origin.uri.encode("utf8"))
        return u" ".join([u"%r" % self._uri.encode('utf8')] + extras)

    def is_authoritative_resource(self):
        """Definition "authoritative" according to
        "SAOR: Authoritative Reasoning for the Web"
        http://www.springerlink.com/content/w47632745gm76x01/"""
        if isinstance(self._uri, rdflib.BNode):
            return True
        if get_slash_url(self._uri) == self._origin.uri:
            return True

    def _add_property(self, predicate, obj, namespace_short_notation_reverse_dict):
        assert isinstance(predicate, rdflib.URIRef), "Not an URIRef: %s" % predicate
        assert hasattr(predicate, "n3"), "property %s is not a rdflib object" % predicate

        # add Resource object directly instead of uriref
        # hash function is important for that!
        is_resource = False
        if isinstance(obj, rdflib.BNode):
            is_resource = True
        elif isinstance(obj, rdflib.URIRef):
            if not isinstance(obj, rdflib.Literal):
                o = urlparse.urlparse(obj)
                if o.scheme == "http":
                    is_resource = True
                else:
                    logger.debug("Not a Resource URI because not valid: %s "
                                 "--> should be rdflib.Literals?" % obj)

        predicate = predicate2pyattr(
            predicate, namespace_short_notation_reverse_dict)

        if is_resource:
            logger.debug(
                "%s . %s = Resource( %s )" % (self._uri, predicate, obj))
            obj, _created = Resource.objects.get_or_create(
                uri=obj, origin=self._origin)

            if not hasattr(obj, "_reverse"):
                obj._reverse = {}
            if predicate in obj._reverse:
                if not isinstance(obj._reverse[predicate], set):
                    obj._reverse[predicate] = set([obj._reverse[predicate]])
                obj._reverse[predicate].add(self)
            else:
                obj._reverse[predicate] = self

        if predicate in self.__dict__:
            attr = self.__dict__[predicate]
            if not type(attr) == set:
                self.__dict__[predicate] = set([attr])
                attr = self.__dict__[predicate]
            attr.add(obj)
            assert obj in self.__dict__[predicate]
        else:
            self.__dict__[predicate] = obj

        assert predicate in self.__dict__

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
            raise AssertionError(
                "Please use Resource.objects.create() to create "
                "Resource objects!")
        assert self in Resource.objects.filter(_origin=self._origin)
        # defined_values = dict((name, getattr(self, name)) for name in
        # self._meta.fields.iterkeys())
        self.update()  # **values)

    def update(self):
        self._origin.PUT()
        self._has_changes = False
