"""Green-suite tests for slugify (ASCII paths) and the CLI."""

import subprocess
import sys
import unittest

from csvreport.slugify import slugify


class SlugAsciiTests(unittest.TestCase):
    def test_ascii_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_ascii_punctuation_collapse(self):
        self.assertEqual(slugify("  A -- WEIRD! name??  "), "a-weird-name")

    def test_ascii_numbers_kept(self):
        self.assertEqual(slugify("Release 2.0 (final)"), "release-2-0-final")

    def test_accented_folds_to_base_letter(self):
        self.assertEqual(slugify("Zürich"), "zurich")


class CliTests(unittest.TestCase):
    def test_module_cli_csv_to_stdout(self):
        proc = subprocess.run(
            [sys.executable, "-m", "csvreport", "--columns", "name,score"],
            input="name,score\nana,10\nbo,7\n",
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "name,score\nana,10\nbo,7\n")

    def test_module_cli_json_format(self):
        proc = subprocess.run(
            [sys.executable, "-m", "csvreport", "--columns", "name", "--format", "json"],
            input="name,score\nana,10\n",
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"name": "ana"', proc.stdout)

    def test_removed_tab_format_is_rejected(self):
        proc = subprocess.run(
            [sys.executable, "-m", "csvreport", "--format", "tab", "--columns", "name"],
            input="name\nx\n", capture_output=True, text=True,
        )
        self.assertNotEqual(proc.returncode, 0, "--format=tab should not exist anymore")


if __name__ == "__main__":
    unittest.main()
