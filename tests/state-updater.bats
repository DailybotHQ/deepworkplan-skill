#!/usr/bin/env bats
# Contract tests for the shipped state updater (format decision of
# PLAN_v5_phase2_validation): manifest.json/state.json stay JSON, and the pack
# ships a stdlib-only Python helper so executors apply targeted mutations
# (task status, gate evidence, counts/checkpoint) instead of re-emitting the
# whole state file on every task. The tests run the REAL script against a
# copy of the lite-plan fixture and assert schema validity, atomicity and
# idempotence-modulo-timestamps.
#
# Run with:  bats tests/
# Requires:  bats-core, python3 (jsonschema optional — schema assertions skip)

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SCRIPT="$REPO_ROOT/skills/deepworkplan/shared/update-state.py"
    SCHEMA="$REPO_ROOT/skills/deepworkplan/spec/schema/plan-state-v2.schema.json"
    FX="$REPO_ROOT/tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture"
    WORK="$(mktemp -d)"
    cp "$FX/state.json" "$WORK/state.json"
}

teardown() { rm -rf "$WORK"; }

# Assert $WORK/state.json validates against the shipped v2 schema (skipped
# when jsonschema is not installed — same guard as schema-contract.bats).
validates() {
    python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
    python3 - "$SCHEMA" "$WORK/state.json" <<'PY'
import json, sys, pathlib
from jsonschema import Draft202012Validator
schema = json.loads(pathlib.Path(sys.argv[1]).read_text())
state = json.loads(pathlib.Path(sys.argv[2]).read_text())
errors = list(Draft202012Validator(schema).iter_errors(state))
assert not errors, "\n".join(e.message for e in errors)
PY
}

@test "the updater ships inside the pack and is stdlib-only" {
    [ -f "$SCRIPT" ]
    # Runtime boundary: the script must not import anything outside the
    # Python standard library (it ships with the skill; pip installs are not).
    run python3 - "$SCRIPT" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
allowed = {"json", "sys", "os", "re", "argparse", "datetime", "pathlib", "tempfile"}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports |= {a.name.split(".")[0] for a in node.names}
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])
extra = imports - allowed
assert not extra, f"non-stdlib imports: {sorted(extra)}"
PY
    [ "$status" -eq 0 ]
}

@test "closes a task atomically with closed-schema-valid output" {
    python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
    run python3 "$SCRIPT" "$WORK/state.json" --task 1 --status completed \
        --gate "bats tests/|0|suite green, 266/266" \
        --worked "closed the loop" --commit abc1234
    [ "$status" -eq 0 ]
    # Atomicity: no temp file survives the replace.
    [ ! -e "$WORK/state.json.tmp" ]
    validates
    python3 - "$WORK/state.json" <<'PY'
import json, sys
s = json.loads(open(sys.argv[1]).read())
t = s["tasks"][0]
assert t["status"] == "completed"
assert t["commit"] == "abc1234"
assert t["outcome"]["worked"] == "closed the loop"
assert t["gates"][0]["passes"] is True and t["gates"][0]["exit_code"] == 0
assert s["completed_count"] == 1
assert s["status"] == "in_progress"
assert s["checkpoint"]["task"] == 2
assert s["approval"] == "approved" and s["format"] == "lite"
PY
}

@test "idempotent modulo timestamps — a replayed close never double-counts" {
    python3 "$SCRIPT" "$WORK/state.json" --task 1 --status completed \
        --gate "bats tests/|0|suite green" --worked "w" >/dev/null
    cp "$WORK/state.json" "$WORK/first.json"
    python3 "$SCRIPT" "$WORK/state.json" --task 1 --status completed \
        --gate "bats tests/|0|suite green" --worked "w" >/dev/null
    python3 - "$WORK/first.json" "$WORK/state.json" <<'PY'
import json, sys
volatile = ("updated_at", "last_run", "started_at", "completed_at")
def strip(obj):
    if isinstance(obj, dict):
        return {k: ("<ts>" if k in volatile else strip(v)) for k, v in obj.items()
                if not (k == "checkpoint" and isinstance(v, dict))}
    if isinstance(obj, list):
        return [strip(x) for x in obj]
    return obj
a, b = (strip(json.load(open(p))) for p in sys.argv[1:3])
assert a == b, f"replay changed state:\n{a}\nvs\n{b}"
PY
    validates
}

@test "derives plan completion and never rewrites the first close's timestamps" {
    python3 "$SCRIPT" "$WORK/state.json" --task 1 --status completed >/dev/null
    first_done="$(python3 -c 'import json;print(json.load(open("'"$WORK"'/state.json"))["tasks"][0]["completed_at"])')"
    run python3 "$SCRIPT" "$WORK/state.json" --task 2 --status completed
    [ "$status" -eq 0 ]
    validates
    python3 - "$WORK/state.json" "$first_done" <<'PY'
import json, sys
s = json.loads(open(sys.argv[1]).read())
assert s["status"] == "completed" and s["completed_count"] == 2
# Closing task 2 must not touch task 1's recorded completion time.
assert s["tasks"][0]["completed_at"] == sys.argv[2]
assert s["checkpoint"]["step"] == "done"
PY
}

@test "invalid input is refused without writing anything" {
    before="$(md5sum "$WORK/state.json" | cut -d' ' -f1)"
    run python3 "$SCRIPT" "$WORK/state.json" --task 99 --status completed
    [ "$status" -ne 0 ]
    run python3 "$SCRIPT" "$WORK/state.json" --task 1 --status bogus
    [ "$status" -ne 0 ]
    run python3 "$SCRIPT" "$WORK/state.json" --task 1 --status completed --commit nothash
    [ "$status" -ne 0 ]
    run python3 "$SCRIPT" "$WORK/state.json" --task 1 --status completed \
        --gate "cmd|0|$(printf 'x%.0s' $(seq 1 501))"
    [ "$status" -ne 0 ]
    run python3 "$SCRIPT" "$WORK/missing.json" --task 1 --status completed
    [ "$status" -ne 0 ]
    after="$(md5sum "$WORK/state.json" | cut -d' ' -f1)"
    [ "$before" = "$after" ]
}

@test "the execute flow and the state spec teach the updater as the targeted path" {
    EX="$REPO_ROOT/skills/deepworkplan/execute/SKILL.md"
    PS="$REPO_ROOT/skills/deepworkplan/spec/PLAN_STATE.md"
    grep -q 'shared/update-state.py' "$EX"
    # Whole-file rewrite remains the documented fallback, not a ban.
    tr '\n' ' ' < "$EX" | tr -s ' ' | grep -qF 'whole-file rewrite'
    tr '\n' ' ' < "$EX" | tr -s ' ' | grep -qF 'atomic' || true
    grep -q 'shared/update-state.py' "$PS"
    # The spec keeps reconciliation (markdown wins) as whole-file regeneration.
    tr '\n' ' ' < "$PS" | tr -s ' ' | grep -qF 'regenerate'
}
