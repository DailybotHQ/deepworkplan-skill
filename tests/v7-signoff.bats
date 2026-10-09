#!/usr/bin/env bash
# Human sign-off and honest human authority (field report F-11, F-20):
# `ledger.py signoff` mints a task-bound asserted record that closes
# asserted-accepting criteria (v6 and v7 alike) and is refused for
# observed-only and orphan criteria; the shipped example closes end to end;
# validation refuses criteria nothing can close and warns on orphans; a
# human-actor append needs an explicit marker.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
OUTCOMES="$SK/shared/outcomes.py"
CV6="$SK/shared/contract_v6.py"
FIX6="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
FIX7="$REPO_ROOT/tests/fixtures/v7/contract-minimal-v7.json"
NOTE="$REPO_ROOT/tests/fixtures/v6/human-note.md"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  REPO="$WORK/repo"
  mkdir -p "$HOME" "$REPO/src"
  printf 'x = 1\n' > "$REPO/src/product.py"
}

teardown() {
  rm -rf "$WORK"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    return 1
  fi
}

# _draft <fixture> <plan> [python mutation of doc] — a closable draft with
# an OWNED asserted-only criterion AC-human-review on T-ship-validator.
_draft() {
  python3 - "$1" "$WORK/$2.json" "$2" "${3:-}" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['plan'] = sys.argv[3]
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
doc['acceptance']['criteria'].append({
    'id': 'AC-human-review', 'statement': 'A human reviewed the diff.',
    'observable_check': 'review sign-off recorded',
    'accepted_evidence': ['asserted']})
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
    if t['id'] == 'T-ship-validator':
        t['gate_intent'].append({'criterion': 'AC-human-review',
                                 'check': 'python3 --version'})
if sys.argv[4]:
    exec(sys.argv[4])
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
}

# _plan <fixture> <plan> — materialize; close T-publish-schemas by its gate.
_plan() {
  local plan="$REPO/.dwp/plans/$2"
  mkdir -p "$plan/analysis_results"
  printf '# Goal\n\nSign-off.\n' > "$plan/README.md"
  printf 'Reviewed the diff; approved.\n' > "$plan/analysis_results/REVIEW_NOTE.md"
  _draft "$1" "$2" || return 1
  (
    set -e
    cd "$REPO"
    python3 "$LEDGER" --plan "$plan" materialize --contract "$WORK/$2.json" --authority bats --mechanism plan_authorship
    python3 "$LEDGER" --plan "$plan" start --task T-publish-schemas
    python3 "$LEDGER" --plan "$plan" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"'
    python3 "$LEDGER" --plan "$plan" complete --task T-publish-schemas
  ) > "$WORK/$2.out" 2>&1 || { cat "$WORK/$2.out"; return 1; }
  PLAN="$plan"
}

_receipt_mechanism() {  # <criterion>
  python3 "$OUTCOMES" --plan "$PLAN" receipt --out "$WORK/receipt.json" >/dev/null || return 1
  python3 - "$WORK/receipt.json" "$1" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
c = next(c for c in r['closure']['criteria'] if c['criterion'] == sys.argv[2])
print('%s %s' % (c['satisfied'], c['mechanism']))
PY
}

@test "an owned asserted criterion closes through signoff, in v6 and v7" {
  for fix in "$FIX6:PLAN_signoff_six" "$FIX7:PLAN_signoff_seven"; do
    _plan "${fix%%:*}" "${fix##*:}" || return 1
    cd "$REPO"
    python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null || return 1
    python3 "$LEDGER" --plan "$PLAN" gate --task T-ship-validator --criterion AC-journal-catalog-closed --json '"python3 --version"' >/dev/null || return 1
    run python3 "$LEDGER" --plan "$PLAN" complete --task T-ship-validator
    [ "$status" -eq 4 ] || { echo "$output"; return 1; }
    run python3 "$LEDGER" --plan "$PLAN" signoff --criterion AC-human-review --evidence-path analysis_results/REVIEW_NOTE.md --authority "Ada Reviewer"
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
    [[ "$output" == *"asserted: a human claim, never executed"* ]] || return 1
    run python3 "$LEDGER" --plan "$PLAN" complete --task T-ship-validator
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
    [ "$(_receipt_mechanism AC-human-review)" = "True signoff" ] || return 1
    # the record: asserted, human, never executed, valid under the contract
    python3 - "$PLAN/journal.ndjson" <<'PY' || return 1
import json, sys
e = [json.loads(l) for l in open(sys.argv[1]) if '"AC-human-review"' in l][-1]
assert e['type'] == 'gate_run' and e['trust'] == 'asserted', e
assert e['actor'] == {'kind': 'human', 'identity': 'Ada Reviewer'}, e
assert e['command'] == 'signoff (asserted, not executed)', e
assert e['task'] == 'T-ship-validator' and 'sha256:' in e['note'], e
PY
    python3 "$CV6" validate-journal "$PLAN/journal.ndjson" --contract "$PLAN/contract.json" >/dev/null || return 1
  done
}

@test "the shipped V6 example closes end to end, its human review through signoff" {
  plan="$REPO/.dwp/plans/PLAN_001_ship_feature_x"
  mkdir -p "$plan/analysis_results"
  printf '# Goal\n\nShip feature X.\n' > "$plan/README.md"
  printf 'Reviewed the diff; approved.\n' > "$plan/analysis_results/REVIEW_NOTE.md"
  python3 - "$SK/examples/V6_PLAN_EXAMPLE.md" "$WORK/example.json" <<'PY2'
import json, re, sys
text = open(sys.argv[1]).read()
doc = json.loads(re.search(r'```json\n(\{.*?\n\})\n```', text, re.S).group(1))
for intent in doc['tasks'][0]['gate_intent']:
    intent['check'] = 'python3 --version'
json.dump(doc, open(sys.argv[2], 'w'))
PY2
  cd "$REPO"
  run python3 "$CV6" validate-contract "$WORK/example.json"
  [ "$status" -eq 0 ] && [[ "$output" != *WARN* ]] || { echo "$output"; return 1; }
  PLAN="$plan"
  python3 "$LEDGER" --plan "$plan" materialize --contract "$WORK/example.json" --authority sergio >/dev/null || return 1
  python3 "$LEDGER" --plan "$plan" start --task T-implement >/dev/null || return 1
  python3 "$LEDGER" --plan "$plan" gate --task T-implement --criterion AC-tests-pass --json '"python3 --version"' >/dev/null || return 1
  python3 "$LEDGER" --plan "$plan" complete --task T-implement >/dev/null || return 1
  python3 "$LEDGER" --plan "$plan" start --task T-final-review >/dev/null || return 1
  run python3 "$LEDGER" --plan "$plan" complete --task T-final-review
  [ "$status" -eq 4 ] || { echo "$output"; return 1; }
  python3 "$LEDGER" --plan "$plan" signoff --criterion AC-human-review --evidence-path analysis_results/REVIEW_NOTE.md --authority sergio >/dev/null || return 1
  python3 "$LEDGER" --plan "$plan" complete --task T-final-review >/dev/null || return 1
  [ "$(_receipt_mechanism AC-human-review)" = "True signoff" ] || return 1
  [ "$(_receipt_mechanism AC-tests-pass)" = "True evidence" ]
}

@test "an orphan criterion cannot be signed off and is a validation warning" {
  _plan "$FIX6" PLAN_signoff_prose || return 1
  cd "$REPO"
  run python3 "$LEDGER" --plan "$PLAN" signoff --criterion AC-prose-only-criterion --evidence-path analysis_results/REVIEW_NOTE.md --authority ada
  [ "$status" -ne 0 ] && [[ "$output" == *"no task gate_intent declares AC-prose-only-criterion"* ]] || { echo "$output"; return 1; }
  run python3 "$CV6" validate-contract "$WORK/PLAN_signoff_prose.json"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"WARN contract.acceptance: AC-prose-only-criterion is declared by no task gate_intent"*"reconciliation with amendment authority"* ]]
}

@test "signoff is refused for observed-only criteria, before task start, and without its marker" {
  _plan "$FIX7" PLAN_signoff_refusals || return 1
  cd "$REPO"
  run python3 "$LEDGER" --plan "$PLAN" signoff --criterion AC-journal-catalog-closed --evidence-path analysis_results/REVIEW_NOTE.md --authority ada
  [ "$status" -ne 0 ] && [[ "$output" == *"accepts only observed"* ]] || { echo "$output"; return 1; }
  run python3 "$LEDGER" --plan "$PLAN" signoff --criterion AC-human-review --evidence-path analysis_results/REVIEW_NOTE.md --authority ada
  [ "$status" -ne 0 ] && [[ "$output" == *"T-ship-validator has not started"* ]] || { echo "$output"; return 1; }
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" signoff --criterion AC-human-review --evidence-path analysis_results/NOPE.md --authority ada
  [ "$status" -ne 0 ] && [[ "$output" == *"does not resolve"* ]] || { echo "$output"; return 1; }
  run python3 "$LEDGER" --plan "$PLAN" signoff --criterion AC-human-review --evidence-path analysis_results/REVIEW_NOTE.md
  [ "$status" -ne 0 ] && [[ "$output" == *"requires --authority"* ]] || { echo "$output"; return 1; }
  # a raw append can still never mint a gate_run
  run python3 "$LEDGER" --plan "$PLAN" append --type gate_run --json '{"criterion": "AC-human-review"}' --trust asserted
  [ "$status" -ne 0 ] && [[ "$output" == *"produced only by the gate executor"* ]]
}

@test "validation refuses criteria nothing can close; materialize refuses them too" {
  _draft "$FIX6" PLAN_signoff_unclosable "doc['acceptance']['criteria'].append({'id': 'AC-imported-only', 'statement': 's', 'observable_check': 'c', 'accepted_evidence': ['imported']}); doc['tasks'][0]['gate_intent'].append({'criterion': 'AC-imported-only', 'check': 'python3 --version'})" || return 1
  run python3 "$CV6" validate-contract "$WORK/PLAN_signoff_unclosable.json"
  [ "$status" -eq 1 ] || { echo "$output"; return 1; }
  [[ "$output" == *"AC-imported-only accepts only imported and nothing can ever close it"*"comes only from a migration"* ]] || return 1
  plan="$REPO/.dwp/plans/PLAN_signoff_unclosable"; mkdir -p "$plan"; printf '# Goal\n' > "$plan/README.md"
  run python3 "$LEDGER" --plan "$plan" materialize --contract "$WORK/PLAN_signoff_unclosable.json" --authority bats
  [ "$status" -ne 0 ] && [[ "$output" == *"nothing can ever close it"* ]] || { echo "$output"; return 1; }
  [ ! -e "$plan/contract.json" ]
  # a controlled orphan stays closable (its control pair closes it): no warning
  _draft "$FIX6" PLAN_signoff_controlled "doc['acceptance']['criteria'].append({'id': 'AC-ctl', 'statement': 's', 'observable_check': 'c', 'accepted_evidence': ['observed'], 'control': {'kind': 'regression', 'rationale': 'r'}})"
  run python3 "$CV6" validate-contract "$WORK/PLAN_signoff_controlled.json"
  [ "$status" -eq 0 ] && [[ "$output" != *"AC-ctl is declared"* ]] || { echo "$output"; return 1; }
}

@test "a human-actor append needs an explicit authority marker (F-20)" {
  _plan "$FIX7" PLAN_signoff_marker || return 1
  cd "$REPO"
  run python3 "$LEDGER" --plan "$PLAN" append --type observation --json '{"statement": "I approve"}' --trust asserted --actor-kind human --actor-identity someone < /dev/null
  [ "$status" -ne 0 ] && [[ "$output" == *"needs an explicit human-authority marker"* ]] || { echo "$output"; return 1; }
  run python3 "$LEDGER" --plan "$PLAN" append --type observation --json '{"statement": "I approve"}' --trust asserted --actor-kind human --actor-identity someone --human-note "$WORK/missing.md"
  [ "$status" -ne 0 ] && [[ "$output" == *"is not a file"* ]] || { echo "$output"; return 1; }
  run python3 "$LEDGER" --plan "$PLAN" append --type observation --json '{"statement": "I approve"}' --trust asserted --actor-kind human --actor-identity someone --human-note "$NOTE" --note "context"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  tail -n 1 "$PLAN/journal.ndjson" | grep -qF 'context | human authority marker: note' || return 1
  tail -n 1 "$PLAN/journal.ndjson" | grep -qE 'sha256:[0-9a-f]{16}' || return 1
  # agents record their own claims without a marker
  run python3 "$LEDGER" --plan "$PLAN" append --type observation --json '{"statement": "agent claim"}' --trust asserted --actor-kind agent
  [ "$status" -eq 0 ]
}
