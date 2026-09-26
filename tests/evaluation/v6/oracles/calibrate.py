#!/usr/bin/env python3
"""Calibrate the public development oracles against known-good and
seeded-broken variants BEFORE they ever score an agent (Task 8).

For every calibration case the matrix must hold:

    pristine seed          -> FAIL (the task is not done)
    seed + reference fix   -> PASS (the documented behavior holds)
    seed + sabotage        -> FAIL (a plausible wrong repair is caught)

The oracle never sees arm labels or agent narration, so the same matrix holds
regardless of who produced the artifact.

Usage:
    python3 tests/evaluation/v6/oracles/calibrate.py [--family NAME] [--json OUT]

Exit 0 iff the whole matrix holds for the selected cases.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts" / "evaluation"))

import scoring as oracles  # noqa: E402

SEEDS = {
    "legacy": REPO / "tests/evaluation/v6/fixtures/legacy/seed",
    "service": REPO / "tests/evaluation/v6/fixtures/service/seed",
    "astro": REPO / "tests/evaluation/v6/fixtures/astro/seed",
}

CALIBRATIONS = [
    {"id": "legacy-LC3", "family": "legacy", "score": oracles.score_legacy_lc3,
     "reference": "legacy_lc3_k1_fix"},
    {"id": "service-SC9", "family": "service", "score": oracles.score_service_sc9,
     "reference": "service_sc9_event_lookup"},
    {"id": "astro-AC1", "family": "astro", "score": oracles.score_astro_ac1,
     "reference": "astro_ac1_reading_time"},
    {"id": "astro-AC6", "family": "astro", "score": oracles.score_astro_ac6,
     "reference": "astro_ac6_skip_link"},
    {"id": "astro-AC2", "family": "astro",
     "score_module": "cases/astro_ac2.py"},
    {"id": "astro-AC3", "family": "astro",
     "score_module": "cases/astro_ac3.py"},
    {"id": "service-SC5", "family": "service",
     "score_module": "cases/service_sc5_sc10.py", "score_fn": "score_sc5",
     "variants": {"pristine": None, "broken": "sabotage_sc5"},
     "expected": {"pristine": "PASS", "broken": "FAIL"}},
    {"id": "service-SC10", "family": "service",
     "score_module": "cases/service_sc5_sc10.py", "score_fn": "score_sc10"},
    {"id": "service-SC2", "family": "service",
     "score_module": "cases/service_sc2_sc4.py", "score_fn": "score_sc2",
     "variants": {"pristine": None, "broken": "sabotage_sc2"},
     "expected": {"pristine": "PASS", "broken": "FAIL"}},
    {"id": "service-SC4", "family": "service",
     "score_module": "cases/service_sc2_sc4.py", "score_fn": "score_sc4",
     "variants": {"pristine": None, "broken": "sabotage_sc4"},
     "expected": {"pristine": "PASS", "broken": "FAIL"}},
]


def load_reference(case):
    if "reference" not in case:
        # Case-file style: the module itself carries score/apply/sabotage.
        return load_case_module(case)
    name = case["reference"]
    spec = importlib.util.spec_from_file_location(f"ref_{name}", HERE / "reference" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_case_module(case):
    rel = case["score_module"]
    spec = importlib.util.spec_from_file_location(f"case_{case['id']}", HERE / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(case, results):
    if "score_module" in case:
        module = load_case_module(case)
        family = case["family"]
        score = getattr(module, case.get("score_fn", "score"))
        reference = module
    else:
        family, score = case["family"], case["score"]
        reference = load_reference(case)
    seed = SEEDS[family]
    matrix = {}
    with tempfile.TemporaryDirectory(prefix=f"calib-{case['id']}-") as td:
        base = Path(td)
        variants = case.get("variants",
                            {"pristine": None, "known_good": "apply", "broken": "sabotage"})
        for variant, op in variants.items():
            work = base / variant
            shutil.copytree(seed, work, symlinks=False)
            if op is None:
                pass  # pristine: no variant applied
            else:
                getattr(reference, op)(work)
            result = score(work, seed)
            matrix[variant] = result
    expected = case.get("expected",
                        {"pristine": "FAIL", "known_good": "PASS", "broken": "FAIL"})
    ok = all(matrix[v]["verdict"] == e for v, e in expected.items())
    results[case["id"]] = {"matrix": matrix, "ok": ok}
    print(f"{'OK  ' if ok else 'FAIL'} {case['id']}: "
          + " | ".join(f"{v}={matrix[v]['verdict']}" for v in expected))
    for v in expected:
        for reason in matrix[v]["reasons"]:
            print(f"       {v}: {reason}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family")
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args()

    cases = [c for c in CALIBRATIONS if not args.family or c["family"] == args.family]
    if not cases:
        print(f"no calibration cases for family {args.family!r}", file=sys.stderr)
        return 2
    results = {}
    all_ok = True
    for case in cases:
        all_ok = run_case(case, results) and all_ok

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print("CALIBRATION " + ("OK" if all_ok else "FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
