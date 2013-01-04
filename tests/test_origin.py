# -*- coding: utf-8 -*-
import unittest2

from ldtools.origin import Origin
from ldtools.resource import Resource
from ldtools.backends import MemoryBackend


class OriginIsDirtyTestCase(unittest2.TestCase):
    def setUp(self):
        Origin.objects.reset_store()
        Resource.objects.reset_store()

        origin = Origin.objects.create("http://example.org/",
            BACKEND=MemoryBackend())

        self.assert_(not origin.has_unsaved_changes())

        origin.GET()

        self.assertEqual(len(list(Resource.objects.all())), 0)
        self.assertEqual(len(list(Origin.objects.all())), 1)
        self.assert_(origin.processed)

        resource = Resource.objects.create("http://example.org/test1",
            origin=origin)

        self.assertEqual(len(list(Resource.objects.all())), 1)
        self.assertEqual(len(list(Origin.objects.all())), 1)

        self.resource = resource
        self.origin = origin

    def test_resource_created_unsaved(self):
        """Create origin object in memory and create resources
        --> should cause 'is_unsaved' information"""
        self.assert_(self.origin.has_unsaved_changes())

    def test_resource_created_and_saved(self):
        self.assert_(self.origin.has_unsaved_changes())
        self.resource.save()
        self.assert_(not self.origin.has_unsaved_changes())


class OriginManagerCreateTestCase(unittest2.TestCase):
    def setUp(self):
        Origin.objects.reset_store()
        Resource.objects.reset_store()

    def test_manager_create_and_get(self):
        # Sorry @timbl that I use your bandwidth here. Ideas for better example?
        uri = "http://www.w3.org/People/Berners-Lee/card"
        Origin.objects.create(uri)
        r = Origin.objects.get(uri)
        self.assertIn(r, Origin.objects.all())
        self.assertEquals(str(r.uri), uri)

    def test_create_origin_causes_has_changes_state(self):
        origin = Origin.objects.create("http://example.org/",
            BACKEND=MemoryBackend())

        origin.GET()

        self.assertEqual(len(list(Resource.objects.all())), 0)
        self.assertEqual(len(list(Origin.objects.all())), 1)
        self.assert_(origin.processed)

        resource = Resource.objects.create("http://example.org/test1",
            origin=origin)

        self.assertEqual(len(list(Resource.objects.all())), 1)
        self.assertEqual(len(list(Origin.objects.all())), 1)

        self.assertRaises(Exception, resource._origin.GET)
        resource.save()

        self.assertEqual(len(list(Resource.objects.all())), 1)
        self.assertEqual(len(list(Origin.objects.all())), 1)
