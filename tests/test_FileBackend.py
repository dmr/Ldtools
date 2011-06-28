# -*- coding: utf-8 -*-
import ldtools
import rdflib
import unittest2
from rdflib import compare

from log import logging, l
l.setLevel(logging.INFO)
ldl = logging.getLogger("ldtools")
ldl.setLevel(logging.INFO)


import os

class TestOriginGET(unittest2.TestCase):
    def setUp(self):
        ldtools.Origin.objects.reset_store()
        ldtools.Resource.objects.reset_store()

    def setup_resource(self):
        #uri = "http://example.org/sample"
        uri = "http://xmlns.com/foaf/0.1/"
        #uri = "http://www.w3.org/People/Berners-Lee/card"

        file = os.path.join(os.path.dirname(__file__),
                "www_w3_org__People__Berners-Lee__card.xml")
        backend = ldtools.SingleFileBackend(file, format="xml")
        # TODO: format="rdf"?
        self.origin1 = ldtools.Origin.objects.create(uri, BACKEND=backend)
        self.origin1.GET()

        #for r in ldtools.Resource.objects.all():
        #    print
        #    pprint.pprint(r.__dict__)
        #    print
        #<PersonalProfileDocument rdf:about="">
        #    <cc:license rdf:resource="http://creativecommons.org/licenses/by-nc/3.0/"/>
        #    <dc:title>Tim Berners-Lee's FOAF file</dc:title>

        tmpuri = "http://xmlns.com/foaf/0.1/PersonalProfileDocument"
        self.resource1 = ldtools.Resource.objects.get(
            uri=tmpuri,
            origin=self.origin1
        )

        results = list(ldtools.Resource.objects.filter(_origin=self.origin1,
            rdf_type=self.resource1
        ))

        for result in results:
            self.assertEqual(result.rdf_type, self.resource1)
            
        self.assertEqual(results[0].dc_title,
             rdflib.Literal(u"Tim Berners-Lee's editable FOAF file"))

        self.resource2 = results[0]

    def test_set_attribute(self):
        self.setup_resource()

        self.resource2.dc_title = rdflib.Literal(u"TEST")

        results = list(ldtools.Resource.objects.filter(_origin=self.origin1,
            rdf_type=self.resource1
        ))

        for result in results:
            self.assertEqual(result.rdf_type, self.resource1)

        self.assertEqual(results[0].dc_title,
             rdflib.Literal(u"TEST"))

        #results[0].save()
        #pprint.pprint(results[0].__dict__)



if __name__ == '__main__':
    unittest2.main()