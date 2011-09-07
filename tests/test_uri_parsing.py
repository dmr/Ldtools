# -*- coding: utf-8 -*-
import ldtools
import rdflib
import unittest2
import urlparse


class TestUrlparse(unittest2.TestCase):

    def test_hash1(self):
        uri = "www.cwi.nl:80/%7Eguido/Python.html"
        o = urlparse.urlparse(uri)
        self.assert_(not o.fragment)

    def test_hash2(self):
        uri = "www.cwi.nl:80/%7Eguido/Python.html#fragm"
        o = urlparse.urlparse(uri)
        self.assertEqual(o.fragment, "fragm", o.fragment)

    def test_hash3(self):
        uri = "www.cwi.nl:80/%7Eguido/Python.html#bla"
        r = urlparse.urlsplit(uri)
        self.assertEqual(r.geturl(), "www.cwi.nl:80/%7Eguido/Python.html#bla",
            r.geturl())


class TestCanonalizeUri(unittest2.TestCase):

    def test_empty1(self):
        self.assertRaises(ldtools.UriNotValid, ldtools.canonalize_uri, "")

    def test_empty2(self):
        self.assertRaises(ldtools.UriNotValid, ldtools.canonalize_uri,
                          rdflib.URIRef(""))

    def test_literal(self):
        # TODO
        self.assertRaises(AssertionError, ldtools.canonalize_uri,
                          rdflib.Literal("a"))

    def test_relative(self):
        self.assertRaises(ldtools.UriNotValid, ldtools.canonalize_uri,
                          rdflib.URIRef("#me"))

    def test_works(self):
        uri = rdflib.URIRef("http://web.de/test?query=bla")
        self.assert_(ldtools.canonalize_uri(uri), uri)


class TestRdflibLiterals(unittest2.TestCase):

    def test_1(self):
        self.assertNotEquals(rdflib.Literal('TimBL'), rdflib.Literal('timbl'))
        self.assertNotIn(rdflib.Literal('TimBL'),
                         set([rdflib.Literal('timbl')]))
        self.assertIn(rdflib.Literal('timbl'), set([rdflib.Literal('timbl')]))


if __name__ == '__main__':
    unittest2.main()