#!/usr/bin/env python3
"""Deterministic fake actor for smoke campaigns.

Exercises the full orchestration path (workspace setup, scrubbed environment,
dispatch, timeout handling, canary verification, scoring) without any
provider call. A fake-actor run is orchestration evidence, never live-agent
evidence (reproduction level 2, per the lab blueprint).
"""
import pathlib
import sys


def main() -> int:
    args = sys.argv[1:]
    workspace = pathlib.Path(args[args.index("--workspace") + 1])
    (workspace / "solution.txt").write_text("done\n", encoding="utf-8")
    print("fake actor: produced solution.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
