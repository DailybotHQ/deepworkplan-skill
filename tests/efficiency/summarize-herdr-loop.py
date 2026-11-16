#!/usr/bin/env python3
"""Summarize Herdr loop logs or a fleet map from stdin, without writing data."""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys


def summarize_log(since: str, until: str) -> None:
    lines = []
    for line in sys.stdin:
        timestamp = line.split(" ", 1)[0]
        if since <= timestamp <= until and re.match(r"^\d{4}-\d\d-\d\dT", timestamp):
            lines.append(line.rstrip("\n"))

    classes = collections.Counter(
        match.group(1)
        for line in lines
        if (match := re.search(r"\bclass=([A-Za-z0-9_-]+)", line))
    )
    actions = collections.Counter(
        match.group(1)
        for line in lines
        if (match := re.search(r"\baction=([A-Za-z0-9_-]+)", line))
    )
    retirements = collections.Counter(
        match.group(1)
        for line in lines
        if "brain_replaced" in line
        and (match := re.search(r"\bwhy=([A-Za-z0-9_-]+)", line))
    )
    timestamps = [line.split(" ", 1)[0] for line in lines]
    result = {
        "source": "autopilot log",
        "since_inclusive": since,
        "until_inclusive": until,
        "timestamped_log_rows_n": len(lines),
        "first_row": timestamps[0] if timestamps else None,
        "last_row": timestamps[-1] if timestamps else None,
        "plan_stalled_events": classes["plan_stalled"],
        "plan_blocked_events": classes["plan_blocked"],
        "plan_completed_events": classes["plan_completed"],
        "prompt_actions": actions["prompt"],
        "brain_launches": classes["brain_launched"],
        "brain_retirements": classes["brain_replaced"],
        "brain_retirement_reasons": dict(sorted(retirements.items())),
        "brain_launch_failures": classes["brain_launch_failed"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def summarize_fleet() -> None:
    data = json.load(sys.stdin)
    machines = data.get("machines", [])
    plans = [plan for machine in machines for plan in machine.get("plans", [])]
    result = {
        "source": "fleet map",
        "generated_at": data.get("generated_at"),
        "age_seconds": data.get("age_seconds"),
        "stale": data.get("stale"),
        "machine_count": len(machines),
        "agent_count": sum(len(machine.get("agents", [])) for machine in machines),
        "plan_rows_n": len(plans),
        "plan_class_counts": dict(
            sorted(collections.Counter(plan.get("class", "unknown") for plan in plans).items())
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="source", required=True)
    log_parser = subparsers.add_parser("log", help="summarize autopilot log lines")
    log_parser.add_argument("--since", required=True, help="inclusive ISO-8601 UTC timestamp")
    log_parser.add_argument("--until", required=True, help="inclusive ISO-8601 UTC timestamp")
    subparsers.add_parser("fleet", help="summarize a fleet-v1 JSON map")
    args = parser.parse_args()
    if args.source == "log":
        summarize_log(args.since, args.until)
    else:
        summarize_fleet()


if __name__ == "__main__":
    main()
