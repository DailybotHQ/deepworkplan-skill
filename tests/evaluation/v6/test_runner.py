"""Regression coverage for the v6 evaluation lab driver (scripts/evaluation/v6/lab.py).

Every case is self-contained: synthetic labs, seeds and actors are built in a
per-test temp directory. No network, no provider call, no real agent. Run:

    python3 -m unittest discover -s tests/evaluation/v6 -p 'test_*.py'
"""
import json
import pathlib
import sys
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "evaluation" / "v6"))

import lab  # noqa: E402

SCHEMA = lab.SCHEMA


class LabTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dwp-v6-lab-test-")
        self.tmp = pathlib.Path(self._tmp.name)
        self.lab_root = self.tmp / "lab"
        self.lab_root.mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    # -- helpers ----------------------------------------------------------
    def make_seed(self, name="seed"):
        seed = self.tmp / name
        (seed / "src").mkdir(parents=True)
        (seed / "README.md").write_text("test seed\n", encoding="utf-8")
        (seed / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
        return seed

    def make_actor(self, name="actor.py", body=None):
        actor = self.tmp / name
        actor.write_text(body or (
            "import pathlib, sys\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ), encoding="utf-8")
        return actor

    def make_pack(self, tag="vT1", digest="aaaaaaaaaaaaaaaa"):
        pack = self.lab_root / "packs" / "vtest" / f"{tag}-{digest}"
        pack.mkdir(parents=True, exist_ok=True)
        (pack / "PACK_MARKER").write_text(tag + "\n", encoding="utf-8")
        return pack

    def make_cfg(self, arms=None, actor=None, paid=False, seed=None, oracles=None):
        seed = seed or self.make_seed()
        actor = actor or self.make_actor()
        return {
            "schema": SCHEMA, "name": "testcamp", "paid": paid,
            "requires_enforced_isolation": False,
            "arms": arms if arms is not None else {"A": None, "B": {"pack": "packs/vtest/vT1-aaaaaaaaaaaaaaaa"}},
            "seed": {"path": str(seed), "family": "testseed"},
            "tasks": [{"id": "T-1", "prompt": "produce solution.txt"}],
            "strata": [{"name": "fake", "launch": {"mode": "fake", "command": str(actor)}}],
            "repeats": 1,
            "oracles": oracles if oracles is not None else [
                {"id": "O1", "kind": "exit_zero_file", "path": "solution.txt"}],
        }

    def unset_design(self):
        design = self.tmp / "design.json"
        design.write_text(json.dumps({"resource_envelope": {
            "status": "UNSET", "per_run_cap": None, "total_cap": None,
            "retry_reserve_fraction": 0.25, "launch_rule": "REFUSED while unset"}}), encoding="utf-8")
        return design

    def read_inventory(self, out):
        return [json.loads(l) for l in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


class CleanRunTests(LabTestBase):
    def test_identical_hashes_across_arms_and_distinct_workspaces(self):
        self.make_pack()
        cfg = self.make_cfg(arms={"A": None, "B": {"pack": "packs/vtest/vT1-aaaaaaaaaaaaaaaa"},
                                  "C": {"pack": "packs/vtest/vT1-aaaaaaaaaaaaaaaa"}})
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertEqual(len(records), 3)
        # The arm overlay on TASK.md is the treatment; seed files must be identical.
        fingerprints = {json.dumps({k: v for k, v in r["initial_hashes"].items() if k != "TASK.md"}, sort_keys=True) for r in records}
        self.assertEqual(len(fingerprints), 1, "initial source hashes differ across arms")
        self.assertEqual(len({r["workspace"] for r in records}), 3, "workspaces are not distinct")
        self.assertTrue(all(r["canary_intact"] for r in records))
        self.assertTrue(all(r["status"] == "completed" for r in records))

    def test_score_passes_only_on_artifacts(self):
        self.make_pack()
        cfg = self.make_cfg()
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        lab.cmd_score(cfg, out)
        scores = lab.load_json(out / "SCORES.json")
        self.assertTrue(all(v["oracles"]["O1"][0] == "PASS" for v in scores.values()))

    def test_score_missing_artifact_is_unverified_never_pass(self):
        actor = self.make_actor(body=(
            "import pathlib, sys\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "print('produced nothing')\n"
        ))
        cfg = self.make_cfg(actor=actor)
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        lab.cmd_score(cfg, out)
        scores = lab.load_json(out / "SCORES.json")
        self.assertEqual(scores["T-1-fake-r1-A"]["oracles"]["O1"][0], "UNVERIFIED")


class CanaryTests(LabTestBase):
    def test_snooping_actor_detected_by_exfiltration_scan(self):
        snoop = self.make_actor(name="snoop.py", body=(
            "import pathlib, sys\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "hidden = ws.parent.parent / 'actor_invisible' / 'CUSTODIAN_CANARY.secret'\n"
            "if hidden.exists():\n"
            "    (ws / 'stolen.txt').write_text(hidden.read_text())\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ))
        cfg = self.make_cfg(actor=snoop)
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        for record in self.read_inventory(out):
            self.assertEqual(record["status"], "ineligible")
            self.assertFalse(record["canary_intact"])

    def test_tampering_actor_detected_by_content_check(self):
        tamper = self.make_actor(name="tamper.py", body=(
            "import pathlib, sys\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "hidden = ws.parent.parent / 'actor_invisible' / 'CUSTODIAN_CANARY.secret'\n"
            "hidden.write_text('tampered\\n')\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ))
        cfg = self.make_cfg(actor=tamper)
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        self.assertTrue(all(not r["canary_intact"] for r in self.read_inventory(out)))


class RefusalTests(LabTestBase):
    def test_output_collision_refused(self):
        cfg = self.make_cfg()
        out = self.tmp / "out"
        out.mkdir()
        (out / "occupied").write_text("x", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            lab.run_full(cfg, self.lab_root, out)
        self.assertEqual(ctx.exception.code, 1)

    def test_paid_without_envelope_refused(self):
        self.make_pack()
        cfg = self.make_cfg(paid=True)
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("envelope" in e for e in errors), errors)

    def test_mutable_pack_reference_refused(self):
        real = self.make_pack(tag="vT9", digest="cccccccccccccccc")
        link = self.lab_root / "packs" / "vtest" / "vT9-live"
        link.symlink_to(real, target_is_directory=True)
        cfg = self.make_cfg(arms={"A": None, "B": {"pack": "packs/vtest/vT9-live"}})
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("symlink" in e for e in errors), errors)

    def test_digestless_pack_name_refused(self):
        sloppy = self.lab_root / "packs" / "vtest" / "main-branch-copy"
        sloppy.mkdir(parents=True, exist_ok=True)
        cfg = self.make_cfg(arms={"A": None, "B": {"pack": "packs/vtest/main-branch-copy"}})
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("<tag>-<digest>" in e for e in errors), errors)

    def test_seed_path_escape_refused(self):
        cfg = self.make_cfg(seed=None)
        cfg["seed"] = {"path": "../../etc", "family": "evil"}
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("escapes" in e for e in errors), errors)

    def test_enforced_isolation_campaign_refused_without_host_support(self):
        cfg = self.make_cfg()
        cfg["requires_enforced_isolation"] = True
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("enforced" in e for e in errors), errors)

    def test_exec_script_missing_refused(self):
        cfg = self.make_cfg()
        cfg["strata"] = [{"name": "fake", "launch": {"mode": "exec", "argv": ["tests/nope/actor.sh"]}}]
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("not found in the repository" in e for e in errors), errors)

    def test_campaign_missing_required_key_refused(self):
        cfg = self.make_cfg()
        del cfg["oracles"]
        errors = lab.validate_campaign(cfg, self.lab_root, self.unset_design())
        self.assertTrue(any("oracles" in e for e in errors), errors)


class OrchestrationTests(LabTestBase):
    def test_timeout_recorded_and_process_killed_quickly(self):
        sleeper = self.make_actor(name="sleeper.py", body=(
            "import pathlib, sys, time\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "time.sleep(29)\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ))
        cfg = self.make_cfg(actor=sleeper)
        out = self.tmp / "out"
        started = time.time()
        lab.run_full(cfg, self.lab_root, out, timeout_s=1)
        elapsed = time.time() - started
        records = self.read_inventory(out)
        self.assertTrue(all(r["status"] == "timeout" for r in records), records)
        self.assertLess(elapsed, 15, "process-tree kill did not happen promptly")

    def test_resume_skips_completed_cells(self):
        cfg = self.make_cfg()
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        attempt_id = self.read_inventory(out)[0]["attempt"]
        before = len(self.read_inventory(out))
        lab.run_full(cfg, self.lab_root, out, resume=attempt_id)
        self.assertEqual(len(self.read_inventory(out)), before, "resume re-ran completed cells")

    def test_prepare_dry_run_writes_nothing(self):
        seed = self.make_seed()
        before = sorted(p.name for p in self.lab_root.rglob("*"))
        lab.cmd_prepare(self.lab_root, "testfamily", dry_run=True, seed_rel=str(seed))
        after = sorted(p.name for p in self.lab_root.rglob("*"))
        self.assertEqual(before, after, "dry-run wrote to the lab")

    def test_prepare_materializes_pinned_manifest_and_refuses_collision(self):
        seed = self.make_seed()
        lab.cmd_prepare(self.lab_root, "testfamily", dry_run=False, seed_rel=str(seed))
        manifest = lab.load_json(self.lab_root / "seeds" / "testfamily" / "manifest.json")
        self.assertIn("src/app.py", manifest["files"])
        self.assertEqual(len(manifest["files"]["src/app.py"]), 64)
        with self.assertRaises(SystemExit):
            lab.cmd_prepare(self.lab_root, "testfamily", dry_run=False, seed_rel=str(seed))

    def test_isolation_posture_is_honest_by_default(self):
        posture = lab.isolation_posture(self.lab_root)
        self.assertTrue(posture["workspace_isolation"])
        self.assertFalse(posture["host_enforced_isolation"],
                         "a hand-made lab root must never claim enforced isolation")


if __name__ == "__main__":
    unittest.main()
