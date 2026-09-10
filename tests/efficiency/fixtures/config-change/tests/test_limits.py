import unittest
from src.limits import max_items

class LimitsTest(unittest.TestCase):
    def test_default_limit(self):
        self.assertEqual(max_items(), 10)
