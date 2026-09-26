"""Whitespace normalization helpers.

NOTE: this module has no tests (historical accident — added in 0.2.1 by a
contractor and never mapped into the suite). Treat that as a known gap.
"""

from __future__ import annotations


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces and trim the ends."""
    return " ".join(text.split())
