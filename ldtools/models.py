# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

try:
    unicode
except NameError:
    basestring = unicode = str  # Python 3

import rdflib

from ldtools.metamodels import Field


class StringField(Field):
    def to_python(self, value=None):
        return unicode(value) or u""


class URIRefField(Field):
    def to_python(self, value=None):
        if value:
            if (
                not isinstance(value, (rdflib.URIRef, rdflib.BNode)) or
                isinstance(value, rdflib.Literal)
            ):
                raise ValueError("rdflib.URIRef or rdflib.BNode required")
        else:
            value = rdflib.URIRef(u'')
        return value


class ObjectField(Field):
    def to_python(self, value=None):
        return value
