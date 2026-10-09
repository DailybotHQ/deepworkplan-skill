#!/usr/bin/env bash
# The mechanical verifier on v6/v7 plans (field report F-01, F-13):
# verify/conformance.sh routes a v6/v7 plan to its own records — contract
# chain, manifest pairing, journal, approval, derived snapshot — through the
# shared ledger readers, read-only. Valid plans materialized by the shipped
# helpers are CONFORMANT; tampered records fail by name; the verifier writes
# nothing; --plan takes a name or a path; the v5 finalization still refuses
# a v6/v7 plan (D2-10).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
CONF="$SK/verify/conformance.sh"
CHECK="$SK/verify/plan_contract.py"
FIX="$REPO_ROOT/tests/fixtures/v7/contract-minimal-v7.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  mkdir -p "$HOME"
  REPO="$WORK/repo"
  mkdir -p "$REPO/src"
  printf 'x = 1\n' > "$REPO/src/product.py"
}

teardown() { rm -rf "$WORK"; }

# _plan <name> <v6|v7> — materialize and close both tasks through the
# shipped ledger, then project the snapshot.
_plan() {
  local name="$1" gen="$2" plan="$REPO/.dwp/plans/$1"
  mkdir -p "$plan/analysis_results"
  printf '# Goal\n\nVerify records.\n' > "$plan/README.md"
  python3 - "$FIX" "$plan/draft.json" "$name" "$gen" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['plan'] = sys.argv[3]
if sys.argv[4] == 'v6':
    doc['schema'] = 'https://deepworkplan.com/schema/plan-contract/v6.json'
    for t in doc['tasks']:
        t.pop('parallel_safe', None)
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
  (
    set -e
    cd "$REPO"
    python3 "$LEDGER" --plan "$plan" materialize --contract "$plan/draft.json" --authority bats --mechanism plan_authorship
    python3 "$LEDGER" --plan "$plan" start --task T-publish-schemas
    python3 "$LEDGER" --plan "$plan" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"'
    python3 "$LEDGER" --plan "$plan" complete --task T-publish-schemas
    python3 "$LEDGER" --plan "$plan" start --task T-ship-validator
    python3 "$LEDGER" --plan "$plan" gate --task T-ship-validator --criterion AC-journal-catalog-closed --json '"python3 --version"'
    python3 "$LEDGER" --plan "$plan" complete --task T-ship-validator
    python3 "$LEDGER" --plan "$plan" project
  ) > "$WORK/$name.out" 2>&1 || { cat "$WORK/$name.out"; return 1; }
  printf 'No unresolved critical findings.\n' > "$plan/analysis_results/SECURITY_REVIEW.md"
}

_tree() { (cd "$REPO" && find .dwp -type f -exec shasum -a 256 {} + | sort); }

@test "a valid v6 plan is CONFORMANT and its records are named" {
  _plan PLAN_verify_records_six v6 || return 1
  run bash "$CONF" --plan PLAN_verify_records_six "$REPO"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"v6 manifest pairs with a v6 contract"* ]] || return 1
  [[ "$output" == *"journal valid"* ]] || return 1
  [[ "$output" == *"an approval cites the live contract id"* ]] || return 1
  [[ "$output" == *"state.json agrees with the journal"* ]] || return 1
  [[ "$output" == *"2/2 tasks completed (derived from gate evidence)"* ]] || return 1
  [[ "$output" == *"Verdict: CONFORMANT"* ]]
}

@test "a valid v7 plan is CONFORMANT (no torn-pair message for the v6 snapshot)" {
  _plan PLAN_verify_records_seven v7 || return 1
  run bash "$CONF" --plan PLAN_verify_records_seven "$REPO"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"v7 manifest pairs with a v7 contract"* ]] || return 1
  [[ "$output" != *"torn pair"* ]] || return 1
  [[ "$output" == *"Verdict: CONFORMANT"* ]]
}

@test "the verifier writes nothing, and a stale snapshot is advisory" {
  _plan PLAN_verify_records_seven v7 || return 1
  plan="$REPO/.dwp/plans/PLAN_verify_records_seven"
  python3 "$LEDGER" --plan "$plan" append --type observation --json '{"statement": "later"}' --trust asserted >/dev/null
  before="$(_tree)"
  run bash "$CONF" --plan PLAN_verify_records_seven "$REPO"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"state.json is stale against the journal"* ]] || return 1
  [ "$before" = "$(_tree)" ]
}

@test "a tampered journal fails by name" {
  _plan PLAN_verify_records_seven v7 || return 1
  plan="$REPO/.dwp/plans/PLAN_verify_records_seven"
  # an agent-actor record claiming observed trust: the mint rule (A1)
  python3 - "$plan/journal.ndjson" <<'PY'
import json, sys
path = sys.argv[1]
lines = [json.loads(l) for l in open(path)]
for e in lines:
    if e['type'] == 'gate_run':
        e['actor'] = {'kind': 'agent', 'identity': 'forger'}
        break
open(path, 'w').write(''.join(json.dumps(e, sort_keys=True, separators=(',', ':')) + '\n' for e in lines))
PY
  run bash "$CONF" --plan PLAN_verify_records_seven "$REPO"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"journal: journal line"*"observed requires a shipped helper"* ]] || return 1
  [[ "$output" == *"NOT CONFORMANT"* ]]
}

@test "a reordered journal and a missing approval fail" {
  _plan PLAN_verify_records_six v6 || return 1
  plan="$REPO/.dwp/plans/PLAN_verify_records_six"
  cp "$plan/journal.ndjson" "$WORK/journal.bak"
  tail -n +2 "$WORK/journal.bak" > "$plan/journal.ndjson"
  run python3 "$CHECK" "$plan"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"no approval cites the live contract id"* ]] || return 1
  { tail -n 1 "$WORK/journal.bak"; sed '$d' "$WORK/journal.bak"; } > "$plan/journal.ndjson"
  run python3 "$CHECK" "$plan"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"positions never go backwards"* ]]
}

@test "a torn tail is reported, never repaired by the verifier" {
  _plan PLAN_verify_records_six v6 || return 1
  plan="$REPO/.dwp/plans/PLAN_verify_records_six"
  printf '{"type": "observ' >> "$plan/journal.ndjson"
  sum="$(shasum -a 256 "$plan/journal.ndjson")"
  run python3 "$CHECK" "$plan"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"torn tail"* ]] || return 1
  [ "$sum" = "$(shasum -a 256 "$plan/journal.ndjson")" ]
}

@test "a manifest pointing at a foreign contract and a wrong-generation pair fail" {
  _plan PLAN_verify_records_seven v7 || return 1
  plan="$REPO/.dwp/plans/PLAN_verify_records_seven"
  cp "$plan/manifest.json" "$WORK/manifest.bak"
  python3 - "$plan/manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); m['contract']['id'] = 'f' * 64
json.dump(m, open(sys.argv[1], 'w'))
PY
  run python3 "$CHECK" "$plan"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"is no revision of this plan's contract"* ]] || return 1
  python3 - "$WORK/manifest.bak" "$plan/manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); m['schema'] = 'https://deepworkplan.com/schema/plan-manifest/v6.json'
json.dump(m, open(sys.argv[2], 'w'))
PY
  run python3 "$CHECK" "$plan"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"manifest.json is v6 but the live contract is v7"* ]]
}

@test "--plan takes a name, an absolute path or a path relative to the caller (F-13)" {
  _plan PLAN_verify_records_six v6 || return 1
  run bash "$CONF" --plan "$REPO/.dwp/plans/PLAN_verify_records_six"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  cd "$REPO"
  run bash "$CONF" --plan .dwp/plans/PLAN_verify_records_six
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  run bash "$CONF" --plan PLAN_verify_records_six
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  run bash "$CONF" --plan ./.dwp/plans/PLAN_missing
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"plan directory $REPO/./.dwp/plans/PLAN_missing exists"* ]]
}

@test "the v5 finalization still refuses a v6/v7 plan naming the contract (D2-10)" {
  _plan PLAN_verify_records_seven v7 || return 1
  plan="$REPO/.dwp/plans/PLAN_verify_records_seven"
  run python3 -c '
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from plan_contract import check
r = check(Path(sys.argv[2]), state_override={"schema": "https://deepworkplan.com/schema/plan-state/v5.json"})
print("\n".join(r.lines)); sys.exit(1 if r.failed else 0)' "$SK/verify" "$plan"
  [ "$status" -eq 1 ] || return 1
  [[ "$output" == *"this plan is v7"*"the v5 runner does not execute v6 plans"* ]]
}
