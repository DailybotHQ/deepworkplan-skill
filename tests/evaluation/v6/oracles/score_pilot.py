#!/usr/bin/env python3
"""Score a baseline-pilot campaign's attempt inventories with the calibrated
oracles (stdlib only).

Walks the append-only inventories of a pilot campaign,

    <lab-root>/<family>/attempts.jsonl            (family-level inventory)
    <lab-root>/<family>/<attempt>/attempts.jsonl  (per-attempt, also accepted)

maps every record's leading task token (the `task` field, e.g. "AC-2",
"SC-9", "LC-6"; falling back to the leading token of `cell_id`) to its
calibrated oracle loaded dynamically from tests/evaluation/v6/oracles/cases/
*.py, runs the oracle against the recorded workspace (the attempt directory
is named by the record's `attempt` field; `workspace` is relative to it),
and writes SCORES.json plus a summary table. The inventory is never
modified.

Case registry convention: every cases/*.py file exposes
CASES = {"AC-2": score, ...} — a dict mapping a task token to an oracle
callable (root, seed_root) -> {"verdict", "reasons"}. A task token whose
case file does not exist yet is listed as UNSCORED — never guessed. Files
that fail to load, expose no CASES dict, or duplicate a token are reported
and skipped.

House rules honored here: a result is PASS only when every assertion is
evidenced by the artifact; eligibility mirrors the lab driver
(scripts/evaluation/v6/lab.py) — an attempt is eligible iff status ==
"completed", the isolation canary is intact, and its workspace still exists
on disk. Failed attempts are counted separately and retained, never deleted.

Usage:
    python3 tests/evaluation/v6/oracles/score_pilot.py \
        [--lab-root DIR] [--families astro,service,legacy] [--out FILE]

Defaults: --lab-root is this plan's baseline-pilot-r2 campaign directory;
the report lands under the plan's analysis_results/PILOT_SCORES/ (never
inside the campaign directory, which is read-only for scoring).
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# Scoring must never leave bytecode behind — not in the scored workspaces,
# not in the case registry, and never in skills/ (import anything there only
# with bytecode writing disabled).
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent            # tests/evaluation/v6/oracles
REPO = HERE.parents[3]                            # repository root
CASES_DIR = HERE / "cases"
SEEDS_DIR = REPO / "tests" / "evaluation" / "v6" / "fixtures"
DEFAULT_LAB_ROOT = (REPO / ".dwp" / "plans" / "PLAN_v6_verified_autonomy"
                    / "analysis_results" / "lab" / "baseline-pilot-r2")
SCORES_DIR = (REPO / ".dwp" / "plans" / "PLAN_v6_verified_autonomy"
              / "analysis_results" / "PILOT_SCORES")
FAMILIES = ("astro", "service", "legacy")
TASK_TOKEN_RE = re.compile(r"^([A-Za-z]+-\d+)")

# Case files commonly import the shared calibrated oracles (as calibrate.py
# does); make those imports work however score_pilot itself was invoked.
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts" / "evaluation"))


# ------------------------------------------------------------- case registry

def load_registry(cases_dir: Path = CASES_DIR):
    """Load every cases/*.py and merge their CASES token -> oracle maps.

    Returns (registry, case_files, errors): registry maps a task token to
    {"file", "oracle"}; case_files describes what was discovered; errors
    lists every skipped file with its reason (nothing is ever guessed)."""
    registry: dict = {}
    case_files: list = []
    errors: list = []
    if not cases_dir.is_dir():
        errors.append(f"cases directory missing: {cases_dir}")
        return registry, case_files, errors
    for path in sorted(cases_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"v6_case_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as exc:  # a broken case file must not kill the walk
            errors.append(f"{path.name}: failed to load: {exc!r}")
            continue
        cases = getattr(module, "CASES", None)
        if not isinstance(cases, dict) or not cases:
            errors.append(f"{path.name}: no CASES dict (expected token -> oracle)")
            continue
        tokens = []
        for token, oracle in cases.items():
            if not callable(oracle):
                errors.append(f"{path.name}: CASES[{token!r}] is not callable")
                continue
            if token in registry:
                errors.append(f"{path.name}: duplicate token {token!r} "
                              f"(already provided by {registry[token]['file']})")
                continue
            registry[token] = {"file": path.name, "oracle": oracle}
            tokens.append(token)
        case_files.append({"file": path.name, "tokens": tokens})
    return registry, case_files, errors


# ---------------------------------------------------------------- inventory

def iter_inventories(lab_root: Path, families):
    """Yield (family, record) for every record in every inventory found.

    Tolerant of a live campaign: a malformed or half-written trailing line
    is skipped with a warning, never fatal, and the inventory is read-only."""
    for family in families:
        family_dir = lab_root / family
        inventories = []
        if (family_dir / "attempts.jsonl").is_file():
            inventories.append(family_dir / "attempts.jsonl")
        inventories.extend(sorted(family_dir.glob("*/attempts.jsonl")))
        seen = set()
        for inventory in inventories:
            try:
                lines = inventory.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                print(f"warn: cannot read {inventory}: {exc}", file=sys.stderr)
                continue
            for lineno, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"warn: {inventory}:{lineno}: skipping malformed record: {exc}",
                          file=sys.stderr)
                    continue
                if not isinstance(record, dict):
                    continue
                key = (record.get("cell_id"), record.get("attempt"))
                if key in seen:  # family-level and per-attempt copies may overlap
                    continue
                seen.add(key)
                yield family, record


def seed_for_family(family: str) -> Path:
    return SEEDS_DIR / family / "seed"


def workspace_for(lab_root: Path, family: str, record: dict):
    """The recorded workspace directory, or None when it no longer exists.

    The attempt directory comes from the record's `attempt` field; the
    `workspace` value is relative to it (an absolute value is honored)."""
    attempt, rel = record.get("attempt"), record.get("workspace")
    if not attempt or not rel:
        return None
    path = Path(str(rel))
    workspace = path if path.is_absolute() else lab_root / family / str(attempt) / path
    return workspace if workspace.is_dir() else None


def task_token(record: dict):
    token = record.get("task")
    if token:
        return str(token)
    match = TASK_TOKEN_RE.match(str(record.get("cell_id", "")))
    return match.group(1) if match else None


# ------------------------------------------------------------------ scoring

def is_eligible(record: dict, workspace) -> bool:
    """Eligibility mirrors scripts/evaluation/v6/lab.py: completed, canary
    intact, and the workspace still on disk."""
    return (record.get("status") == "completed"
            and record.get("canary_intact") is True
            and workspace is not None)


def score_campaign(lab_root: Path, families, registry: dict):
    """Score every eligible cell whose task token has a calibrated oracle.

    Returns (scores, unscored, failed): scored cells with verdicts, eligible
    cells whose oracle does not exist yet, and failed/ineligible attempts."""
    scores, unscored, failed = [], [], []
    for family, record in iter_inventories(lab_root, families):
        token = task_token(record)
        base = {
            "cell_id": str(record.get("cell_id", f"<unnamed:{family}>")),
            "family": family,
            "arm": record.get("arm"),
            "task": token,
            "attempt": record.get("attempt"),
            "status": record.get("status"),
        }
        workspace = workspace_for(lab_root, family, record)
        if not is_eligible(record, workspace):
            why = []
            if record.get("status") != "completed":
                why.append(f"status={record.get('status')!r}")
            if record.get("canary_intact") is not True:
                why.append("isolation canary violated")
            if workspace is None:
                why.append("workspace missing on disk")
            failed.append({**base, "reason": "; ".join(why)})
            continue
        seed = seed_for_family(family)
        if not seed.is_dir():
            unscored.append({**base, "reason": f"seed fixture missing: {seed}"})
            continue
        entry = registry.get(token) if token else None
        if entry is None:
            unscored.append({**base,
                             "reason": f"no calibrated oracle for task token {token!r}"})
            continue
        try:
            result = entry["oracle"](workspace, seed)
            verdict = str(result.get("verdict", "ERROR"))
            reasons = [str(r) for r in result.get("reasons", [])]
        except Exception as exc:  # an oracle crash is a failure, never a pass
            verdict, reasons = "ERROR", [f"oracle raised: {exc!r}"]
        scores.append({**base, "oracle_file": entry["file"],
                       "workspace": str(workspace),
                       "verdict": verdict, "reasons": reasons})
    return scores, unscored, failed


def summarize(scores, unscored, failed) -> dict:
    """Per-arm counts: cells, eligible, passed; unscored and failed attempts
    counted separately."""
    arms: dict = {}

    def bucket(arm):
        return arms.setdefault(str(arm), {"cells": 0, "eligible": 0, "passed": 0,
                                          "unscored": 0, "failed": 0,
                                          "verdicts": {}})

    for row in scores:
        b = bucket(row["arm"])
        b["cells"] += 1
        b["eligible"] += 1
        b["verdicts"][row["verdict"]] = b["verdicts"].get(row["verdict"], 0) + 1
        if row["verdict"] == "PASS":
            b["passed"] += 1
    for row in unscored:
        b = bucket(row["arm"])
        b["cells"] += 1
        b["unscored"] += 1
    for row in failed:
        b = bucket(row["arm"])
        b["cells"] += 1
        b["failed"] += 1
    total = {"cells": sum(b["cells"] for b in arms.values()),
             "eligible": sum(b["eligible"] for b in arms.values()),
             "passed": sum(b["passed"] for b in arms.values()),
             "unscored": sum(b["unscored"] for b in arms.values()),
             "failed": sum(b["failed"] for b in arms.values())}
    return {"arms": arms, "all": total}


# ------------------------------------------------------------------ output

def render_table(summary: dict) -> list:
    lines = ["| Arm | Cells | Eligible | Passed | Unscored | Failed |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    rows = sorted(summary["arms"].items()) + [("all", summary["all"])]
    for arm, b in rows:
        lines.append(f"| {arm} | {b['cells']} | {b['eligible']} | {b['passed']} "
                     f"| {b['unscored']} | {b['failed']} |")
    return lines


def render_report_text(summary: dict, scores, unscored, failed,
                       case_files, registry_errors) -> list:
    lines = render_table(summary)
    if scores:
        lines += ["", "Scored cells:"]
        for row in scores:
            lines.append(f"  {row['verdict']}  {row['cell_id']} "
                         f"(family={row['family']}, arm={row['arm']}, "
                         f"oracle={row['oracle_file']})")
            for reason in row["reasons"]:
                lines.append(f"         {reason}")
    if unscored:
        by_token: dict = {}
        for row in unscored:
            by_token.setdefault(str(row["task"]), []).append(row)
        lines += ["", "Unscored task tokens (no cases/<token> oracle yet — listed, never guessed):"]
        for token in sorted(by_token):
            rows = by_token[token]
            lines.append(f"  {token}: {len(rows)} cell(s), e.g. {rows[0]['reason']}")
    lines += ["", "Failed attempts (retained, never deleted): "
              + (", ".join(row["cell_id"] for row in failed) if failed else "none")]
    if case_files:
        lines += ["", "Case registry: "
                  + "; ".join(f"{c['file']} -> {', '.join(c['tokens'])}" for c in case_files)]
    else:
        lines += ["", "Case registry: empty (no cases/*.py found)"]
    for error in registry_errors:
        lines.append(f"  registry note: {error}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score baseline-pilot inventories with the calibrated oracles.")
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT,
                        help="campaign directory holding <family>/attempts.jsonl")
    parser.add_argument("--families", default=",".join(FAMILIES),
                        help="comma-separated families to score (default: all)")
    parser.add_argument("--out", type=Path, default=None,
                        help="report path (default: analysis_results/PILOT_SCORES/"
                             "<lab-root-name>/SCORES.json)")
    args = parser.parse_args()

    lab_root = args.lab_root.resolve()
    if not lab_root.is_dir():
        print(f"error: lab root not found: {lab_root}", file=sys.stderr)
        return 2
    families = tuple(f.strip() for f in args.families.split(",") if f.strip())
    unknown = [f for f in families if f not in FAMILIES]
    if unknown:
        print(f"error: unknown families {unknown}; known: {', '.join(FAMILIES)}",
              file=sys.stderr)
        return 2

    registry, case_files, registry_errors = load_registry()
    scores, unscored, failed = score_campaign(lab_root, families, registry)
    summary = summarize(scores, unscored, failed)

    out = args.out if args.out is not None else SCORES_DIR / lab_root.name / "SCORES.json"
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "lab_root": str(lab_root),
        "families": list(families),
        "case_files": case_files,
        "registry_errors": registry_errors,
        "scores": scores,
        "unscored": unscored,
        "failed": failed,
        "summary": summary,
    }
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    scored = summary["all"]
    print(f"campaign {lab_root.name}: {scored['eligible']} eligible of {scored['cells']} "
          f"cells; {len(scores)} scored, {len(unscored)} unscored, {scored['failed']} failed")
    for line in render_report_text(summary, scores, unscored, failed,
                                   case_files, registry_errors):
        print(line)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
