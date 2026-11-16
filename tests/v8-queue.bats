#!/usr/bin/env bats
# The plan queue (dwp-queue-v1, skills/deepworkplan/shared/queue.py): the
# pack is the only writer, the document is closed and bounded, the write is
# atomic at 0600, and a damaged queue never breaks the lifecycle.

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    QUEUE="$REPO_ROOT/skills/deepworkplan/shared/queue.py"
    [ -f "$QUEUE" ]
    export PYTHONDONTWRITEBYTECODE=1
    DWP="$(mktemp -d)"
}

teardown() {
    rm -rf "$DWP"
}

q() { python3 "$QUEUE" --dwp "$DWP" "$@"; }

@test "append creates the queue and show returns a valid closed document" {
    q append --plan PLAN_1_x >/dev/null
    q show > "$DWP/out.json"
    python3 - "$DWP/out.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["schema"] == "dwp-queue-v1", d
assert d["items"][0]["plan"] == "PLAN_1_x"
assert d["items"][0]["state"] == "queued"
assert d["items"][0]["start"] == "prompt-lead"
assert d["items"][0]["after"] is None and d["items"][0]["lead"] is None
PY
}

@test "append with --after records the dependency" {
    q append --plan PLAN_1_x >/dev/null
    q append --plan PLAN_2_y --after PLAN_1_x --start launch >/dev/null
    q show | grep -q '"after": "PLAN_1_x"'
    q show | grep -q '"start": "launch"'
}

@test "a duplicate open plan is refused" {
    q append --plan PLAN_1_x >/dev/null
    run q append --plan PLAN_1_x
    [ "$status" -ne 0 ]
}

@test "the lifecycle: queued -> started (with the lead) -> done" {
    q append --plan PLAN_1_x >/dev/null
    q set-state --plan PLAN_1_x --state started --lead local:w1:p2 >/dev/null
    q show | grep -q '"state": "started"'
    q show | grep -q '"lead": "local:w1:p2"'
    q set-state --plan PLAN_1_x --state done >/dev/null
    q show | grep -q '"state": "done"'
}

@test "skipping needs a note, and the note is kept" {
    q append --plan PLAN_1_x >/dev/null
    run q set-state --plan PLAN_1_x --state skipped
    [ "$status" -ne 0 ]
    q set-state --plan PLAN_1_x --state skipped --note "superseded by PLAN_9_z" >/dev/null
    q show | grep -q '"note": "superseded by PLAN_9_z"'
}

@test "done is terminal and started only comes from queued" {
    q append --plan PLAN_1_x >/dev/null
    q set-state --plan PLAN_1_x --state started --lead local:w1:p2 >/dev/null
    q set-state --plan PLAN_1_x --state done >/dev/null
    run q set-state --plan PLAN_1_x --state started --lead local:w1:p2
    [ "$status" -ne 0 ]
}

@test "a missing plan and a bad id are refused" {
    q append --plan PLAN_1_x >/dev/null
    run q set-state --plan PLAN_9_nothing --state done
    [ "$status" -ne 0 ]
    run q append --plan "not a plan id"
    [ "$status" -ne 0 ]
}

@test "the file is written atomically at 0600, no temp left behind" {
    q append --plan PLAN_1_x >/dev/null
    PERM="$(stat -f '%Lp' "$DWP/queue.json" 2>/dev/null || stat -c '%a' "$DWP/queue.json")"
    [ "$PERM" = "600" ]
    ls "$DWP" | grep -c "^\.queue\..*\.tmp$" | grep -qx "0"
}

@test "a damaged queue is a quiet none: show warns, append refuses to touch it" {
    printf 'not json at all' > "$DWP/queue.json"
    run q show
    [ "$status" -eq 1 ]
    run q append --plan PLAN_1_x
    [ "$status" -ne 0 ]
    [ "$(cat "$DWP/queue.json")" = "not json at all" ]
}

@test "an oversized queue is a quiet none (bounded read, like every daemon input)" {
    head -c 70000 /dev/zero | tr '\0' 'x' > "$DWP/queue.json"
    run q show
    [ "$status" -eq 1 ]
}

@test "an unknown top-level key makes the document unusable (closed schema)" {
    q append --plan PLAN_1_x >/dev/null
    python3 - "$DWP/queue.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["surprise"] = True
json.dump(d, open(p, "w"))
PY
    run q show
    [ "$status" -eq 1 ]
}
