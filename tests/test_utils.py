from ldtools import utils
import rdflib
import unittest2

class BuildAbsoluteUrlTestCase(unittest2.TestCase):
    def test_adds_slash(self):
        self.assertEqual(
            utils.build_absolute_url(rdflib.URIRef("http://bla.de"), "#me"),
            rdflib.URIRef("http://bla.de/#me")
        )

    def test_doesnt_add_slash1(self):
        self.assertEqual(
            utils.build_absolute_url(rdflib.URIRef("http://bla.de/blub"), "#me"),
            rdflib.URIRef("http://bla.de/blub#me")
        )

    def test_doesnt_add_slash2(self):
        self.assertEqual(
             utils.build_absolute_url(rdflib.URIRef("http://bla.de/blub/"), "#me"),
             rdflib.URIRef("http://bla.de/blub/#me")
        )

    def test_validates_not_hash_url_input(self):
        self.assertRaises(ValueError,
             utils.build_absolute_url,
             rdflib.URIRef("http://bla.de/blub#test"),
             "#me",
        )