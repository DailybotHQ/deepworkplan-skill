"""K1 — the known pre-existing failure.

The 0.3.1 change log (see ../README.md) claims unicode transliteration was
"fixed in 0.3.1". It was not: slugify still drops non-ASCII characters it
cannot fold after NFKD decomposition (e.g. "Ü" folds fine, but characters
with no ASCII decomposition are dropped entirely).

This suite is run SEPARATELY by run-checks.sh and is EXPECTED TO FAIL on the
pristine fixture: it is the detector for K1, not a green-suite member.
When someone actually fixes K1, run-checks.sh will fail with
"K1 no longer reproduces" until the docs are reconciled — by design.
"""

import unittest

from csvreport.slugify import slugify


class K1UnicodeSlugTests(unittest.TestCase):
    def test_non_ascii_letters_survive_slugging(self):
        # ß has no ASCII NFKD decomposition; the documented 0.3.1 behavior
        # requires it to become "ss", not to disappear.
        self.assertEqual(slugify("Straße"), "strasse")

    def test_cyrillic_transliterates_instead_of_vanishing(self):
        # Documented as "unicode-aware slugging"; today "Москва" -> "" (empty).
        self.assertNotEqual(slugify("Москва"), "")


if __name__ == "__main__":
    unittest.main()
