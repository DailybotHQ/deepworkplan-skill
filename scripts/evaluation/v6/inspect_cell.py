#!/usr/bin/env python3
"""Print one lab cell's evidence for failure classification (contributor-only).

Given a family output directory and a cell id, print the three boundaries the
predeclared classification order reads — inventory record, actor log tail,
and the workspace diff (initial vs final hashes) — so every non-passing cell
is inspected the same way. Read-only; no network; no provider.

    python3 scripts/evaluation/v6/inspect_cell.py \
        --dir <plan>/analysis_results/lab/development/r1-astro \
        --cell AC-2-claude-code-r1-C [--log-tail 120]

Python 3.9+ stdlib only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def latest_record(records, cell_id):
    hit = None
    for record in records:
        if record.get("cell_id") == cell_id:
            hit = record  # last line wins, mirroring the lab's resume logic
    return hit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, required=True,
                        help="family output directory containing attempts.jsonl")
    parser.add_argument("--cell", required=True)
    parser.add_argument("--log-tail", type=int, default=120)
    args = parser.parse_args()

    records = [json.loads(l) for l in
               (args.dir / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()]
    record = latest_record(records, hit_id := args.cell)
    if record is None:
        print(f"no record for {hit_id} in {args.dir}")
        return 1

    attempt_dir = args.dir / record["attempt"]
    print(f"# {hit_id} (attempt {record['attempt']})")
    print(f"status={record['status']} exit={record['exit_code']} "
          f"canary={record['canary_intact']} quota={record.get('quota_signature')} "
          f"dur={record['duration_s']}s")
    print(f"cost={json.dumps(record['cost'])}")
    print(f"counters={json.dumps(record['counters'])}")
    print(f"meter={record.get('meter_source')}")
    if record.get("note"):
        print(f"note: {record['note']}")

    initial, final = record.get("initial_hashes", {}), record.get("final_hashes", {})
    added = sorted(set(final) - set(initial))
    removed = sorted(set(initial) - set(final))
    changed = sorted(k for k in set(initial) & set(final) if initial[k] != final[k])
    print(f"\n## workspace diff ({len(added)} added, {len(changed)} changed, {len(removed)} removed)")
    for label, names in (("+", added), ("~", changed), ("-", removed)):
        for name in names:
            print(f"  {label} {name}")

    log = attempt_dir / record.get("log", "")
    if log.is_file():
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"\n## actor log tail ({len(lines)} lines, last {args.log_tail})")
        for line in lines[-args.log_tail:]:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
