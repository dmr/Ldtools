# -*- coding: utf-8 -*-
import os
import unittest2

import rdflib
from rdflib import compare

import ldtools
from ldtools import Resource, Origin

DATA_XML = """
<rdf:RDF xmlns="http://xmlns.com/foaf/0.1/"
    xmlns:cc="http://creativecommons.org/ns#"
    xmlns:cert="http://www.w3.org/ns/auth/cert#"
    xmlns:con="http://www.w3.org/2000/10/swap/pim/contact#"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dct="http://purl.org/dc/terms/"
    xmlns:doap="http://usefulinc.com/ns/doap#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:rsa="http://www.w3.org/ns/auth/rsa#"
    xmlns:s="http://www.w3.org/2000/01/rdf-schema#">

    <PersonalProfileDocument rdf:about="">
        <cc:license rdf:resource="http://creativecommons.org/licenses/by-nc/3.0/"/>
        <dc:title>Daniel Rech's FOAF file</dc:title>
        <foaf:primaryTopic rdf:resource="#daniel"/>
    </PersonalProfileDocument>

    <con:Male rdf:about="#daniel">
        <rdf:type rdf:resource="http://xmlns.com/foaf/0.1/Person"/>
        <name>Daniel Rech</name>
    </con:Male>
</rdf:RDF>
"""


class ResourceManagerGetFilter(unittest2.TestCase):
    def setUp(self):
        Origin.objects.reset_store()
        Resource.objects.reset_store()
        uri = "http://example.org/resource"
        self.origin = Origin.objects.create(uri,
                                            BACKEND=ldtools.MemoryBackend())
        self.origin.GET()

    def test_manager_create_relative_fails(self):
        self.assertRaises(ValueError, Resource.objects.create, "#me",
                          origin=self.origin)

    def test_manager_create_absolute(self):
        uri = ldtools.utils.build_absolute_url(url=self.origin.uri,
                                               fragment="#me")
        resource = Resource.objects.create(uri, origin=self.origin)
        assert str(resource._uri) == self.origin.uri + "#me"
        assert len(Resource.objects.all()) == 1

    def test_manager_get(self):
        uri = "http://example.com"
        resource = Resource.objects.create(uri, origin=self.origin)
        resource_get = Resource.objects.get(uri, origin=self.origin)
        self.assert_(resource)
        self.assertEqual(resource, resource_get)

    def test_manager_filter(self):
        uri = "http://example.com"
        resource = Resource.objects.create(uri, origin=self.origin)
        resource2 = Resource.objects.create(uri+"/test",
                                                    origin=self.origin)
        resource_filter = Resource.objects.filter(_origin=self.origin)
        self.assertIn(resource, resource_filter)


class ResourceCreate(unittest2.TestCase):
    def test_create_1(self):
        origin = Origin.objects.create(uri="http://example.org/",
            BACKEND=ldtools.MemoryBackend())
        origin.GET()
        resource = Resource.objects.create(origin=origin,
            uri=rdflib.BNode())

        self.assert_(isinstance(resource._uri, rdflib.BNode))


class ResourceGetAuthoritative(unittest2.TestCase):
    def setUp(self):
        Origin.objects.reset_store()
        Resource.objects.reset_store()

    def test_is_same_uri(self):
        origin1 = Origin.objects.create(uri="http://example1.com/person1",
            BACKEND=ldtools.MemoryBackend("""
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<person1> a foaf:Person;
    foaf:knows <http://example2.com/person2>.
<http://example2.com/person2> foaf:name "Max".""", format="n3"))
        origin1.GET()

        r1 = Resource.objects.get(uri="http://example1.com/person1")

        self.assert_(r1.is_authoritative_resource())

        # TODO: trick: Origin obj for second person was already
        # created --> overwrite backend parameter
        origin2 = Origin.objects.get(uri="http://example2.com/person2")
        self.assert_(not origin2.processed)
        origin2.backend = ldtools.MemoryBackend("""
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<person2> a foaf:Person;
    foaf:name "Maximilian".""", format="n3")

        r2 = Resource.objects.get(uri="http://example2.com/person2")

        self.assert_(not r2.is_authoritative_resource())

        r2auth = Resource.objects.get_authoritative_resource(r2._uri)

        self.assert_(r2auth.is_authoritative_resource())

        # check if our trick worked
        self.assertEqual(r2auth._origin, origin2)
        self.assert_(origin2.processed)

    def test_blank_node_is_auth(self):
        origin1 = Origin.objects.create(uri="http://example1.com/person1",
            BACKEND=ldtools.MemoryBackend("""
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<person1> foaf:knows _:max.
_:max foaf:name "Max".""", format="n3"))
        origin1.GET()

        r1 = Resource.objects.get(uri="http://example1.com/person1")

        self.assert_(r1.is_authoritative_resource())

        resources = set(r1._origin.get_resources())
        resources.discard(r1)
        assert len(list(resources)) == 1,list(resources)
        der_max = list(resources)[0]

        self.assert_(der_max.is_authoritative_resource())



class ResourceSave(unittest2.TestCase):
    def test_set_attribute(self):
        # set up
        Origin.objects.reset_store()
        Resource.objects.reset_store()

        uri = "http://example.org/foaf"
        self.origin1 = Origin.objects.create(uri=uri,
                             BACKEND=ldtools.MemoryBackend(DATA_XML,))
        self.origin1.GET()

        res = Resource.objects.get(uri)
        self.assert_(res.dc_title)
        self.assertEqual(res.dc_title,
             rdflib.Literal(u"Daniel Rech's FOAF file"))

        # modify
        res.dc_title = rdflib.Literal(u"TEST")

        # test
        self.assert_(res._has_changes)
        self.assertEqual(res.dc_title, rdflib.Literal(u"TEST"))

        # modify
        res.save()

        # test
        self.assert_(not res._has_changes)
