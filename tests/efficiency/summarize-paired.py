#!/usr/bin/env python3
"""Reproduce recorded byte observations, retaining failures and incomplete pairs.

Usage: python3 tests/efficiency/summarize-paired.py [DATA_DIRECTORY]
This is a contributor-side evidence reader, not a runtime or token meter.
"""

import json
from pathlib import Path
import re
import statistics
import sys


def summarize(directory: Path) -> dict:
    protocol = json.loads((directory / "protocol.json").read_text())
    static = {}
    for arm in ("baseline", "candidate"):
        content = (directory / f"static-{arm}.txt").read_text()
        static[arm] = {
            name: int(size)
            for name, size in re.findall(r"^(\w+)\s+(\d+) bytes", content, re.M)
        }
    observations = []
    missing = []
    # Arms the protocol records as never executed are absent by declaration, not by
    # loss. They are reported, never silently dropped, and never treated as evidence.
    not_run = list(protocol.get("arms_not_run", []))
    for pair in range(1, protocol["pairs_requested"] + 1):
        for arm in ("baseline", "candidate"):
            stem = f"pair{pair}-{arm}"
            if stem in not_run:
                continue
            report_path = directory / f"{stem}-report.json"
            trace_path = directory / f"{stem}.jsonl"
            if not report_path.is_file() or not trace_path.is_file():
                missing.append(stem)
                continue
            report = json.loads(report_path.read_text())
            trace = [json.loads(line) for line in trace_path.read_text().splitlines()]
            if not trace:
                raise ValueError(f"Empty trace: {stem}")
            for event in trace:
                for field in ("output_bytes", "elapsed_seconds"):
                    if not isinstance(event[field], (int, float)) or event[field] < 0:
                        raise ValueError(f"Invalid {field}: {stem}")
            reads = [event for event in trace if event["mode"] == "read"]
            commands = [event for event in trace if event["mode"] == "run"]
            observations.append({
                "pair": pair,
                "arm": arm,
                "outcome": report["outcome"],
                "read_bytes": sum(event["read_bytes"] for event in reads),
                "pack_read_bytes": sum(
                    event["read_bytes"] for event in reads
                    if "/packs/" in event["path"]
                ),
                "captured_output_bytes": sum(event["output_bytes"] for event in trace),
                "captured_command_seconds": sum(event["elapsed_seconds"] for event in commands),
                "read_events": len(reads),
                "command_events": len(commands),
                "nonzero_commands": sum(event["exit_code"] != 0 for event in commands),
                "provider_tokens": None,
            })
    paired = []
    for pair in range(1, protocol["pairs_requested"] + 1):
        arms = {row["arm"]: row for row in observations if row["pair"] == pair}
        if set(arms) != {"baseline", "candidate"}:
            continue
        baseline, candidate = arms["baseline"], arms["candidate"]
        both_completed = all(row["outcome"] == "completed" for row in arms.values())
        # A delta between arms that stopped at different points measures how far each
        # run got, not efficiency. Only completed pairs may produce a comparison.
        row = {
            "pair": pair,
            "both_completed": both_completed,
            "pack_read_delta_percent": None,
            "output_delta_percent": None,
        }
        if both_completed:
            row["pack_read_delta_percent"] = 100 * (
                candidate["pack_read_bytes"] / baseline["pack_read_bytes"] - 1
            ) if baseline["pack_read_bytes"] else None
            row["output_delta_percent"] = 100 * (
                candidate["captured_output_bytes"] / baseline["captured_output_bytes"] - 1
            ) if baseline["captured_output_bytes"] else None
        else:
            row["comparison_withheld"] = (
                "At least one arm did not complete; a byte delta between unequal "
                "progress is not an efficiency observation."
            )
        paired.append(row)
    # Spread includes every completed pair; never silently discard a stopped arm.
    deltas = [row["pack_read_delta_percent"] for row in paired]
    spread = None
    if deltas and all(value is not None for value in deltas):
        spread = {"min": min(deltas), "median": statistics.median(deltas), "max": max(deltas)}
    return {
        "static_bytes": static,
        "observations": observations,
        "pairs": paired,
        "pack_read_delta_spread_percent": spread,
        "missing": missing,
        "not_run": not_run,
        "pairs_completed": sum(1 for row in paired if row["both_completed"]),
        "instrumented_claim_eligible": bool(paired) and all(
            row["both_completed"] for row in paired
        ) and len(paired) >= protocol["pairs_requested"],
        "timing_claim_eligible": False,
        "live_token_claim_eligible": False,
        "release_efficiency_claim_eligible": False,
        "limitations": "Captured byte observations only; see protocol and every report. No automatic release claim follows from this summary.",
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[2] / "docs/evaluations/token-efficiency-data"
    )
    try:
        result = summarize(root)
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as error:
        print(f"Incomplete or invalid measurement evidence: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["missing"] else 0)
