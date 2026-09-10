#!/usr/bin/env bats
# Self-checks for tests/efficiency/fixtures: clean controls pass, seeded faults are
# detected at their intended validation boundary (see fixtures/ORACLES.md).

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    FX="$REPO_ROOT/tests/efficiency/fixtures"
    TMPDIR_TEST="$(mktemp -d)"
}
teardown() { rm -rf "$TMPDIR_TEST"; }

copy_fixture() { cp -r "$FX/$1" "$TMPDIR_TEST/fx"; cd "$TMPDIR_TEST/fx"; }
apply_fault() { patch -p1 -s < seeded-fault.patch; }

@test "every inventory fixture exists with a README" {
    for f in isolated-change shared-core-change config-change integration-seam no-toolchain interrupted-plan legacy-plan-v217 long-history-plan new-shape-plan; do
        [ -f "$FX/$f/README.md" ]
    done
    [ -f "$FX/ORACLES.md" ]
}

@test "isolated-change: clean passes; fault caught by the scoped test" {
    copy_fixture isolated-change
    run python3 -m unittest discover -s tests; [ "$status" -eq 0 ]
    apply_fault
    run python3 -m unittest tests.test_greeter; [ "$status" -ne 0 ]
    run python3 -m unittest tests.test_math;    [ "$status" -eq 0 ]
}

@test "shared-core-change: core-only scoped test passes but the consumer fails (widening required)" {
    copy_fixture shared-core-change
    run python3 -m unittest discover -s tests; [ "$status" -eq 0 ]
    apply_fault
    run python3 -m unittest tests.test_core;   [ "$status" -eq 0 ]
    run python3 -m unittest tests.test_report; [ "$status" -ne 0 ]
}

@test "config-change: a JSON-only change breaks a runtime test" {
    copy_fixture config-change
    run python3 -m unittest discover -s tests; [ "$status" -eq 0 ]
    apply_fault
    run python3 -m unittest tests.test_limits; [ "$status" -ne 0 ]
}

@test "integration-seam: mocked unit passes, real-seam integration fails" {
    copy_fixture integration-seam
    run python3 -m unittest discover -s tests; [ "$status" -eq 0 ]
    apply_fault
    run python3 -m unittest tests.test_client;      [ "$status" -eq 0 ]
    run python3 -m unittest tests.test_integration; [ "$status" -ne 0 ]
}

@test "plan fixtures: state.json parses and matches task files" {
    for p in legacy-plan-v217/.dwp/plans/PLAN_legacy_fixture interrupted-plan/.dwp/plans/PLAN_interrupted_fixture new-shape-plan/.dwp/plans/PLAN_new_shape_fixture; do
        python3 - "$FX/$p" <<'PY'
import json, os, sys, re
d=sys.argv[1]; s=json.load(open(os.path.join(d,"state.json")))
files={f for f in os.listdir(d) if re.match(r"^\d+\.task_",f)}
assert {t["file"] for t in s["tasks"]}==files, (d, files)
assert s["task_count"]==len(files)
PY
    done
}

@test "long-history-plan: decision D-7 exists only in entry 7 and Task 51 points at it" {
    grep -q 'DECISION D-7' "$FX/long-history-plan/.dwp/plans/PLAN_long_history_fixture/PROGRESS.md"
    [ "$(grep -c 'DECISION D-7' "$FX/long-history-plan/.dwp/plans/PLAN_long_history_fixture/PROGRESS.md")" -eq 1 ]
    grep -q 'Task 7 Completion & Log' "$FX/long-history-plan/.dwp/plans/PLAN_long_history_fixture/51.task_add_price_formatter.md"
}

@test "measure-instruction-load.sh runs and reports every flow" {
    run bash "$REPO_ROOT/tests/efficiency/measure-instruction-load.sh" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    for flow in create execute resume refine onboard; do echo "$output" | grep -q "^$flow "; done
}

@test "measurement of a nested export does not attribute its parent's revision" {
    git -C "$TMPDIR_TEST" init -q
    mkdir -p "$TMPDIR_TEST/export/skills"
    cp -r "$REPO_ROOT/skills/deepworkplan" "$TMPDIR_TEST/export/skills/"
    run bash "$REPO_ROOT/tests/efficiency/measure-instruction-load.sh" "$TMPDIR_TEST/export"
    [ "$status" -eq 0 ]
    [[ "$output" == *"# Instruction load — export (record source revision separately)"* ]]
    [[ "$output" != *"$TMPDIR_TEST/export/skills/deepworkplan/"* ]]
}
