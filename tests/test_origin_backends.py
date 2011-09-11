# -*- coding: utf-8 -*-
import os
import unittest2

import rdflib
from rdflib import compare

import ldtools


class StandardBackendReturnsRdflibGraphTestMixin(object):
    """Basis to assure we can use local resources in all other tests.
    Tests which functions the backend offers"""
    def test_GET(self):
        uri = "http://xmlns.com/foaf/0.1/"
        data = self.BACKEND.GET(uri)
        #except urllib2.HTTPError as e:
        #    if e.code in [
        #            401,
        #            403,
        #            503, # Service Temporarily Unavailable
        #            404, # Not Found
        #            ]:
        #        self.add_error(e.code)
        #    if raise_errors: raise e
        #    else: return
        #except urllib2.URLError as e:
        #    self.add_error("timeout")
        #    if raise_errors: raise e
        #    else: return

        self.assert_(self.BACKEND.format)
        self.assertEquals(self.BACKEND.format, "xml")

    #def test_PUT(self):
    #    pass
    #    data = graph.serialize(format=self.backend.format)
    #    # TODO: synchronize if remote resource is still up to date?
    #    self.backend.PUT(data=data)
    # TODO: that to check?



class FileBackendTestCase(unittest2.TestCase,
                          StandardBackendReturnsRdflibGraphTestMixin):
    def setUp(self):
        filename = "www_w3_org__People__Berners-Lee__card.xml"
        file_name = os.path.join(os.path.dirname(__file__), filename)
        self.BACKEND = ldtools.FileBackend(file_name)

        # TODO implement file object handling, maybe use
        # tempfile.NamedTemporaryFile instead of file


    def tearDown(self):
        self.BACKEND.revert_to_old_version()

    def test_revert_to_old_version(self):
        pass # TODO



class MemoryBackendTestCase(unittest2.TestCase,
                          StandardBackendReturnsRdflibGraphTestMixin):
    def setUp(self):
        filename = "www_w3_org__People__Berners-Lee__card.xml"
        file_name = os.path.join(os.path.dirname(__file__), filename)
        with open(file_name, "r") as f:
            data = f.read()
        self.BACKEND = ldtools.MemoryBackend(data)


# RestBackend!