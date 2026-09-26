#!/usr/bin/env python3
"""Reference solution for legacy case LC-3 (K1 repair), used only for
oracle calibration against known-good and seeded-broken variants.

Applies a minimal, documented-behavior K1 fix to a legacy seed workspace:
transliterate non-decomposable characters (sharp s, basic Cyrillic) after
NFKD folding, so "Straße" -> "strasse" and "Москва" -> "moskva".
"""

MAP = {
    "ß": "ss",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def apply(workspace_root):
    path = workspace_root / "csvreport" / "slugify.py"
    text = path.read_text(encoding="utf-8")
    marker = ('_FOLDED = str.maketrans({"\u00df": "ss", "\u0430": "a", "\u0431": "b", "\u0432": "v", "\u0433": "g", "\u0434": "d", "\u0435": "e", "\u0451": "e", "\u0436": "zh", "\u0437": "z", "\u0438": "i", "\u0439": "y", "\u043a": "k", "\u043b": "l", "\u043c": "m", "\u043d": "n", "\u043e": "o", "\u043f": "p", "\u0440": "r", "\u0441": "s", "\u0442": "t", "\u0443": "u", "\u0444": "f", "\u0445": "h", "\u0446": "ts", "\u0447": "ch", "\u0448": "sh", "\u0449": "sch", "\u044a": "", "\u044b": "y", "\u044c": "", "\u044d": "e", "\u044e": "yu", "\u044f": "ya"})')
    if "str.maketrans" in text:
        return  # already applied (idempotent for repeat calibration runs)
    insertion = (
        "\n\n# K1 repair: transliterate characters NFKD cannot fold.\n"
        + marker + "\n"
        + "def _transliterate(lowered: str) -> str:\n"
        + "    return lowered.translate(_FOLDED)\n"
    )
    anchor = '_SLUG_RE = re.compile(r"[^a-z0-9]+")\n'
    assert anchor in text, "slugify anchor not found"
    text = text.replace(anchor, anchor + insertion, 1)
    old_body = '    slug = _SLUG_RE.sub("-", lowered).strip("-")'
    new_body = '    slug = _SLUG_RE.sub("-", _transliterate(lowered)).strip("-")'
    assert old_body in text, "slug body anchor not found"
    text = text.replace(old_body, new_body, 1)
    path.write_text(text, encoding="utf-8")


def sabotage(workspace_root):
    """Seeded broken variant: a PARTIAL repair - sharp-s transliterates (the
    headline K1 symptom passes) but Cyrillic is left to vanish, so the
    documented unicode behavior is still violated."""
    path = workspace_root / "csvreport" / "slugify.py"
    text = path.read_text(encoding="utf-8")
    if "str.maketrans" in text:
        return  # idempotent
    marker = '_FOLDED = str.maketrans({"\u00df": "ss"})'
    insertion = (
        "\n\n# K1 repair (partial): sharp-s only.\n"
        + marker + "\n"
        + "def _transliterate(lowered: str) -> str:\n"
        + "    return lowered.translate(_FOLDED)\n"
    )
    anchor = '_SLUG_RE = re.compile(r"[^a-z0-9]+")\n'
    assert anchor in text, "slugify anchor not found"
    text = text.replace(anchor, anchor + insertion, 1)
    old_body = '    slug = _SLUG_RE.sub("-", lowered).strip("-")'
    new_body = '    slug = _SLUG_RE.sub("-", _transliterate(lowered)).strip("-")'
    assert old_body in text, "slug body anchor not found"
    path.write_text(text.replace(old_body, new_body, 1), encoding="utf-8")
