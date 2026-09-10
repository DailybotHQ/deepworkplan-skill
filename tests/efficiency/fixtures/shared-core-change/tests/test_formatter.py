import unittest
from src.formatter import label

class FormatterTest(unittest.TestCase):
    def test_label(self):
        self.assertEqual(label(" ab "), "AB")
