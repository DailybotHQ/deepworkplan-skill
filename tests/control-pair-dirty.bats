#!/usr/bin/env bash
# Dirty-start controls (ADR 0006, the non-breaking repair of the defect the
# 2026 debate found: every live control pair was control_unavailable because
# each attempt started on a dirty tree). D3-3 itself is unchanged; the ledger
# now warns at task start, and the unavailable verdict names the recovery.
bats_require_minimum_version 1.5.0
REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
OUTCOMES="$SK/shared/outcomes.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
TASK='T-publish-schemas'
AC='AC-valid-contract-shape'
export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_dirty_bats"
  mkdir -p "$PLAN"
  git init -q "$TEST_REPO"
  git -C "$TEST_REPO" config user.email t@t.invalid
  git -C "$TEST_REPO" config user.name tester
  printf '.dwp/\n' > "$TEST_REPO/.gitignore"
  mkdir -p "$TEST_REPO/src" "$TEST_REPO/tests"
  printf 'def validate(x):\n    return True\n' > "$TEST_REPO/src/product.py"
  git -C "$TEST_REPO" add -A
  git -C "$TEST_REPO" commit -qm 'seeded bug'
  PLAN="$PLAN" python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_dirty_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
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

_fix_and_check() {
  printf 'def validate(x):\n    return x != "BAD"\n' > "$TEST_REPO/src/product.py"
  cat > "$TEST_REPO/tests/check_seeded.py" <<'PY'
import sys
sys.path.insert(0, 'src')
from product import validate
sys.exit(0 if validate('BAD') is False else 1)
PY
}

_control() {
  run python3 "$OUTCOMES" --plan "$PLAN" control --task "$TASK" \
    --criterion "$AC" --command 'python3 tests/check_seeded.py' \
    --artifact tests/check_seeded.py
}

@test "a clean start on a controlled task prints no dirty-start warning" {
  run --separate-stderr python3 "$LEDGER" --plan "$PLAN" start --task "$TASK" --actor-identity tester
  [ "$status" -eq 0 ]
  ! grep -q 'dirty working tree' <<<"$stderr"
}

@test "a dirty start on a controlled task warns before any control runs" {
  printf 'scratch\n' > "$TEST_REPO/notes.txt"
  run --separate-stderr python3 "$LEDGER" --plan "$PLAN" start --task "$TASK" --actor-identity tester
  [ "$status" -eq 0 ]
  grep -q 'dirty working tree' <<<"$stderr"
  grep -q "$AC" <<<"$stderr"
  grep -q 'Commit the work in progress before starting' <<<"$stderr"
}

@test "an unavailable dirty-start control names the recovery and stays unavailable" {
  printf 'scratch\n' > "$TEST_REPO/notes.txt"
  run python3 "$LEDGER" --plan "$PLAN" start --task "$TASK" --actor-identity tester
  [ "$status" -eq 0 ]
  _fix_and_check
  _control
  [ "$status" -eq 0 ]
  grep -q 'verdict control_unavailable' <<<"$output"
  grep -q 'D3-3' <<<"$output"
  grep -q 'restarting the task' <<<"$output"
}

@test "committing and restarting recovers a discriminating control" {
  printf 'scratch\n' > "$TEST_REPO/notes.txt"
  run python3 "$LEDGER" --plan "$PLAN" start --task "$TASK" --actor-identity tester
  [ "$status" -eq 0 ]
  # recovery: commit the pre-existing work, then restart the attempt
  git -C "$TEST_REPO" add -A
  git -C "$TEST_REPO" commit -qm 'commit work in progress'
  run --separate-stderr python3 "$LEDGER" --plan "$PLAN" start --task "$TASK" --actor-identity tester
  [ "$status" -eq 0 ]
  ! grep -q 'dirty working tree' <<<"$stderr"
  _fix_and_check
  _control
  [ "$status" -eq 0 ]
  grep -q 'verdict discriminating' <<<"$output"
}
