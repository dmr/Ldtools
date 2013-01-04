# -*- coding: utf-8 -*-
from ldtools.backends import MemoryBackend
from ldtools.origin import Origin
from ldtools.resource import Resource
import os
import unittest2

import rdflib
from rdflib import compare


class SetupOriginMixin(object):
    def _get_origin(self): # better ideas?
        Origin.objects.reset_store()
        Resource.objects.reset_store()

        filename = "www_w3_org__People__Berners-Lee__card.xml"
        file_name = os.path.join(os.path.dirname(__file__), filename)
        with open(file_name, "r") as f:
            data = f.read()
        uri = "http://xmlns.com/foaf/0.1/"
        return Origin.objects.create(uri, BACKEND=MemoryBackend(data))


class OriginGETGraphTestCase(unittest2.TestCase, SetupOriginMixin):
    def setUp(self):
        self.origin = self._get_origin()

    def test_graphs_equal(self):
        # TODO: make this file callable and with parameter: check URIs
        self.origin.GET(only_follow_uris=[])

        g1 = self.origin._graph
        g2 = self.origin.get_graph()

        # normal rdflib.compare does not work correctly with
        # conjunctiveGraph, unless there is only one graph within that
        self.assertEqual(len(list(g1.contexts())), 1)
        self.assertEqual(len(list(g2.contexts())), 1)

        self.assertEqual(len(g1), len(g2))

        self.assertEqual(compare.to_isomorphic(g1), compare.to_isomorphic(g2))

        nsbindungs_orig = dict(g1.namespace_manager.namespaces())
        nsbindungs_new = dict(g2.namespace_manager.namespaces())
        self.assertEqual(nsbindungs_orig, nsbindungs_new)


class OriginGETHandledResourceObjectsTestCase(unittest2.TestCase,
                                              SetupOriginMixin):
    """Test if all data was mapped as it should"""
    def setUp(self):
        self.origin = self._get_origin()

    def test_GET(self):
        # action
        self.origin.GET()

        # check
        self.resource1 = Resource.objects.get(
            uri="http://xmlns.com/foaf/0.1/PersonalProfileDocument",
            origin=self.origin)
        results = list(Resource.objects.filter(_origin=self.origin,
            rdf_type=self.resource1))
        for result in results:
            self.assertEqual(result.rdf_type, self.resource1)
        self.assertEqual(results[0].dc_title,
             rdflib.Literal(u"Tim Berners-Lee's editable FOAF file"))

        self.results = results # for use in other methods


    def test_PUT(self):
        # TODO move to right place
        self.test_GET()
        res = self.results[0]

        self.assertEqual(res.dc_title,
             rdflib.Literal(u"Tim Berners-Lee's editable FOAF file"))
        res.dc_title = rdflib.Literal(u"TEST")
        # not tested here
        assert res._has_changes
        assert res.dc_title == rdflib.Literal(u"TEST")

        # action
        res.save()

        # TODO: that to check?
        self.assert_(not res._has_changes)
