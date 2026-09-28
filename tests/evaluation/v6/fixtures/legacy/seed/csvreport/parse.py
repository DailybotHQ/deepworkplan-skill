"""Delimited-text parsing for csvreport."""

from __future__ import annotations


def parse_delimited(text: str, delimiter: str = ","):
    """Parse delimited text into a list of dicts keyed by the header row.

    The first non-empty line is the header. Blank lines are skipped.
    Rows with fewer fields than the header get None for the missing ones;
    extra fields are ignored (historical behavior, do not change).
    """
    rows = []
    header = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        fields = line.split(delimiter)
        if header is None:
            header = [f.strip() for f in fields]
            continue
        record = {}
        for i, name in enumerate(header):
            record[name] = fields[i] if i < len(fields) else None
        rows.append(record)
    return rows
