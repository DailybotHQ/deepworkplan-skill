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
    # every verb that names a plan applies the same id guard
    for verb in set-lead set-state; do
        case "$verb" in
            set-lead)  run q set-lead --plan "../PLAN_1_x" --lead local:w1:p1 ;;
            set-state) run q set-state --plan "../PLAN_1_x" --state done ;;
        esac
        [ "$status" -ne 0 ] || return 1
        [[ "$output" == *"not a plan id"* ]] || { echo "$verb: $output"; return 1; }
    done
}

@test "the file is written atomically at 0600, no temp left behind" {
    q append --plan PLAN_1_x >/dev/null
    PERM="$(python3 -c "import os,sys; print(oct(os.stat(sys.argv[1]).st_mode)[-3:])" "$DWP/queue.json")"
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

@test "H1: re-queuing a finished plan is refused (plan ids are one-shot)" {
    q append --plan PLAN_1_x >/dev/null
    q set-state --plan PLAN_1_x --state done >/dev/null
    run q append --plan PLAN_1_x
    [ "$status" -ne 0 ]
    # and the queue still reads valid — never bricked
    q show | grep -q '"state": "done"'
}

@test "M1: the lead must be a protocol pane address, and only with started" {
    q append --plan PLAN_1_x >/dev/null
    run q set-state --plan PLAN_1_x --state started --lead "wP"
    [ "$status" -ne 0 ]
    run q set-state --plan PLAN_1_x --state done --lead local:w1:p2
    [ "$status" -ne 0 ]
    q set-state --plan PLAN_1_x --state started --lead local:wP:p2 >/dev/null
    q show | grep -q '"lead": "local:wP:p2"'
}

@test "review: started needs a lead; a lead cannot start with '-'; the queue's address form is the contract's" {
    q append --plan PLAN_1_x >/dev/null
    run q set-state --plan PLAN_1_x --state started
    [ "$status" -ne 0 ]
    q show | grep -q '"state": "queued"'
    run q set-state --plan PLAN_1_x --state started --lead "-x:w1:p2"
    [ "$status" -ne 0 ]
    python3 - "$REPO_ROOT/skills/deepworkplan/shared" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import contract_v6, queue as Q
assert Q.PANE_ADDRESS.pattern == contract_v6.PANE_ADDRESS.pattern, (Q.PANE_ADDRESS.pattern, contract_v6.PANE_ADDRESS.pattern)
PY
}

@test "review: a hand-edited queue with a bad lead, a lead-less started item or 65 items is not valid" {
    python3 - "$REPO_ROOT/skills/deepworkplan/shared" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import queue as Q
item = lambda p, **kw: dict({'plan': p, 'after': None, 'state': 'queued', 'lead': None, 'start': 'prompt-lead'}, **kw)
doc = lambda items: {'schema': Q.SCHEMA, 'items': items}
assert Q.valid_doc(doc([item('P1', state='started', lead='local:w1:p2')]))
assert not Q.valid_doc(doc([item('P1', lead='-x:w1:p2')])), 'a lead that reads as an option'
assert not Q.valid_doc(doc([item('P1', state='started')])), 'started without its lead'
assert not Q.valid_doc(doc([item('P%d' % i) for i in range(Q.MAX_ITEMS + 1)])), 'above the cap'
assert Q.valid_doc(doc([item('P%d' % i) for i in range(Q.MAX_ITEMS)]))
PY
}

@test "M2: the 65th append is refused (the consumer's cap)" {
    local i
    for i in $(seq 1 64); do q append --plan "PLAN_${i}_x" >/dev/null; done
    run q append --plan PLAN_65_x
    [ "$status" -ne 0 ]
    q show | grep -c '"state": "queued"' | grep -qx 64
}

@test "L1: an item cannot wait for itself or for a plan outside the queue" {
    run q append --plan PLAN_1_x --after PLAN_1_x
    [ "$status" -ne 0 ]
    run q append --plan PLAN_1_x --after PLAN_9_not_here
    [ "$status" -ne 0 ]
}

@test "H2: a symlinked .dwp is refused; a symlinked queue.json is not read" {
    local real linked
    real="$(mktemp -d)"
    linked="$(mktemp -d)/dwp-link"
    ln -s "$real" "$linked"
    run q --dwp "$linked" append --plan PLAN_1_x
    [ "$status" -ne 0 ]
    printf '{"schema":"dwp-queue-v1","items":[]}' > "$real/other.json"
    ln -s "$real/other.json" "$DWP/queue.json"
    run q show
    [ "$status" -eq 1 ]
    rm -f "$DWP/queue.json"
}

@test "the flows write the queue: create appends after approval, execute marks started and done, refine skips" {
    SK="$REPO_ROOT/skills/deepworkplan"
    c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
    c "$SK/create/v6.md" 'python3 ../shared/queue.py --dwp <dwp_dir> append --plan <PLAN_id>'
    c "$SK/create/v6.md" 'Not queuing is the default and always correct.'
    c "$SK/execute/v6.md" '`herdr-peers lead show --plan <PLAN_id> --json`'
    c "$SK/execute/v6.md" '--state started --lead <that address>'
    c "$SK/execute/delegation.md" '1. The contract is v7 or v8 and grants `agent_delegation`.'
    c "$SK/spec/LOOP_ENGINEERING.md" 'marks `done` after the plan'
    c "$SK/execute/v6.md" 'On any task start while `.dwp/queue.json` still lists this plan as `queued`'
    c "$SK/spec/LOOP_ENGINEERING.md" 'execute MUST mark `started` on a task start while the item is still `queued`'
    c "$SK/execute/v6.md" 'On a v7 or v8 plan that grants `agent_delegation`'
    c "$SK/spec/V7_CONTRACT.md" '1. the contract is v7 or later'
    c "$SK/execute/v6.md" 'set-state --plan <PLAN_id> --state done'
    c "$SK/refine/SKILL.md" '--state skipped --note "<one line>"'
    # the commands the flows name are the helper's real CLI
    q append --plan PLAN_1_x >/dev/null
    q set-state --plan PLAN_1_x --state started --lead local:wP:p2 >/dev/null
    q set-state --plan PLAN_1_x --state done >/dev/null
    q append --plan PLAN_2_x >/dev/null
    q set-state --plan PLAN_2_x --state skipped --note "dropped by the developer" >/dev/null
    q show | grep -q '"state": "skipped"'
}

@test "review: an address or plan id with a trailing newline is refused (whole-string match)" {
    python3 - "$REPO_ROOT/skills/deepworkplan/shared" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import queue as Q
item = lambda p, **kw: dict({'plan': p, 'after': None, 'state': 'queued', 'lead': None, 'start': 'prompt-lead'}, **kw)
doc = lambda items: {'schema': Q.SCHEMA, 'items': items}
assert not Q.valid_doc(doc([item('P1', state='started', lead='local:w1:p2\n')])), 'lead with a newline'
assert not Q.valid_doc(doc([item('P1\n')])), 'plan id with a newline'
assert not Q.valid_doc(doc([item('P1', after='P0\n'), item('P0')])), 'after with a newline'
PY
    q append --plan PLAN_1_x >/dev/null
    run q set-state --plan PLAN_1_x --state started --lead $'local:w1\n:p2'
    [ "$status" -ne 0 ]
}

@test "review of 5026f38: autonomy.queue drives the append; started is Herdr-scoped; refine's write scope names the queue" {
    SK="$REPO_ROOT/skills/deepworkplan"
    c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
    c "$SK/create/v6.md" 'or a v8 contract records `autonomy.queue` other than `none`'
    c "$SK/create/v6.md" '[--start prompt-lead|launch]'
    c "$SK/spec/LOOP_ENGINEERING.md" 'Inside Herdr, where the lead'"'"'s pane address exists, execute MUST mark `started`'
    c "$SK/spec/LOOP_ENGINEERING.md" 'outside Herdr the item stays `queued`'
    c "$SK/refine/SKILL.md" 'One write outside the plan folder: a queued plan'"'"'s `skipped` state in `.dwp/queue.json`'
    c "$SK/create/SKILL.md" '(also v7 and v8)'
    # the CLI the create flow names takes --start
    q append --plan PLAN_9_x --start launch >/dev/null
    q show | grep -q '"start": "launch"'
}

@test "review of #97: append records the lead the daemon prompts; a malformed one is refused" {
    q append --plan PLAN_1_x --lead local:wP:p2 >/dev/null
    q show | grep -q '"lead": "local:wP:p2"'
    q show | grep -q '"state": "queued"'
    run q append --plan PLAN_2_x --lead "-x:w1:p2"
    [ "$status" -ne 0 ]
    run q append --plan PLAN_3_x --lead $'local:w1:p2\nx'
    [ "$status" -ne 0 ]
    q append --plan PLAN_4_x >/dev/null
    python3 - "$DWP/queue.json" <<'PY'
import json, sys
items = dict((i['plan'], i) for i in json.load(open(sys.argv[1]))['items'])
assert items['PLAN_4_x']['lead'] is None and 'PLAN_2_x' not in items and 'PLAN_3_x' not in items, items
PY
    SK="$REPO_ROOT/skills/deepworkplan"
    tr '\n' ' ' < "$SK/create/v6.md" | tr -s ' ' | grep -qF -- 'append --plan <PLAN_id> --lead <address>'
    tr '\n' ' ' < "$SK/create/v6.md" | tr -s ' ' | grep -qF -- 'set-lead --plan <PLAN_id> --lead <address>'
    # set-lead names a queued plan's lead later; only a queued one; a malformed address is refused
    q set-lead --plan PLAN_4_x --lead local:wP:p9 >/dev/null
    q show | grep -q '"lead": "local:wP:p9"'
    run q set-lead --plan PLAN_4_x --lead "-x:w1:p2"
    [ "$status" -ne 0 ]
    q set-state --plan PLAN_1_x --state started --lead local:wP:p2 >/dev/null
    run q set-lead --plan PLAN_1_x --lead local:wP:p3
    [ "$status" -ne 0 ]
    run q set-lead --plan PLAN_404_x --lead local:wP:p3
    [ "$status" -ne 0 ]
    # $HERDR_PANE_ID may hold a pane id or a full address: both are accepted, never doubled
    q append --plan PLAN_5_x --lead "wP:p5" >/dev/null
    q append --plan PLAN_6_x --lead " local:wP:p6 " >/dev/null
    run q append --plan PLAN_7_x --lead "local:local:wP:p7"
    [ "$status" -ne 0 ]
    q set-lead --plan PLAN_5_x --lead "wP:p8" >/dev/null
    python3 - "$DWP/queue.json" <<'PY'
import json, sys
items = dict((i['plan'], i) for i in json.load(open(sys.argv[1]))['items'])
assert items['PLAN_5_x']['lead'] == 'local:wP:p8', items['PLAN_5_x']
assert items['PLAN_6_x']['lead'] == 'local:wP:p6', items['PLAN_6_x']
assert 'PLAN_7_x' not in items
PY
    tr '\n' ' ' < "$SK/create/v6.md" | tr -s ' ' | grep -qF -- 'pass `$HERDR_PANE_ID` as it is'
}
