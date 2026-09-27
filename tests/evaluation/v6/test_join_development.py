"""Regression coverage for scripts/evaluation/v6/join_development.py.

The join is the mechanical half of the development failure taxonomy: a wrong
key or a swallowed unjoinable cell would silently shrink the evidence table.
These cases pin the keying, the last-record-wins resume semantics, and the
refusal on structural gaps. Run:

    python3 -m unittest discover -s tests/evaluation/v6 -p 'test_*.py'
"""
import json
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "evaluation" / "v6"))

import join_development as jd  # noqa: E402


class JoinDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dwp-v6-join-test-")
        self.plan = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_comparator(self, family="astro", keys=(("AC-2", "claude-code", 1),)):
        fam = self.plan / "lab" / "baseline-pilot-r3" / family
        fam.mkdir(parents=True, exist_ok=True)
        cells = []
        for case, stratum, repeat in keys:
            for arm in "AB":
                cells.append({"cell_id": f"{case}-{stratum}-r{repeat}-{arm}",
                              "arm": arm, "stratum": stratum, "repeat": repeat,
                              "task": case, "case": case, "verdict": "PASS",
                              "eligible": True})
        (fam / "SCORES.json").write_text(
            json.dumps({"family": family, "cells": cells}), encoding="utf-8")
        return fam

    def write_development(self, family="astro", records=(), scored=None):
        dev = self.plan / "lab" / "development" / f"r1-{family}"
        dev.mkdir(parents=True, exist_ok=True)
        with (dev / "attempts.jsonl").open("w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        rows = scored if scored is not None else [
            {"cell_id": r["cell_id"], "arm": "C", "stratum": r["stratum"],
             "repeat": r["repeat"], "task": r["task"], "case": r["task"],
             "verdict": "FAIL", "eligible": True, "reasons": ["unit fixture"]}
            for r in records]
        (dev / "SCORES.json").write_text(
            json.dumps({"family": family, "cells": rows}), encoding="utf-8")
        return dev

    def record(self, cell_id="AC-2-claude-code-r1-C", **over):
        base = {"cell_id": cell_id, "attempt": "att", "arm": "C",
                "stratum": cell_id.split("-")[2] + "-" + "claude-code",
                "repeat": 1, "task": "AC-2", "status": "completed",
                "exit_code": 0, "duration_s": 12.5,
                "cost": {"class": "invoiced", "amount": 1.25},
                "counters": {"input_tokens": 5}, "quota_signature": None,
                "canary_intact": True, "note": ""}
        # stratum derives from the conventional id <case>-<stratum>-r<n>-<arm>,
        # where the case token itself may contain a hyphen (AC-2)
        head = cell_id.rsplit("-", 2)[0]         # AC-2-claude-code
        base["stratum"] = head[len(str(base["task"])) + 1:]
        base.update(over)
        return base

    def test_join_matches_comparator_and_writes_outputs(self):
        self.write_comparator()
        self.write_development(records=[self.record()])
        # Drive main() through argparse by patching sys.argv.
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        code = jd.main()
        self.assertEqual(code, 0)
        join_json = json.loads(
            (self.plan / "lab" / "development" / "r1-astro" / "JOIN.json")
            .read_text(encoding="utf-8"))
        row = join_json["joined"]["AC-2-claude-code-r1"]
        self.assertEqual(row["A"]["verdict"], "PASS")
        self.assertEqual(row["B"]["verdict"], "PASS")
        self.assertEqual(row["C"]["verdict"], "FAIL")
        self.assertEqual(row["C"]["cost"]["amount"], 1.25)
        md = (self.plan / "lab" / "development" / "JOIN-r1.md").read_text(encoding="utf-8")
        self.assertIn("AC-2-claude-code-r1", md)

    def test_last_record_wins_so_resumed_cells_shed_quota_ghosts(self):
        self.write_comparator()
        quota = self.record(status="quota_refused", quota_signature="claude",
                            cost={"class": "unavailable"}, note="quota refused this cell")
        done = self.record(status="completed", cost={"class": "invoiced", "amount": 2.0})
        self.write_development(records=[quota, done])
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        self.assertEqual(jd.main(), 0)
        join_json = json.loads(
            (self.plan / "lab" / "development" / "r1-astro" / "JOIN.json")
            .read_text(encoding="utf-8"))
        c = join_json["joined"]["AC-2-claude-code-r1"]["C"]
        self.assertEqual(c["status"], "completed")
        self.assertIsNone(c["quota_signature"])

    def test_missing_comparator_row_is_structural_not_silent(self):
        self.write_comparator(keys=(("AC-2", "codex-cli", 1),))  # no claude row
        self.write_development(records=[self.record()])
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        self.assertEqual(jd.main(), 1)  # refused, never a partial join


if __name__ == "__main__":
    unittest.main()


class ComparatorPhantomTests(unittest.TestCase):
    """Pilot r3 froze codex cells as `completed` that were really usage-limit
    refusals (<30s, never metered, signature in the log) — their oracle
    verdicts reflect the untouched seed, not agent work. The join must FLAG
    them (row-level, per family, with evidence) and still exit 0: a phantom
    comparator is a property of the frozen evidence, never a reason to
    silently shrink or silently trust the table."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dwp-v6-join-phantom-")
        self.plan = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_pilot(self, family="astro", keys=(("AC-2", "codex-cli", 1),)):
        """Comparator SCORES rows plus an attempts.jsonl + logs. Every arm-B
        cell is a phantom (fast, unmetered, usage-limit line in its log);
        every arm-A cell is real (metered, slow)."""
        fam = self.plan / "lab" / "baseline-pilot-r3" / family
        fam.mkdir(parents=True, exist_ok=True)
        rows, records = [], []
        for case, stratum, repeat in keys:
            for arm in ("A", "B"):
                cid = f"{case}-{stratum}-r{repeat}-{arm}"
                rows.append({"cell_id": cid, "arm": arm, "stratum": stratum,
                             "repeat": repeat, "task": case, "case": case,
                             "verdict": "PASS", "eligible": True})
                phantom = arm == "B"
                records.append({
                    "cell_id": cid, "attempt": "att", "arm": arm,
                    "stratum": stratum, "repeat": repeat, "task": case,
                    "status": "completed",
                    "duration_s": 4.2 if phantom else 407.5,
                    "cost": ({"class": "unavailable", "reason": "no meter"}
                             if phantom else {"class": "invoiced", "amount": 1.0}),
                    "log": f"logs/{cid}.log",
                })
                logdir = fam / "att" / "logs"
                logdir.mkdir(parents=True, exist_ok=True)
                body = ("ERROR: You’ve hit your usage limit. "
                        "try again at 10:10 PM.\n") if phantom else "real work\n"
                (logdir / f"{cid}.log").write_text(body, encoding="utf-8")
        (fam / "SCORES.json").write_text(
            json.dumps({"family": family, "cells": rows}), encoding="utf-8")
        with (fam / "attempts.jsonl").open("w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return fam

    def write_dev_cell(self, family="astro", cell_id="AC-2-codex-cli-r1-C"):
        dev = self.plan / "lab" / "development" / f"r1-{family}"
        dev.mkdir(parents=True, exist_ok=True)
        head = cell_id.rsplit("-", 2)[0]           # AC-2-codex-cli
        task = case = "AC-2"                      # fixture case token
        stratum = head[len(task) + 1:]             # codex-cli
        record = {"cell_id": cell_id, "attempt": "att", "arm": "C",
                  "stratum": stratum, "repeat": 1, "task": task,
                  "status": "completed", "exit_code": 0, "duration_s": 300.0,
                  "cost": {"class": "invoiced", "amount": 2.5},
                  "counters": {}, "quota_signature": None,
                  "canary_intact": True, "note": ""}
        with (dev / "attempts.jsonl").open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        rows = [{"cell_id": cell_id, "arm": "C", "stratum": stratum,
                 "repeat": 1, "task": task, "case": case,
                 "verdict": "FAIL", "eligible": True, "reasons": ["unit fixture"]}]
        (dev / "SCORES.json").write_text(
            json.dumps({"family": family, "cells": rows}), encoding="utf-8")
        return dev

    def test_phantom_comparator_flagged_with_evidence_not_silent(self):
        self.write_pilot()
        self.write_dev_cell()
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        self.assertEqual(jd.main(), 0)  # reported, not structural
        join_json = json.loads(
            (self.plan / "lab" / "development" / "r1-astro" / "JOIN.json")
            .read_text(encoding="utf-8"))
        row = join_json["joined"]["AC-2-codex-cli-r1"]
        self.assertFalse(row["A"]["phantom"])
        self.assertTrue(row["B"]["phantom"])
        self.assertEqual(row["comparator_phantom"], ["B"])
        self.assertEqual(row["B"]["verdict"], "PASS")  # raw verdict preserved
        ev = join_json["comparator_phantom_cells"]["AC-2-codex-cli-r1-B"]
        self.assertEqual(ev["usage_limit_signature"], True)
        md = (self.plan / "lab" / "development" / "JOIN-r1.md").read_text(encoding="utf-8")
        self.assertIn("PASS*", md)                    # the marked table cell
        self.assertIn("phantom comparator", md)       # the explanation
        self.assertIn("AC-2-codex-cli-r1-B", md)      # the listing

    def test_metered_slow_comparator_is_never_phantom(self):
        self.write_pilot()
        self.write_dev_cell()
        # Flip the B record to real work: no flag may appear anywhere.
        fam = self.plan / "lab" / "baseline-pilot-r3" / "astro"
        lines = []
        for line in (fam / "attempts.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["arm"] == "B":
                r["duration_s"] = 511.0
                r["cost"] = {"class": "invoiced", "amount": 0.9}
            lines.append(json.dumps(r))
        (fam / "attempts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        self.assertEqual(jd.main(), 0)
        join_json = json.loads(
            (self.plan / "lab" / "development" / "r1-astro" / "JOIN.json")
            .read_text(encoding="utf-8"))
        row = join_json["joined"]["AC-2-codex-cli-r1"]
        self.assertFalse(row["B"]["phantom"])
        self.assertNotIn("comparator_phantom", row)
        self.assertEqual(join_json["comparator_phantom_cells"], {})

    def test_real_fast_completion_is_not_phantom(self):
        # Two pilot claude cells finished verify-only cases in 26-29s with no
        # metering but REAL agent output in their logs — the record predicate
        # alone would have voided genuine evidence. Evidence decides.
        self.write_pilot()
        fam = self.plan / "lab" / "baseline-pilot-r3" / "astro"
        lines = []
        for line in (fam / "attempts.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["arm"] == "B":
                r["duration_s"] = 28.4                 # still under 30s
                r["cost"] = {"class": "unavailable"}    # still unmetered
            lines.append(json.dumps(r))
        (fam / "attempts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        # And B's log shows a real agent result, not a refusal line.
        (fam / "att" / "logs" / "AC-2-codex-cli-r1-B.log").write_text(
            '{\'result\': \'verified all criteria; no change needed\', '
            '"type": "result", "duration_ms": 25909}\n', encoding="utf-8")
        self.write_dev_cell()
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        self.assertEqual(jd.main(), 0)
        join_json = json.loads(
            (self.plan / "lab" / "development" / "r1-astro" / "JOIN.json")
            .read_text(encoding="utf-8"))
        self.assertFalse(join_json["joined"]["AC-2-codex-cli-r1"]["B"]["phantom"])

    def test_unreadable_log_with_untouched_workspace_is_phantom(self):
        # Log destroyed (rotated scratch), workspace untouched: the cell did
        # nothing measurable — flagged, with the honest null signature.
        self.write_pilot()
        fam = self.plan / "lab" / "baseline-pilot-r3" / "astro"
        lines = []
        for line in (fam / "attempts.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["arm"] == "B":
                r["log"] = "logs/vanished.log"         # no such file
                r["produced_change"] = False
            lines.append(json.dumps(r))
        (fam / "attempts.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.write_dev_cell()
        sys.argv = ["join_development.py", "--round", "r1",
                    "--plan", str(self.plan), "--families", "astro"]
        self.assertEqual(jd.main(), 0)
        join_json = json.loads(
            (self.plan / "lab" / "development" / "r1-astro" / "JOIN.json")
            .read_text(encoding="utf-8"))
        ev = join_json["comparator_phantom_cells"]["AC-2-codex-cli-r1-B"]
        self.assertIsNone(ev["usage_limit_signature"])
        self.assertTrue(join_json["joined"]["AC-2-codex-cli-r1"]["B"]["phantom"])
