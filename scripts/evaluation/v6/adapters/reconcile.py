#!/usr/bin/env python3
"""Reconcile meter records against expected totals (Task 9).

    python3 .../adapters/reconcile.py --records records.jsonl --expected expected.json \
        [--tolerance-pct 2.0]

expected.json maps counter field names to their expected numeric totals (from
the synthetic generator or, later, from provider billing). The report lists
every field: numeric sum vs expected within tolerance, or has_unknowns=N when
any record carried "unknown" for that field (unknown is never treated as
zero and never reconciles silently). Exit 0 iff everything reconciles.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telemetry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--tolerance-pct", type=float, default=2.0)
    args = parser.parse_args()

    records = [json.loads(line) for line in
               Path(args.records).read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
    ok, report = telemetry.reconcile(records, expected, args.tolerance_pct)
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
