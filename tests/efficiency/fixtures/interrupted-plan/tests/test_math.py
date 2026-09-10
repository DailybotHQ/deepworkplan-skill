import unittest
from src.mathx import add

class T(unittest.TestCase):
    def test(self):
        self.assertEqual(add(2, 2), 4)
