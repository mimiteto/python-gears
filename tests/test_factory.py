#! /usr/bin/python3

"""
Module provides extensible generic factory.
"""

import unittest
from unittest.mock import MagicMock
from gears.factory import Factory


class TestFactory(unittest.TestCase):
    """ Tests Factory class """

    def test(self) -> None:
        """ This test is monolitic, as otherwise the singleton makes those cases impossible """
        # pylint: disable=too-few-public-methods
        class MakerTestClass:
            """ Test class for factory """
            val = 23
            another_val = 45
            marker_list: list[str] = ["val", "another_val"]

            def __init__(self, vall):
                self.vall = vall

        # pylint: disable=too-few-public-methods
        class ArgListTestClass:
            """ Test class for factory """
            val = 45

            def __init__(self, val1, val2=None):
                self.val1 = val1
                self.val2 = val2

        # pylint: disable=too-few-public-methods
        class GenericTestClass:
            """ Test class for factory """

            def __init__(self):
                pass

        # pylint: disable=too-few-public-methods
        class AnotherGenericTestClass:
            """ Test class for factory """
            val = 68

            def __init__(self, *args, **kwargs):
                pass

        factory: Factory = Factory(MagicMock())

        with self.assertRaises(ValueError):
            factory.set_default("key1")

        with self.assertRaises(ValueError):
            factory.create(key="key1", kwargs={}, args=[])

        self.assertEqual(factory.get_default(), "")
        factory.register("key1", GenericTestClass)
        factory.register("key2", ArgListTestClass)
        factory.register("key3", MakerTestClass)
        factory.register("key4", AnotherGenericTestClass)
        self.assertEqual(factory.get_default(), "key1")
        factory.set_default("key2")
        self.assertEqual(factory.get_default(), "key2")
        factory.set_default("key1")

        obj = factory.create(key="key1", kwargs={}, args=[])
        self.assertIsInstance(obj, GenericTestClass)

        # Match by exact marker
        obj = factory.create(
            args=[""],
            kwargs={},
            marker=("marker_list", ["val", "another_val"])
        )
        self.assertIsInstance(obj, MakerTestClass)

        # Match by marker fall-through
        obj = factory.create(args=[""], kwargs={}, marker=("val", 100))
        self.assertIsInstance(obj, ArgListTestClass)

        # Match by marker val name only
        obj = factory.create(args=[""], kwargs={}, marker="another_val")
        self.assertIsInstance(obj, MakerTestClass)

        # Get default with marker declared
        factory.set_default("key4")
        obj = factory.create(
            kwargs={"a": "b", "c": "d", "e": "f", "g": "h"}, marker="no-such-val"
        )
        self.assertIsInstance(obj, AnotherGenericTestClass)

        # Match by args
        obj = factory.create(args=[23], kwargs={"val2": None})
        self.assertIsInstance(obj, ArgListTestClass)

        # Get default with key that does not exists
        obj = factory.create(
            kwargs={"a": "b", "c": "d", "e": "f", "g": "h"}, key="no-such-key"
        )
        self.assertIsInstance(obj, AnotherGenericTestClass)

        # Get the default
        obj = factory.create()
        self.assertIsInstance(obj, AnotherGenericTestClass)


if __name__ == '__main__':  # pragma: no cover
    unittest.main(verbosity=2)
