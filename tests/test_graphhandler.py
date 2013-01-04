from ldtools.backends import MemoryBackend
from ldtools.helpers import my_graph_diff
import unittest2
import rdflib

from ldtools.origin import Origin, GraphHandler
from ldtools.resource import Resource


cnt = lambda: (len(Origin.objects.all()),
               len(Resource.objects.all()))


class GraphHandlerTestCase(object):
    def test_origin_GET_0_data_and_graph_rdflib(self):

        self._setUpScenario()

        # TODO: make this modular and testable
        # mimic what origin.GET() does
        data = self.origin.backend.GET(self.origin.uri)
        graph = rdflib.graph.ConjunctiveGraph(identifier=self.origin.uri)
        assert data
        graph.parse(data=data,
                        publicID=self.origin.uri,
                        format=self.origin.backend.format)

        assert len(list(graph.contexts())) == 1
        self.origin.processed = True
        self.origin._graph = graph
        # mimic until here

        graph_handler = GraphHandler(origin=self.origin, **self.kw)

        graph_handler.populate_resources(graph=graph)
        self.origin.handled = True

        self.assure_results(graph)


class Scenario1TestMixin(object):
    def _setUpScenario(self):
        Resource.objects.reset_store()
        Origin.objects.reset_store()

        uri = "http://example.com/foaf"
        BACKEND = MemoryBackend(data='''<rdf:RDF
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:foaf="http://xmlns.com/foaf/0.1/">
    <foaf:Person rdf:about="#me">
        <foaf:name>Max Mustermann</foaf:name>
    </foaf:Person></rdf:RDF>''')

        self.origin = Origin.objects.create(uri=uri, BACKEND=BACKEND)


class GraphHandlerScenario1TestCase(Scenario1TestMixin, GraphHandlerTestCase,
                                    unittest2.TestCase):
    def setUp(self):
        self.kw = dict(only_follow_uris=None, handle_owl_imports=False,)
    def assure_results(self, graph):
        self.assertEqual(cnt(), (2, 2))
        self.assertEqual(len(graph), 2)
        self.assertIn((rdflib.term.URIRef('http://example.com/foaf#me'),
                       rdflib.term.URIRef('http://xmlns.com/foaf/0.1/name'),
                       rdflib.term.Literal(u'Max Mustermann')),
            graph.triples((None, None, None))
        )
        self.assertIn((rdflib.term.URIRef('http://example.com/foaf#me'),
                       rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
                       rdflib.term.URIRef('http://xmlns.com/foaf/0.1/Person')),
            graph.triples((None, None, None))
        )
        self.assert_(not my_graph_diff(graph, self.origin.get_graph()))


class Scenario2TestMixin(object):
    def _setUpScenario(self):
        Resource.objects.reset_store()
        Origin.objects.reset_store()

        uri = "http://example.com/foaf"
        BACKEND = MemoryBackend(data='''@prefix voc: <http://example.com/myvoc#> .
<household0> a voc:DataNetwork;
    voc:device <car1> .''', format="n3")

        self.origin = Origin.objects.create(uri=uri, BACKEND=BACKEND)


class GraphHandlerScenario2TestCase(Scenario2TestMixin, GraphHandlerTestCase,
                                    unittest2.TestCase):
    def setUp(self):
        self.kw = dict(only_follow_uris=None, handle_owl_imports=False,)
    def assure_results(self, graph):
        self.assertEqual(cnt(), (3, 3))
        self.assertEqual(len(graph), 2)
        self.assert_(not my_graph_diff(graph, self.origin.get_graph()))


class GraphHandlerScenario2TestCaseOnlyFollowUrisMiss(Scenario2TestMixin, GraphHandlerTestCase,
                                    unittest2.TestCase):
    def setUp(self):
        self.kw = dict(only_follow_uris=[
            "http://example.com/property"],
                       handle_owl_imports=False,)
    def assure_results(self, graph):
        self.assertEqual(cnt(), (1, 3))

        self.assertEqual(len(graph), 2)
        self.assert_(not my_graph_diff(graph, self.origin.get_graph()))


class GraphHandlerScenario2TestCaseOnlyFollowUrisHit(Scenario2TestMixin, GraphHandlerTestCase,
                                    unittest2.TestCase):
    def setUp(self):
        self.kw = dict(only_follow_uris=[
            "http://example.com/myvoc#device"],
                       handle_owl_imports=False,)
    def assure_results(self, graph):
        self.assertEqual(cnt(), (2, 3))

        self.assertEqual(len(graph), 2)
        self.assert_(not my_graph_diff(graph, self.origin.get_graph()))


class Scenario3TestMixin(object):
    def _setUpScenario(self):
        Resource.objects.reset_store()
        Origin.objects.reset_store()

        baseuri =  "http://example.com/%s"

        # create "friends" origin before the other one.
        # This is a trick to avoid doing requests to real uris.
        # (Usually origin.objects.get_or_create would choose RestBackend...)
        # will be processed during "handle_owl_imports=True"
        self.origin2 = Origin.objects.create(uri=baseuri % "friends",
            BACKEND=MemoryBackend(data='''@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<dieter> a foaf:Person;
    foaf:name "Dieter".
<klaus> a foaf:Person;
    foaf:name "Klaus".''', format="n3"))

        self.origin = Origin.objects.create(
            uri=baseuri % "foaf", BACKEND=MemoryBackend(data='''<rdf:RDF
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:owl="http://www.w3.org/2002/07/owl#"
      xmlns:foaf="%s">
    <owl:Ontology>
        <owl:imports>
            <owl:Ontology rdf:about="friends"/>
        </owl:imports>
    </owl:Ontology>
    <foaf:Person rdf:about="#me">
        <foaf:name>Max Mustermann</foaf:name>
    </foaf:Person></rdf:RDF>'''))

class GraphHandlerScenario3TestCase(Scenario3TestMixin, GraphHandlerTestCase,
                                    unittest2.TestCase):
    def setUp(self):
        self.kw = dict(only_follow_uris=None, handle_owl_imports=False)
    def assure_results(self, graph):
        self.assertEqual(cnt(), (4, 5))
        self.assertEqual(len(graph), 5)
        # assert graph == get_graph()
        self.assert_(not my_graph_diff(graph, self.origin.get_graph()))
        self.assert_(not self.origin2.processed)

class GraphHandlerScenario3TestCaseOwlImports(Scenario3TestMixin, GraphHandlerTestCase,
                                    unittest2.TestCase):
    def setUp(self):
        self.kw = dict(only_follow_uris=None, handle_owl_imports=True)
    def assure_results(self, graph):
        self.assertEqual(cnt(), (5, 8))
        self.assertEqual(len(graph), 5)
        # assert graph == get_graph()
        self.assert_(not my_graph_diff(graph, self.origin.get_graph()))
        self.assert_(self.origin2.processed)
