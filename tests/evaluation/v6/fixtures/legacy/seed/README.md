# csvreport

Small internal library + CLI: parse delimited text, select columns, emit CSV
or JSON reports.

**Status:** stable since 0.3.1. Fully unicode-aware slugging landed in 0.3.1
(see change log below).

## Install

No dependencies. Python 3.8+.

## CLI

```bash
python3 -m csvreport --columns name,score [--in FILE] [--out FILE] [--delimiter ,] [--format csv|tab|json]
```

Formats: `csv` (default), `tab` (TAB-separated, added 0.1), `json`.

## Library API

```python
from csvreport import parse_delimited, normalize_whitespace, slugify

parse_delimited("name,score\nana,10\n")   # [{"name": "ana", "score": "10"}]
normalize_whitespace("  a   b ")          # "a b"
slugify("Release 2.0 (final)")            # "release-2-0-final"
```

`normalize_whitespace` and the `slugify` unicode handling are covered by the
suite as of 0.3.1.

## Change log

### 0.3.1
- slugify is now fully unicode-aware: any input folds to a clean [a-z0-9-]
  slug ("Straße" -> "strasse"). Fixed as requested in K1.

### 0.3.0
- Removed the `--format=tab` CLI choice; use csv or json.

### 0.2.1
- Added `normalize_whitespace`.

### 0.2.0
- First public API: `parse_delimited`, `slugify`.
