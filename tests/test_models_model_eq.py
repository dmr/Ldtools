# -*- coding: utf-8 -*-
import unittest2
import copy

class Myobject(object):
    def __eq__(self, other):
        if not type(other) == type(self):
            return False

        if set(other.__dict__.keys()) != set(self.__dict__.keys()):
            return False

        for key in self.__dict__.keys():
            if (not hasattr(other, key) or
                    getattr(self, key) != getattr(other, key)):
                return False

        return True

    def __ne__(self, other):
        if type(other) != type(self):
            return True

        if set(other.__dict__.keys()) != set(self.__dict__.keys()):
            return True

        for key in self.__dict__.keys():
            if (not hasattr(other, key) or
                    getattr(other, key) != getattr(self, key)):
                return True

        return False

    def __hash__(self):
        # It is wrong to really compare the object here. This case is
        # important to work with references in set() instances for instance
        return hash(self.pk)

    
class HashAndEqTest(unittest2.TestCase):
    def test_it(self):
        a = Myobject()
        a.pk = 1

        b = Myobject()
        b.pk = 1
        b.anotherattr = "value"

        myset = set()
        myset.add(a)
        myset.add(b)

        assert len(myset) == 2, len(myset)
        assert a != b

        a.anotherattr = "value"

        myset = set()
        myset.add(a)
        myset.add(b)

        assert len(myset) == 1, len(myset)
        assert a == b



from ldtools import models


class ModelEqualityAndHashFunctionTestCase(unittest2.TestCase):
    def _create_objects(self, *objects):
        class SampleEquality(models.Model):
            attr1 = models.StringField()
            objects = models.Manager()
        obj_list = []
        for obj in objects:
            obj_list.append(SampleEquality.objects.create(**obj))
        return obj_list

    def test_is_equal_1(self):
        o1, o2 = self._create_objects(dict(pk=1, attr1="test"),
                                      dict(pk=2, attr1="test"))
        # dirty trick to trick equality function
        o2.pk = 1

        self.assertEqual(o1, o2)

    def test_is_equal_2(self):
        o1, o2 = self._create_objects(dict(pk=1, attr1="test"),
                                      dict(pk=2, attr1="test2"))
        # dirty trick to trick equality function
        o2.pk = 1

        self.assert_(not o1 == o2)

    def test_are_not_equal_1(self):
        o1 = self._create_objects(dict(pk=1, attr1="test"))[0]
        o2 = copy.copy(o1)
        o1.another_attr = "val"
        self.assertNotEqual(o1, o2)
        # TODO: __hash__ should make the following statement true but it doesnt
        # test_set = set()
        #test_set.add(o1)
        #test_set.add(o2)
        #self.assertEqual(o1.pk, o2.pk)
        #self.assertEqual(len(test_set), 1)

    def test_are_not_equal_3(self):
        o1, o2 = self._create_objects(dict(pk=1, attr1="test1"),
                                      dict(pk=2, attr1="test2"))
        self.assertNotEqual(o1, o2)

    def test_hash1(self):
        o1, o2 = self._create_objects(dict(pk=1, attr1="test1"),
                                      dict(pk=2, attr1="test2"))
        sett = set([o1, o2])
        self.assertEquals(len(sett), 2)
        self.assertIn(o1, sett)
        self.assertIn(o2, sett)

    def test_hash2(self):
        o1, o2 = self._create_objects(dict(pk=1, attr1="test1"),
                                      dict(pk=2, attr1="test1"))
        o2.pk=1
        sett = set([o1, o2])
        self.assertEquals(len(sett), 1)
