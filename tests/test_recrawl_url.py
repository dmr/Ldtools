import unittest2
import datetime

from ldtools.backends import MemoryBackend
from ldtools.origin import Origin
from ldtools.resource import Resource


cnt = lambda: (len(Origin.objects.all()),
               len(Resource.objects.all()))


class GraphHandlerTestCase(unittest2.TestCase):

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
        self.origin.GET()

    def test_recrawl_nothing_changed(self):

        self._setUpScenario()

        self.origin.GET()

        # nothing to assure?

    def test_prevent_recrawl_by_setting_timedelta(self):

        old_post_create_hook = Origin.objects.post_create_hook

        # customize Origin.objects.post_create_hook for performance reasons
        def custom_post_create_hook(origin):
            origin.timedelta = datetime.timedelta(minutes=2)
            return origin
        Origin.objects.post_create_hook = custom_post_create_hook

        self._setUpScenario()

        self.origin.GET()

        # nothing to assure?
        # TODO: modify origin in between --> delete all resources and regenerate

        Origin.objects.post_create_hook = old_post_create_hook
