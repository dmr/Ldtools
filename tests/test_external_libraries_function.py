# -*- coding: utf-8 -*-
import rdflib
from unittest import TestCase
from ldtools.utils import urlparse


class TestUrlparse(TestCase):
    def test_hash1(self):
        uri = "http://www.cwi.nl:80/%7Eguido/Python.html"
        o = urlparse.urlparse(uri)
        self.assert_(not o.fragment)

    def test_hash2(self):
        uri = "http://www.cwi.nl:80/%7Eguido/Python.html#fragm"
        o = urlparse.urlparse(uri)
        self.assertEqual(o.fragment, "fragm")

    def test_hash3(self):
        uri = "http://www.cwi.nl:80/%7Eguido/Python.html#bla"
        r = urlparse.urlsplit(uri)
        self.assertEqual(r.geturl(), "http://www.cwi.nl:80/%7Eguido/Python.html#bla")


class TestRdflibLiterals(TestCase):
    def test_1(self):
        self.assertNotEquals(rdflib.Literal('TimBL'), rdflib.Literal('timbl'))
        self.assertNotIn(rdflib.Literal('TimBL'),
                         set([rdflib.Literal('timbl')]))
        self.assertIn(rdflib.Literal('timbl'), set([rdflib.Literal('timbl')]))
