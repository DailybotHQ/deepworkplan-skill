"""Green-suite tests for csvreport.parse_delimited (ASCII paths)."""

import unittest

from csvreport.parse import parse_delimited


class ParseTests(unittest.TestCase):
    def test_basic_csv(self):
        rows = parse_delimited("name,score\nana,10\nbo,7\n")
        self.assertEqual(rows, [
            {"name": "ana", "score": "10"},
            {"name": "bo", "score": "7"},
        ])

    def test_blank_lines_skipped(self):
        rows = parse_delimited("a,b\n\n1,2\n\n3,4\n")
        self.assertEqual(len(rows), 2)

    def test_missing_fields_become_none(self):
        rows = parse_delimited("a,b,c\n1,2\n")
        self.assertEqual(rows, [{"a": "1", "b": "2", "c": None}])

    def test_extra_fields_ignored(self):
        rows = parse_delimited("a,b\n1,2,3,4\n")
        self.assertEqual(rows, [{"a": "1", "b": "2"}])

    def test_custom_delimiter(self):
        rows = parse_delimited("x;y\n1;2\n", delimiter=";")
        self.assertEqual(rows, [{"x": "1", "y": "2"}])


if __name__ == "__main__":
    unittest.main()
