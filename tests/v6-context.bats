#!/usr/bin/env bash
# v6 context selection: the per-task context manifest, dead-end digest,
# freshness invalidation and four-quantity accounting (RFC section 7).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
CONTEXT="$SK/shared/context_manifest.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
TASK='T-publish-schemas'
AC='AC-valid-contract-shape'

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_context_bats"
  mkdir -p "$PLAN" "$TEST_REPO/src"
  printf 'def validate(x):\n    return True\n' > "$TEST_REPO/src/product.py"
}

teardown() {
  rm -rf "$TEST_REPO"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    find "$SK" -name '__pycache__' -o -name '*.pyc'
    return 1
  fi
}

_write_contract() { # _write_contract [control-kind] [plan-name]
  PLAN="$PLAN" CTRL="${1:-regression}" python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_context_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
doc['acceptance']['criteria'][0]['control'] = {
    'kind': os.environ.get('CTRL', 'regression'),
    'rationale': 'the pre-v6 failure mode'}
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

_manifest_field() { # _manifest_field KEY -> python expr over the manifest doc
  PLAN="$PLAN" TASK="$TASK" EXPR="$2" python3 - "$CONTEXT" <<'PY'
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import context_manifest
import json
doc = context_manifest.manifest(os.environ['PLAN'], os.environ['TASK'])
print(eval(os.environ['EXPR']))
PY
}

@test "context self-test passes" {
  run python3 "$CONTEXT" self-test
  [ "$status" -eq 0 ]
  grep -q 'self-test: OK' <<<"$output"
}

@test "a task outside the contract is refused, never guessed" {
  _write_contract
  run python3 "$CONTEXT" --plan "$PLAN" manifest --task T-missing
  [ "$status" -eq 1 ]
  grep -q 'never guesses' <<<"$output"
}

@test "pruning cannot drop the acceptance or authorization boundary" {
  _write_contract
  run python3 "$CONTEXT" --plan "$PLAN" manifest --task "$TASK" \
    --sections authorization,repository_rules
  [ "$status" -eq 1 ]
  grep -q 'cannot hide the acceptance or' <<<"$output"
}

@test "before approval the manifest names the approval step and nothing else" {
  _write_contract
  [ "$(_manifest_field x "doc['next_action']['step']")" = "approval" ]
  # no evidence is inherited: nothing has happened yet
  [ "$(_manifest_field x "len(doc['evidence'])")" = "0" ]
  [ "$(_manifest_field x "len(doc['dead_ends'])")" = "0" ]
}

@test "authorization and repository rules are carried verbatim" {
  _write_contract
  _approve
  _start
  [ "$(_manifest_field x "doc['authorization']['approvals'][0]['authority']")" = "bats tester" ]
  [ "$(_manifest_field x "'publish' in doc['repository_rules']['scope']['forbidden_operations']")" = "True" ]
  [ "$(_manifest_field x "doc['repository_rules']['invariants'][0]['state']")" = "unevaluated" ]
}

@test "consent checkpoints ride the manifest verbatim, never summarized" {
  _write_contract
  _approve
  _start
  # the fixture's own checkpoint text, read not hardcoded, must appear
  # verbatim inside the derived authorization section
  local checkpoint
  checkpoint="$(python3 -c 'import json; print(json.load(open("'"$FIXTURE"'"))["authorization"]["consent_checkpoints"][0])')"
  [ -n "$checkpoint" ]
  export CHECKPOINT_TEXT="$checkpoint"
  [ "$(_manifest_field x "os.environ['CHECKPOINT_TEXT'] in json.dumps(doc['authorization'])")" = "True" ]
}

@test "an open controlled criterion demands its control pair, not any gate pass" {
  _write_contract
  _approve
  _start
  [ "$(_manifest_field x "doc['next_action']['step']")" = "control" ]
  [ "$(_manifest_field x "doc['next_action']['criteria']")" = "['$AC']" ]
}

@test "a passing gate never closes a controlled criterion in the manifest" {
  _write_contract
  _approve
  _start
  printf 'def validate(x):\n    return True\n' > "$TEST_REPO/src/product.py"
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$TASK" \
    --criterion "$AC" --json '"python3 -c \"exit(0)\""'
  [ "$status" -eq 0 ]
  [ "$(_manifest_field x "doc['next_action']['step']")" = "control" ]
}

@test "an exempt criterion advances the ladder to complete on a gate pass" {
  _write_contract exempt
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$TASK" \
    --criterion "$AC" --json '"python3 -c \"exit(0)\""'
  [ "$status" -eq 0 ]
  [ "$(_manifest_field x "doc['next_action']['step']")" = "complete" ]
}

@test "a failing gate enters the dead-end digest with its cause pointer" {
  _write_contract exempt
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$TASK" \
    --criterion "$AC" --json '"python3 -c \"exit(3)\""'
  [ "$status" -eq 1 ]
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$TASK" \
    --criterion "$AC" --json '"python3 -c \"exit(0)\""'
  [ "$status" -eq 0 ]
  [ "$(_manifest_field x "[e for e in doc['dead_ends'] if e['kind']=='failed_gate'][0]['exit_code']")" = "3" ]
  [ "$(_manifest_field x "'gates/' in [e for e in doc['dead_ends'] if e['kind']=='failed_gate'][0]['cause']")" = "True" ]
}

@test "a superseded contract revision marks its dead controls aged_out" {
  _write_contract exempt
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" append --type control_pair \
    --trust asserted --evidence-path gates/c.log \
    --json "{\"criterion\": \"$AC\", \"check_artifacts\": [\"f.txt\"], \"starting_fingerprint\": {\"revision\": \"r1\", \"dirty\": \"\"}, \"old_leg\": {\"available\": true, \"outcome\": \"PASS\", \"log\": \"gates/c.log\"}, \"new_leg\": {\"outcome\": \"PASS\", \"log\": \"gates/c.log\"}, \"verdict\": \"non_discriminating\"}"
  [ "$status" -eq 0 ]
  _write_contract exempt   # same content -> same contract_id; not superseded
  [ "$(_manifest_field x "doc['dead_ends'][0].get('aged_out')")" = "None" ]
  # a revision-2 contract in the chain -> new live id: the pair is
  # retained but marked aged_out (retention-biased invalidation)
  mkdir -p "$PLAN/contracts"
  PLAN="$PLAN" python3 - "$PLAN/contract.json" <<'INNEREOF'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['revision'] = 2
doc['parent_contract_id'] = doc.pop('contract_id')
doc['acceptance']['criteria'][0]['accepted_evidence'].append('imported')
doc.pop('contract_id', None)
cid = contract_v6.compute_contract_id(doc)
json.dump(dict(doc, contract_id=cid),
          open(os.path.join(os.environ['PLAN'], 'contracts', 'r2.json'), 'w'),
          indent=2, sort_keys=True)
INNEREOF
  [ "$(_manifest_field x "doc['dead_ends'][0].get('aged_out')")" = "superseded contract revision" ]
}

@test "a missing touched file widens discovery and surfaces the miss" {
  _write_contract
  _approve
  _start
  rm "$TEST_REPO/src/product.py"
  [ "$(_manifest_field x "doc['touched_surface']['widen_discovery']")" = "True" ]
  [ "$(_manifest_field x "doc['touched_surface']['files']['src/product.py']")" = "None" ]
}

@test "freshness: unchanged inputs are fresh, changed inputs invalidate" {
  _write_contract
  _approve
  _start
  run python3 "$CONTEXT" --plan "$PLAN" manifest --task "$TASK" --out "$PLAN/manifest.json"
  [ "$status" -eq 0 ]
  python3 - "$PLAN/manifest.json" "$PLAN/summary.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
json.dump({'inputs_fingerprint': doc['freshness']['inputs_fingerprint'],
           'summary': 'any cached summary'},
          open(sys.argv[2], 'w'))
PY
  run python3 "$CONTEXT" --plan "$PLAN" freshness --task "$TASK" \
    --summary "$PLAN/summary.json"
  [ "$status" -eq 0 ]
  grep -q '"verdict": "fresh"' <<<"$output"
  printf 'changed\n' > "$TEST_REPO/src/product.py"
  run python3 "$CONTEXT" --plan "$PLAN" freshness --task "$TASK" \
    --summary "$PLAN/summary.json"
  [ "$status" -eq 1 ]
  grep -q '"verdict": "stale"' <<<"$output"
  grep -q 'never silently inherited' <<<"$output"
}

@test "an unattributable summary (no fingerprint) is stale by construction" {
  _write_contract
  echo '{}' > "$PLAN/summary.json"
  run python3 "$CONTEXT" --plan "$PLAN" freshness --task "$TASK" \
    --summary "$PLAN/summary.json"
  [ "$status" -eq 1 ]
  grep -q 'stale by' <<<"$output"
}

@test "accounting keeps four quantities apart and missing means missing" {
  _write_contract
  _approve
  _start
  run python3 "$CONTEXT" --plan "$PLAN" accounting
  [ "$status" -eq 0 ]
  grep -q '"instruction_bytes"' <<<"$output"
  grep -q '"provider_tokens"' <<<"$output"
  grep -q '"cost_usd"' <<<"$output"
  grep -q '"wall_clock_hours"' <<<"$output"
  grep -q '"status": "missing"' <<<"$output"
  grep -q 'never converted' <<<"$output"
  # a real meter sample surfaces as the cost value, never imputed
  echo '{"spend_usd": 1.25}' > "$PLAN/analysis_results/meter.json" 2>/dev/null || \
    mkdir -p "$PLAN/analysis_results" && echo '{"spend_usd": 1.25}' > "$PLAN/analysis_results/meter.json"
  run python3 "$LEDGER" --plan "$PLAN" append --type resource_sample \
    --trust observed --evidence-path analysis_results/meter.json \
    --actor-kind host_adapter --actor-identity bats-meter \
    --json '{"source": "bats-meter", "limit_id": "spend_usd", "value": 1.25, "unit": "USD"}'
  [ "$status" -eq 0 ]
  run python3 "$CONTEXT" --plan "$PLAN" accounting
  grep -q '"value": 1.25' <<<"$output"
}

@test "the manifest is deterministic and record-anchored, never wall-clocked" {
  _write_contract
  _approve
  _start
  A="$(_manifest_field x "json.dumps(doc, sort_keys=True)")"
  B="$(_manifest_field x "json.dumps(doc, sort_keys=True)")"
  [ "$A" = "$B" ]
  # as_of is the last record's position; before any event it is empty
  ts="$(_manifest_field x "doc['as_of']['event_ts']")"
  [ -n "$ts" ]
  python3 - "$PLAN" "$ts" <<'PY'
import json, sys
events = [json.loads(line) for line in open(sys.argv[1] + '/journal.ndjson')]
assert sys.argv[2] == max(e['ts'] for e in events), 'as_of must be record-derived'
PY
}

@test "the markdown render carries the boundaries and dead ends" {
  _write_contract exempt
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" gate --task "$TASK" \
    --criterion "$AC" --json '"python3 -c \"exit(9)\""'
  run python3 "$CONTEXT" --plan "$PLAN" manifest --task "$TASK" --md
  [ "$status" -eq 0 ]
  grep -q '## Authorization' <<<"$output"
  grep -q '## Repository rules' <<<"$output"
  grep -q '## Dead ends' <<<"$output"
  grep -q 'failed_gate' <<<"$output"
  grep -q 'Freshness fingerprint' <<<"$output"
}

@test "history loads only on declared triggers" {
  _write_contract
  _approve
  _start
  [ "$(_manifest_field x "doc['history_triggers'][0]['loads']")" = "this manifest alone" ]
  # a handoff condition in the contract declares its trigger
  [ "$(_manifest_field x "'handoff' in doc['history_triggers'][1]['trigger']")" = "True" ]
}
