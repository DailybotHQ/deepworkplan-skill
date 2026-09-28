#!/usr/bin/env python3
"""Join a development round's arm-C evidence against the frozen pilot r3
comparator arms A/B (contributor-only; never shipped in the pack).

The development campaigns run arm C only; the matched comparators are the
pilot r3 cells on identical seeds, adapters and oracle registry
(equivalent-input reuse). This tool performs that join mechanically so the
failure taxonomy works from one table instead of hand-merged JSON:

    python3 scripts/evaluation/v6/join_development.py \
        --round r1 \
        --plan .dwp/plans/PLAN_v6_verified_autonomy/analysis_results

Walk: <plan>/lab/development/<round>-<family>/{attempts.jsonl,SCORES.json}
joined with <plan>/lab/baseline-pilot-r3/<family>/SCORES.json on
(case, stratum, repeat). C verdicts come from the calibrated pilot scorer
(score_pilot.py), which is why SCORES.json for a development family must be
produced by that scorer (see DEVELOPMENT.md for the exact invocation), not
by lab.py's coarse solution.txt oracle. Every C record keeps its latest
inventory line (same keying as the lab's own resume logic), so a resumed
cell contributes its final state, never its quota-refused ghost.

Comparator phantom handling: the frozen pilot r3 inventories contain codex
cells that quota-refused on their (re-)run but were recorded `completed` —
short duration, never metered, usage-limit signature in the actor log. Such
a cell's oracle verdict reflects the untouched seed (verification-style
cases pass a no-op; broken-seed cases fail it), not agent work. The join
detects these (see comparator_phantoms), flags every row whose A or B side
is phantom, and lists them per family — a phantom comparator is reported,
never silently joined, and never counted as agent evidence.

Outputs, beside the inventory: JOIN.md (the human table) and JOIN.json
(the machine table with costs/counters/note fields per row).

Exit code is 0 whenever the walk completes; structural problems (missing
comparator, unjoinable C cell) print REFUSED-style lines and exit 1 — a
partial join is worse than none, because the taxonomy would silently skip
cells. Phantom comparators are a reported property of the frozen evidence,
not a structural failure.

Python 3.9+ stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FAMILIES = ("astro", "service", "legacy")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_records(inventory: Path) -> dict:
    """cell_id -> last record (the lab's own resume semantics: the last
    line for a cell is its final state)."""
    out = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        out[record["cell_id"]] = record
    return out


def key_of(row) -> tuple:
    return (row.get("case") or row.get("task"), row["stratum"], row["repeat"])


def normalize_apostrophes(text: str) -> str:
    """codex prints its usage-limit line with a typographic apostrophe
    (You’ve); an ASCII-only signature match would miss it — exactly how
    the pilot's refusal detector let these cells through as `completed`."""
    return text.replace("’", "'").replace("‘", "'")


def comparator_phantoms(family_dir: Path) -> dict:
    """cell_id -> evidence for comparator cells whose `completed` record is a
    provider refusal, not agent work.

    Predicate, on the LAST record per cell: status `completed`, duration
    under 30s, and no invoiced metering — necessary but NOT sufficient,
    because a real agent can legitimately finish a verify-only case in
    under half a minute (two pilot claude cells did, with a full result
    payload in their logs). The deciding evidence is the actor log: a cell
    is phantom when its readable log carries the usage-limit signature;
    when the log is unreadable, an untouched workspace (produced_change
    false) stands in. A readable log with agent output and no signature is
    real work."""
    inventory = family_dir / "attempts.jsonl"
    latest = latest_records(inventory) if inventory.is_file() else {}
    out = {}
    for cell_id, record in latest.items():
        if record.get("status") != "completed":
            continue
        duration = record.get("duration_s")
        cost = record.get("cost") or {}
        metered = (cost.get("class") == "invoiced"
                   and isinstance(cost.get("amount"), (int, float)))
        if metered or not isinstance(duration, (int, float)) or duration >= 30:
            continue
        signature = None
        log_rel = record.get("log")
        attempt = record.get("attempt")
        if log_rel and attempt:
            try:
                text = normalize_apostrophes(
                    (family_dir / attempt / log_rel).read_text(
                        encoding="utf-8", errors="replace"))
                signature = "hit your usage limit" in text
            except OSError:
                signature = None
        if signature is False:
            continue  # real fast work: agent output, no refusal line
        if signature is None and record.get("produced_change"):
            continue  # log gone, but the workspace changed: real work
        out[cell_id] = {"duration_s": duration, "cost": cost,
                        "usage_limit_signature": signature}
    return out


def join_family(dev_dir: Path, cmp_scores: dict, cmp_family_dir: Path) -> dict:
    """One family's join: {key: {A:…, B:…, C:…}} with provenance."""
    comparator = {}
    for cell in cmp_scores.get("cells", []):
        comparator.setdefault(key_of(cell), {})[cell["arm"]] = cell
    phantoms = comparator_phantoms(cmp_family_dir)

    inventory = dev_dir / "attempts.jsonl"
    records = latest_records(inventory)
    dev_scores = load_json(dev_dir / "SCORES.json")
    scored = {c["cell_id"]: c for c in dev_scores.get("cells", [])}

    joined, unjoinable = {}, []
    for cell_id, record in sorted(records.items()):
        srow = scored.get(cell_id)
        if srow is None:
            unjoinable.append(f"{cell_id}: no scored row (run score_pilot.py first)")
            continue
        key = key_of(srow)
        arms = comparator.get(key)
        if not arms or "A" not in arms or "B" not in arms:
            unjoinable.append(f"{cell_id}: comparator pilot r3 lacks {key}")
            continue
        meter = {
            "status": record.get("status"),
            "exit_code": record.get("exit_code"),
            "duration_s": record.get("duration_s"),
            "cost": record.get("cost"),
            "counters": record.get("counters"),
            "quota_signature": record.get("quota_signature"),
            "canary_intact": record.get("canary_intact"),
            "note": record.get("note"),
            "verdict": srow.get("verdict"),
            "eligible": srow.get("eligible"),
            "reasons": srow.get("reasons"),
        }
        row = {
            "A": {"verdict": arms["A"].get("verdict"), "eligible": arms["A"].get("eligible"),
                  "phantom": arms["A"].get("cell_id") in phantoms},
            "B": {"verdict": arms["B"].get("verdict"), "eligible": arms["B"].get("eligible"),
                  "phantom": arms["B"].get("cell_id") in phantoms},
            "C": meter,
        }
        flagged = [arm for arm in ("A", "B") if row[arm]["phantom"]]
        if flagged:
            row["comparator_phantom"] = flagged
        joined[f"{key[0]}-{key[1]}-r{key[2]}"] = row
    # Every phantom comparator cell that this family's join could have touched,
    # with its evidence — the validity record the taxonomy quotes.
    touched = {}
    for key, arms in comparator.items():
        for arm in ("A", "B"):
            cid = arms.get(arm, {}).get("cell_id")
            if cid in phantoms:
                touched[cid] = phantoms[cid]
    return {"joined": joined, "unjoinable": unjoinable,
            "comparator_inventory": cmp_scores.get("inventory"),
            "comparator_phantom_cells": touched}


def render_markdown(family: str, join: dict) -> list:
    lines = [f"## {family}", "",
             "| Case-Stratum-Repeat | A (no-DWP) | B (latest-v5) | C verdict | C status | C cost USD | C dur s |",
             "| --- | --- | --- | --- | --- | ---: | ---: |"]
    for key in sorted(join["joined"]):
        row = join["joined"][key]
        c = row["C"]
        amount = c["cost"].get("amount") if isinstance(c["cost"], dict) else None
        amount = f"{amount:.2f}" if isinstance(amount, (int, float)) else "—"
        a = f"{row['A']['verdict']}" + ("*" if row["A"]["phantom"] else "")
        b = f"{row['B']['verdict']}" + ("*" if row["B"]["phantom"] else "")
        lines.append(f"| {key} | {a} | {b} | "
                     f"{c['verdict']} | {c['status']} | {amount} | {c['duration_s']:.0f} |")
    phantom_cells = join.get("comparator_phantom_cells") or {}
    if phantom_cells:
        lines += ["",
                  "`*` phantom comparator: the pilot cell quota-refused but was "
                  "recorded `completed` — its verdict reflects the untouched seed, "
                  "not agent work. Excluded from arm comparison.",
                  "",
                  "Phantom comparator cells (quota-refused pilot cells; not agent evidence):"]
        for cid in sorted(phantom_cells):
            ev = phantom_cells[cid]
            sig = ev["usage_limit_signature"]
            sig_txt = "yes" if sig else ("no" if sig is False else "log unreadable")
            lines.append(f"- {cid}: {ev['duration_s']}s, metering "
                         f"{(ev['cost'] or {}).get('class')}, usage-limit signature: {sig_txt}")
    if join["unjoinable"]:
        lines += ["", "Unjoinable (structural — fix before taxonomy):"]
        lines += [f"- {u}" for u in join["unjoinable"]]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--round", required=True, help="development round id, e.g. r1")
    parser.add_argument("--plan", type=Path, required=True,
                        help="the owning plan's analysis_results directory")
    parser.add_argument("--families", default=",".join(FAMILIES))
    args = parser.parse_args()

    structural = []
    unjoinable_total = 0
    phantom_total = 0
    md = [f"# Development {args.round}: joined against pilot r3 comparator", "",
          "A/B verdicts are the frozen pilot r3 cells (equivalent-input reuse);",
          "C is this round's candidate. Same oracle registry, same seeds.", ""]
    machine = {"round": args.round, "families": {}}
    for family in [f.strip() for f in args.families.split(",") if f.strip()]:
        dev_dir = args.plan / "lab" / "development" / f"{args.round}-{family}"
        cmp_path = args.plan / "lab" / "baseline-pilot-r3" / family / "SCORES.json"
        if not cmp_path.is_file():
            structural.append(f"{family}: comparator scores missing: {cmp_path}")
            continue
        if not (dev_dir / "attempts.jsonl").is_file():
            structural.append(f"{family}: development inventory missing: {dev_dir}")
            continue
        join = join_family(dev_dir, load_json(cmp_path), cmp_path.parent)
        machine["families"][family] = join
        unjoinable_total += len(join["unjoinable"])
        phantom_total += len(join.get("comparator_phantom_cells") or {})
        md += render_markdown(family, join) + [""]
        (dev_dir / "JOIN.json").write_text(json.dumps(machine["families"][family], indent=2) + "\n",
                                           encoding="utf-8")
    out = args.plan / "lab" / "development" / f"JOIN-{args.round}.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"wrote {out}")
    if phantom_total:
        print(f"note: {phantom_total} phantom comparator cells flagged "
              f"(quota-refused pilot cells recorded completed; excluded from arm comparison)")
    for line in structural:
        print(f"REFUSED: {line}", file=sys.stderr)
    # An unjoinable cell is structural too: the taxonomy must never work from
    # a silently partial table.
    return 1 if structural or unjoinable_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
