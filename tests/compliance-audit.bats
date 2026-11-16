#!/usr/bin/env bash
# The read-only compliance audit of finished v6/v7 plans (ADR 0006, R17/R11):
# driven through the shipped helpers on a real materialized plan, so the
# audit reads exactly what the ledger writes. It must never write.
bats_require_minimum_version 1.5.0
REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
AUDIT="$SK/verify/compliance_audit.py"
FIX="$REPO_ROOT/tests/fixtures/v7"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  REPO="$WORK/repo"
  PLAN="$REPO/.dwp/plans/PLAN_v7_fixture_minimal"
  mkdir -p "$PLAN/analysis_results" "$REPO/src"
  printf '# Goal\n\naudit fixture.\n' > "$PLAN/README.md"
  printf 'x = 1\n' > "$REPO/src/product.py"
  git -C "$REPO" init -q
  printf '.dwp/\n' > "$REPO/.gitignore"
  git -C "$REPO" add -A && git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init
  python3 - "$FIX/contract-minimal-v7.json" "$PLAN/draft.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['invariants'] = []
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
    for g in t['gate_intent']:
        g['check'] = 'python3 -c pass'
for c in doc['acceptance']['criteria']:
    c.pop('control', None)          # undecided controls: the §5.1.4 finding
    c['accepted_evidence'] = ['observed']
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
  run python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" --authority bats --mechanism plan_authorship
  [ "$status" -eq 0 ]
  FIRST="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tasks"][0]["id"])' "$PLAN/contract.json")"
  FIRST_AC="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tasks"][0]["gate_intent"][0]["criterion"])' "$PLAN/contract.json")"
}

teardown() {
  rm -rf "$WORK"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    return 1
  fi
}

_close_first() {
  run python3 "$LEDGER" --plan "$PLAN" start --task "$FIRST" --actor-identity tester
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$FIRST" --criterion "$FIRST_AC" --json '"python3 -c pass"'
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" complete --task "$FIRST"
  [ "$status" -eq 0 ]
}

_field() { # _field KEY -> JSON value of plans[0][KEY]
  python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["plans"][0][sys.argv[1]]))' "$1"
}

@test "the audit reports a criterion closed on its declared evidence class" {
  _close_first
  run python3 "$AUDIT" "$PLAN" --json
  [ "$status" -eq 0 ]
  closed="$(_field criteria_closed_on_declared_class <<<"$output")"
  grep -q "$FIRST_AC" <<<"$closed"
  [ "$(_field criteria_closed_outside_declared_class <<<"$output")" = "[]" ]
  [ "$(_field tasks_completed <<<"$output")" = "1" ]
}

@test "the audit counts the §5.1.4 observations the ledger recorded" {
  _close_first
  run python3 "$AUDIT" "$PLAN" --json
  [ "$status" -eq 0 ]
  [ "$(_field section_5_1_4_observations <<<"$output")" = "1" ]
  grep -q "$FIRST_AC" <<<"$(_field criteria_without_control_decision <<<"$output")"
}

@test "the audit reports the verbatim request and re-anchoring honestly" {
  run python3 "$AUDIT" "$PLAN" --json
  [ "$status" -eq 0 ]
  [ "$(_field verbatim_request <<<"$output")" = "false" ]
  printf 'the human words\n' > "$PLAN/analysis_results/HUMAN_NOTE.md"
  run python3 "$AUDIT" "$PLAN" --json
  [ "$(_field verbatim_request <<<"$output")" = "true" ]
  grep -q 'unmeasured' <<<"$(_field re_anchoring <<<"$output")"
}

@test "the audit writes nothing" {
  _close_first
  before="$(cd "$PLAN" && find . -type f -exec shasum {} + | sort)"
  run python3 "$AUDIT" "$PLAN"
  [ "$status" -eq 0 ]
  run python3 "$AUDIT" "$PLAN" --json
  [ "$status" -eq 0 ]
  after="$(cd "$PLAN" && find . -type f -exec shasum {} + | sort)"
  [ "$before" = "$after" ]
}

@test "a plan without v6/v7 records is skipped, never judged" {
  mkdir -p "$WORK/plans/PLAN_old"
  printf '# old\n' > "$WORK/plans/PLAN_old/README.md"
  run python3 "$AUDIT" --plans-dir "$WORK/plans" --json
  [ "$status" -eq 0 ]
  grep -q 'not a v6/v7 record-layer plan' <<<"$output"
}

@test "usage errors exit 2" {
  run python3 "$AUDIT"
  [ "$status" -eq 2 ]
  run python3 "$AUDIT" "$WORK/missing-plan"
  [ "$status" -eq 2 ]
}

@test "the Final Review is matched by name, not by any 'final' in a task id" {
  run python3 -c 'import sys; sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import compliance_audit as ca
assert ca._FINAL_REVIEW.search("T-final-review")
assert ca._FINAL_REVIEW.search("T-qa Final Review")
assert not ca._FINAL_REVIEW.search("T-finalize-schema Finalize the schema")
assert not ca._FINAL_REVIEW.search("T-review Review")' "$SK/verify"
  [ "$status" -eq 0 ]
}

@test "one unreadable plan is reported as skipped and never hides the others" {
  mkdir -p "$WORK/plans"
  cp -R "$PLAN" "$WORK/plans/PLAN_good"
  cp -R "$PLAN" "$WORK/plans/PLAN_torn"
  printf '{"schema": "https://deepworkplan.com/schema/plan-manifest/v7.json"}' > "$WORK/plans/PLAN_torn/manifest.json"
  rm -rf "$WORK/plans/PLAN_torn/contracts" "$WORK/plans/PLAN_torn/contract.json"
  run --separate-stderr python3 "$AUDIT" --plans-dir "$WORK/plans" --json
  [ "$status" -eq 2 ]
  grep -q '"plan": "PLAN_good"' <<<"$output"
  grep -q 'unreadable' <<<"$output"
}
