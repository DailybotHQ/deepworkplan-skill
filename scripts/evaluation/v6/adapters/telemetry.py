#!/usr/bin/env python3
"""Run telemetry model for the v6 evaluation lab (contributor-only).

A meter record is the complete, closed resource accounting of ONE attempted
run — including failed runs. Core properties (preregistration, metrics_and_cost):

- Provider counters (input / output / cached-input / reasoning tokens) are
  recorded ONLY from an exposed meter, each carrying its source. A counter
  the host does not expose is the string "unknown" — NEVER zero, never
  imputed. Zero (a meter that truly reported 0) stays distinct from unknown.
- Cost is classified: "invoiced" (from provider billing), "list_price"
  (computed at dated public rates) or "unavailable" (reason recorded).
  Bytes are never converted to tokens or money.
- Behavior categories are counted separately: process time, build/test time,
  searches, repeated reads, repeated gates, workspace edits, human
  interventions (by category) and required authorization questions.
- The stratum (host + model + version) is pinned at record time; a mismatch
  against the expected stratum is a refusal, never a silent substitution.

Python 3.9+ stdlib only.
"""

from __future__ import annotations

COUNTER_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")
COST_CLASSES = ("invoiced", "list_price", "unavailable")
INTERVENTION_CATEGORIES = ("missing_intent", "new_authority", "environment_repair", "engineering_rescue")
BEHAVIOR_FIELDS = (
    "process_time_s", "build_test_time_s", "searches", "repeated_reads",
    "repeated_gates", "workspace_edits",
)
STATUS_VALUES = ("completed", "failed", "timeout", "ineligible", "blocked")


class TelemetryError(Exception):
    pass


def meter_record(*, run_id, campaign, cell_id, arm, stratum, status, counters=None,
                 cost=None, behavior=None, interventions=None, auth_questions=0,
                 meter_source="unknown", notes=""):
    """Build and validate one closed meter record."""
    if status not in STATUS_VALUES:
        raise TelemetryError(f"invalid status: {status!r}")
    counters = counters or {}
    clean_counters = {}
    for field in COUNTER_FIELDS:
        value = counters.get(field, "unknown")
        if value == "unknown":
            clean_counters[field] = "unknown"
        elif isinstance(value, (int, float)) and value >= 0:
            clean_counters[field] = value
        else:
            raise TelemetryError(f"counter {field} must be a non-negative number or 'unknown', got {value!r}")
    cost = cost or {}
    if cost.get("class", "unavailable") not in COST_CLASSES:
        raise TelemetryError(f"invalid cost class: {cost.get('class')!r}")
    if cost.get("class") == "list_price" and not cost.get("rate_date"):
        raise TelemetryError("list_price cost requires rate_date")
    for cat in (interventions or {}):
        if cat not in INTERVENTION_CATEGORIES:
            raise TelemetryError(f"unknown intervention category: {cat!r}")
    for field in (behavior or {}):
        if field not in BEHAVIOR_FIELDS:
            raise TelemetryError(f"unknown behavior field: {field!r}")
    return {
        "run_id": run_id, "campaign": campaign, "cell_id": cell_id, "arm": arm,
        "stratum": dict(stratum), "status": status,
        "counters": clean_counters, "meter_source": meter_source,
        "cost": {"class": cost.get("class", "unavailable"), "amount": cost.get("amount"),
                 "rate_date": cost.get("rate_date"), "reason": cost.get("reason", "")},
        "behavior": {f: (behavior or {}).get(f, 0) for f in BEHAVIOR_FIELDS},
        "interventions": dict(interventions or {}),
        "auth_questions": auth_questions,
        "notes": notes,
    }


def verify_stratum(record, expected):
    """Refuse a silent model/host substitution (preregistration strata rule)."""
    for key, want in expected.items():
        got = record["stratum"].get(key)
        if got != want:
            raise TelemetryError(
                f"stratum substitution for {key}: expected {want!r}, recorded {got!r} "
                f"(run {record['run_id']}) - pin the stratum or record a new block")


def numeric(value):
    return isinstance(value, (int, float))


def totals(records):
    """Per-field sums over numeric values; unknowns stay visible, never zero."""
    out = {"counters": {f: {"sum": 0, "unknown_count": 0} for f in COUNTER_FIELDS},
           "behavior": {f: 0 for f in BEHAVIOR_FIELDS},
           "runs": len(records),
           "status": {}}
    for record in records:
        out["status"][record["status"]] = out["status"].get(record["status"], 0) + 1
        for field in COUNTER_FIELDS:
            value = record["counters"][field]
            if numeric(value):
                out["counters"][field]["sum"] += value
            else:
                out["counters"][field]["unknown_count"] += 1
        for field in BEHAVIOR_FIELDS:
            out["behavior"][field] += record["behavior"].get(field, 0)
    return out


def reconcile(records, expected, tolerance_pct=2.0):
    """Reconcile summed records against expected totals (synthetic or billed).

    Returns (ok: bool, report: dict). Unknown fields are reported per family
    and never treated as zero: a field with any unknown contribution cannot
    reconcile numerically and is listed as 'has_unknowns'.
    """
    sums = totals(records)
    report = {"ok": True, "fields": {}, "tolerance_pct": tolerance_pct}
    for field, want in expected.items():
        entry = sums["counters"].get(field)
        if entry is None:
            report["fields"][field] = {"error": "unknown field"}
            report["ok"] = False
            continue
        if entry["unknown_count"]:
            report["fields"][field] = {"has_unknowns": entry["unknown_count"],
                                       "numeric_sum": entry["sum"], "expected": want}
            report["ok"] = False
            continue
        delta = abs(entry["sum"] - want)
        allowed = abs(want) * tolerance_pct / 100.0
        ok = delta <= max(allowed, 1e-9)
        report["fields"][field] = {"sum": entry["sum"], "expected": want,
                                   "delta": delta, "ok": ok}
        report["ok"] = report["ok"] and ok
    return report["ok"], report
