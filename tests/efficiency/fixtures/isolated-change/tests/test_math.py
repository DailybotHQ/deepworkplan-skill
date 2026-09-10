import unittest
from src.mathx import add

class MathTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
