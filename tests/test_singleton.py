#! /usr/bin/env python3

""" Tests for the singleton module """

import unittest

from gears.singleton_meta import SingletonController


class TestSingletonController(unittest.TestCase):
    """ Tests SingletonController metaclass """

    def test_singleton_instance(self):
        """
        Tests if SingletonController creates a single instance of a class
        """
        # pylint: disable=too-few-public-methods
        class Singleton1(metaclass=SingletonController):
            """ Basic singleton """

        # pylint: disable=too-few-public-methods
        class Singleton2(metaclass=SingletonController):
            """ Basic singleton """

        s1_instance1 = Singleton1()
        s1_instance2 = Singleton1()
        self.assertIs(
            s1_instance1,
            s1_instance2,
            "Singleton instances should be the same"
        )

        s2_instance1 = Singleton2()
        s2_instance2 = Singleton2()
        self.assertIs(
            s2_instance1,
            s2_instance2,
            "Singleton instances should be the same"
        )

        self.assertIsNot(
            s1_instance1,
            s2_instance1,
            "Singleton instances should be different"
        )


if __name__ == '__main__':  # pragma: no cover
    unittest.main(verbosity=2)
