#!/usr/bin/env bash
# Structured blockers (spec/LOOP_ENGINEERING.md section 3): a v8 plan records
# its blocker through the ledger's block/unblock helper as journal-event/v8
# `blocker` events, and projects it into plan-snapshot/v8 as
# blocker = {task, reason, since, needs, class, resolver?} - the shape the
# herdr-peers fleet and brain read. v6/v7 plans keep their records.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
HEADER="$SK/shared/progress_header.py"
VERIFY="$SK/verify/plan_contract.py"
FIX="$REPO_ROOT/tests/fixtures/v7/contract-minimal-v7.json"
READER_FIX="$REPO_ROOT/tests/fixtures/v8/state-blocked-v8.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  REPO="$WORK/repo"
  mkdir -p "$REPO/src"
  git -C "$REPO" init -q
  printf '.dwp/\n' > "$REPO/.gitignore"
  printf 'x = 1\n' > "$REPO/src/product.py"
  git -C "$REPO" add -A && git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init
}

teardown() {
  rm -rf "$WORK"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    return 1
  fi
}

# _plan NAME GENERATION -> materializes a plan of that contract generation.
_plan() {
  PLAN="$REPO/.dwp/plans/$1"
  mkdir -p "$PLAN/analysis_results"
  printf '# Goal\n\nblockers.\n' > "$PLAN/README.md"
  python3 - "$FIX" "$PLAN/draft.json" "$1" "$2" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['plan'] = sys.argv[3]
doc['schema'] = 'https://deepworkplan.com/schema/plan-contract/%s.json' % sys.argv[4]
doc['invariants'] = []
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
    t['prerequisites'] = []
    for g in t['gate_intent']:
        g['check'] = 'python3 -c pass'
for c in doc['acceptance']['criteria']:
    c.pop('control', None)
    c['accepted_evidence'] = ['observed']
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
  run python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" --authority bats --mechanism plan_authorship
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  T1="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tasks"][0]["id"])' "$PLAN/contract.json")"
  AC1="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tasks"][0]["gate_intent"][0]["criterion"])' "$PLAN/contract.json")"
  T2="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tasks"][1]["id"])' "$PLAN/contract.json")"
}

_block() { # _block TASK JSON
  run python3 "$LEDGER" --plan "$PLAN" block --task "$1" --json "$2"
}

_snap() { # _snap PYTHON-EXPRESSION over `s` (the state.json document)
  python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(json.dumps(eval(sys.argv[2])))' "$PLAN/state.json" "$1"
}

@test "a v8 plan records its blocker under journal-event/v8 and projects it into plan-snapshot/v8" {
  _plan PLAN_v8_blockers v8
  grep -q '"schema":"https://deepworkplan.com/schema/journal-event/v8.json"' "$PLAN/journal.ndjson"
  python3 "$LEDGER" --plan "$PLAN" start --task "$T1" >/dev/null
  _block "$T1" '{"reason": "the fixture service is down", "needs": "restart the fixture service", "class": "C3", "resolver": "lead"}'
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"blocked at seq"*"C3, resolver lead"* ]]
  [ "$(_snap 's["schema"]')" = '"https://deepworkplan.com/schema/plan-snapshot/v8.json"' ]
  [ "$(_snap 's["generated_by"]')" = '"dwp-ledger/8.0"' ]
  [ "$(_snap 'sorted(s["blocker"])')" = '["class", "needs", "reason", "resolver", "since", "task"]' ]
  [ "$(_snap '[s["blocker"][k] for k in ("task", "class", "resolver", "needs")]')" = \
    "[\"$T1\", \"C3\", \"lead\", \"restart the fixture service\"]" ]
  [ "$(_snap '[t["status"] for t in s["tasks"]][0]')" = '"blocked"' ]
  # the verifier accepts the projection and names the blocker
  run python3 "$VERIFY" "$PLAN"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"state.json agrees with the journal"* ]]
  [[ "$output" == *"blocked: $T1 (C3, resolver lead)"* ]]
}

@test "the projected snapshot and the blocker events validate under the published v8 schemas" {
  python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
  _plan PLAN_v8_schemas v8
  _block "$T1" '{"reason": "needs a login", "needs": "log in to the registry", "class": "C2"}'
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  python3 - "$SK/spec/schema" "$PLAN" <<'PY'
import json, os, sys
import jsonschema
d, plan = sys.argv[1], sys.argv[2]
snap = json.load(open(os.path.join(d, 'plan-snapshot-v8.schema.json')))
jour = json.load(open(os.path.join(d, 'journal-event-v8.schema.json')))
state = json.load(open(os.path.join(plan, 'state.json')))
jsonschema.Draft202012Validator(snap).validate(state)
for line in open(os.path.join(plan, 'journal.ndjson')):
    if line.strip():
        jsonschema.Draft202012Validator(jour).validate(json.loads(line))
# the schema half refuses what the runtime refuses
bad = dict(state['blocker'], resolver='lead')            # lead on C2
assert list(jsonschema.Draft202012Validator(snap).iter_errors(dict(state, blocker=bad)))
event = [json.loads(l) for l in open(os.path.join(plan, 'journal.ndjson')) if '"blocker"' in l][-1]
for mutant in (dict(event, needs='a\nb'), dict(event, resolver='lead'),
               {k: v for k, v in event.items() if k != 'class'},
               dict(event, action='resolved')):
    assert list(jsonschema.Draft202012Validator(jour).iter_errors(mutant)), mutant
PY
}

@test "lead is refused for C1, C2, C5 and C6; accepted for C3, C4 and C7; absent resolver means human" {
  _plan PLAN_v8_resolver v8
  for klass in C1 C2 C5 C6; do
    _block "$T1" "{\"reason\": \"r\", \"needs\": \"n\", \"class\": \"$klass\", \"resolver\": \"lead\"}"
    [ "$status" -eq 5 ] || { echo "$klass: $output"; return 1; }
    [[ "$output" == *"lead is refused for $klass"* ]]
  done
  # every refusal is recorded
  [ "$(grep -c '"type":"refusal"' "$PLAN/journal.ndjson")" -eq 4 ]
  for klass in C3 C4 C7; do
    _block "$T1" "{\"reason\": \"r\", \"needs\": \"n\", \"class\": \"$klass\", \"resolver\": \"lead\"}"
    [ "$status" -eq 0 ] || { echo "$klass: $output"; return 1; }
  done
  _block "$T1" '{"reason": "r", "needs": "approve the release", "class": "C1"}'
  [ "$status" -eq 0 ]
  [[ "$output" == *"resolver human"* ]]
  [ "$(_snap '"resolver" in s["blocker"]')" = 'false' ]
}

@test "needs is one line, class is required, and unknown fields are refused" {
  _plan PLAN_v8_shape v8
  _block "$T1" '{"reason": "r", "needs": "one\ntwo", "class": "C3"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"needs: expected one non-empty line"* ]]
  _block "$T1" '{"reason": "r", "needs": "n"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"class: expected one of C1/C2/C3/C4/C5/C6/C7"* ]]
  _block "$T1" '{"reason": "r", "needs": "n", "class": "C3", "owner": "me"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"unknown blocker field(s): owner"* ]]
  _block "$T1" '{"reason": " ", "needs": "n", "class": "C3"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"reason: expected a non-empty string"* ]]
}

@test "an unresolved raise keeps its task from completing; unblock lets it complete" {
  _plan PLAN_v8_complete v8
  python3 "$LEDGER" --plan "$PLAN" start --task "$T1" --actor-identity tester >/dev/null
  _block "$T1" '{"reason": "review pending", "needs": "the reviewer answers", "class": "C3", "resolver": "lead"}'
  [ "$status" -eq 0 ]
  # evidence that lands while the blocker is open does not close the task
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$T1" --criterion "$AC1" --json '"python3 -c pass"'
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" complete --task "$T1"
  [ "$status" -eq 4 ]
  [[ "$output" == *"an unresolved blocker holds it"* ]]
  [ "$(_snap '[t["status"] for t in s["tasks"]][0]')" = '"blocked"' ]
  run python3 "$LEDGER" --plan "$PLAN" unblock --task "$T1" --note "the reviewer answered"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [ "$(_snap 's["blocker"]')" = 'null' ]
  run python3 "$LEDGER" --plan "$PLAN" complete --task "$T1"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  # a task its evidence already closed cannot be blocked afterwards
  _block "$T1" '{"reason": "late", "needs": "n", "class": "C3"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"the task is already complete"* ]]
}

@test "one active blocker per plan; a re-raise keeps since; unblock needs a blocker; no raw append" {
  _plan PLAN_v8_single v8
  _block "$T1" '{"reason": "first", "needs": "n1", "class": "C3"}'
  [ "$status" -eq 0 ]
  since="$(_snap 's["blocker"]["since"]')"
  _block "$T2" '{"reason": "second", "needs": "n2", "class": "C3"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"already blocked on $T1"* ]]
  sleep 1
  _block "$T1" '{"reason": "first, updated", "needs": "n1b", "class": "C4", "resolver": "lead"}'
  [ "$status" -eq 0 ]
  [ "$(_snap 's["blocker"]["since"]')" = "$since" ]
  [ "$(_snap 's["blocker"]["needs"]')" = '"n1b"' ]
  run python3 "$LEDGER" --plan "$PLAN" unblock --task "$T2"
  [ "$status" -eq 5 ]; [[ "$output" == *"no unresolved blocker holds this task"* ]]
  run python3 "$LEDGER" --plan "$PLAN" append --type blocker --json "{\"task\": \"$T1\", \"action\": \"resolved\"}"
  [ "$status" -ne 0 ]; [[ "$output" == *"produced only by \`ledger.py block\`"* ]]
}

@test "v7 plans are unaffected: no blocker events, plan-snapshot/v6, journal-event/v7" {
  _plan PLAN_v7_untouched v7
  _block "$T1" '{"reason": "r", "needs": "n", "class": "C3"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"this plan is v7"* ]]
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  [ "$(_snap 's["schema"]')" = '"https://deepworkplan.com/schema/plan-snapshot/v6.json"' ]
  [ "$(_snap 's["blocker"]')" = 'null' ]
  [ "$(_snap 's["generated_by"]')" = '"dwp-ledger/7.0"' ]
  ! grep -q 'journal-event/v8' "$PLAN/journal.ndjson"
  ! grep -q '"type":"blocker"' "$PLAN/journal.ndjson"
}

@test "a v8 journal is held to its generation: a v7-URL event in a v8 plan is refused" {
  _plan PLAN_v8_mixed v8
  python3 - "$PLAN/journal.ndjson" <<'PY'
import json, sys
lines = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
extra = dict(lines[-1], seq=lines[-1]['seq'] + 1,
             schema='https://deepworkplan.com/schema/journal-event/v7.json')
with open(sys.argv[1], 'a') as fh:
    fh.write(json.dumps(extra, sort_keys=True, separators=(',', ':')) + '\n')
PY
  run python3 "$VERIFY" "$PLAN"
  [ "$status" -ne 0 ]
  [[ "$output" == *"mixed-era records are refused"* ]]
}

@test "herdr-peers reader shape: the projected blocker reads as the fleet and brain expect" {
  # The consumer contract (herdr-peers 2.0.2 fleet_report.plan_detail and
  # classify, brain.blocker_is_askable), restated: state['blocked'] if present
  # else state['blocker']; a dict whose reason/needs are strings; resolver in
  # (lead, human) or absent; a C1..C7 class findable in class/needs/reason.
  _plan PLAN_v8_reader v8
  _block "$T1" '{"reason": "the fixture service is down", "needs": "restart the fixture service", "class": "C3", "resolver": "lead"}'
  [ "$status" -eq 0 ]
  for doc in "$PLAN/state.json" "$READER_FIX"; do
    python3 - "$doc" <<'PY'
import json, re, sys
state = json.load(open(sys.argv[1]))
blocker = state.get('blocked') if 'blocked' in state else state.get('blocker')
assert isinstance(blocker, dict), blocker
assert isinstance(blocker.get('reason'), str) and isinstance(blocker.get('needs'), str)
assert blocker.get('resolver') in ('lead', 'human', None)
text = ' '.join(str(blocker.get(k) or '') for k in ('class', 'needs', 'reason'))
assert re.search(r'\bC[1-7]\b', text), text
assert blocker.get('resolver') == 'lead'          # askable by the brain
assert 'blocked' in [t.get('status') for t in state['tasks']]
PY
  done
  # the committed fixture is what the ledger projects (same keys, same generation)
  [ "$(python3 -c 'import json,sys; print(sorted(json.load(open(sys.argv[1]))["blocker"]))' "$READER_FIX")" = \
    "$(python3 -c 'import json,sys; print(sorted(json.load(open(sys.argv[1]))["blocker"]))' "$PLAN/state.json")" ]
  grep -q '"schema": "https://deepworkplan.com/schema/plan-snapshot/v8.json"' "$READER_FIX"
}

@test "PROGRESS.md header: written at create, refreshed on every transition, the body untouched" {
  _plan PLAN_v8_header v8
  printf '# PLAN_v8_header - progress\n\n## Active context\n\nnotes the agents keep.\n' > "$PLAN/PROGRESS.md"
  run python3 "$HEADER" --plan "$PLAN" --goal "ship the blockers" --next "start $T1"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [ "$(sed -n 3,6p "$PLAN/PROGRESS.md")" = "Goal: ship the blockers
Current task: $T1 - $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tasks"][0]["title"])' "$PLAN/contract.json") (pending)
Next action: start $T1
Needs: none" ]
  grep -q '^notes the agents keep\.$' "$PLAN/PROGRESS.md"
  python3 "$LEDGER" --plan "$PLAN" start --task "$T1" >/dev/null
  _block "$T1" '{"reason": "r", "needs": "restart the fixture service", "class": "C3", "resolver": "lead"}'
  # stale until refreshed; --check says so and writes nothing
  run python3 "$HEADER" --plan "$PLAN" --check
  [ "$status" -eq 1 ]
  run python3 "$HEADER" --plan "$PLAN" --next "wait for the lead to restart the service"
  [ "$status" -eq 0 ]
  grep -q '^Goal: ship the blockers$' "$PLAN/PROGRESS.md"
  grep -q "^Current task: $T1 - .* (blocked)\$" "$PLAN/PROGRESS.md"
  grep -q '^Needs: C3 (lead): restart the fixture service$' "$PLAN/PROGRESS.md"
  python3 "$LEDGER" --plan "$PLAN" unblock --task "$T1" >/dev/null
  run python3 "$HEADER" --plan "$PLAN" --next "run the gate"
  [ "$status" -eq 0 ]
  grep -q '^Needs: none$' "$PLAN/PROGRESS.md"
  [ "$(grep -c '^Goal: ' "$PLAN/PROGRESS.md")" -eq 1 ]
  grep -q '^## Active context$' "$PLAN/PROGRESS.md"
  run python3 "$HEADER" --plan "$PLAN" --check
  [ "$status" -eq 0 ]
  # a header needs a goal; v7 plans keep their PROGRESS.md
  rm "$PLAN/PROGRESS.md"
  run python3 "$HEADER" --plan "$PLAN" --next "x"
  [ "$status" -eq 1 ]; [[ "$output" == *"Goal (--goal) must be a non-empty line"* ]]
  _plan PLAN_v7_header v7
  run python3 "$HEADER" --plan "$PLAN" --goal g --next n
  [ "$status" -eq 1 ]; [[ "$output" == *"this plan is v7"* ]]
}
