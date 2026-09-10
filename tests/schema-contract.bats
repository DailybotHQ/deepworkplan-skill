#!/usr/bin/env bats
# Tests for scripts/check-schema-contract.py (dev-only state-layer contract).
# Requires python3 + jsonschema (pip install jsonschema), like CI.

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    CHECK="$REPO_ROOT/scripts/check-schema-contract.py"
    FX="$REPO_ROOT/tests/efficiency/fixtures"
    TMPDIR_TEST="$(mktemp -d)"
    python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
}
teardown() { rm -rf "$TMPDIR_TEST"; }

mutant() { cp -r "$FX/new-shape-plan/.dwp/plans/PLAN_new_shape_fixture" "$TMPDIR_TEST/PLAN_mutant"; echo "$TMPDIR_TEST/PLAN_mutant"; }

@test "shipped fixtures pass in both directions and the probes hold" {
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$FX"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "2.2.0 manifest valid (backward direction)"
    echo "$output" | grep -q "extra top-level state field rejected"
}

@test "an extra top-level state field is rejected" {
    m="$(mutant)"
    python3 - "$m" <<'PY'
import json,sys,os; p=os.path.join(sys.argv[1],"state.json"); d=json.load(open(p)); d["cost"]={"tokens":1}; json.dump(d,open(p,"w"))
PY
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$TMPDIR_TEST/none" "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "state.json INVALID"
}

@test "an unknown future spec_version is flagged, not treated as legacy" {
    m="$(mutant)"
    python3 - "$m" <<'PY'
import json,sys,os; p=os.path.join(sys.argv[1],"manifest.json"); d=json.load(open(p)); d["spec_version"]="9.9.9"; json.dump(d,open(p,"w"))
PY
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$TMPDIR_TEST/none" "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "newer than supported"
}

@test "a passing gate with zero-selection evidence is invalid evidence" {
    m="$(mutant)"
    python3 - "$m" <<'PY'
import json,sys,os; p=os.path.join(sys.argv[1],"state.json"); d=json.load(open(p))
d["tasks"][0]["gates"]=[{"command":"pytest -k zzz","passes":True,"exit_code":0,"last_run":"2026-09-01T10:00:00Z","evidence":"scope=x; ran=0/0"}]
json.dump(d,open(p,"w"))
PY
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$TMPDIR_TEST/none" "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "zero-selection evidence"
}

@test "a state projection ahead of the README is stale and fails" {
    m="$(mutant)"
    python3 - "$m" <<'PY'
import json,sys,os; p=os.path.join(sys.argv[1],"state.json"); d=json.load(open(p)); d["completed_count"]=3; json.dump(d,open(p,"w"))
PY
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$TMPDIR_TEST/none" "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "stale/ahead projection"
}

@test "a README still saying 'Plan Status: materializing' is a partial materialization that names the intended shape" {
    m="$(mutant)"
    sed -i 's/Plan Status: *[0-9]*\/[0-9]* completed/Plan Status: materializing/' "$m/README.md"
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$TMPDIR_TEST/none" "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "partial materialization"
    echo "$output" | grep -q "manifest declares"
}

@test "a plan folder without README.md is reported as partial materialization" {
    m="$(mutant)"
    rm "$m/README.md"
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan" --fixtures "$TMPDIR_TEST/none" "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "partial materialization"
}
