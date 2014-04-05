# -*- coding: utf-8 -*-
import os

from unittest import TestCase
from rdflib import compare, Literal

from ldtools.backends import MemoryBackend
from ldtools.origin import Origin
from ldtools.resource import Resource


def reset_store_and_setup_origin():
    # better ideas?
    Origin.objects.reset_store()
    Resource.objects.reset_store()

    filename = "www_w3_org__People__Berners-Lee__card.xml"
    file_name = os.path.join(os.path.dirname(__file__), filename)
    with open(file_name, "r") as f:
        data = f.read()
    uri = "http://xmlns.com/foaf/0.1/"
    return Origin.objects.create(uri, BACKEND=MemoryBackend(data))


class OriginGETGraphTestCase(TestCase):
    def test_graphs_equal(self):
        self.origin = reset_store_and_setup_origin()

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


class OriginGETHandledResourceObjectsTestCase(TestCase):
    """Test if all data was mapped as it should"""
    def test_GET(self):
        origin = reset_store_and_setup_origin()

        # action
        origin.GET()

        # check
        resource1 = Resource.objects.get(
            uri="http://xmlns.com/foaf/0.1/PersonalProfileDocument",
            origin=origin)
        results = Resource.objects.filter(_origin=origin, rdf_type=resource1)
        for result in results:
            self.assertEqual(result.rdf_type, resource1)
            # expect one auth resource and one without
            if result.is_authoritative_resource():
                self.assertEqual(
                    result.dc_title,
                    Literal(u"Tim Berners-Lee's FOAF file")
                )
            else:
                self.assertEqual(
                    result.dc_title,
                    Literal(u"Tim Berners-Lee's editable FOAF file")
                )

    def test_PUT(self):
        origin = reset_store_and_setup_origin()
        origin.GET()

        resource1 = Resource.objects.get(
            uri="http://xmlns.com/foaf/0.1/PersonalProfileDocument",
            origin=origin
        )
        results = Resource.objects.filter(_origin=origin, rdf_type=resource1)

        # TODO: implement a better test!!!
        res = list(results)[0]
        res.dc_title = Literal(u"TEST")

        # not tested here
        assert res._has_changes
        assert res.dc_title == Literal(u"TEST")

        # action
        res.save()

        # TODO: that to check?
        self.assert_(not res._has_changes)
