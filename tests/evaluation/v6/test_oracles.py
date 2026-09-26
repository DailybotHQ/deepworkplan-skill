"""Calibration regression tests for the v6 oracles (fast subset).

The astro oracle's full calibration (real install/build) runs via
oracles/calibrate.py in the task gates; here we prove the legacy and service
oracles end to end on the real seeds, plus the arm-blindness property.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "oracles"))

import scoring as oracles  # noqa: E402

REPO = HERE.parents[2]
SEEDS = REPO / "tests" / "evaluation" / "v6" / "fixtures"
REFERENCES = HERE / "oracles" / "reference"


def load_reference(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"ref_{name}", REFERENCES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OracleCalibrationBase(unittest.TestCase):
    def variant(self, family, op, reference=None):
        tmp = tempfile.TemporaryDirectory(prefix=f"oracle-{family}-{op}-")
        self.addCleanup(tmp.cleanup)
        work = Path(tmp.name) / "ws"
        shutil.copytree(SEEDS / family / "seed", work, symlinks=False)
        if op == "apply":
            reference.apply(work)
        elif op == "sabotage":
            reference.sabotage(work)
        return work


class LegacyOracleTests(OracleCalibrationBase):
    def setUp(self):
        self.ref = load_reference("legacy_lc3_k1_fix")

    def test_matrix(self):
        self.assertEqual(oracles.score_legacy_lc3(
            self.variant("legacy", "none"), SEEDS / "legacy" / "seed")["verdict"], "FAIL")
        self.assertEqual(oracles.score_legacy_lc3(
            self.variant("legacy", "apply", self.ref), SEEDS / "legacy" / "seed")["verdict"], "PASS")
        self.assertEqual(oracles.score_legacy_lc3(
            self.variant("legacy", "sabotage", self.ref), SEEDS / "legacy" / "seed")["verdict"], "FAIL")

    def test_user_files_survival_is_enforced(self):
        work = self.variant("legacy", "apply", self.ref)
        (work / "USER_NOTES.md").write_text("tampered\n", encoding="utf-8")
        result = oracles.score_legacy_lc3(work, SEEDS / "legacy" / "seed")
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(any("USER_NOTES" in r for r in result["reasons"]))

    def test_arm_blind_structural(self):
        # A workspace with a fake narration claiming success must still FAIL:
        # the oracle reads artifacts, never claims.
        work = self.variant("legacy", "none")
        (work / "narration.json").write_text('{"success": true, "claims": "all done"}', encoding="utf-8")
        self.assertEqual(oracles.score_legacy_lc3(work, SEEDS / "legacy" / "seed")["verdict"], "FAIL")


class ServiceOracleTests(OracleCalibrationBase):
    def setUp(self):
        self.ref = load_reference("service_sc9_event_lookup")

    def test_matrix(self):
        self.assertEqual(oracles.score_service_sc9(
            self.variant("service", "none"), SEEDS / "service" / "seed")["verdict"], "FAIL")
        self.assertEqual(oracles.score_service_sc9(
            self.variant("service", "apply", self.ref), SEEDS / "service" / "seed")["verdict"], "PASS")
        self.assertEqual(oracles.score_service_sc9(
            self.variant("service", "sabotage", self.ref), SEEDS / "service" / "seed")["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
