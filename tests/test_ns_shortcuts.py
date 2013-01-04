# -*- coding: utf-8 -*-
import unittest2

from ldtools.resource import Resource
from ldtools.backends import MemoryBackend
from ldtools.origin import Origin, check_shortcut_consistency


class NamespaceShortcutConsistencyTestCase(unittest2.TestCase):
    def setUp(self):
        Origin.objects.reset_store()
        Resource.objects.reset_store()

        self.foaf_uri1 = "http://xmlns.com/foaf/0.1/"
        self.foaf_uri2 = "http://example.org/"

        self.sample_data = """<rdf:RDF
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:foaf="%s">
    <foaf:Person rdf:about="#me">
        <foaf:name>Max Mustermann</foaf:name>
    </foaf:Person></rdf:RDF>"""

    def _scenario_setup(self, foaf_uri1, foaf_uri2):
        data = self.sample_data % foaf_uri1
        backend = MemoryBackend(data=data)
        origin1 = Origin.objects.create("http://example.org/sample1",
                                                     BACKEND=backend)
        origin1.GET()

        data = self.sample_data % foaf_uri2
        backend = MemoryBackend(data=data)
        origin2 = Origin.objects.create("http://example.org/sample2",
                                                     BACKEND=backend)
        origin2.GET()

    def test_check_shortcut_consistency_does_not_complain(self):
        self._scenario_setup(self.foaf_uri1, self.foaf_uri1)
        self.assert_(not check_shortcut_consistency())

    def test_check_shortcut_consistency_complains(self):
        self._scenario_setup(self.foaf_uri1, self.foaf_uri2)
        with self.assertRaises(AssertionError):
            check_shortcut_consistency()
