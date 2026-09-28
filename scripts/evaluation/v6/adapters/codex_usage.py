#!/usr/bin/env python3
"""Codex CLI usage-counter extraction (Task 9 continuation).

Codex writes one rollout JSONL per run under ~/.codex/sessions/YYYY/MM/DD/.
Each run carries `token_usage_record` events whose `usage` object holds the
per-turn counters; `total_token_usage` objects are session totals and are
deliberately IGNORED here to avoid double counting (the per-turn records
already sum to them).

Field mapping into the lab's four-slot counter model (no double counting):
    input_tokens      <- usage.input_tokens - usage.cached_input_tokens
                         (codex reports input INCLUSIVE of cached reads)
    cached_input_tokens <- usage.cached_input_tokens
    output_tokens     <- usage.output_tokens
    reasoning_tokens  <- usage.reasoning_output_tokens
Extra codex fields (cache_write_input_tokens, total_tokens) are preserved in
"extra" so nothing is silently dropped.

Python 3.9+ stdlib only.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def find_rollouts(sessions_dir: Path, newer_than_epoch: float):
    found = []
    for path in sorted(Path(sessions_dir).rglob("rollout-*.jsonl")):
        if path.stat().st_mtime >= newer_than_epoch:
            found.append(path)
    return found


def extract_usage(rollout_path: Path) -> dict:
    counters = {"input_tokens": 0, "cached_input_tokens": 0,
                "output_tokens": 0, "reasoning_tokens": 0}
    extra = {"cache_write_input_tokens": 0, "total_tokens": 0}
    records = 0
    for line in rollout_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or "token_usage_record" not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        usage = (event.get("payload") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        records += 1
        cached = usage.get("cached_input_tokens", 0) or 0
        counters["input_tokens"] += max(0, (usage.get("input_tokens", 0) or 0) - cached)
        counters["cached_input_tokens"] += cached
        counters["output_tokens"] += usage.get("output_tokens", 0) or 0
        counters["reasoning_tokens"] += usage.get("reasoning_output_tokens", 0) or 0
        extra["cache_write_input_tokens"] += usage.get("cache_write_input_tokens", 0) or 0
        extra["total_tokens"] += usage.get("total_tokens", 0) or 0
    return {"files": [rollout_path.name], "turn_records": records,
            "counters": counters, "extra": extra}


def usage_since(sessions_dir: Path, newer_than_epoch: float) -> dict:
    """Sum every rollout newer than the epoch (one actor run = one rollout)."""
    rollouts = find_rollouts(sessions_dir, newer_than_epoch)
    result = {"files": [], "turn_records": 0,
              "counters": {"input_tokens": 0, "cached_input_tokens": 0,
                           "output_tokens": 0, "reasoning_tokens": 0},
              "extra": {"cache_write_input_tokens": 0, "total_tokens": 0}}
    for path in rollouts:
        one = extract_usage(path)
        result["files"].extend(one["files"])
        result["turn_records"] += one["turn_records"]
        for field in result["counters"]:
            result["counters"][field] += one["counters"][field]
        for field in result["extra"]:
            result["extra"][field] += one["extra"][field]
    result["rollout_count"] = len(rollouts)
    return result


def default_sessions_dir() -> Path:
    return Path.home() / ".codex" / "sessions"


def epoch_now() -> float:
    return time.time()
