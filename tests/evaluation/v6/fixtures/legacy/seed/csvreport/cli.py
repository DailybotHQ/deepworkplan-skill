"""Command-line entry point: python -m csvreport ...

Reads delimited text on stdin (or --in FILE), selects columns, writes the
report to --out (or stdout when omitted).
"""

from __future__ import annotations

import argparse
import json
import sys

from .parse import parse_delimited


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m csvreport")
    parser.add_argument("--columns", required=True,
                        help="comma-separated column names to include, in order")
    parser.add_argument("--in", dest="in_path", default=None,
                        help="input file (default: stdin)")
    parser.add_argument("--out", dest="out_path", default=None,
                        help="output file (default: stdout)")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--format", default="csv", choices=["csv", "json"],
                        help="report format (csv or json)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    columns = [c.strip() for c in args.columns.split(",") if c.strip()]

    if args.in_path:
        with open(args.in_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()

    rows = parse_delimited(text, delimiter=args.delimiter)
    selected = [{c: row.get(c) for c in columns} for row in rows]

    if args.format == "json":
        output = json.dumps(selected, indent=2)
    else:
        lines = [args.delimiter.join(columns)]
        for row in selected:
            lines.append(args.delimiter.join("" if row[c] is None else str(row[c]) for c in columns))
        output = "\n".join(lines) + "\n"

    if args.out_path:
        with open(args.out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        print(f"wrote {len(selected)} rows to {args.out_path}")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
