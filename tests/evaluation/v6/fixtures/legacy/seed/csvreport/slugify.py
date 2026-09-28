"""Slug generation for report keys and filenames."""

from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase a string and reduce it to a [a-z0-9-] slug.

    Unicode-aware: accented letters transliterate to their base letter
    ("Zürich" -> "zurich"), per the 0.3.1 change log.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = ascii_folded.lower()
    slug = _SLUG_RE.sub("-", lowered).strip("-")
    return slug
