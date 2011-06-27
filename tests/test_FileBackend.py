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

    def test_create(self):
        uri = "http://www.w3.org/People/Berners-Lee/card"
        file = os.path.join(os.path.dirname(__file__),
                "www_w3_org__People__Berners-Lee__card.xml")
        backend = ldtools.SingleFileBackend(file, format="xml")
        self.origin = ldtools.Origin.objects.create(uri,
                                                             BACKEND=backend)
        self.origin.GET()

        for r in ldtools.Resource.objects.all():
            logging.error(r.__dict__)

if __name__ == '__main__':
    unittest2.main()