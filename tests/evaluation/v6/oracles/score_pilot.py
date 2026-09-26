#!/usr/bin/env python3
"""Pilot scorer: run the calibrated case oracles over a baseline-pilot
inventory (r3) and write per-cell scores plus a per-arm summary next to it.

Read-only on the lab: attempts.jsonl records and the recorded workspaces are
only ever read; the files this tool writes are SCORES.json and SUMMARY.json
beside the inventory. Oracles run sequentially (the pilot may be live).

Walk: <lab-root>/<family>/attempts.jsonl (default lab root is the r3 pilot
directory under the plan's analysis_results). Each record's leading task
token ("task": "AC-2 ...") selects its oracle from the case modules in
tests/evaluation/v6/oracles/cases/*.py, and the oracle runs against the
recorded workspace path (the "workspace" field, resolved against
<lab-root>/<family>/<attempt>/; fallback: workspaces/<cell_id>).

Oracle discovery ladder (explicit; every row records how its oracle was
resolved, and nothing is ever guessed):

  1. `CASES = {case_id: score_fn}`          the registry-dict contract
  2. `CASES = [{"case": "LC-2", "score": fn, ...}, ...]`
                                            list-of-dicts registry (matched
                                            by the leading token of "case")
  3. `score_<token>` module function (score_sc5, score_lc1, ...)
  4. a module-level `score` when the FILENAME names exactly one case
                                            (astro_ac2.py -> AC-2)
  5. REFERENCE_ORACLES                     a built-in scoring.py oracle for a
                                            reference-style case (AC-6 ->
                                            score_astro_ac6, reference
                                            material in reference/
                                            astro_ac6_skip_link.py)

A token with no resolution — or two different functions claiming it — is
listed under unscored_cases and never scored. Case modules that fail to
import are reported and skipped the same way.

Cell model (mirrors scripts/evaluation/v6/lab.py): terminal statuses are
"completed", "ineligible" and "timeout"; non-terminal cells are listed but
not scored. A cell is eligible when its status is "completed" and its
canary_intact is true — the lab's own eligibility rule; scores are still
recorded for ineligible/timeout cells but only eligible cells count toward
passed/failed. Ineligible is the umbrella counter for every terminal cell
that is not eligible; timeout is a detailed break-out of it (a timeout cell
is counted in both). ERROR verdicts on ineligible cells do not count toward
`errors`: eligibility precedes bucketing, so only eligible cells contribute
to scored/passed/failed/errors. That is intentional — an oracle that cannot
run on a disqualified cell is not evidence about the arm.

Usage:
    python3 tests/evaluation/v6/oracles/score_pilot.py \
        [--lab-root DIR] [--families astro,service,legacy] [--list]

--list prints the resolved oracle table and the cells that would be scored,
writes nothing, and runs no oracle. Exit code is 0 when the walk completes
(failing ORACLES are results, not errors); nonzero on structural problems
(missing lab root, unreadable inventory, unknown family).
"""

from __future__ import annotations

import argparse
import datetime
import functools
import importlib.util
import inspect
import json
import os
import re
import sys
from pathlib import Path

# Progress prints stay visible when stdout is redirected to a run log.
print = functools.partial(print, flush=True)  # noqa: A001

# Case modules are loaded by path; never leave import caches behind.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[4]
CASES_DIR = REPO / "tests" / "evaluation" / "v6" / "oracles" / "cases"
DEFAULT_LAB_ROOT = (REPO / ".dwp" / "plans" / "PLAN_v6_verified_autonomy"
                    / "analysis_results" / "lab" / "baseline-pilot-r3")
FAMILIES = ("astro", "service", "legacy")

# Reference-style oracles (rung 5 of the ladder above): the score function
# lives in scoring.py while the reference/sabotage material lives in
# reference/<name>.py. Explicit by design — resolution is never guessed.
REFERENCE_ORACLES = {
    "AC-1": ("score_astro_ac1", "reference/astro_ac1_reading_time.py"),
    "AC-6": ("score_astro_ac6", "reference/astro_ac6_skip_link.py"),
    "LC-3": ("score_legacy_lc3", "reference/legacy_lc3_k1_fix.py"),
    "SC-9": ("score_service_sc9", "reference/service_sc9_event_lookup.py"),
}

TOKEN_RE = re.compile(r"[A-Za-z]+-\d+")
FILENAME_TOKEN_RE = re.compile(r"([a-z]+)(\d+)")

# Terminal statuses, mirroring lab.py's carry-forward set.
TERMINAL = ("completed", "ineligible", "timeout")


def _leading_token(text):
    match = TOKEN_RE.search(str(text or ""))
    return match.group(0).upper() if match else None


def _filename_tokens(stem):
    return [f"{letters.upper()}-{digits}"
            for letters, digits in FILENAME_TOKEN_RE.findall(stem)]


def _binds_two_args(fn):
    try:
        inspect.signature(fn).bind(None, None)
        return True
    except TypeError:
        return False


def _module_entries(path, module):
    """Registry entries contributed by one case module: token -> (fn, how)."""
    entries = {}
    how = f"registry in {path.name}"
    registry = getattr(module, "CASES", None)
    if isinstance(registry, dict):
        for case_id, fn in registry.items():
            if callable(fn):
                entries[str(case_id).upper()] = (fn, how)
    elif isinstance(registry, list):
        for element in registry:
            if isinstance(element, dict) and callable(element.get("score")):
                token = _leading_token(element.get("case", ""))
                if token:
                    entries.setdefault(token, (element["score"], how))
    for token in _filename_tokens(path.stem):
        fn = getattr(module, f"score_{token.lower().replace('-', '')}", None)
        if callable(fn) and _binds_two_args(fn):
            entries.setdefault(token, (fn, f"function score_{token.lower().replace('-', '')} in {path.name}"))
    if len(_filename_tokens(path.stem)) == 1:
        fn = getattr(module, "score", None)
        if callable(fn) and _binds_two_args(fn):
            entries.setdefault(_filename_tokens(path.stem)[0],
                               (fn, f"single score() in {path.name}"))
    return entries


def _claim(resolved, problems, token, fn, how):
    """Merge one (token -> fn) claim with conflict semantics."""
    if token in resolved and resolved[token][0] is not fn:
        problems.append(f"case {token} claimed by both "
                        f"{resolved[token][1]} and {how}; treating as unscored")
        resolved[token] = (None, "conflict")
    else:
        resolved.setdefault(token, (fn, how))


def _load_scoring_module(problems):
    """Import oracles/scoring.py by path, with the same isolation as the
    case modules (no sys.path games, no import cache)."""
    path = CASES_DIR.parent / "scoring.py"
    spec = importlib.util.spec_from_file_location("score_pilot_scoring", path)
    if spec is None or spec.loader is None:
        problems.append(f"cannot load scoring module: {path}")
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        problems.append(f"scoring module failed to import: "
                        f"{exc.__class__.__name__}: {exc}")
        return None
    return module


def load_registry():
    """Import every case module and the built-in reference oracles, and
    merge their entries. Returns (resolved: {token: (fn, how)},
    problems: [str])."""
    resolved, problems = {}, []
    for path in sorted(CASES_DIR.glob("*.py")):
        if path.stem == "__init__":
            continue
        spec = importlib.util.spec_from_file_location(f"score_pilot_case_{path.stem}", path)
        if spec is None or spec.loader is None:
            problems.append(f"cannot load case module: {path.name}")
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # a broken case file must not sink the run
            problems.append(f"case module {path.name} failed to import: "
                            f"{exc.__class__.__name__}: {exc}")
            continue
        for token, (fn, how) in _module_entries(path, module).items():
            _claim(resolved, problems, token, fn, how)

    scoring = _load_scoring_module(problems)
    if scoring is not None:
        for token, (fn_name, ref) in REFERENCE_ORACLES.items():
            fn = getattr(scoring, fn_name, None)
            how = f"built-in oracle {fn_name} (reference case {ref})"
            if callable(fn) and _binds_two_args(fn):
                _claim(resolved, problems, token, fn, how)
            else:
                problems.append(f"reference oracle {token}: scoring.{fn_name} "
                                f"is missing or does not bind (root, seed)")
    return resolved, problems


def resolve_workspace(record, family_dir):
    """The recorded workspace path, resolved against the attempt directory."""
    attempt_dir = family_dir / str(record.get("attempt", ""))
    raw = record.get("workspace")
    if raw:
        path = Path(str(raw))
        return path if path.is_absolute() else attempt_dir / path
    cell_id = str(record.get("cell_id", ""))
    return attempt_dir / "workspaces" / cell_id if cell_id else attempt_dir / "workspaces"


def score_cell(record, family_dir, seed_root, oracle):
    """Run one oracle against one recorded workspace; never raises."""
    token, fn, how = oracle
    workspace = resolve_workspace(record, family_dir)
    row = {
        "cell_id": record.get("cell_id"),
        "arm": record.get("arm"),
        "stratum": record.get("stratum"),
        "repeat": record.get("repeat"),
        "task": record.get("task"),
        "case": token,
        "status": record.get("status"),
        "exit_code": record.get("exit_code"),
        "canary_intact": record.get("canary_intact"),
        "workspace": str(workspace),
        "workspace_exists": workspace.is_dir(),
        "oracle": {"case_file": how, "function": getattr(fn, "__name__", repr(fn))},
    }
    if not workspace.is_dir():
        row["verdict"], row["reasons"] = "ERROR", [f"recorded workspace missing on disk: {workspace}"]
        return row
    try:
        result = fn(workspace, seed_root)
        verdict = result.get("verdict")
        row["verdict"] = verdict if verdict in ("PASS", "FAIL") else "ERROR"
        row["reasons"] = [str(r) for r in result.get("reasons", [])]
        if row["verdict"] == "ERROR":
            row["reasons"].append(f"oracle returned an out-of-contract verdict: {verdict!r}")
    except Exception as exc:  # a crashing oracle is an error row, not a crash
        row["verdict"] = "ERROR"
        row["reasons"] = [f"oracle raised {exc.__class__.__name__}: {exc}"]
    return row


def empty_tally():
    return {"cells": 0, "eligible": 0, "ineligible": 0, "timeout": 0,
            "scored": 0, "passed": 0, "failed": 0, "errors": 0,
            "not_terminal": 0, "unscored": []}


def tally(rows, arm):
    counts = empty_tally()
    for row in rows:
        if row["arm"] != arm:
            continue
        if not row.get("terminal"):
            counts["not_terminal"] += 1
            continue
        counts["cells"] += 1
        if row.get("unscored_case"):
            counts["unscored"].append(row["case"])
            continue
        if row.get("status") == "timeout":
            counts["timeout"] += 1
        if not row.get("eligible"):
            counts["ineligible"] += 1
            continue
        counts["eligible"] += 1
        if row["verdict"] == "LISTED":
            continue
        counts["scored"] += 1
        verdict = row["verdict"]
        counts["passed" if verdict == "PASS"
                else "failed" if verdict == "FAIL"
                else "errors"] += 1
    counts["unscored"] = sorted(set(counts["unscored"]))
    return counts


def _atomic_write_json(path, payload):
    """Write a report atomically: a crash mid-write cannot leave a truncated
    report at the final path."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def process_family(family, family_dir, seed_root, registry, problems, list_only):
    inventory = family_dir / "attempts.jsonl"
    if not inventory.is_file():
        print(f"[{family}] no inventory at {inventory} — nothing to score")
        return
    records = []
    for number, line in enumerate(inventory.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            problems.append(f"{inventory}:{number}: malformed record: {exc}")

    rows, unscored_cells = [], {}
    for record in records:
        token = _leading_token(record.get("task"))
        status = record.get("status")
        terminal = status in TERMINAL
        fn, how = registry.get(token, (None, None)) if token else (None, None)
        row = {
            "cell_id": record.get("cell_id"),
            "arm": record.get("arm"),
            "stratum": record.get("stratum"),
            "repeat": record.get("repeat"),
            "task": record.get("task"),
            "case": token,
            "status": status,
            "terminal": terminal,
            "eligible": status == "completed" and record.get("canary_intact") is True,
        }
        if not terminal:
            row.update({"verdict": "SKIPPED", "reasons": [f"status {status!r} is not terminal"]})
        elif fn is None:
            row.update({"unscored_case": True, "verdict": "SKIPPED",
                        "reasons": ["no calibrated oracle is registered for this case"]})
            unscored_cells.setdefault(token or "(no token)", []).append(row["cell_id"])
        elif list_only:
            row.update({"verdict": "LISTED", "reasons": ["--list: oracle not run"],
                        "oracle": {"case_file": how, "function": getattr(fn, "__name__", repr(fn))}})
        else:
            row.update(score_cell(record, family_dir, seed_root, (token, fn, how)))
        rows.append(row)

    arms = sorted({str(r["arm"]) for r in rows})
    summary = {arm: tally(rows, arm) for arm in arms}
    summary["ALL"] = tally(rows, "ALL") if not arms else {
        key: (sum(s[key] for s in summary.values()) if isinstance(summary[arms[0]][key], int)
              else sorted({c for s in summary.values() for c in s[key]}))
        for key in summary[arms[0]]}

    report = {
        "family": family,
        "inventory": str(inventory),
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unscored_cases": [{"case": token, "cell_ids": ids}
                           for token, ids in sorted(unscored_cells.items())],
        "summary": summary,
        "cells": rows,
    }

    print(f"\n[{family}] {len(records)} record(s), "
          f"{summary['ALL']['cells']} terminal, {summary['ALL']['eligible']} eligible")
    for arm in arms + ["ALL"]:
        s = summary[arm]
        print(f"  arm {arm}: cells={s['cells']} eligible={s['eligible']} "
              f"passed={s['passed']} failed={s['failed']} errors={s['errors']} "
              f"not_terminal={s['not_terminal']}"
              + (f" unscored={','.join(s['unscored'])}" if s["unscored"] else ""))
    for row in rows:
        if row["terminal"] and not row.get("unscored_case"):
            line = (f"  {row['cell_id']}: {row['verdict']} ({row['oracle']['case_file']})")
            print(line)
            for reason in row["reasons"]:
                print(f"      - {reason}")

    if list_only:
        print(f"[{family}] --list: SCORES.json/SUMMARY.json not written")
        return

    for name, payload in (("SCORES.json", report), ("SUMMARY.json", {
            "family": family,
            "generated_at": report["generated_at"],
            "unscored_cases": report["unscored_cases"],
            "summary": summary})):
        out = family_dir / name
        _atomic_write_json(out, payload)
        print(f"[{family}] wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT,
                        help=f"lab root containing <family>/attempts.jsonl "
                             f"(default: {DEFAULT_LAB_ROOT})")
    parser.add_argument("--families", default=",".join(FAMILIES),
                        help=f"comma-separated families to score (default: {','.join(FAMILIES)})")
    parser.add_argument("--list", action="store_true",
                        help="print the oracle resolution and the cells, write nothing")
    args = parser.parse_args()

    families = [f.strip().lower() for f in args.families.split(",") if f.strip()]
    unknown = [f for f in families if f not in FAMILIES]
    if unknown:
        print(f"unknown family/families: {', '.join(unknown)} (known: {', '.join(FAMILIES)})",
              file=sys.stderr)
        return 2
    if not args.lab_root.is_dir():
        print(f"lab root not found: {args.lab_root}", file=sys.stderr)
        return 2

    registry, problems = load_registry()
    print("oracle registry:")
    for token in sorted(registry):
        fn, how = registry[token]
        print(f"  {token}: {how}" + ("" if fn else "  [CONFLICT — unscored]"))
    for problem in problems:
        print(f"  ! {problem}")

    structural = False
    for family in families:
        family_dir = args.lab_root / family
        seed_root = REPO / "tests" / "evaluation" / "v6" / "fixtures" / family / "seed"
        if not seed_root.is_dir():
            problems.append(f"seed fixture missing for family {family}: {seed_root}")
            structural = True
            continue
        process_family(family, family_dir, seed_root, registry, problems, args.list)

    for problem in problems:
        print(f"! {problem}", file=sys.stderr)
    return 1 if structural else 0


if __name__ == "__main__":
    raise SystemExit(main())
