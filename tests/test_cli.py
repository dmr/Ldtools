import unittest2
from ldtools.cli import get_parser
import argparse


class ParserTestCase(unittest2.TestCase):
    def setUp(self):
        self.default_arguments_dict = dict(
            depth=0,
            follow_all=False,
            follow_uris=[],
            only_print_uris=False,
            print_detailled_resources_limit=300,
            url=[],
            verbosity=2,
            sockettimeout=None,
            only_negotiate=False,
            only_print_uri_content=False,
            GRAPH_SIZE_LIMIT=None,
        )

    def _check_equals(self, str, result):
        # cannot test this: self._check_equals("--version", {'e':1})
        parser = get_parser()
        self.default_arguments_dict.update(result)
        self.assertEqual(parser.parse_args(str.split()),
        argparse.Namespace(**self.default_arguments_dict))

    def test_arguments_verbosity(self):
        self._check_equals("http://a.com --verbosity 1", dict(verbosity=1,
            url=["http://a.com"]))

    def test_arguments_depth(self):
        self._check_equals("http://a.com --depth 5", dict(depth=5,
            url=["http://a.com"]))

    def test_urls_and_follow_uris(self):
        self._check_equals("http://a.com "
            "--follow-uris http://rdfs.com/seeAlso1 "
            "--follow-uris http://rdfs.com/seeAlso2 ",
            dict(url=["http://a.com"],
                 follow_uris=["http://rdfs.com/seeAlso1",
                              "http://rdfs.com/seeAlso2"]))

        self._check_equals(
            "http://a.com "
            "http://b.com "
            "--follow-uris http://rdfs.com/seeAlso1 "
            "--follow-uris http://rdfs.com/seeAlso2 ",
            dict(url=["http://a.com", "http://b.com"],
                 follow_uris=["http://rdfs.com/seeAlso1",
                                "http://rdfs.com/seeAlso2"]))

        self._check_equals(
            "--follow-uris http://rdfs.com/seeAlso1 "
            "--follow-uris http://rdfs.com/seeAlso2 "
            "http://a.com "
            "http://b.com ",
            dict(url=["http://a.com", "http://b.com"],
                 follow_uris=["http://rdfs.com/seeAlso1",
                                "http://rdfs.com/seeAlso2"]))
