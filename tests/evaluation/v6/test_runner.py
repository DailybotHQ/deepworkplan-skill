"""Regression coverage for the v6 evaluation lab driver (scripts/evaluation/v6/lab.py).

Every case is self-contained: synthetic labs, seeds and actors are built in a
per-test temp directory. No network, no provider call, no real agent. Run:

    python3 -m unittest discover -s tests/evaluation/v6 -p 'test_*.py'
"""
import json
import os
import pathlib
import subprocess
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


class TreatmentOverlayTests(LabTestBase):
    """The arm overlay is the treatment: it must describe the pack actually
    mounted, and per-cell metering must key off the provider, not the launch
    mode (the pilot needed a post-hoc metering regenerator for exactly this
    mis-keying)."""

    def make_pack_with_version(self, version=None, tag="vT1", digest="aaaaaaaaaaaaaaaa"):
        pack = self.make_pack(tag=tag, digest=digest)
        if version is not None:
            (pack / "SKILL.md").write_text(
                "---\nname: deepworkplan\nversion: %s\n---\nbody\n" % version,
                encoding="utf-8")
        return pack

    def task_md(self, out, cell_id):
        ws = next(out.glob("*/workspaces/" + cell_id))
        return (ws / "TASK.md").read_text(encoding="utf-8")

    def test_overlay_names_the_mounted_packs_own_version(self):
        pack = self.make_pack_with_version("9.9.9")
        cfg = self.make_cfg(arms={"C": {"pack": "packs/vtest/%s" % pack.name}})
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        task = self.task_md(out, "T-1-fake-r1-C")
        self.assertIn("(v9.9.9)", task)
        self.assertNotIn("v5.5.4", task,
                         "overlay hardcoded the comparator version for a v6 arm")

    def test_overlay_omits_the_version_when_the_pack_carries_none(self):
        pack = self.make_pack_with_version(None)  # PACK_MARKER only, no SKILL.md
        cfg = self.make_cfg(arms={"B": {"pack": "packs/vtest/%s" % pack.name}})
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        task = self.task_md(out, "T-1-fake-r1-B")
        self.assertIn("A read-only DWP skill pack is mounted", task)
        self.assertNotIn("(v", task.split("skill pack is mounted")[0].split("pack")[-1])

    def test_meter_keys_off_stratum_provider_not_launch_mode(self):
        # An exec-mode stratum named for the provider: its log line must be
        # parsed by the claude meter, not reported as "no meter exposed".
        wrapper = self.tmp / "fake_claude.sh"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "while [ $# -gt 0 ]; do case \"$1\" in --workspace|--task) shift 2;; *) shift;; esac; done\n"
            "echo '{\"duration_api_ms\": 1, \"total_cost_usd\": 0.5, "
            "\"usage\": {\"input_tokens\": 10, \"output_tokens\": 20, "
            "\"cache_read_input_tokens\": 0, \"cache_creation_input_tokens\": 0}}'\n",
            encoding="utf-8")
        seed = self.make_seed()
        cfg = self.make_cfg(seed=seed)
        cfg["strata"] = [{"name": "claude-code", "launch": {"mode": "exec",
                           "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertEqual(len(records), 2)
        for r in records:
            self.assertIn("claude", r.get("meter_source", ""),
                          "exec stratum meter not attributed: %r" % r.get("meter_source"))
            self.assertEqual(r["cost"].get("class"), "invoiced", r)
            self.assertEqual(r["cost"].get("amount"), 0.5, r)
            self.assertEqual(r["counters"]["input_tokens"], 10, r)


class ProviderRefusalTests(LabTestBase):
    """A provider-side refusal is not actor work: it must record a
    non-terminal status so scoring never counts a phantom failure and a
    resume re-runs the cell for real (the round-1 development findings —
    quota walls AND the expired-auth family that died in 2 seconds per
    cell while recording phantom completions)."""

    def claude_result_wrapper(self, name, payload):
        wrapper = self.tmp / name
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "while [ $# -gt 0 ]; do case \"$1\" in --workspace|--task) shift 2;; *) shift;; esac; done\n"
            "echo '%s'\n"
            "exit 1\n" % payload,
            encoding="utf-8")
        return wrapper

    def test_claude_quota_refusal_records_non_terminal_status(self):
        wrapper = self.claude_result_wrapper(
            "quota_claude.sh",
            '{"duration_api_ms":0,"total_cost_usd":0,"is_error":true,'
            '"api_error_status":429,"result":"session limit reached",'
            '"type":"result"}')
        cfg = self.make_cfg()
        cfg["strata"] = [{"name": "claude-code", "launch": {"mode": "exec",
                           "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertTrue(records)
        for r in records:
            self.assertEqual(r["status"], "provider_refused", r)
            self.assertEqual(r["quota_signature"], "claude", r)
            self.assertEqual(r["provider_refusal"], "quota-claude", r)
            self.assertIn("refused this cell", r["note"])

    def test_expired_auth_records_non_terminal_status_not_phantom_completed(self):
        # The round-1 auth wall: instant death, is_error true, terminal
        # api_error — recorded by the old driver as a phantom "completed".
        wrapper = self.claude_result_wrapper(
            "auth_dead.sh",
            '{"duration_api_ms":0,"total_cost_usd":0,"is_error":true,'
            '"terminal_reason":"api_error","num_turns":1,'
            '"result":"Failed to authenticate: OAuth session expired and '
            'could not be refreshed","type":"result"}')
        cfg = self.make_cfg()
        cfg["strata"] = [{"name": "claude-code", "launch": {"mode": "exec",
                           "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        for r in self.read_inventory(out):
            self.assertEqual(r["status"], "provider_refused", r)
            self.assertIsNone(r["quota_signature"], r)
            self.assertEqual(r["provider_refusal"], "auth", r)

    def test_provider_refused_cell_is_rerun_on_resume(self):
        # Half the cells quota-refused, half succeeded: resume must re-run
        # only the refused ones, never the recorded completions.
        # The lab scrubs the environment down to PATH/HOME/TMPDIR/locale,
        # so the wrapper cannot read an ambient variable: the wall is a
        # flag file beside the wrapper, toggled between passes.
        flag = self.tmp / "refuse.flag"
        flag.write_text("1\n", encoding="utf-8")
        wrapper = self.tmp / "half_quota.sh"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "WS=\"\"; while [ $# -gt 0 ]; do case \"$1\" in --workspace) WS=\"$2\"; shift 2;; *) shift;; esac; done\n"
            "DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            "if [ -e \"$DIR/refuse.flag\" ]; then\n"
            "  echo '{\"api_error_status\":429,\"total_cost_usd\":0,\"type\":\"result\"}'\n"
            "  exit 1\n"
            "fi\n"
            "echo done > \"$WS/solution.txt\"\n",
            encoding="utf-8")
        cfg = self.make_cfg()
        cfg["strata"] = [{"name": "claude-code", "launch": {"mode": "exec",
                           "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)          # all refused
        refused = {r["cell_id"] for r in self.read_inventory(out)}
        self.assertEqual(len(refused), 2)
        # A resumed pass with the wall gone: both cells re-run and complete.
        flag.unlink()
        attempt = sorted(p.name for p in out.iterdir() if p.is_dir())[-1]
        lab.run_full(cfg, self.lab_root, out, resume=attempt)
        recs = self.read_inventory(out)
        by_id = {}
        for r in recs:
            by_id.setdefault(r["cell_id"], []).append(r["status"])
        for cid, statuses in by_id.items():
            self.assertIn("provider_refused", statuses, cid)
            self.assertIn("completed", statuses, cid)


class ProviderEnvAuthTests(LabTestBase):
    """The env-token auth route: provider auth variables pass through the
    scrubbed environment (a static token has no rotation race), and the
    credential-file copy is skipped when that route is armed — copied OAuth
    pairs rot on the first rotation and then refuse every cell."""

    def test_provider_env_keys_pass_through_when_present(self):
        import os as _os
        for key in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
            self.addCleanup(_os.environ.pop, key, None)
            _os.environ[key] = "test-value"
        env = lab.scrubbed_env(self.tmp / "ws", self.tmp / "home")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "test-value")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "test-value")
        # Nothing else leaks: the scrub stays minimal — base keys plus
        # exactly the provider keys the ambient environment carries.
        expected = {"PATH", "HOME", "TMPDIR", "TZ", "LC_ALL", "LANG",
                    "PYTHONDONTWRITEBYTECODE", "DWP_DIR"} | {
            k for k in lab.PROVIDER_ENV_KEYS if _os.environ.get(k)}
        self.assertEqual(set(env), expected)

    def test_provider_env_keys_absent_stay_absent(self):
        import os as _os
        saved = {k: _os.environ.pop(k, None) for k in lab.PROVIDER_ENV_KEYS}
        self.addCleanup(lambda: [k is not None and _os.environ.__setitem__(k, v)
                                 for k, v in saved.items()])
        env = lab.scrubbed_env(self.tmp / "ws", self.tmp / "home")
        self.assertFalse(set(env) & set(lab.PROVIDER_ENV_KEYS))


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

    def test_rerun_timeouts_flag_reruns_only_timeout_cells(self):
        # A ceiling that was too low for the lane killed healthy cells mid-work
        # (round 1: AC-3 died 7 seconds after writing its validation gate).
        # Timeouts stay terminal on a normal resume; --rerun-timeouts opts in
        # to re-running exactly those cells — completed work is never re-run.
        cfg = self.make_cfg(arms={"A": None})  # one cell, fast to cycle
        flag = self.tmp / "sleep.flag"
        flag.write_text("1\n", encoding="utf-8")
        sleeper = self.make_actor(name="flag_sleeper.py", body=(
            "import pathlib, sys, time\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "if (pathlib.Path(__file__).parent / 'sleep.flag').is_file():\n"
            "    time.sleep(29)\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ))
        cfg["strata"] = [{"name": "fake", "launch": {"mode": "fake", "command": str(sleeper)}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out, timeout_s=1)
        records = self.read_inventory(out)
        self.assertTrue(all(r["status"] == "timeout" for r in records))
        attempt = records[0]["attempt"]
        lab.run_full(cfg, self.lab_root, out, resume=attempt)
        self.assertEqual(len(self.read_inventory(out)), len(records),
                         "a normal resume re-ran timeout cells")
        flag.unlink()
        lab.run_full(cfg, self.lab_root, out, resume=attempt, rerun_timeouts=True)
        after = self.read_inventory(out)
        self.assertEqual(len(after), 2 * len(records),
                         "--rerun-timeouts did not re-run the timeout cells")
        by_id = {}
        for r in after:
            by_id.setdefault(r["cell_id"], []).append(r["status"])
        for statuses in by_id.values():
            self.assertIn("timeout", statuses)
            self.assertIn("completed", statuses)

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


class UnreadableStateTests(LabTestBase):
    """An actor's own validation work may leave unreadable state (write-only
    probe files, chmod'd scratch): round 1's AC-5 cell did exactly that and
    the driver crashed hashing the final tree, orphaning the cell and killing
    the rest of its family. Unreadable entries become markers, never
    crashes; the canary scan lists what it could not read."""

    def test_write_only_scratch_file_does_not_crash_the_cell(self):
        if getattr(os, "geteuid", lambda: -1)() == 0:
            self.skipTest("root reads through restrictive modes; marker path unreachable")
        prober = self.make_actor(name="prober.py", body=(
            "import pathlib, sys, os\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "probe = ws / '.scratch' / 'control.txt'\n"
            "probe.write_text('probe', encoding='utf-8')\n"
            "os.chmod(probe, 0o200)\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ))
        cfg = self.make_cfg(actor=prober)
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertTrue(records)
        for r in records:
            self.assertEqual(r["status"], "completed", r)
            self.assertIn(".scratch/control.txt", r["unreadable_files"], r)
            self.assertTrue(
                any(v.startswith("unreadable:") for v in r["final_hashes"].values()), r)
            self.assertTrue(r["canary_intact"], r)

    def test_chmod000_directory_survives_workspace_rebuild(self):
        if getattr(os, "geteuid", lambda: -1)() == 0:
            self.skipTest("root reads through restrictive modes; marker path unreachable")
        locker = self.make_actor(name="locker.py", body=(
            "import pathlib, sys, os\n"
            "ws = pathlib.Path(sys.argv[sys.argv.index('--workspace') + 1])\n"
            "locked = ws / '.scratch' / 'lockeddir'\n"
            "locked.mkdir(parents=True, exist_ok=True)\n"
            "locked.joinpath('inner.txt').write_text('x', encoding='utf-8')\n"
            "os.chmod(locked, 0o000)\n"
            "(ws / 'solution.txt').write_text('done\\n')\n"
        ))
        cfg = self.make_cfg(actor=locker)
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertTrue(records)
        attempt = records[0]["attempt"]
        # Rebuilding the SAME workspace (run_cell's precondition wipe) must
        # survive the chmod-000 directory the actor left behind.
        cell = lab.campaign_cells(cfg, cfg["arms"])[0]
        rec = lab.run_cell(cell, cfg, out / attempt, self.lab_root, timeout_s=20)
        self.assertEqual(rec["status"], "completed", rec)


class ActorFailureTests(LabTestBase):
    """A nonzero actor exit is never a completion: the take-5->take-6 chain
    stop SIGTERM'd an in-flight claude actor, the CLI trapped the signal and
    exited 143, and the old driver recorded a phantom `completed` that the
    resume done-set then skipped forever (SC-2-claude-code-r1-C, the sole
    unmetered claude completion of round 1)."""

    def test_nonzero_exit_records_actor_failed_not_completed(self):
        # Exits 143 after doing real work — exactly the trapped-SIGTERM
        # signature the claude CLI shows when killed mid-session.
        wrapper = self.tmp / "sigterm_trap.sh"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "WS=\"\"; while [ $# -gt 0 ]; do case \"$1\" in --workspace) WS=\"$2\"; shift 2;; *) shift;; esac; done\n"
            "echo done > \"$WS/solution.txt\"\n"
            "exit 143\n",
            encoding="utf-8")
        cfg = self.make_cfg()
        cfg["strata"] = [{"name": "claude-code", "launch": {"mode": "exec",
                           "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertTrue(records)
        for r in records:
            self.assertEqual(r["status"], "actor_failed", r)
            self.assertEqual(r["exit_code"], 143, r)
            self.assertIn("resume re-runs it", r["note"], r)

    def test_actor_failed_cell_is_rerun_on_resume(self):
        # The bogus terminal record used to pin the cell as done forever;
        # actor_failed must be non-terminal so a resume re-runs it for real.
        flag = self.tmp / "fail.flag"
        flag.write_text("1\n", encoding="utf-8")
        wrapper = self.tmp / "half_dead.sh"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "WS=\"\"; while [ $# -gt 0 ]; do case \"$1\" in --workspace) WS=\"$2\"; shift 2;; *) shift;; esac; done\n"
            "DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            "if [ -e \"$DIR/fail.flag\" ]; then exit 137; fi\n"
            "echo done > \"$WS/solution.txt\"\n",
            encoding="utf-8")
        cfg = self.make_cfg()
        cfg["strata"] = [{"name": "claude-code", "launch": {"mode": "exec",
                           "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)          # all actor_failed
        for r in self.read_inventory(out):
            self.assertEqual(r["status"], "actor_failed", r)
        flag.unlink()
        attempt = sorted(p.name for p in out.iterdir() if p.is_dir())[-1]
        lab.run_full(cfg, self.lab_root, out, resume=attempt)
        by_id = {}
        for r in self.read_inventory(out):
            by_id.setdefault(r["cell_id"], []).append(r["status"])
        for cid, statuses in by_id.items():
            self.assertIn("actor_failed", statuses, cid)
            self.assertIn("completed", statuses, cid)


class WorkspaceEscapeTests(LabTestBase):
    """Repair #15 — pin DWP_DIR inside the workspace. context.sh derives
    dwp_dir from `git rev-parse --show-toplevel`, and evaluation workspaces
    sit inside the host repository's work tree, so an un-pinned actor that
    resolves before creating anything local writes its plan into the HOST
    .dwp/ (three SC-5 cells escaped exactly this way in round 1). The pin
    uses the pack's documented DWP_DIR override — the public contract for
    exactly this situation."""

    def test_scrubbed_env_pins_dwp_dir_inside_workspace(self):
        env = lab.scrubbed_env(self.tmp / "ws", self.tmp / "home")
        self.assertEqual(env["DWP_DIR"], str(self.tmp / "ws" / ".dwp"))

    def test_actor_process_sees_the_pin(self):
        # An exec-mode actor echoes its DWP_DIR into the solution file; the
        # recorded solution proves the override reached the actor process,
        # not just the driver-side dict.
        import os as _os
        for key in lab.PROVIDER_ENV_KEYS:
            self.addCleanup(_os.environ.pop, key, None)
            _os.environ.pop(key, None)
        wrapper = self.tmp / "pin_probe.sh"
        wrapper.write_text(
            "#!/usr/bin/env bash\n"
            "while [ $# -gt 0 ]; do case \"$1\" in\n"
            "  --workspace) ws=\"$2\"; shift 2;;\n"
            "  *) shift;;\n"
            "esac; done\n"
            "printf '%s' \"$DWP_DIR\" > \"$ws/solution.txt\"\n"
            "exit 0\n")
        wrapper.chmod(0o755)
        cfg = self.make_cfg(arms={"C": None})
        cfg["strata"] = [{"name": "claude-code",
                          "launch": {"mode": "exec", "argv": ["bash", str(wrapper)]}}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        records = self.read_inventory(out)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["status"], "completed")
        from pathlib import Path as _P
        # records store the workspace relative to the attempt directory
        ws = out / rec["attempt"] / rec["workspace"]
        sol = (ws / "solution.txt").read_text().strip()
        self.assertEqual(sol, str(ws / ".dwp"))


class PackIntegrityTests(LabTestBase):
    """The treatment tree must be frozen at run time, not just at validation
    time. Round 1 proved an actor's Python writes __pycache__ INTO the mounted
    pack (two .pyc files drifted the content digest; the run-time validation
    refused the next resume exactly as designed). Three mechanisms, three
    regressions: bytecode-free actors, a read-only pack lock, and explicit
    cell re-runs for cells whose evidence overlaps a treatment-tree event."""

    def test_actor_env_never_writes_bytecode(self):
        env = lab.scrubbed_env(self.tmp / "ws", self.tmp / "home")
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1",
                         "an actor's Python may write .pyc into the mounted pack")

    def test_actor_python_writes_no_bytecode_under_scrubbed_env(self):
        # Behavioral check, not just the key: import the pack's module inside
        # the scrubbed environment and assert no __pycache__ appears.
        pack = self.make_pack(tag="vT2", digest="bbbbbbbbbbbbbbbb")
        (pack / "mod.py").write_text("X = 1\n", encoding="utf-8")
        import stat
        lab.lock_packs_readonly({"arms": {"C": {"pack": "packs/vtest/%s" % pack.name}}},
                                self.lab_root)
        self.addCleanup(lambda: [
            os.chmod(f, 0o700 if (f.stat().st_mode & stat.S_IFDIR) else 0o600)
            for f in sorted(pack.rglob("*"), reverse=True)] and
            os.chmod(pack, 0o700))
        scratch = self.tmp / "home"
        scratch.mkdir(exist_ok=True)
        code = ("import os, sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "import mod\n"
                "print(mod.X)\n")
        proc = subprocess.run([sys.executable, "-c", code, str(pack)],
                              env=lab.scrubbed_env(self.tmp / "ws", scratch),
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(list(pack.rglob("__pycache__")),
                         "bytecode was written into the pack tree")

    def test_lock_packs_readonly_blocks_writes_and_preserves_digest(self):
        if getattr(os, "geteuid", lambda: -1)() == 0:
            self.skipTest("root writes through restrictive modes")
        import stat
        pack = self.make_pack(tag="vT3", digest="cccccccccccccccc")
        (pack / "shared").mkdir()
        (pack / "shared" / "ledger.py").write_text("L = 1\n", encoding="utf-8")
        before = lab.pack_content_digest(pack)
        cfg = {"arms": {"C": {"pack": "packs/vtest/%s" % pack.name}}}
        lab.lock_packs_readonly(cfg, self.lab_root)  # idempotent by design
        lab.lock_packs_readonly(cfg, self.lab_root)
        self.addCleanup(lambda: [
            os.chmod(f, 0o700 if (f.stat().st_mode & stat.S_IFDIR) else 0o600)
            for f in sorted(pack.rglob("*"), reverse=True)] and
            os.chmod(pack, 0o700))
        with self.assertRaises(PermissionError):
            (pack / "shared" / "ledger.py").write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(PermissionError):
            (pack / "shared" / "new_file.py").write_text("injected\n", encoding="utf-8")
        self.assertEqual(lab.pack_content_digest(pack), before,
                         "the lock itself must not change the frozen identity")

    def test_rerun_cells_flag_reruns_exactly_the_listed_cells(self):
        # A treatment-tree integrity event taints cells that already recorded
        # terminal completions (round 1: pack __pycache__ drift overlapping
        # two completed cells). --rerun-cells re-runs exactly those cells;
        # every other completed cell stays untouched.
        cfg = self.make_cfg(arms={"A": None},
                            tasks=None) if False else self.make_cfg(arms={"A": None})
        cfg["tasks"] = [{"id": "T-1", "prompt": "produce solution.txt"},
                        {"id": "T-2", "prompt": "produce solution.txt"}]
        out = self.tmp / "out"
        lab.run_full(cfg, self.lab_root, out)
        attempt = self.read_inventory(out)[0]["attempt"]
        lab.run_full(cfg, self.lab_root, out, resume=attempt,
                     rerun_cells="T-1-fake-r1-A")
        after = self.read_inventory(out)
        counts = {}
        for r in after:
            counts[r["cell_id"]] = counts.get(r["cell_id"], 0) + 1
        self.assertEqual(counts["T-1-fake-r1-A"], 2,
                         "the listed cell was not re-run")
        self.assertEqual(counts["T-2-fake-r1-A"], 1,
                         "an unlisted completed cell was re-run")
        self.assertEqual(after[-1]["cell_id"], "T-1-fake-r1-A",
                         "last record must be the re-run (last-record-wins)")

    def test_rerun_cells_rejects_unknown_ids(self):
        # A typo in the re-run list must refuse the run, never silently no-op
        # and leave tainted evidence in place.
        cfg = self.make_cfg(arms={"A": None})
        out = self.tmp / "out"
        out.mkdir()
        with self.assertRaises(SystemExit) as ctx:
            lab.cmd_run(cfg, self.lab_root, out, resume="", timeout_s=20,
                        rerun_timeouts=False, rerun_cells="T-9-fake-r1-A")
        self.assertEqual(ctx.exception.code, 1)
        self.assertFalse((out / "attempts.jsonl").exists(),
                         "a refused run must not write an inventory")


if __name__ == "__main__":
    unittest.main()
