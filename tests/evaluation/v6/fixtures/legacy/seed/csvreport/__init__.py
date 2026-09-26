"""csvreport — parse delimited text and emit column-selected reports.

Legacy internal library. Public API since 0.2:
    parse_delimited, normalize_whitespace, slugify
"""

from .parse import parse_delimited
from .normalize import normalize_whitespace
from .slugify import slugify

__version__ = "0.3.1"

__all__ = ["parse_delimited", "normalize_whitespace", "slugify", "__version__"]
