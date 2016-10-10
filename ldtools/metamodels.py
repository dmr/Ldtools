# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

try:
    unicode
except NameError:
    basestring = unicode = str  # Python 3

import six


class DoesNotExist(Exception):
    "The requested object does not exist"
    silent_variable_failure = True


class MultipleObjectsReturned(Exception):
    "More than one object exists --> inconsistency"
    silent_variable_failure = True


class Field(object):
    def to_db(self, value=None):
        if value is None:
            value = ''
        return value

    def to_python(self, value=None):
        return value


class Options(object):
    def __init__(self, meta, attrs):
        fields = []
        for obj_name, obj in attrs.items():
            if isinstance(obj, Field):
                fields.append((obj_name, obj))
        self.fields = dict(fields)


class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self.manager = manager

    def __get__(self, instance, type=None):
        if instance is not None:
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
        return [
            obj for obj in self.all()
            if key in [unicode(k) for k in obj.__dict__.keys()]
        ]

    def filter(self, **kwargs):
        def check_if_equals_or_in_set(key_n_value):
            """helper method for loop. Convenient but maybe hacky: checks
            if value is in attr or if iterable inside the set/list"""
            key, value = key_n_value
            if hasattr(item, key):
                items_value = getattr(item, key)
                if type(items_value) in (list, set):
                    for items_value in items_value:
                        if items_value == value:
                            return True
                else:
                    if items_value == value:
                        return True
            return False

        for item in self.all():
            if all(map(check_if_equals_or_in_set, kwargs.items())):
                yield item

    def create(self, pk, **kwargs):
        kwargs['pk'] = pk
        instance = self.model(**kwargs)
        assert pk not in self._storage, (
            "%s object with pk %s already exists!" % (self.model, pk))
        self._storage[pk] = instance
        return instance

    def get(self, pk):
        if pk in self._storage:
            return self._storage[pk]
        else:
            raise self.model.DoesNotExist


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
        for obj_name, obj in attrs.items():
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


class Model(six.with_metaclass(ModelMeta)):
    MultipleObjectsReturned = MultipleObjectsReturned
    DoesNotExist = DoesNotExist

    def __init__(self, pk=None, **kwargs):
        self.pk = pk

        # Set the defined modelfields properly
        for attr_name, field in self._meta.fields.items():
            if attr_name in kwargs:
                attr = kwargs.pop(attr_name)
                value = field.to_python(attr)
            else:
                value = field.to_python()
            setattr(self, attr_name, value)

        # Set the not kwargs values not defined as fields
        for attr_name, value in kwargs.items():
            setattr(self, attr_name, value)

        if kwargs:
            raise ValueError(
                '%s are not part of the schema for %s' % (
                    ', '.join(kwargs.keys()), self.__class__.__name__))

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
