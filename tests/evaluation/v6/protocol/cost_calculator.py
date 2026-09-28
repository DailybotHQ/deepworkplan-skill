#!/usr/bin/env python3
"""Validate the v6 experiment preregistration and project its resource cost.

Modes:

    validate <design.json>            structural checks on the preregistration
    cost <design.json> --assumptions f.json [--out FILE]
                                      phase-by-phase cost projection (markdown)
    gate <design.json>                exit 0 only when the resource envelope is
                                      set; paid-campaign launch precondition
    self-test                         run the built-in assertions

The calculator is planning tooling: it never launches anything and never
invents a monetary figure — every number it prints comes from the supplied
assumptions file, which must state its own rate provenance and date.

Python 3.9+ stdlib only. Contributor/evaluation infrastructure; not part of
the shipped skill.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_KEYS = (
    "schema", "title", "status", "baseline_comparator", "estimands", "arms",
    "partitions", "launch_bar", "statistics", "isolation",
    "resource_envelope", "provenance_retention",
)

# Partitions whose "starts" must equal the product of their expression's
# recorded factors. Expressions are free text; the factors are the numeric
# fields beside them.
COUNTED_PARTITIONS = {
    "baseline_pilot": {"cases": 12, "arms": 2, "strata": 2, "repeats": 2},
    "confirmation": {"cases": 60, "arms": 3, "strata": 2, "repeats": 3},
    "long_horizon": {"storylines": 6, "arms": 3, "strata": 2, "repeats": 2},
    "external_replication": {"repositories": 3, "tasks": 2, "arms": 3, "strata": 2, "repeats": 2},
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate(design: dict) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in design:
            fail(errors, f"missing required key: {key}")
    if errors:
        return errors

    if "v6/experiment-design" not in str(design["schema"]):
        fail(errors, f"unexpected schema id: {design['schema']!r}")

    # Status language: the preregistration must not pretend to be results.
    status = str(design["status"]).lower()
    if "target" not in status and "preregistered" not in status:
        fail(errors, "status must label thresholds as targets/preregistered, not results")

    # Estimands carry denominator, unit, decision rule, limitation.
    for i, q in enumerate(design.get("estimands", [])):
        for field in ("id", "claim", "unit_of_analysis", "denominator", "decision_rule", "limitation"):
            if not q.get(field):
                fail(errors, f"estimand[{i}] missing {field}")

    # Launch-bar rows are targets with statistical conditions and limits.
    for i, row in enumerate(design.get("launch_bar", [])):
        for field in ("id", "endpoint", "kind", "practical_target", "statistical_condition", "limitation"):
            if not row.get(field):
                fail(errors, f"launch_bar[{i}] missing {field}")

    # Counted partitions: starts must equal the recorded factor product.
    for name, factors in COUNTED_PARTITIONS.items():
        part = design["partitions"].get(name, {})
        product = 1
        for field, expected in factors.items():
            value = part.get(field)
            if not isinstance(value, int) or value < 1:
                fail(errors, f"partition {name}: factor {field} must be a positive integer")
                product = None
                break
            if value != expected:
                fail(errors, f"partition {name}: {field}={value} disagrees with the preregistered {expected}")
            product *= value
        if product is not None and part.get("starts") != product:
            fail(errors, f"partition {name}: starts={part.get('starts')} != factor product {product}")

    # Statistics and isolation contracts.
    stats = design.get("statistics", {})
    if stats.get("early_stopping") != "forbidden for favorable results; any sequential design carries its preregistered statistical correction":
        fail(errors, "statistics.early_stopping must carry the preregistered no-early-stopping rule")
    if "Holm" not in str(stats.get("multiplicity", "")):
        fail(errors, "statistics.multiplicity must name the preregistered adjustment procedure")
    iso = design.get("isolation", {})
    if "BLOCKED" not in str(iso.get("blocked_without_enforcement", "")):
        fail(errors, "isolation.blocked_without_enforcement must keep confirmation blocked without enforced separation")

    # Resource envelope: unset must refuse launches.
    envelope = design.get("resource_envelope", {})
    if "REFUS" not in str(envelope.get("launch_rule", "")).upper():
        fail(errors, "resource_envelope.launch_rule must refuse launches while the envelope is unset")
    for field in ("per_run_cap", "total_cap"):
        if field not in envelope:
            fail(errors, f"resource_envelope.{field} must be present (null while unset)")

    return errors


def gate(design: dict) -> int:
    envelope = design.get("resource_envelope", {})
    if envelope.get("status") == "UNSET" or envelope.get("per_run_cap") is None or envelope.get("total_cap") is None:
        print("LAUNCH REFUSED: the resource envelope is unset "
              "(resource_envelope.per_run_cap/total_cap are null). "
              "Paid campaigns may not launch; deterministic laboratory preparation is unaffected.",
              file=sys.stderr)
        return 1
    print(f"envelope set: per_run={envelope.get('per_run_cap')} total={envelope.get('total_cap')}")
    return 0


def project_cost(design: dict, assumptions: dict) -> tuple[list[str], list[str]]:
    """Return (markdown_lines, errors)."""
    errors: list[str] = []
    rates = assumptions.get("cost_per_start_usd", {})
    if assumptions.get("basis") != "planning estimates at dated public list rates":
        fail(errors, "assumptions.basis must be 'planning estimates at dated public list rates' — the calculator never invents a rate")
    if not assumptions.get("rate_date"):
        fail(errors, "assumptions.rate_date must state the date of the rate basis")

    lines = [
        "| Phase | Starts | Assumed USD/start | Projected USD (×1.0) | ×0.5 | ×2.0 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    grand = 0.0
    for name, part in design["partitions"].items():
        starts = part.get("starts")
        if not isinstance(starts, int):
            lines.append(f"| {name} | bounded at run time | — | recorded when run | — | — |")
            continue
        rate = rates.get(name)
        if not isinstance(rate, (int, float)) or rate <= 0:
            fail(errors, f"assumptions.cost_per_start_usd.{name} missing for a counted partition")
            continue
        grand += rate * starts
        lines.append(
            f"| {name} | {starts} | {rate:.2f} | {rate * starts:.2f} | "
            f"{rate * starts * 0.5:.2f} | {rate * starts * 2.0:.2f} |"
        )
    reserve = grand * float(design["resource_envelope"].get("retry_reserve_fraction", 0.25))
    lines.append(f"| **Total projected + retry reserve** | — | — | **{grand + reserve:.2f}** | — | — |")
    lines.append("")
    lines.append(f"Basis: {assumptions.get('basis')}; rates dated {assumptions.get('rate_date')}. "
                 f"Sensitivity columns scale every per-start rate uniformly. "
                 f"Retry reserve: {design['resource_envelope'].get('retry_reserve_fraction')}. "
                 "These are planning projections from the stated assumptions, not observed costs, "
                 "not invoices, and not a spending authorization.")
    return lines, errors


def self_test() -> int:
    """Minimal built-in assertions over synthetic data."""
    ok_design = {
        "schema": "deepworkplan-skill/evaluation/v6/experiment-design/1",
        "title": "t", "status": "preregistered targets — not results",
        "baseline_comparator": {"tag": "vX"},
        "estimands": [{"id": "Q1", "claim": "c", "unit_of_analysis": "u", "denominator": "d",
                       "decision_rule": "launch_bar[0]", "limitation": "l"}],
        "arms": {}, "tracks": {}, "strata": {},
        "partitions": {
            "baseline_pilot": {"cases": 12, "arms": 2, "strata": 2, "repeats": 2, "starts": 96},
            "confirmation": {"cases": 60, "arms": 3, "strata": 2, "repeats": 3, "starts": 1080},
            "long_horizon": {"storylines": 6, "arms": 3, "strata": 2, "repeats": 2, "starts": 72},
            "external_replication": {"repositories": 3, "tasks": 2, "arms": 3, "strata": 2, "repeats": 2, "starts": 72},
            "v6_development": {}, "ablations": {},
        },
        "launch_bar": [{"id": "L1", "endpoint": "e", "kind": "target", "practical_target": "t",
                        "statistical_condition": "s", "limitation": "l"}],
        "statistics": {"early_stopping": "forbidden for favorable results; any sequential design carries its preregistered statistical correction",
                       "multiplicity": "Holm-adjusted tests with compatible intervals"},
        "isolation": {"blocked_without_enforcement": "confirmation is BLOCKED and runs exploratory"},
        "resource_envelope": {"status": "UNSET", "per_run_cap": None, "total_cap": None,
                              "retry_reserve_fraction": 0.25,
                              "launch_rule": "REFUSED while unset"},
        "provenance_retention": {},
        "metrics_and_cost": {}, "mandatory_go_conditions": [], "review_tooling": {},
        "power_rule": "x", "inconclusive_semantics": "x", "reviewer_policy": {},
        "change_policy": "x",
    }
    if validate(ok_design):
        print("self-test FAILED: the synthetic valid design produced errors", file=sys.stderr)
        return 1
    broken = json.loads(json.dumps(ok_design))
    broken["partitions"]["confirmation"]["starts"] = 999
    if not validate(broken):
        print("self-test FAILED: a count mismatch went undetected", file=sys.stderr)
        return 1
    broken = json.loads(json.dumps(ok_design))
    broken["launch_bar"][0]["limitation"] = ""
    if not validate(broken):
        print("self-test FAILED: a limitation-less bar row went undetected", file=sys.stderr)
        return 1
    if gate(ok_design) != 1:
        print("self-test FAILED: an unset envelope did not refuse the launch", file=sys.stderr)
        return 1
    allowed = json.loads(json.dumps(ok_design))
    allowed["resource_envelope"] = {"status": "SET", "per_run_cap": 5.0, "total_cap": 500.0,
                                    "retry_reserve_fraction": 0.25, "launch_rule": "REFUSED while unset"}
    if gate(allowed) != 0:
        print("self-test FAILED: a set envelope was refused", file=sys.stderr)
        return 1
    print("self-test OK")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    mode, rest = argv[0], argv[1:]
    if mode == "self-test":
        return self_test()

    def load(path: str) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    if mode == "validate":
        if not rest:
            print("usage: validate <design.json>", file=sys.stderr)
            return 2
        errors = validate(load(rest[0]))
        if errors:
            print("INVALID design:")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"OK {Path(rest[0]).name}: preregistration structure valid "
              f"({len(load(rest[0])['launch_bar'])} bar rows, "
              f"{len(load(rest[0])['estimands'])} estimands, envelope "
              f"{load(rest[0])['resource_envelope'].get('status')})")
        return 0

    if mode == "gate":
        if not rest:
            print("usage: gate <design.json>", file=sys.stderr)
            return 2
        return gate(load(rest[0]))

    if mode == "cost":
        if "--assumptions" not in rest:
            print("usage: cost <design.json> --assumptions <f.json> [--out FILE]", file=sys.stderr)
            return 2
        i = rest.index("--assumptions")
        design = load(rest[0])
        assumptions = load(rest[i + 1])
        lines, errors = project_cost(design, assumptions)
        if errors:
            print("INVALID assumptions:")
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        text = "\n".join(lines) + "\n"
        if "--out" in rest:
            out = Path(rest[rest.index("--out") + 1])
            out.write_text(text, encoding="utf-8")
            print(f"wrote {out}")
        else:
            print(text, end="")
        return 0

    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
