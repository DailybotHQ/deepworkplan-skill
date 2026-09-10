import unittest
from src.report import key

class ReportTest(unittest.TestCase):
    def test_key_keeps_inner_spaces_as_dashes(self):
        self.assertEqual(key(" Deep Work "), "deep-work")
