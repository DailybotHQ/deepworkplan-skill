"""Regression tests for the v6 telemetry model and host adapters.

Fast and self-contained: synthetic usage only; real CLI probes are exercised
by the canary gate, not here.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "evaluation" / "v6" / "adapters"))
sys.path.insert(0, str(REPO / "scripts" / "evaluation" / "v6"))

from adapters import adapters, telemetry  # noqa: E402


def record(**over):
    fields = dict(run_id="r1", campaign="c", cell_id="cell-1", arm="A",
                  stratum={"host": "fake", "model": "synthetic"},
                  status="completed")
    fields.update(over)
    return telemetry.meter_record(**fields)


class MeterRecordTests(unittest.TestCase):
    def test_missing_counters_are_unknown_never_zero(self):
        rec = record()
        for field in telemetry.COUNTER_FIELDS:
            self.assertEqual(rec["counters"][field], "unknown")

    def test_zero_is_distinct_from_unknown(self):
        rec = record(counters={"input_tokens": 0})
        self.assertEqual(rec["counters"]["input_tokens"], 0)
        self.assertEqual(rec["counters"]["output_tokens"], "unknown")

    def test_negative_counter_refused(self):
        with self.assertRaises(telemetry.TelemetryError):
            record(counters={"input_tokens": -1})

    def test_list_price_requires_rate_date(self):
        with self.assertRaises(telemetry.TelemetryError):
            record(cost={"class": "list_price", "amount": 1.5})
        ok = record(cost={"class": "list_price", "amount": 1.5, "rate_date": "2026-09-26"})
        self.assertEqual(ok["cost"]["class"], "list_price")

    def test_intervention_categories_validated(self):
        with self.assertRaises(telemetry.TelemetryError):
            record(interventions={"invented_category": 1})
        ok = record(interventions={"new_authority": 2}, auth_questions=1)
        self.assertEqual(ok["interventions"]["new_authority"], 2)

    def test_stratum_substitution_refused(self):
        rec = record(stratum={"host": "fake", "model": "synthetic"})
        with self.assertRaises(telemetry.TelemetryError):
            telemetry.verify_stratum(rec, {"model": "claude-fable-5-1"})
        telemetry.verify_stratum(rec, {"model": "synthetic"})


class ReconcileTests(unittest.TestCase):
    def records(self, n):
        return [record(run_id=f"r{i}",
                       counters=adapters.synthetic_usage(seed_value=i + 1))
                for i in range(n)]

    def test_synthetic_totals_reconcile(self):
        records = self.records(5)
        expected = {f: sum(adapters.synthetic_usage(seed_value=i + 1)[f] for i in range(5))
                    for f in telemetry.COUNTER_FIELDS}
        ok, report = telemetry.reconcile(records, expected)
        self.assertTrue(ok, report)
        self.assertTrue(all(f["ok"] for f in report["fields"].values()))

    def test_perturbation_beyond_tolerance_fails(self):
        records = self.records(5)
        expected = {f: sum(adapters.synthetic_usage(seed_value=i + 1)[f] for i in range(5))
                    for f in telemetry.COUNTER_FIELDS}
        expected["input_tokens"] = int(expected["input_tokens"] * 1.10)
        ok, _ = telemetry.reconcile(records, expected, tolerance_pct=2.0)
        self.assertFalse(ok)

    def test_unknown_fields_are_visible_and_block_numeric_reconciliation(self):
        records = self.records(3) + [record(run_id="rx")]  # last one: all unknown
        expected = {f: sum(adapters.synthetic_usage(seed_value=i + 1)[f] for i in range(3))
                    for f in telemetry.COUNTER_FIELDS}
        ok, report = telemetry.reconcile(records, expected)
        self.assertFalse(ok)
        for field in telemetry.COUNTER_FIELDS:
            self.assertEqual(report["fields"][field]["has_unknowns"], 1)

    def test_failed_runs_are_counted(self):
        records = self.records(3) + [record(run_id="rf", status="failed")]
        totals = telemetry.totals(records)
        self.assertEqual(totals["status"]["failed"], 1)
        self.assertEqual(totals["runs"], 4)


class AdapterTests(unittest.TestCase):
    def test_probe_record_shape_has_no_secret_fields(self):
        for name in ("fake", "claude", "codex"):
            probe = adapters.probe(name)
            self.assertTrue(set(probe) <= {"adapter", "description", "counter_source",
                                           "available", "version", "reason"}, probe)
            self.assertIn("counter_source", probe)

    def test_fake_adapter_launch_and_meter_end_to_end(self):
        probe = adapters.probe("fake")
        self.assertTrue(probe["available"])
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            ws.mkdir()
            code, duration, out = adapters.launch("fake", [sys.executable, "-c", "print('ok')"], ws)
            self.assertEqual(code, 0)
            self.assertGreater(duration, 0.0)
        rec = record(run_id="fake-1", counters=adapters.synthetic_usage(seed_value=1),
                     behavior={"process_time_s": duration})
        ok, report = telemetry.reconcile([rec], adapters.synthetic_usage(seed_value=1))
        self.assertTrue(ok, report)

    def test_real_cli_probes_recorded_honestly(self):
        # Availability depends on the host; the RECORD must be honest either way.
        for name in ("claude", "codex"):
            probe = adapters.probe(name)
            self.assertIn("available", probe)
            if not probe["available"]:
                self.assertIn("reason", probe)

    def test_canary_fake_reports_synthetic(self):
        report = adapters.canary("fake")
        self.assertTrue(report["counters_available"])
        self.assertIn("synthetic", report["canary"])


if __name__ == "__main__":
    unittest.main()
