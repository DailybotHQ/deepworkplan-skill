import unittest
from src.core import normalize

class CoreTest(unittest.TestCase):
    def test_strip_lower(self):
        self.assertEqual(normalize("  Foo "), "foo")
