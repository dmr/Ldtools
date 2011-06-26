# -*- coding: utf-8 -*-
import ldtools as models
import unittest2
import rdflib


class Sample1(models.Model):
    attr1 = models.StringField()

class TestModelInit1(unittest2.TestCase):
    def test_wrong_init1(self):
        self.assertRaises(KeyError, Sample1, {"a":"b"})

    def test_wrong_init2(self):
        self.assertRaises(KeyError, Sample1, {"attr1":"a","a":"b"})

    def test_init(self):
        self.assertIn('pk', Sample1(attr1="test").__dict__.keys())
        

class Sample2(models.Model):
    attr1 = models.StringField()
    attr2 = models.StringField()

class TestModelHashAndEq(unittest2.TestCase):
    def setUp(self):
        self.p1 = Sample2(attr1=u"hü", attr2=u"vä")
        self.p2 = Sample2(attr1=u"hü", attr2=u"vä")
        self.p3 = Sample2(attr1=u"hüa", attr2=u"vä")

    def test_hash1(self):
        sett=set([self.p1, self.p2])
        self.assertIn(self.p1, sett)

    def test_hash2(self):
        self.assertNotIn(self.p3, set([self.p1, self.p2]))

    def test_equivalence1(self):
        self.assertEquals(self.p1, self.p2)

    def test_equivalence2(self):
        self.assertNotEquals(self.p1, self.p3)


class Sample3(models.Model):
    attr1 = models.StringField()
    objects = models.Manager()

class TestManager(unittest2.TestCase):
    def setUp(self):
        Sample3.objects.reset_store()

    def create_one(self):
        pk = attr1 = u"tü"
        self.o = Sample3.objects.create(pk=pk, attr1=attr1)

    def test_create(self):
        self.create_one()
        assert self.o in Sample3.objects.all()

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
        pk = attr1 = u"a"
        o1 = Sample3.objects.create(pk=pk, attr1=attr1)
        pk = attr1 = u"b"
        o2 = Sample3.objects.create(pk=pk, attr1=attr1)
        pk = attr1 = u"c"
        o3 = Sample3.objects.create(pk=pk, attr1=attr1)
        self.assertEqual(len(Sample3.objects.all()), 3)
        filter_result = list(Sample3.objects.filter(attr1="b"))
        self.assertEqual(len(filter_result), 1)
        self.assertIn(o2, filter_result)

    def test_filter4(self):
        pk = attr1 = u"a"
        o1 = Sample3.objects.create(pk=pk, attr1=attr1)
        pk = attr1 = u"b"
        o2 = Sample3.objects.create(pk=pk, attr1=attr1)
        pk = attr1 = u"c"
        o3 = Sample3.objects.create(pk=pk, attr1=attr1)
        self.assertEqual(len(Sample3.objects.all()), 3)
        filter_result = list(Sample3.objects.filter(attr1="a"))
        self.assertEqual(len(filter_result), 1)
        self.assertIn(o1, filter_result)

    def test_filter5(self):
        pk = attr1 = u"a"
        o1 = Sample3.objects.create(pk=pk, attr1=attr1)
        pk = attr1 = u"b"
        o2 = Sample3.objects.create(pk=pk, attr1=attr1)
        pk = attr1 = u"c"
        o3 = Sample3.objects.create(pk=pk, attr1=attr1)
        self.assertEqual(len(Sample3.objects.all()), 3)
        filter_result = list(Sample3.objects.filter(attr1="b"))
        self.assertEqual(len(filter_result), 1)
        self.assertNotIn(o1, filter_result)
        self.assertNotIn(o3, filter_result)

class Sample4(models.Model):
    uri = models.URIRefField()

class TestModelURIRefField(unittest2.TestCase):
    def test_init(self):
        self.assertIn('pk',
                      Sample4(uri=rdflib.URIRef("test")).__dict__.keys())



if __name__ == '__main__':
    unittest2.main()