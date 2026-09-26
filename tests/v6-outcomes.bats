#!/usr/bin/env bash
# v6 outcome verification: control pairs, closure discipline, review
# states, reconciled completions and receipts (RFC section 6).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
OUTCOMES="$SK/shared/outcomes.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
TASK='T-publish-schemas'
AC='AC-valid-contract-shape'
AC_PROSE='AC-prose-only-criterion'

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_outcomes_bats"
  mkdir -p "$PLAN"
}

teardown() {
  rm -rf "$TEST_REPO"
  # pack purity: nothing this suite ran may leave bytecode in the pack
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    find "$SK" -name '__pycache__' -o -name '*.pyc'
    return 1
  fi
}

# A scratch git repository with a SEEDED BUG committed: validate() accepts
# anything. A real DWP repository gitignores .dwp/ (repo conformance
# requires it) so the task-start fingerprint stays clean.
_make_repo() {
  git init -q "$TEST_REPO"
  git -C "$TEST_REPO" config user.email t@t.invalid
  git -C "$TEST_REPO" config user.name tester
  printf '.dwp/\n' > "$TEST_REPO/.gitignore"
  mkdir -p "$TEST_REPO/src" "$TEST_REPO/tests"
  printf 'def validate(x):\n    return True\n' > "$TEST_REPO/src/product.py"
  git -C "$TEST_REPO" add -A
  git -C "$TEST_REPO" commit -qm 'seeded bug: validate accepts anything'
  _write_contract
}

_write_contract() {
  PLAN="$PLAN" python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_outcomes_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
doc.pop('contract_id', None)
cid = contract_v6.compute_contract_id(doc)
json.dump(dict(doc, contract_id=cid), open(os.path.join(
    os.environ['PLAN'], 'contract.json'), 'w'), indent=2, sort_keys=True)
PY
}

_approve() {
  run python3 "$LEDGER" --plan "$PLAN" append --type approval --idempotent \
    --actor-kind human --actor-identity tester \
    --json '{"authority": "bats tester", "mechanism": "plan_authorship", "plan_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
  [ "$status" -eq 0 ]
}

_start() {
  run python3 "$LEDGER" --plan "$PLAN" start --task "$TASK" \
    --actor-identity tester
  [ "$status" -eq 0 ]
}

# The fix (working tree) + the discriminating check artifact.
_fix_and_check() {
  printf 'def validate(x):\n    return x != "BAD"\n' > "$TEST_REPO/src/product.py"
  cat > "$TEST_REPO/tests/check_seeded.py" <<'PY'
import sys
sys.path.insert(0, 'src')
from product import validate
sys.exit(0 if validate('BAD') is False else 1)
PY
}

_closure_field() { # _closure_field CRITERION KEY -> printed value
  python3 - "$PLAN" "$1" "$2" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import outcomes, ledger
rec = ledger.PlanRecords(sys.argv[1])
events, _t, _f = rec.read_journal()
result = outcomes.closure(rec.contract, rec.archived_events() + events)
for crit in result['criteria']:
    if crit['criterion'] == sys.argv[2]:
        print(crit.get(sys.argv[3]))
        break
PY
}

_plan_blocked() {
  python3 - "$PLAN" <<'PY'
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import outcomes, ledger
rec = ledger.PlanRecords(sys.argv[1])
events, _t, _f = rec.read_journal()
result = outcomes.closure(rec.contract, rec.archived_events() + events)
print('true' if result['plan_blocked'] else 'false')
PY
}

@test "outcomes self-test passes" {
  run python3 "$OUTCOMES" self-test
  [ "$status" -eq 0 ]
  grep -q 'self-test: OK' <<<"$output"
}

@test "start records the task's starting fingerprint (clean git host)" {
  _make_repo
  _approve
  _start
  grep -q 'starting fingerprint' <<<"$output"
  grep -qv 'none' <<<"$(grep -o 'fingerprint [0-9a-f]*' <<<"$output")"
  # and the raw append path records none - controls stay honest
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'task_start' <<<"$output"
}

@test "a clean control passes: (old FAIL, new PASS) closes the criterion" {
  _make_repo
  _approve
  _start
  _fix_and_check
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
  [ "$status" -eq 0 ]
  grep -q 'verdict discriminating' <<<"$output"
  run _closure_field "$AC" satisfied
  [ "$output" = "True" ]
  run _closure_field "$AC" mechanism
  [ "$output" = "control_pair" ]
}

@test "a seeded bug passing superficial checks is rejected: (PASS, PASS) never closes" {
  _make_repo
  _approve
  _start
  # a tautological check that always exits 0 - superficially green on
  # BOTH legs, so it discriminates nothing
  printf 'import sys\nsys.exit(0)\n' > "$TEST_REPO/tests/weak_check.py"
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/weak_check.py' \
    --artifact tests/weak_check.py
  [ "$status" -eq 0 ]
  grep -q 'verdict non_discriminating' <<<"$output"
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
  run _closure_field "$AC" mechanism
  grep -q 'did not discriminate' <<<"$output"
}

@test "an asserted control pair is a claim, never behavior" {
  _make_repo
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" append --type control_pair \
    --actor-identity tester --json "$(cat <<'JSON'
{"criterion": "AC-valid-contract-shape", "check_artifacts": ["tests/x.py"],
 "starting_fingerprint": {"revision": "r0", "dirty": ""},
 "old_leg": {"available": true, "outcome": "FAIL", "log": "l"},
 "new_leg": {"outcome": "PASS", "log": "l2"},
 "verdict": "discriminating", "trust": "asserted"}
JSON
)"
  [ "$status" -eq 0 ]
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
  run _closure_field "$AC" mechanism
  grep -q 'asserted, not executed' <<<"$output"
}

@test "a restart reopens the control window: pre-restart pairs go stale" {
  _make_repo
  _approve
  _start
  _fix_and_check
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
  [ "$status" -eq 0 ]
  run _closure_field "$AC" satisfied
  [ "$output" = "True" ]
  # a restart is a new attempt: the pair recorded before it is stale
  _start
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
  run _closure_field "$AC" mechanism
  grep -q 'no in-window control pair' <<<"$output"
}

@test "a dirty STARTING fingerprint makes the control unavailable and blocks" {
  _make_repo
  _approve
  # user dirty state BEFORE the attempt starts (never reverted, row 16)
  printf 'scratch\n' > "$TEST_REPO/src/dirty_user_file.txt"
  _start
  _fix_and_check
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
  [ "$status" -eq 0 ]
  grep -q 'verdict control_unavailable' <<<"$output"
  grep -q 'D3-3' <<<"$output"
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
  run _closure_field "$AC" mechanism
  grep -q 'blocked (control unavailable' <<<"$output"
  run _plan_blocked
  [ "$output" = "true" ]
}

@test "a non-git host records control=unavailable, never a synthesized old leg" {
  # no git init: the plan lives in a plain directory
  _write_contract
  _approve
  _start
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'true' --artifact anything.txt
  [ "$status" -eq 0 ]
  grep -q 'verdict control_unavailable' <<<"$output"
  grep -q 'non-git host' <<<"$output"
}

@test "exempt criteria refuse control pairs and close on ordinary evidence only" {
  _make_repo
  # the task's OWN criterion, but declared exempt (prose-only surface)
  PLAN="$PLAN" python3 - <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
path = os.path.join(os.environ['PLAN'], 'contract.json')
doc = json.load(open(path))
doc['acceptance']['criteria'][0]['control'] = {
    'kind': 'exempt', 'rationale': 'prose-only surface for the refusal probe'}
doc.pop('contract_id', None)
json.dump(dict(doc, contract_id=contract_v6.compute_contract_id(doc)),
          open(path, 'w'), indent=2, sort_keys=True)
PY
  _approve
  _start
  _fix_and_check
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
  [ "$status" -eq 1 ]
  grep -q 'exempt/undeclared criteria close on ordinary accepted evidence' \
    <<<"$output"
  # and with no accepted evidence at all, the criterion stays open
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
}

@test "a control on a criterion outside the task's gate intent is refused" {
  _make_repo
  _approve
  _start
  _fix_and_check
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion AC-journal-catalog-closed \
    --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
  [ "$status" -eq 1 ]
  grep -q 'not declared in task' <<<"$output"
}

@test "an exhausted control timeout is a recorded failure, never a weakened pass" {
  _make_repo
  _approve
  _start
  printf 'import time\ntime.sleep(30)\n' > "$TEST_REPO/tests/slow_check.py"
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/slow_check.py' \
    --artifact tests/slow_check.py --timeout 2
  [ "$status" -eq 0 ]
  grep -q 'verdict non_discriminating' <<<"$output"
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
  # the timeout exit is visible in the leg log, not swallowed
  grep -rq -- 'exit 124' "$PLAN/gates/$TASK/"*-control-*-new.log
}

@test "review states: clean satisfies nothing, critical blocks the plan" {
  _make_repo
  _approve
  _start
  run python3 "$OUTCOMES" --plan "$PLAN" review --state clean
  [ "$status" -eq 0 ]
  run _closure_field "$AC" satisfied
  [ "$output" = "False" ]
  run _plan_blocked
  [ "$output" = "false" ]
  run python3 "$OUTCOMES" --plan "$PLAN" review --state critical \
    --finding 'seeded defect survives the diff'
  [ "$status" -eq 0 ]
  run _plan_blocked
  [ "$output" = "true" ]
}

@test "review states outside the closed set are refused" {
  _make_repo
  _approve
  run python3 "$OUTCOMES" --plan "$PLAN" review --state pristine
  [ "$status" -eq 1 ]
  grep -q 'outside the closed set' <<<"$output"
}

@test "reconciliation without amendment authority blocks; with it, closes reconciled" {
  _make_repo
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" append --type reconciliation \
    --actor-kind human --actor-identity operator \
    --json '{"trigger": "generated-view divergence for AC-prose-only-criterion", "editor": "human edit of views/tasks.md", "authority": "operator A"}'
  [ "$status" -eq 0 ]
  run _closure_field "$AC_PROSE" mechanism
  grep -q 'blocked (reconciliation without amendment authority' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" append --type amendment \
    --actor-kind human --actor-identity operator \
    --json "$(cat <<'JSON'
{"original_criterion": "AC-prose-only-criterion: prose criteria may declare no control",
 "observed_finding": "wording drifted from the shipped anatomy",
 "disposition": "revised",
 "revised_criterion": "AC-prose-only-criterion: prose criteria may declare no control (v6 wording)",
 "reason": "v6 contract vocabulary", "authority": "operator A",
 "affected_tasks": [], "evidence_invalidated": [], "evidence_preserved": []}
JSON
)"
  [ "$status" -eq 0 ]
  run _closure_field "$AC_PROSE" satisfied
  [ "$output" = "True" ]
  run _closure_field "$AC_PROSE" mechanism
  [ "$output" = "reconciled" ]
}

@test "the receipt recomputes from records and changes when they change" {
  _make_repo
  _approve
  _start
  _fix_and_check
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
  [ "$status" -eq 0 ]
  local first second
  first="$(python3 "$OUTCOMES" --plan "$PLAN" receipt | grep -o 'sha256 [0-9a-f]*')"
  second="$(python3 "$OUTCOMES" --plan "$PLAN" receipt | grep -o 'sha256 [0-9a-f]*')"
  [ "$first" = "$second" ]
  run python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --actor-identity tester --json '{"statement": "receipt probe", "trust": "asserted"}'
  [ "$status" -eq 0 ]
  local third
  third="$(python3 "$OUTCOMES" --plan "$PLAN" receipt | grep -o 'sha256 [0-9a-f]*')"
  [ "$first" != "$third" ]
}

@test "fresh evaluator support falls back honestly and is never independence evidence" {
  _make_repo
  _approve
  _start
  local out="$PLAN/receipt-fresh.json"
  DWP_FRESH_EVALUATOR= run python3 "$OUTCOMES" --plan "$PLAN" receipt \
    --evaluator fresh --out "$out"
  [ "$status" -eq 0 ]
  grep -q '"used": "local"' "$out"
  grep -q 'never claimed as fresh' "$out"
  grep -q 'never as independence evidence' "$out"
  DWP_FRESH_EVALUATOR=1 run python3 "$OUTCOMES" --plan "$PLAN" receipt \
    --evaluator fresh
  [ "$status" -eq 0 ]
}

@test "closure --task filters to the named task's criteria" {
  _make_repo
  _approve
  _start
  run python3 "$OUTCOMES" --plan "$PLAN" closure --task "$TASK"
  [ "$status" -eq 0 ]
  grep -q '"AC-valid-contract-shape"' <<<"$output"
  ! grep -q '"AC-journal-catalog-closed"' <<<"$output"
}
