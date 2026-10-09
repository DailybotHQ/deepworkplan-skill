#!/usr/bin/env bash
# v6 execution ledger + generated views: write discipline, crash recovery,
# idempotence, staleness, completion refusal, view divergence (RFC 4).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
VIEWS="$SK/shared/views.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_ledger_bats"
  mkdir -p "$PLAN" "$TEST_REPO/src"
  echo 'check input v1' > "$TEST_REPO/src/check.txt"
  _write_contract
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

# Writes a v6 contract fixture whose single task's touched_surface is the
# scratch source file, stamped with its computed contract_id.
_write_contract() {
  PLAN="$PLAN" SRC="src/check.txt" python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.environ.get('PLAN', ''), '../../..'))
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import importlib.util
spec = importlib.util.spec_from_file_location(
    'c6', os.path.join(os.getcwd(), 'skills/deepworkplan/shared/contract_v6.py'))
c6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c6)
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_ledger_bats'
for task in doc['tasks']:
    task['touched_surface'] = [os.environ['SRC']]
doc['scope']['allowed_command_classes'] = [
    'cat', 'echo', 'true', 'definitely-not-a-command-xyz']
doc.pop('contract_id', None)
doc['invariants'] = []  # invariant enforcement is covered by tests/v7-amend.bats
cid = c6.compute_contract_id(doc)
json.dump(dict(doc, contract_id=cid), open(os.path.join(
    os.environ['PLAN'], 'contract.json'), 'w'), indent=2, sort_keys=True)
PY
}

@test "ledger and views self-tests pass" {
  run python3 "$LEDGER" self-test
  [ "$status" -eq 0 ]
  grep -q 'self-test: OK' <<<"$output"
  run python3 "$VIEWS" self-test
  [ "$status" -eq 0 ]
  grep -q 'self-test: OK' <<<"$output"
}

@test "inspect reads the plan and reports zero events" {
  run python3 "$LEDGER" --plan "$PLAN" inspect
  [ "$status" -eq 0 ]
  grep -q 'PLAN_ledger_bats' <<<"$output"
  grep -q '0 events' <<<"$output"
}

@test "task_start before approval is refused and the refusal recorded" {
  run python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  [ "$status" -eq 3 ]
  grep -q 'no approval event cites the live contract_id' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'refusal' <<<"$output"
}

@test "approval then task_start works; duplicate submission is idempotent" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  run python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  [ "$status" -eq 0 ]
  # exactly one task_start event despite two submissions
  run python3 "$LEDGER" --plan "$PLAN" inspect
  [ "$(grep -c 'task_start' <<<"$output")" -eq 1 ]
}

@test "gate executes a real command and records observed evidence" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"'
  [ "$status" -eq 0 ]
  grep -q 'RAN: exit 0' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'gate_run' <<<"$output"
  ls "$PLAN"/gates/T-publish-schemas/*.log >/dev/null
}

@test "a failing gate propagates its exit code and keeps the log" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"echo out; echo err >&2; exit 7"'
  [ "$status" -eq 1 ]
  run bash -c "grep -l 'err' $PLAN/gates/T-publish-schemas/*.log"
  [ "$status" -eq 0 ]
}

@test "equivalent input reuses evidence; changed input re-runs" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"' >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"'
  [ "$status" -eq 0 ]
  grep -q 'REUSED: exit 0' <<<"$output"
  echo 'check input v2 — changed' > "$TEST_REPO/src/check.txt"
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"'
  [ "$status" -eq 0 ]
  grep -q 'RAN: exit 0' <<<"$output"
}

@test "a command that never runs records no event; a shell 127 is history" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  # array form: exec'd without a shell — a missing binary never ran
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape \
    --json '["definitely-not-a-command-xyz"]'
  [ "$status" -eq 1 ]
  grep -q 'no event is recorded' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  ! grep -q 'gate_run' <<<"$output"
  # string form runs through a shell: a 127 IS an execution, recorded honestly
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape \
    --json '"definitely-not-a-command-xyz"'
  [ "$status" -eq 1 ]
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'gate_run' <<<"$output"
}

@test "projection is deterministic and carries v6 positions" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  cp "$PLAN/state.json" "$TEST_REPO/state-1.json"
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  cmp "$TEST_REPO/state-1.json" "$PLAN/state.json"
  grep -q 'plan-snapshot/v6.json' "$PLAN/state.json"
  grep -q '"task_start"' "$PLAN/state.json"
}

@test "completion with zero evidence is refused (zero-test control)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
  grep -q 'zero-test control' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  [ "$(grep -c 'refusal' <<<"$output")" -eq 1 ]
}

@test "a restart reopens the evidence window: pre-restart evidence is stale (M4)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"' >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
  # a SECOND task_start (new session actor) restarts the attempt: the
  # window anchors on the LATEST task_start, so the first attempt's
  # observed evidence is stale and can never satisfy the new attempt
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --actor-identity bats-restart \
    --idempotent
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
  grep -q 'lack in-window accepted evidence' <<<"$output"
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  python3 - "$PLAN/state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
crit = [c for t in state['tasks'] if t['id'] == 'T-publish-schemas'
        for c in t['criteria']]
assert crit and crit[0].get('stale_seqs') == [3], crit
assert crit[0].get('satisfied') is False, crit
print('stale carried:', crit[0]['stale_seqs'])
PY
}

@test "append can never mint gate_run records or observed trust (B1/A1)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  mkdir -p "$PLAN/analysis_results"
  echo '{"spend_usd": 1.0}' > "$PLAN/analysis_results/meter.json"
  # a mediated write can never be observed gate evidence
  run python3 "$LEDGER" --plan "$PLAN" append --type gate_run \
    --json '{"command": "cat src/check.txt", "cwd": ".", "timeout_seconds": 30,
             "exit_code": 0, "criterion": "AC-valid-contract-shape",
             "task": "T-publish-schemas"}' \
    --actor-kind helper --actor-identity dwp-ledger/6.0 --trust observed \
    --evidence-path 'gates/x.log'
  [ "$status" -eq 1 ]
  grep -q 'produced only by the gate executor' <<<"$output"
  # observations are agent-mediated claims: asserted, never observed
  run python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "looks green"}' --actor-kind helper \
    --actor-identity dwp-ledger/6.0 --trust observed \
    --evidence-path 'analysis_results/meter.json'
  [ "$status" -eq 1 ]
  grep -q 'minted only by execution' <<<"$output"
  # observed metering requires a host_adapter that read the meter
  run python3 "$LEDGER" --plan "$PLAN" append --type resource_sample \
    --json '{"source": "bats-meter", "limit_id": "spend_usd", "value": 1.0,
             "unit": "USD"}' \
    --actor-kind agent --actor-identity bats --trust observed \
    --evidence-path 'analysis_results/meter.json'
  [ "$status" -eq 1 ]
  grep -q 'host_adapter' <<<"$output"
  # and the cited artifact must exist
  run python3 "$LEDGER" --plan "$PLAN" append --type resource_sample \
    --json '{"source": "bats-meter", "limit_id": "spend_usd", "value": 1.0,
             "unit": "USD"}' \
    --actor-kind host_adapter --actor-identity bats-meter --trust observed \
    --evidence-path 'analysis_results/nope.json'
  [ "$status" -eq 1 ]
  grep -q 'does not resolve' <<<"$output"
  # the one legal non-gate observed record: host adapter, real artifact
  run python3 "$LEDGER" --plan "$PLAN" append --type resource_sample \
    --json '{"source": "bats-meter", "limit_id": "spend_usd", "value": 1.0,
             "unit": "USD"}' \
    --actor-kind host_adapter --actor-identity bats-meter --trust observed \
    --evidence-path 'analysis_results/meter.json'
  [ "$status" -eq 0 ]
  # none of the refused appends left a record behind
  run python3 "$LEDGER" --plan "$PLAN" inspect
  [ "$(grep -c 'gate_run' <<<"$output")" -eq 0 ]
  [ "$(grep -c 'resource_sample' <<<"$output")" -eq 1 ]
}

@test "gate runs bind to declared intent, task start and command class (M5)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  # observed evidence exists only inside an attempt: no task_start, no gate
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"'
  [ "$status" -eq 1 ]
  grep -q 'no task_start' <<<"$output"
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  # the criterion must be one this task declares
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-journal-catalog-closed --json '"cat src/check.txt"'
  [ "$status" -eq 1 ]
  grep -q 'not declared in task' <<<"$output"
  # the command must be inside the declared command classes
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"grep -c x src/check.txt"'
  [ "$status" -eq 1 ]
  grep -q 'outside the contract declared command classes' <<<"$output"
  # nothing was recorded for the refused runs
  run python3 "$LEDGER" --plan "$PLAN" inspect
  ! grep -q 'gate_run' <<<"$output"
}

@test "a replayed task_start under an unapproved revision is refused (M1)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  # revision 2 exists but carries no approval: the replayed event would
  # be content-identical to the recorded one — the approval gate runs
  # BEFORE dedup, so the replay is refused instead of silently accepted
  python3 - "$PLAN/contract.json" <<'PY'
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location(
    'c6', os.path.join(os.getcwd(), 'skills/deepworkplan/shared/contract_v6.py'))
c6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c6)
doc = json.load(open(sys.argv[1]))
doc['revision'] = 2
doc['parent_contract_id'] = doc.pop('contract_id')
doc['tasks'][0]['title'] += ' (revision 2)'
cid2 = c6.compute_contract_id(doc)
json.dump(dict(doc, contract_id=cid2), open(sys.argv[1], 'w'),
          indent=2, sort_keys=True)
PY
  run python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  [ "$status" -eq 3 ]
  grep -q 'no approval event cites the live contract_id' <<<"$output"
}

@test "a complete final event that lost only its newline is restored (B2)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"' >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
  # simulate the interrupted append that lost only the framing byte
  python3 - "$PLAN/journal.ndjson" <<'PY'
import sys
raw = open(sys.argv[1], 'rb').read()
assert raw.endswith(b'\n')
open(sys.argv[1], 'wb').write(raw[:-1])
PY
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "post-framing"}' --trust asserted >/dev/null
  # the complete gate_run event survived; the newline is back
  run python3 "$LEDGER" --plan "$PLAN" inspect
  [ "$(grep -c 'gate_run' <<<"$output")" -eq 1 ]
  grep -q 'framing newline restored' "$PLAN/journal.ndjson"
  [ "$(tail -c 1 "$PLAN/journal.ndjson" | wc -l)" -eq 1 ]
  # completion still holds on the preserved evidence
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
  # reopening again is stable: exactly one repair of any kind
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "stability"}' --trust asserted >/dev/null
  [ "$(grep -c 'journal_repair' "$PLAN/journal.ndjson")" -eq 1 ]
}

@test "after a roll the plan continues: approval and evidence survive (B3)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"' >/dev/null
  python3 "$LEDGER" --plan "$PLAN" roll >/dev/null
  # the replayed task_start dedups against the archive instead of being
  # refused as unapproved (the archived approval still binds)
  run python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  [ "$status" -eq 0 ]
  # the archived gate evidence still satisfies completion
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  python3 - "$PLAN/state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
task = [t for t in state['tasks'] if t['id'] == 'T-publish-schemas'][0]
# status derives completed once every criterion is in-window satisfied
assert task['status'] == 'completed', task
assert task['started_seq'] == 2, task
assert task['criteria'][0]['satisfied'] is True, task
print('post-roll projection intact')
PY
}

@test "observed evidence after task_start satisfies completion" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111111"}' 2>/dev/null \
    || python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  # run gates for every criterion the task's gate_intent declares
  for crit in $(python3 -c '
import json, sys
doc = json.load(open(sys.argv[1]))
for t in doc["tasks"]:
    if t["id"] == "T-publish-schemas":
        print(" ".join(g["criterion"] for g in t["gate_intent"]))
' "$PLAN/contract.json"); do
    python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
      --criterion "$crit" --json '"true"' >/dev/null
  done
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
  grep -q 'criteria satisfied' <<<"$output"
}

@test "a torn tail is repaired with a journal_repair event" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  printf '{"schema": "https://deepworkplan.com/schema/journal' >> "$PLAN/journal.ndjson"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'TORN TAIL' <<<"$output"
  # a writer open repairs it and records the repair
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'journal_repair' <<<"$output"
  ! grep -q 'TORN TAIL' <<<"$output"
}

@test "the cooperative lock refuses a second writer" {
  mkdir "$PLAN/.ledger.lock"
  # pid 1 exists on every host (and is unsignalable as non-root: EPERM
  # means alive, never dead) with a fresh epoch timestamp: not stale
  echo '{"identity": "other writer", "pid": 1, "epoch_ts": 99999999999.0}' \
    > "$PLAN/.ledger.lock/owner.json"
  run python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "x"}' --trust asserted
  [ "$status" -eq 1 ]
  grep -q 'another writer holds the plan lock' <<<"$output"
}

@test "views render deterministically and refuse human edits" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$VIEWS" --plan "$PLAN" render --view tasks,evidence,audit
  [ "$status" -eq 0 ]
  grep -q 'dwp-view: tasks' "$PLAN/views/tasks.md"
  cp "$PLAN/views/tasks.md" "$TEST_REPO/tasks-1.md"
  python3 "$VIEWS" --plan "$PLAN" render --view tasks,evidence,audit >/dev/null
  cmp "$TEST_REPO/tasks-1.md" "$PLAN/views/tasks.md"
  printf '\nHUMAN NOTE\n' >> "$PLAN/views/tasks.md"
  run python3 "$VIEWS" --plan "$PLAN" render --view tasks
  [ "$status" -eq 5 ]
  grep -q 'refusing to overwrite silently' <<<"$output"
}

@test "an intact generated view refreshes after the snapshot changes; a hand-edited one still refuses" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  run python3 "$VIEWS" --plan "$PLAN" render --view tasks,evidence,audit
  [ "$status" -eq 0 ]
  cp "$PLAN/views/tasks.md" "$TEST_REPO/tasks-1.md"
  # new records move the snapshot on; the views on disk are untouched
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" project
  cmp "$TEST_REPO/tasks-1.md" "$PLAN/views/tasks.md"
  # intact + stale: refreshed in place, no divergence, no reconciliation
  run python3 "$VIEWS" --plan "$PLAN" render --view tasks,evidence,audit
  [ "$status" -eq 0 ]
  grep -q 'OK: rendered' <<<"$output"
  run ! cmp -s "$TEST_REPO/tasks-1.md" "$PLAN/views/tasks.md"
  run grep -q 'reconciliation' "$PLAN/journal.ndjson"
  [ "$status" -eq 1 ]
  # the refreshed bytes are the recorded ones: an edit after it still refuses
  printf '\nHUMAN NOTE\n' >> "$PLAN/views/tasks.md"
  run python3 "$VIEWS" --plan "$PLAN" render --view tasks
  [ "$status" -eq 5 ]
  grep -q 'refusing to overwrite silently' <<<"$output"
}

@test "generated-wins reconciliation preserves the human copy and records authority" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$VIEWS" --plan "$PLAN" render --view tasks >/dev/null
  printf '\nHUMAN NOTE\n' >> "$PLAN/views/tasks.md"
  run python3 "$VIEWS" --plan "$PLAN" render --view tasks \
    --reconcile generated-wins --authority "bats operator"
  [ "$status" -eq 0 ]
  grep -q 'HUMAN NOTE' "$PLAN/views/tasks.human.md"
  grep -q 'dwp-view: tasks' "$PLAN/views/tasks.md"
  grep -q 'reconciliation' "$PLAN/journal.ndjson"
  grep -q 'bats operator' "$PLAN/journal.ndjson"
}

@test "export copies journal, snapshot, contracts and the evidence chain (A10/M2)" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --criterion AC-valid-contract-shape --json '"cat src/check.txt"' >/dev/null
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" export --dest "$TEST_REPO/export"
  [ "$status" -eq 0 ]
  ls "$TEST_REPO/export/journal.ndjson" >/dev/null
  ls "$TEST_REPO/export/state.json" >/dev/null
  ls "$TEST_REPO/export/EXPORT_MANIFEST.json" >/dev/null
  # M2: the reuse cache and every gates/ log travel too — the exported
  # snapshot cites evidence that must resolve inside the export
  ls "$TEST_REPO/export/evidence.jsonl" >/dev/null
  ls "$TEST_REPO/export"/gates/T-publish-schemas/*.log >/dev/null
  python3 - "$TEST_REPO/export" <<'PY'
import hashlib, json, os, sys
d = sys.argv[1]
m = json.load(open(os.path.join(d, 'EXPORT_MANIFEST.json')))
for name, digest in m['files'].items():
    raw = open(os.path.join(d, name), 'rb').read()
    assert hashlib.sha256(raw).hexdigest() == digest, name
# every evidence_path the snapshot cites resolves inside the export
state = json.load(open(os.path.join(d, 'state.json')))
for task in state['tasks']:
    for crit in task['criteria']:
        path = crit.get('evidence_path')
        if path:
            assert os.path.isfile(os.path.join(d, path)), path
assert 'missing_evidence' not in m, m.get('missing_evidence')
print('digests and evidence chain verified')
PY
}

@test "roll archives without deleting and continues the sequence" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --human-note "$BATS_TEST_DIRNAME/fixtures/v6/human-note.md" --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$LEDGER" --plan "$PLAN" roll
  [ "$status" -eq 0 ]
  ls "$PLAN"/journal-archive-*.ndjson >/dev/null
  [ -s "$PLAN"/journal-archive-*.ndjson ]
  # the live journal restarts empty and the next event continues the seq
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "post-roll"}' --trust asserted >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'seq 3' <<<"$output" || grep -qE '^ *3 observation' <<<"$output"
  grep -q 'journal-archive' "$PLAN/state.json"
}
