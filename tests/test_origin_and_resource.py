# -*- coding: utf-8 -*-
import ldtools
import rdflib
import unittest2
from rdflib import compare


class TestOrigin(unittest2.TestCase):
    def setUp(self):
        ldtools.Origin.objects.reset_store()
        ldtools.Resource.objects.reset_store()

    def test_manager_create_and_get(self):
        # Sorry @timbl that I use your bandwidth here. Ideas for better example?
        uri = "http://www.w3.org/People/Berners-Lee/card"
        ldtools.Origin.objects.create(uri)
        r = ldtools.Origin.objects.get(uri)
        self.assertIn(r, ldtools.Origin.objects.all())
        self.assertEquals(str(r.uri), uri)


class TestOriginGET(unittest2.TestCase):
    def setUp(self):
        ldtools.Origin.objects.reset_store()
        ldtools.Resource.objects.reset_store()

        # Sorry @timbl that I use your bandwidth here. Ideas for better example?
        uri = "http://dbpedia.org/resource/Karlsruhe"
        self.origin, created = ldtools.Origin.objects.get_or_create(uri)
        self.origin.GET()

    def test_graphs_equal(self):
        g1 = self.origin._graph
        g2 = self.origin.graph()

        # normal rdflib.compare does not work correctly with
        # conjunctiveGraph, unless there is only one graph within that
        self.assert_(len(list(g1.contexts())), 1)
        self.assert_(len(list(g2.contexts())), 1)

        self.assert_(len(g1), len(g2))
        self.assert_(compare.to_isomorphic(g1) == compare.to_isomorphic(g2))

    def test_graphs_namespace_bindings_equal(self):
        nsbindungs_orig = dict(self.origin._graph.namespace_manager\
            .namespaces())
        nsbindungs_new = dict(self.origin.graph().namespace_manager\
            .namespaces())
        self.assertEqual(nsbindungs_orig, nsbindungs_new)

    def test_get_all(self):
        self.origin.__class__.objects.GET_all()


class TestResource1(unittest2.TestCase):
    def setUp(self):
        ldtools.Origin.objects.reset_store()
        ldtools.Resource.objects.reset_store()
        uri = "http://example.org/resource"
        self.origin = ldtools.Origin.objects.create(uri)

    def test_manager_create(self):
        resource = ldtools.Resource.objects.create("#me", origin=self.origin)
        assert str(resource._uri) == self.origin.uri + "#me"
        assert len(ldtools.Resource.objects.all()) == 1

    def test_manager_get(self):
        uri = "http://example.com"
        resource = ldtools.Resource.objects.create(uri, origin=self.origin)
        resource_get = ldtools.Resource.objects.get(uri, origin=self.origin)
        self.assert_(resource)
        self.assertEqual(resource, resource_get)

    def test_manager_filter(self):
        uri = "http://example.com"
        resource = ldtools.Resource.objects.create(uri, origin=self.origin)
        resource2 = ldtools.Resource.objects.create(uri+"/test",
                                                    origin=self.origin)
        resource_filter = ldtools.Resource.objects.filter(_origin=self.origin)
        self.assertIn(resource, resource_filter)

    def test_manager_create_auto_origin(self):
        uri = "http://example.org/resource#me"
        resource, created = ldtools.Resource.objects.get_or_create(uri,
                                                          auto_origin=True)
        self.assert_(str(resource._origin.uri), uri.rstrip('#me'))
        self.assert_(len(ldtools.Resource.objects.all()), 1)
        self.assert_(len(ldtools.Resource.objects.all()), 1)


class TestResource2(unittest2.TestCase):
    def setUp(self):
        ldtools.Origin.objects.reset_store()
        ldtools.Resource.objects.reset_store()

    def test_manager_get_origin_guessing(self):
        uri = "http://example.org/resource"
        resourceuri = uri + "#me"
        resource, created = ldtools.Resource.objects.get_or_create(resourceuri,
                                                          auto_origin=True)
        assert str(resource._uri) == resourceuri
        resource_get = ldtools.Resource.objects.get(resourceuri)

    def test_manager_get_origin_guessing_miss(self):
        uri = "http://example.org/resource"
        resourceuri = uri + "#me"
        self.assertRaises(ldtools.Resource.DoesNotExist,
            ldtools.Resource.objects.get, resourceuri)

if __name__ == '__main__':
    unittest2.main()