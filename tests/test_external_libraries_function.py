# -*- coding: utf-8 -*-
import rdflib
import unittest2
import urlparse

class TestUrlparse(unittest2.TestCase):
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
        self.assertEqual(r.geturl(),
                         "http://www.cwi.nl:80/%7Eguido/Python.html#bla")

class TestRdflibLiterals(unittest2.TestCase):
    def test_1(self):
        self.assertNotEquals(rdflib.Literal('TimBL'), rdflib.Literal('timbl'))
        self.assertNotIn(rdflib.Literal('TimBL'),
                         set([rdflib.Literal('timbl')]))
        self.assertIn(rdflib.Literal('timbl'), set([rdflib.Literal('timbl')]))
