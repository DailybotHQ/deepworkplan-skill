#!/usr/bin/env bash
# §5.1.4 made visible without blocking (ADR 0006): completing a task whose
# gate-closed criterion declares no control warns once and records an
# observation the compliance audit can count. A decided control (including
# exempt with a rationale) is not the finding. Completion never refuses.
bats_require_minimum_version 1.5.0
REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_warn_bats"
  mkdir -p "$PLAN"
  git init -q "$TEST_REPO"
  git -C "$TEST_REPO" config user.email t@t.invalid
  git -C "$TEST_REPO" config user.name tester
  printf '.dwp/\n' > "$TEST_REPO/.gitignore"
  git -C "$TEST_REPO" add -A
  git -C "$TEST_REPO" commit -qm init
  PLAN="$PLAN" python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_warn_bats'
doc['scope']['allowed_command_classes'] = ['python3']
doc['invariants'] = []  # this suite is about controls, not invariants
doc['acceptance']['criteria'] = [
    {'id': 'AC-plain', 'statement': 'A gate-closed criterion with no control.',
     'observable_check': 'python3 -c pass', 'accepted_evidence': ['observed']},
    {'id': 'AC-exempt', 'statement': 'A prose criterion, exempt by decision.',
     'observable_check': 'python3 -c pass', 'accepted_evidence': ['observed'],
     'control': {'kind': 'exempt', 'rationale': 'cosmetic wording only'}}]
doc['tasks'] = [
    {'id': 'T-plain', 'title': 'Plain', 'prerequisites': [], 'touched_surface': ['a.txt'],
     'gate_intent': [{'criterion': 'AC-plain', 'check': 'python3 -c pass'}]},
    {'id': 'T-exempt', 'title': 'Exempt', 'prerequisites': [], 'touched_surface': ['b.txt'],
     'gate_intent': [{'criterion': 'AC-exempt', 'check': 'python3 -c pass'}]}]
doc.pop('contract_id', None)
cid = contract_v6.compute_contract_id(doc)
json.dump(dict(doc, contract_id=cid), open(os.path.join(
    os.environ['PLAN'], 'contract.json'), 'w'), indent=2, sort_keys=True)
PY
  run python3 "$LEDGER" --plan "$PLAN" append --type approval --idempotent \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity tester \
    --json '{"authority": "bats tester", "mechanism": "plan_authorship", "plan_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
  [ "$status" -eq 0 ]
}

teardown() {
  rm -rf "$TEST_REPO"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    return 1
  fi
}

_close() { # _close TASK CRITERION
  run python3 "$LEDGER" --plan "$PLAN" start --task "$1" --actor-identity tester
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$1" --criterion "$2" \
    --json '"python3 -c pass"'
  [ "$status" -eq 0 ]
}

_missing_observations() {
  grep -c 'control missing: AC-' "$PLAN/journal.ndjson" || true
}

@test "an undecided control warns at completion and completion still succeeds" {
  _close T-plain AC-plain
  run --separate-stderr python3 "$LEDGER" --plan "$PLAN" complete --task T-plain
  [ "$status" -eq 0 ]
  grep -q '§5.1.4 control missing: AC-plain' <<<"$stderr"
  [ "$(_missing_observations)" -eq 1 ]
}

@test "the finding is recorded once per attempt, not on every completion call" {
  _close T-plain AC-plain
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-plain
  [ "$status" -eq 0 ]
  run --separate-stderr python3 "$LEDGER" --plan "$PLAN" complete --task T-plain
  [ "$status" -eq 0 ]
  run grep -q '§5.1.4' <<<"$stderr"
  [ "$status" -ne 0 ]
  [ "$(_missing_observations)" -eq 1 ]
}

@test "an exempt control is a decision, not the finding" {
  _close T-exempt AC-exempt
  run --separate-stderr python3 "$LEDGER" --plan "$PLAN" complete --task T-exempt
  [ "$status" -eq 0 ]
  run grep -q '§5.1.4' <<<"$stderr"
  [ "$status" -ne 0 ]
  [ "$(_missing_observations)" -eq 0 ]
}

@test "the journal with the warning still validates" {
  _close T-plain AC-plain
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-plain
  [ "$status" -eq 0 ]
  run python3 "$SK/shared/contract_v6.py" validate-journal "$PLAN/journal.ndjson"
  [ "$status" -eq 0 ]
}
