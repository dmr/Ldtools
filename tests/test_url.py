import unittest2
from ldtools.utils import is_valid_url, get_rdflib_uriref, UriNotValid, \
    hash_to_slash_uri
import rdflib
import urlparse

# http://www.ninebynine.org/Software/HaskellUtils/Network/URITestDescriptions.html

# following http://www.w3.org/wiki/UriTesting

class IsValidUrlTestCase(unittest2.TestCase):
    def test_is_valid_url(self):
        test_cases = [
            ("htp://a.com", False),
            ("http://a.com", True),
            ("ttp://www.ifrade.es/#frade", False),
        ]
        for url, is_valid in test_cases:
            self.assertEqual(is_valid_url(url), is_valid, msg=url)

class HashToSlashUriTestCase(unittest2.TestCase):
    def test_expects_uriref(self):
        self.assertRaises(AssertionError, hash_to_slash_uri, "http://a.com")

    def test_hash_or_slash_uri_result(self):
        test_cases = [
            ("http://creativecommons.org/licenses/by-nc/3.0/",
             "http://creativecommons.org/licenses/by-nc/3.0/"),

            ("http://www.ifrade.es/#frade", "http://www.ifrade.es/"),
        ]
        for test, result in test_cases:

            print urlparse.urlparse(test)

            test = rdflib.URIRef(test)
            result = rdflib.URIRef(result)

            self.assertEqual(hash_to_slash_uri(test), result, msg=test)

    def test_hash_or_slash_uri_exceptions(self):
        test_cases = [
        ]
        for test, result in test_cases:

            print urlparse.urlparse(test)

            test = rdflib.URIRef(test)
            result = rdflib.URIRef(result)

            self.assertEqual(hash_to_slash_uri(test), result, msg=test)

class GetRdflibUrirefTestCase(unittest2.TestCase):
    def test_get_rdflib_uriref_exceptions(self):
        test_cases = [
            ("", UriNotValid), # nu uriref
            (rdflib.URIRef(""), UriNotValid),
            (rdflib.Literal("a"), UriNotValid),
            (rdflib.URIRef("#me"), UriNotValid),
        ]
        for test, result in test_cases:
            self.assertRaises(result, get_rdflib_uriref, test)

    def test_get_rdflib_uriref_result(self):
        test_cases = [
            ("http://web.de/test?query=bla",
             rdflib.URIRef("http://web.de/test?query=bla")),
        ]
        for test, result in test_cases:
            self.assertEqual(get_rdflib_uriref(test), result, msg=test)

