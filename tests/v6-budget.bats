#!/usr/bin/env bash
# v6 resource controls: host capability negotiation, counter sources,
# reserves, exhaustion holds and cancellation settlement (RFC section 8).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
RESOURCES="$SK/shared/resources.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
TASK='T-publish-schemas'
AC='AC-valid-contract-shape'

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_budget_bats"
  mkdir -p "$PLAN" "$TEST_REPO/src" "$PLAN/analysis_results"
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

_write_contract() { # _write_contract  (env: RESERVE/UNIT/GRANT variants)
  PLAN="$PLAN" python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_budget_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
limit = doc['resource_envelope']['limits'][0]
if os.environ.get('RESERVE'):
    limit['reserve'] = float(os.environ['RESERVE'])
if os.environ.get('UNIT'):
    limit['unit'] = os.environ['UNIT']
if os.environ.get('GRANT'):
    doc['permissions']['granted'] = sorted(
        set(doc['permissions']['granted']) | {os.environ['GRANT']})
    doc['permissions']['not_granted'] = [
        c for c in doc['permissions']['not_granted']
        if c != os.environ['GRANT']]
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

_meter() { # _meter [value]  — a host adapter reads the meter and samples it
  _METER_VALUE="${1:-8.5}" python3 - "$PLAN" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import ledger
plan = os.environ['PLAN_DIR'] if 'PLAN_DIR' in os.environ else sys.argv[1]
value = float(os.environ['_METER_VALUE'])
path = os.path.join(plan, 'analysis_results', 'meter.json')
json.dump({'spend_usd': value}, open(path, 'w'))
rec = ledger.PlanRecords(plan)
lock = ledger.CooperativeLock(plan).acquire()
try:
    ledger.Writer(rec, lock).append(
        'resource_sample',
        {'source': 'bats-meter', 'limit_id': 'spend_usd',
         'value': value, 'unit': 'USD'},
        actor={'kind': 'host_adapter', 'identity': 'bats-meter'},
        trust='observed', evidence_path='analysis_results/meter.json')
finally:
    lock.release()
PY
}

_report_field() { # _report_field CAPS EXPR -> eval over envelope_report
  PLAN="$PLAN" CAPS="$1" EXPR="$2" python3 - "$RESOURCES" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import resources
plan = os.environ['PLAN']
rec = __import__('ledger').PlanRecords(plan)
events = rec.archived_events() + rec.read_journal()[0]
report = resources.envelope_report(
    rec.contract, events, resources.host_capabilities(
        json.loads(os.environ['CAPS'])))
print(eval(os.environ['EXPR']))
PY
}

@test "resources self-test passes" {
  run python3 "$RESOURCES" self-test
  [ "$status" -eq 0 ]
  grep -q 'self-test: OK' <<<"$output"
}

@test "an unknown host capability is refused, never invented" {
  run python3 "$RESOURCES" capabilities --caps '{"time_travel": true}'
  [ "$status" -eq 1 ]
  grep -q 'unknown host capability' <<<"$output"
  grep -q 'never invented' <<<"$output"
}

@test "the minimal all-False host is a supported degraded posture" {
  run python3 "$RESOURCES" capabilities
  [ "$status" -eq 0 ]
  # no model switching, no subagents, no telemetry, no stop — all False
  for cap in model_routing subagents telemetry stop_agent meter_spend; do
    grep -q "\"$cap\": false" <<<"$output"
  done
}

@test "journal-computed counters enforce with no host at all" {
  _write_contract
  _approve
  _start
  # gate_retries is enforced and its unit family is journal-observable:
  # the core counts gate re-runs from the records, no host meter needed
  run _report_field '{}' "next(r for r in report['limits'] if r['limit_id'] == 'gate_retries')['effective_mode']"
  [ "$status" -eq 0 ]
  grep -q 'enforced (journal-computed counter)' <<<"$output"
  run _report_field '{}' "next(r for r in report['limits'] if r['limit_id'] == 'gate_retries')['counter_source']"
  [ "$status" -eq 0 ]
  [ "$output" = "journal" ]
}

@test "spend on a meterless host is honestly advisory" {
  _write_contract
  _approve
  _start
  run _report_field '{}' "next(r for r in report['limits'] if r['limit_id'] == 'spend_usd')['effective_mode']"
  [ "$status" -eq 0 ]
  grep -q 'advisory (host cannot meter: no meter_spend capability' <<<"$output"
}

@test "a metered host reads the observed sample; a missing one is never free" {
  _write_contract
  _approve
  _start
  # host CAN meter but no sample is on record: pending-side only
  run _report_field '{"meter_spend": true}' "next(r for r in report['limits'] if r['limit_id'] == 'spend_usd')['effective_mode']"
  [ "$status" -eq 0 ]
  grep -q 'enforced-pending-only (unmetered spend' <<<"$output"
  run _report_field '{"meter_spend": true}' "next(r for r in report['limits'] if r['limit_id'] == 'spend_usd')['spent']"
  [ "$status" -eq 0 ]
  [ "$output" = "None" ]
  # the host adapter reads the meter: enforced with the meter's value
  _meter 8.5
  run _report_field '{"meter_spend": true}' "next(r for r in report['limits'] if r['limit_id'] == 'spend_usd')['spent']"
  [ "$status" -eq 0 ]
  [ "$output" = "8.5" ]
  run _report_field '{"meter_spend": true}' "next(r for r in report['limits'] if r['limit_id'] == 'spend_usd')['effective_mode']"
  [ "$status" -eq 0 ]
  grep -q 'enforced (observed meter sample)' <<<"$output"
}

@test "a reserve the spent cannot fit flips the refusal" {
  RESERVE=3995 _write_contract
  _approve
  _start
  _meter 8.5
  run _report_field '{"meter_spend": true}' "next(r for r in report['limits'] if r['limit_id'] == 'spend_usd')['dispatch_ceiling']"
  [ "$status" -eq 0 ]
  [ "$output" = "5.0" ]
  run _report_field '{"meter_spend": true}' "report['refusal']['rule']"
  [ "$status" -eq 0 ]
  [ "$output" = "limit-exhausted" ]
  run _report_field '{"meter_spend": true}' "report['refusal']['detail']"
  [ "$status" -eq 0 ]
  grep -q 'limit 4000 - reserve 3995' <<<"$output"
}

@test "a reserve above the limit is refused at declaration" {
  RESERVE=9999 _write_contract
  run python3 "$RESOURCES" --plan "$PLAN" report --caps '{}'
  [ "$status" -eq 1 ]
  grep -q 'reserve 9999.0 exceeds the limit' <<<"$output"
}

@test "exhaustion of an undeclared limit is never recorded" {
  _write_contract
  _approve
  run python3 "$RESOURCES" --plan "$PLAN" exhaust --limit not_a_limit
  [ "$status" -eq 1 ]
  grep -q 'never recorded' <<<"$output"
  run grep -c 'LIMIT:' "$PLAN/journal.ndjson"
  [ "$output" = "0" ]
}

@test "exhaustion holds dispatch and an explicit recovery clears it" {
  _write_contract
  _approve
  _start
  run python3 "$RESOURCES" --plan "$PLAN" exhaust --limit spend_usd \
    --detail 'commit-plus-pending over the ceiling'
  [ "$status" -eq 0 ]
  run python3 "$RESOURCES" --plan "$PLAN" hold
  [ "$status" -eq 1 ]
  grep -q 'HOLD: limit spend_usd' <<<"$output"
  run python3 "$RESOURCES" --plan "$PLAN" recover --limit spend_usd \
    --detail 'meter back under the ceiling'
  [ "$status" -eq 0 ]
  run python3 "$RESOURCES" --plan "$PLAN" hold
  [ "$status" -eq 0 ]
  grep -q 'no resource hold' <<<"$output"
}

@test "an exhaustion observation never satisfies a criterion" {
  _write_contract
  _approve
  _start
  run python3 "$RESOURCES" --plan "$PLAN" exhaust --limit spend_usd
  [ "$status" -eq 0 ]
  PLAN="$PLAN" TASK="$TASK" python3 - <<'PY'
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import ledger
rec = ledger.PlanRecords(os.environ['PLAN'])
events = rec.archived_events() + rec.read_journal()[0]
states = ledger.criterion_states(rec.contract, events, os.environ['TASK'])
assert states and not any(s.get('satisfied') for s in states), states
print('OK: exhaustion is not completion evidence')
PY
}

@test "settlement is exactly-once: replay dedups, conflict refused" {
  _write_contract
  _approve
  run python3 "$RESOURCES" --plan "$PLAN" settle --key seq-1 \
    --disposition released --detail 'child cancelled mid-flight'
  [ "$status" -eq 0 ]
  seq_first="$(grep -o 'seq [0-9]*' <<<"$output" | head -1)"
  run python3 "$RESOURCES" --plan "$PLAN" settle --key seq-1 \
    --disposition released --detail 'child cancelled mid-flight'
  [ "$status" -eq 0 ]
  seq_again="$(grep -o 'seq [0-9]*' <<<"$output" | head -1)"
  [ "$seq_first" = "$seq_again" ]
  run python3 "$RESOURCES" --plan "$PLAN" settle --key seq-1 \
    --disposition committed --detail 'late report'
  [ "$status" -eq 1 ]
  grep -q 'double-charge ambiguity' <<<"$output"
}

@test "a released settlement subtracts its impact exactly once" {
  _write_contract
  _approve
  _start
  run python3 "$LEDGER" --plan "$PLAN" append --type adaptation \
    --actor-identity tester \
    --json '{"kind": "retry", "trigger_observation": 1, "evidence_artifact": "gates/T-publish-schemas/001-x.log", "hypothesis": "the gate failed on a missing dependency", "action": "install it and retry the same gate", "rationale": "environmental failure, not a criterion change", "authority": "scheduling.max_retries_per_gate", "affected_tasks": ["T-publish-schemas"], "affected_criteria": [], "evidence_invalidated": [], "evidence_preserved": [], "resource_impact": {"declared": 2.0, "unit": "USD"}, "decision": "authorized"}'
  [ "$status" -eq 0 ]
  PLAN="$PLAN" python3 - <<'PY'
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import ledger, resources, scheduler
plan = os.environ['PLAN']
rec = ledger.PlanRecords(plan)
events = rec.archived_events() + rec.read_journal()[0]
base = {r['limit_id']: r['pending']
        for r in scheduler.envelope_status(rec.contract, events)}
assert base['spend_usd'] == 2.0, base  # the authorized adaptation commits
withpend = resources.pending_after_settlements(rec.contract, events)
assert withpend['spend_usd'] == base['spend_usd'], (withpend, base)  # drift guard
seq = max(e['seq'] for e in events if e['type'] == 'adaptation')
resources.settle_cancellation(plan, 'seq-%d' % seq, 'released',
                              'cancelled before consuming')
events = rec.archived_events() + rec.read_journal()[0]
after = resources.pending_after_settlements(rec.contract, events)
assert after['spend_usd'] == 0.0, (after, base)  # released: never consumed
print('OK: released subtracts exactly once, zero-settlement equals scheduler')
PY
}

@test "routing: fixed-model default and both sides required" {
  _write_contract
  _approve
  run python3 "$RESOURCES" --plan "$PLAN" routing --caps '{}'
  [ "$status" -eq 0 ]
  grep -q '"posture": "fixed_model"' <<<"$output"
  grep -q 'contract grant model_routing' <<<"$output"
  grep -q 'host capability model_routing' <<<"$output"
  # the grant alone does not flip it: the host ability is still missing
  GRANT=model_routing _write_contract
  run python3 "$RESOURCES" --plan "$PLAN" routing --caps '{}'
  [ "$status" -eq 0 ]
  grep -q '"posture": "fixed_model"' <<<"$output"
  grep -q 'host capability model_routing' <<<"$output"
  # grant AND host ability together authorize switching
  run python3 "$RESOURCES" --plan "$PLAN" routing \
    --caps '{"model_routing": true}'
  [ "$status" -eq 0 ]
  grep -q '"posture": "switching_authorized"' <<<"$output"
}

@test "parallel dispatch needs the delegation grant and the host" {
  _write_contract
  run python3 "$RESOURCES" --plan "$PLAN" routing --caps '{}'
  [ "$status" -eq 0 ]
  grep -q '"posture": "sequential_only"' <<<"$output"
  grep -q 'contract grant agent_delegation' <<<"$output"
}

@test "an unknown counter family is advisory with the unit named" {
  UNIT=vibes _write_contract
  _approve
  _start
  run _report_field '{"meter_spend": true}' "next(r for r in report['limits'] if r['unit'] == 'vibes')['effective_mode']"
  [ "$status" -eq 0 ]
  grep -q "advisory (counter family unknown for unit 'vibes'" <<<"$output"
  run _report_field '{"meter_spend": true}' "report['unsupported_counters']"
  [ "$status" -eq 0 ]
  grep -q "spend_usd" <<<"$output"
}
