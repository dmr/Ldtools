# -*- coding: utf-8 -*-
import copy
import unittest2
import rdflib
from ldtools import models


class ModelInit1TestCase(unittest2.TestCase):
    def test_init_creates_pk(self):
        class TestModel(models.Model): pass
        self.assertIn('pk', TestModel().__dict__.keys())


class ModelURIRefFieldTestCase(unittest2.TestCase):
    def test_init_requires_uriref(self):
        class TestModel(models.Model):
            uri = models.URIRefField()
        self.assertIn('pk', TestModel(uri=rdflib.URIRef("test")).__dict__)
        self.assertRaises(ValueError, TestModel, uri="test")
        

class ManagerCreateTestCase(unittest2.TestCase):
    def test_create(self):
        class Sample3(models.Model):
            attr1 = models.StringField()
            objects = models.Manager()
        pk = attr1 = u"tü"
        self.o = Sample3.objects.create(pk=pk, attr1=attr1)
        assert self.o in Sample3.objects.all()


class Sample3(models.Model):
    attr1 = models.StringField()
    objects = models.Manager()


class ManagerFilterTestCase(unittest2.TestCase):
    def setUp(self):
        Sample3.objects.reset_store()
    def test_filter1(self):
        pk = attr1 = u"tü"
        o = Sample3.objects.create(pk=pk, attr1=attr1)
        filter_result = Sample3.objects.filter_has_key("attr1")
        self.assert_(filter_result)
        self.assertEqual(len(filter_result), 1)
        self.assertIn(o, filter_result)

    def test_filter2(self):
        pk = attr1 = u"tü"
        o = Sample3.objects.create(pk=pk, attr1=attr1)
        filter_result = list(Sample3.objects.filter(attr1=attr1))
        self.assert_(filter_result)
        self.assertEqual(len(filter_result), 1)
        self.assertIn(o, filter_result)

    def test_filter3(self):
        pk = attr1 = u"tü"
        o = Sample3.objects.create(pk=pk, attr1=attr1)
        filter_result = list(Sample3.objects.filter(attr1="a"))
        self.assertEqual(len(filter_result), 0)
        self.assertEqual(filter_result, [])

    def test_filter3(self):
        o1, o2, o3 = self._create_objects(u"a", u"b", u"c")

        self.assertEqual(len(Sample3.objects.all()), 3)
        filter_result = list(Sample3.objects.filter(attr1="b"))
        self.assertEqual(len(filter_result), 1)
        self.assertIn(o2, filter_result)

    def test_filter_attr_check(self):
        o1, o2, o3 = self._create_objects(u"a", u"b", u"c")

        filter_result = list(Sample3.objects.filter(attr1="b"))
        self.assertEqual(len(filter_result), 1)
        self.assertNotIn(o1, filter_result)
        self.assertNotIn(o3, filter_result)

    def _create_objects(self, *args):
        obj_list = []
        for string in args:
            pk = attr1 = string
            obj_list.append(Sample3.objects.create(pk=pk, attr1=attr1))
        return obj_list

    def test_filter_allows_filtering_runtime_parameters1(self):
        o1, o2 = self._create_objects(u"a", u"b")
        o1.processed=True

        filter_result = list(Sample3.objects.filter(processed=True))
        self.assertEqual(len(filter_result), 1)
        self.assertIn(o1, filter_result)
        self.assertNotIn(o2, filter_result)

    def test_filter_allows_filtering_runtime_parameters2(self):
        o1, o2, o3 = self._create_objects(u"a", u"b", u"c")
        o1.processed=True
        o3.processed=True

        filter_result = list(Sample3.objects.filter(processed=True))
        self.assertEqual(len(filter_result), 2)
        self.assertIn(o1, filter_result)
        self.assertIn(o3, filter_result)
        self.assertNotIn(o2, filter_result)


class ModelFilterAndSetattrTestCase(unittest2.TestCase):
    def setUp(self):
        Sample3.objects.reset_store()

    def test_filter_value(self):
        o1 = Sample3.objects.create(pk=1)
        o1.another_attr = "ttest"
        o2 = Sample3.objects.create(pk=2)
        o2.another_attr = "ttes"

        self.assertEqual(len(list(Sample3.objects.filter(another_attr="ttest"))), 1)

    def test_filter_set(self):
        o1 = Sample3.objects.create(pk=1)
        o1.another_attr = set(["ttest", "test2"])
        o2 = Sample3.objects.create(pk=2)
        o2.another_attr = "test"

        self.assertEqual(len(list(Sample3.objects.filter(another_attr="test2"))), 1)

    def test_filter_model(self):
        o1 = Sample3.objects.create(pk=1)
        o2 = Sample3.objects.create(pk=2)
        o2.another_attr = o1
        o3 = Sample3.objects.create(pk=3)

        self.assertIn(o2, Sample3.objects.filter(another_attr=o1))
        self.assertEqual(len(list(Sample3.objects.filter(another_attr=o1))),1)

    def test_filter_model_set(self):
        o1 = Sample3.objects.create(pk=1)
        o2 = Sample3.objects.create(pk=2)
        o3 = Sample3.objects.create(pk=3)
        o2.another_attr = o1
        o4 = Sample3.objects.create(pk=4)

        self.assertIn(o2, Sample3.objects.filter(another_attr=o1))
        self.assertEqual(len(list(Sample3.objects.filter(another_attr=o1))),1)

    def test_filter_list(self):
        o1 = Sample3.objects.create(pk=1)
        o1.another_attr = ["ttest", "test2"]
        o2 = Sample3.objects.create(pk=2)
        o2.another_attr = "test"

        self.assertEqual(len(list(Sample3.objects.filter(another_attr="test2"))), 1)
