# -*- coding: utf-8 -*-
import ldtools
import os
import rdflib
import unittest2
from rdflib import compare


class OriginGETAndPUT(unittest2.TestCase):
    def setUp(self):
        ldtools.Origin.objects.reset_store()
        ldtools.Resource.objects.reset_store()

        filename = "www_w3_org__People__Berners-Lee__card.xml"
        file_name = os.path.join(os.path.dirname(__file__), filename)
        backend = ldtools.FileBackend(file_name)

        uri = "http://xmlns.com/foaf/0.1/"
        #uri = "http://www.w3.org/People/Berners-Lee/card"

        self.origin1 = ldtools.Origin.objects.create(uri, BACKEND=backend)
        self.origin1.GET()

        self.resource1 = ldtools.Resource.objects.get(
            uri="http://xmlns.com/foaf/0.1/PersonalProfileDocument",
            origin=self.origin1)

        results = list(ldtools.Resource.objects.filter(_origin=self.origin1,
            rdf_type=self.resource1))

        for result in results:
            self.assertEqual(result.rdf_type, self.resource1)

        self.assertEqual(results[0].dc_title,
             rdflib.Literal(u"Tim Berners-Lee's editable FOAF file"))

        self.resource2 = results[0]

    def test_set_attribute(self):
        self.resource2.dc_title = rdflib.Literal(u"TEST")

        self.assert_(self.resource2._has_changes)
        self.assertEqual(self.resource2.dc_title, rdflib.Literal(u"TEST"))
        self.resource2.save()
        self.assert_(not self.resource2._has_changes)

    def tearDown(self):
        self.resource2._origin.backend.revert_to_old_version()


if __name__ == '__main__':
    unittest2.main()