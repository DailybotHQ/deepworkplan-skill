#!/usr/bin/env bash
# v6 authorization core: propose/decide split, named refusals, bounded
# adaptation, starvation aging, envelope commit-plus-pending, static and
# adaptive scheduling under the same acceptance contracts (RFC 5).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
SCHED="$SK/shared/scheduler.py"

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_scheduler_bats"
  mkdir -p "$PLAN/analysis_results" "$TEST_REPO/src" "$TEST_REPO/docs"
  echo 'INV-closed-objects: pass - closed-object check ran' \
    > "$PLAN/analysis_results/inv.log"
  echo 'prepare input' > "$TEST_REPO/src/prepare.py"
  echo 'build input' > "$TEST_REPO/src/build.py"
  echo 'docs input' > "$TEST_REPO/docs/guide.md"
  _write_contract
}

teardown() {
  rm -rf "$TEST_REPO"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    find "$SK" -name '__pycache__' -o -name '*.pyc'
    return 1
  fi
}

# A four-task contract with a declared invariant, a scheduling block and
# an enforced envelope limit — the surface every rule in this suite binds.
_write_contract() {
  PLAN="$PLAN" python3 - <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
doc = {
  'schema': contract_v6.CONTRACT_SCHEMA_URL,
  'spec_version': '6.0.0',
  'plan': 'PLAN_scheduler_bats',
  'revision': 1,
  'created_at': '2026-09-26T00:00:00Z',
  'title': 'scheduler bats scenario',
  'outcome': {
    'statement': 'The core decides proposals deterministically.',
    'success_definition': 'Every named rule fires exactly where claimed.',
    'out_of_scope': ['live dispatch wiring']},
  'acceptance': {'criteria': [
    {'id': 'AC-prepare', 'statement': 'Prepare done',
     'observable_check': 'gate exit 0', 'accepted_evidence': ['observed']},
    {'id': 'AC-build', 'statement': 'Build done',
     'observable_check': 'gate exit 0', 'accepted_evidence': ['observed']},
    {'id': 'AC-docs', 'statement': 'Docs done',
     'observable_check': 'gate exit 0',
     'accepted_evidence': ['observed', 'asserted']},
    {'id': 'AC-docs2', 'statement': 'Second doc task done',
     'observable_check': 'gate exit 0', 'accepted_evidence': ['observed']}],
  },
  'invariants': [{'id': 'INV-closed-objects',
                  'statement': 'Records stay closed objects.'}],
  'scope': {'allowed_paths': ['src/', 'docs/'],
            'allowed_command_classes': ['test', 'true'],
            'forbidden_operations': ['network']},
  'authorization': {
    'mechanism': 'plan_authorship', 'authority': 'bats',
    'timestamp': '2026-09-26T00:00:00Z', 'boundaries': 'scenario only',
    'consent_checkpoints': []},
  'permissions': {'granted': ['fs_write_plan_scope'],
                  'not_granted': ['network_access', 'agent_delegation']},
  'dependencies': [],
  'resource_envelope': {'limits': [
    {'id': 'spend_usd', 'limit': 100, 'unit': 'USD', 'enforcement':
     'enforced', 'metering_source': 'bats: declared samples'}]},
  'scheduling': {'starvation_threshold_events': 2,
                 'max_adaptations_per_task': 2,
                 'max_retries_per_gate': 1},
  'tasks': [
    {'id': 'T-prepare', 'title': 'Prepare', 'prerequisites': [],
     'touched_surface': ['src/prepare.py'],
     'gate_intent': [{'criterion': 'AC-prepare', 'check': 'gate'}]},
    {'id': 'T-build', 'title': 'Build', 'prerequisites': ['T-prepare'],
     'touched_surface': ['src/build.py'],
     'gate_intent': [{'criterion': 'AC-build', 'check': 'gate'}]},
    {'id': 'T-docs', 'title': 'Docs', 'prerequisites': [],
     'touched_surface': ['docs/guide.md'],
     'gate_intent': [{'criterion': 'AC-docs', 'check': 'gate'}]},
    {'id': 'T-docs2', 'title': 'Same surface', 'prerequisites': [],
     'touched_surface': ['docs/guide.md'],
     'gate_intent': [{'criterion': 'AC-docs2', 'check': 'gate'}]},
  ],
}
cid = contract_v6.compute_contract_id(doc)
plan = os.environ['PLAN']
json.dump(dict(doc, contract_id=cid),
          open(os.path.join(plan, 'contract.json'), 'w'),
          indent=2, sort_keys=True)
PY
}

# -- scenario helpers (every append goes through the real writer) ---------

_approve() {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json "$(python3 -c 'import json,sys;print(json.dumps({"authority":"bats","mechanism":"plan_authorship","plan_digest":sys.argv[1]}))' "$(_cid)")" \
    --actor-kind human --actor-identity bats --idempotent
}

_cid() {
  python3 -c 'import json,sys;print(json.load(open(sys.argv[1]+"/contract.json"))["contract_id"])' "$PLAN"
}

_inv() {  # invariant evaluation with the closed grammar (A1: an
          # evaluation is an agent-mediated claim - recorded asserted,
          # never observed; the core reads pass/fail from the statement)
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "INV-closed-objects: pass"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/inv.log
}

_start() {  # task_start followed by the D3-6 invariant re-evaluation
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json "{\"task\": \"$1\"}" --actor-kind helper \
    --actor-identity "$SCHED" --idempotent
  _inv
}

_gate_ok() {  # a real observed gate execution (A1: only the helper runs it)
  python3 "$LEDGER" --plan "$PLAN" gate --task "$1" --json '"true"' \
    --criterion "$2" --no-reuse
}

_last_seq() {
  python3 -c 'import json,sys;print(json.loads(open(sys.argv[1]).readlines()[-1])["seq"])' "$PLAN/journal.ndjson"
}

_select() {
  python3 "$SCHED" authorize "$PLAN" --json "{\"type\": \"select\", \"task\": \"$1\"}"
}

# -- the suite --------------------------------------------------------------

@test "scheduler self-test passes" {
  run python3 "$SCHED" self-test
  [ "$status" -eq 0 ]
  grep -q 'self-test: OK' <<<"$output"
}

@test "no dispatch before the approval cites the live contract" {
  _inv
  run _select T-prepare
  [ "$status" -eq 10 ]
  grep -q '"rule": "approval-missing"' <<<"$output"
}

@test "a declared but never-evaluated invariant stops dispatch" {
  _approve
  run _select T-prepare
  [ "$status" -eq 10 ]
  grep -q '"rule": "invariant-unevaluated"' <<<"$output"
}

@test "a stale invariant evaluation (before task_start) stops dispatch" {
  _approve
  _inv                     # evaluated BEFORE the task starts
  # a bare task_start (no _start helper: that would re-evaluate after)
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-docs"}' --actor-kind helper \
    --actor-identity "$SCHED" --idempotent
  run _select T-docs
  [ "$status" -eq 10 ]
  grep -q '"rule": "invariant-stale"' <<<"$output"
}

@test "static walk: approval, fresh invariant, select, start, observed gate" {
  _approve
  _inv
  run _select T-prepare
  [ "$status" -eq 0 ]
  grep -q '"decision": "accept"' <<<"$output"
  _start T-prepare         # re-evaluates the invariant at/after start
  run _gate_ok T-prepare AC-prepare
  [ "$status" -eq 0 ]
  grep -q 'RAN: exit 0' <<<"$output"
}

@test "prerequisites: an unmet prerequisite refuses select" {
  _approve; _inv
  run _select T-build
  [ "$status" -eq 10 ]
  grep -q '"rule": "prerequisite-open"' <<<"$output"
}

@test "deferral disguised as completion: a restart reopens the window and stale evidence stops counting (D2-9b/M4)" {
  _approve; _inv
  _start T-prepare
  _gate_ok T-prepare AC-prepare
  run _select T-build
  [ "$status" -eq 0 ]       # in-window evidence unlocks the prerequisite
  # a restart: a new task_start reopens the evidence window (the LATEST
  # task_start is the boundary, not the first - M4)
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-prepare"}' --actor-kind helper \
    --actor-identity bats-restart --idempotent
  _inv                      # re-verify the boundary at/after the restart
  run _select T-build
  [ "$status" -eq 10 ]
  grep -q '"rule": "prerequisite-open"' <<<"$output"
  # the projection shows the pre-restart gate as stale, never satisfying
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  run python3 -c 'import json,sys;s=json.load(open(sys.argv[1]+"/state.json"));t=[x for x in s["tasks"] if x["id"]=="T-prepare"][0];print(json.dumps(t["criteria"]))' "$PLAN"
  grep -q '"satisfied": false' <<<"$output"
  grep -q 'stale_seqs' <<<"$output"
  # and the old forging path is closed outright (B1): a mediated append
  # can never mint a gate_run record
  run python3 "$LEDGER" --plan "$PLAN" append --type gate_run \
    --json '{"command": "true", "cwd": ".", "timeout_seconds": 30,
             "exit_code": 0, "criterion": "AC-prepare", "task": "T-prepare"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust observed \
    --evidence-path gates/pre-start.log
  [ "$status" -eq 1 ]
  grep -q 'produced only by the gate executor' <<<"$output"
}

@test "completion is earned: a satisfied prerequisite unlocks select" {
  _approve; _inv
  _start T-prepare
  _gate_ok T-prepare AC-prepare
  run _select T-build
  [ "$status" -eq 0 ]
}

@test "surface serialization: overlapping in-progress work is refused, independent work is not" {
  _approve; _inv
  _start T-docs
  run _select T-docs2
  [ "$status" -eq 10 ]
  grep -q '"rule": "surface-serialization"' <<<"$output"
  grep -q 'T-docs' <<<"$output"
  run _select T-prepare
  [ "$status" -eq 0 ]
}

@test "unknown task, completed task and closed proposal set" {
  _approve; _inv
  run _select T-nope
  [ "$status" -eq 10 ]
  grep -q '"rule": "unknown-task"' <<<"$output"
  run python3 "$SCHED" authorize "$PLAN" --json '{"type": "teleport"}'
  [ "$status" -eq 10 ]
  grep -q '"rule": "proposal-type"' <<<"$output"
}

@test "a prerequisite cycle is refused before any policy applies" {
  # cycle: rewrite the contract so T-build and T-prepare require each other
  PLAN="$PLAN" python3 - <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.getcwd(), 'skills/deepworkplan/shared'))
import contract_v6
plan = os.environ['PLAN']
doc = json.load(open(os.path.join(plan, 'contract.json')))
doc['tasks'][0]['prerequisites'] = ['T-build']
doc['tasks'][1]['prerequisites'] = ['T-prepare', 'T-build']
doc.pop('contract_id', None)
json.dump(doc, open(os.path.join(plan, 'contract.json'), 'w'),
          indent=2, sort_keys=True)
PY
  # no approval recorded: the invalid contract stops everything first
  run _select T-docs
  [ "$status" -eq 10 ]
  grep -q '"rule": "contract-invalid"' <<<"$output"
  grep -qi 'cycle' <<<"$output"
}

@test "an adaptation never carries criterion content (discarded requirements)" {
  _approve; _inv
  run python3 "$SCHED" authorize "$PLAN" --json \
    '{"type": "adapt", "kind": "change_strategy",
      "trigger_observation": 2, "evidence_artifact": "a.md",
      "hypothesis": "a second tactic converges",
      "action": "switch tactics", "rationale": "the first plateaued",
      "authority": "recorded observation",
      "affected_tasks": ["T-build"], "affected_criteria": [],
      "evidence_invalidated": [], "evidence_preserved": [],
      "resource_impact": {"declared": 0, "unit": "USD"},
      "revised_criterion": "AC-build: only when convenient"}'
  [ "$status" -eq 10 ]
  grep -q '"rule": "proposal-shape"' <<<"$output"
  # ...and the closed adaptation enumeration refuses a non-kind
  run python3 "$SCHED" authorize "$PLAN" --json \
    '{"type": "adapt", "kind": "drop_requirement",
      "trigger_observation": 2, "evidence_artifact": "a.md",
      "hypothesis": "fewer criteria", "action": "delete AC-build",
      "rationale": "it is hard", "authority": "nobody",
      "affected_tasks": ["T-build"], "affected_criteria": ["AC-build"],
      "evidence_invalidated": [], "evidence_preserved": [],
      "resource_impact": {"declared": 0, "unit": "USD"}}'
  [ "$status" -eq 10 ]
  grep -q '"rule": "adaptation-shape"' <<<"$output"
}

@test "an accepted adapt returns the recordable event; the writer accepts it; the cap then refuses" {
  _approve; _inv
  PROPOSAL='{"type": "adapt", "kind": "change_strategy",
    "trigger_observation": 2, "evidence_artifact": "a.md",
    "hypothesis": "a different tactic converges",
    "action": "switch tactics on T-build", "rationale": "plateau",
    "authority": "recorded observation",
    "affected_tasks": ["T-build"], "affected_criteria": [],
    "evidence_invalidated": [], "evidence_preserved": [],
    "resource_impact": {"declared": 0, "unit": "USD"}}'
  run python3 "$SCHED" authorize "$PLAN" --json "$PROPOSAL"
  [ "$status" -eq 0 ]
  grep -q '"decision": "accept"' <<<"$output"
  # extract the returned event body and append it through the real writer
  python3 "$SCHED" authorize "$PLAN" --json "$PROPOSAL" | \
    python3 -c 'import json,sys;d=json.load(sys.stdin);e=d["event"];body={k:v for k,v in e.items() if k not in ("schema","type","seq","ts","plan","contract_id","actor")};print(json.dumps(body))' > "$TEST_REPO/event.json"
  run python3 "$LEDGER" --plan "$PLAN" append --type adaptation \
    --json "$(cat "$TEST_REPO/event.json")" \
    --actor-kind agent --actor-identity "$SCHED"
  [ "$status" -eq 0 ]
  # a SECOND distinct adaptation on the same task: the cap (2) still allows
  SECOND='{"type": "adapt", "kind": "change_strategy",
    "trigger_observation": 2, "evidence_artifact": "a.md",
    "hypothesis": "a third tactic also converges",
    "action": "switch tactics again on T-build", "rationale": "plateau",
    "authority": "recorded observation",
    "affected_tasks": ["T-build"], "affected_criteria": [],
    "evidence_invalidated": [], "evidence_preserved": [],
    "resource_impact": {"declared": 0, "unit": "USD"}}'
  python3 "$SCHED" authorize "$PLAN" --json "$SECOND" | \
    python3 -c 'import json,sys;d=json.load(sys.stdin);e=d["event"];body={k:v for k,v in e.items() if k not in ("schema","type","seq","ts","plan","contract_id","actor")};print(json.dumps(body))' > "$TEST_REPO/event2.json"
  run python3 "$LEDGER" --plan "$PLAN" append --type adaptation \
    --json "$(cat "$TEST_REPO/event2.json")" \
    --actor-kind agent --actor-identity "$SCHED"
  [ "$status" -eq 0 ]
  # the third adaptation on the task: the contract-declared cap (2) refuses
  run python3 "$SCHED" authorize "$PLAN" --json "$PROPOSAL"
  [ "$status" -eq 10 ]
  grep -q '"rule": "adaptation-cap"' <<<"$output"
}

@test "blind retries are refused; a retry with a fresh trigger is authorized, then capped" {
  _approve; _inv
  _start T-prepare
  _gate_ok T-prepare AC-prepare
  GATE_SEQ=$(_last_seq)
  BLIND="{\"type\": \"adapt\", \"kind\": \"retry\",
    \"trigger_observation\": 1, \"evidence_artifact\": \"b.md\",
    \"hypothesis\": \"maybe flaky\", \"action\": \"retry the gate\",
    \"rationale\": \"hunch\", \"authority\": \"hunch\",
    \"affected_tasks\": [\"T-prepare\"], \"affected_criteria\": [\"AC-prepare\"],
    \"evidence_invalidated\": [], \"evidence_preserved\": [],
    \"resource_impact\": {\"declared\": 0, \"unit\": \"USD\"}}"
  run python3 "$SCHED" authorize "$PLAN" --json "$BLIND"
  [ "$status" -eq 10 ]
  grep -q '"rule": "blind-retry"' <<<"$output"
  # a discovery observation AFTER the last attempt justifies the retry
  # (asserted: a mediated forensic reading, never minted observed - A1)
  echo 'cache poisoned, not a defect' \
    > "$PLAN/analysis_results/gate-forensics.log"
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "the gate log shows a poisoned cache, not a defect"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/gate-forensics.log
  TRIGGER=$(_last_seq)
  FRESH="${BLIND/\"trigger_observation\": 1/\"trigger_observation\": $TRIGGER}"
  run python3 "$SCHED" authorize "$PLAN" --json "$FRESH"
  [ "$status" -eq 0 ]
  # record it, then a second fresh-trigger retry hits max_retries_per_gate
  python3 "$SCHED" authorize "$PLAN" --json "$FRESH" | \
    python3 -c 'import json,sys;d=json.load(sys.stdin);e=d["event"];body={k:v for k,v in e.items() if k not in ("schema","type","seq","ts","plan","contract_id","actor")};print(json.dumps(body))' > "$TEST_REPO/retry.json"
  python3 "$LEDGER" --plan "$PLAN" append --type adaptation \
    --json "$(cat "$TEST_REPO/retry.json")" \
    --actor-kind agent --actor-identity "$SCHED"
  echo 'second forensics pass confirms the cache' \
    > "$PLAN/analysis_results/gate-forensics-2.log"
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "second forensics pass confirms the cache"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/gate-forensics-2.log
  TRIGGER2=$(_last_seq)
  SECOND="${BLIND/\"trigger_observation\": 1/\"trigger_observation\": $TRIGGER2}"
  run python3 "$SCHED" authorize "$PLAN" --json "$SECOND"
  [ "$status" -eq 10 ]
  grep -q '"rule": "retry-cap"' <<<"$output"
}

@test "envelope: commit-plus-pending refuses the second commitment (A5)" {
  _approve; _inv
  # B1: observed metering is host-adapter-read and cites a real artifact
  printf '{"spend_usd": 99.5, "unit": "USD"}\n' \
    > "$PLAN/analysis_results/meter.json"
  python3 "$LEDGER" --plan "$PLAN" append --type resource_sample \
    --json '{"source": "bats-meter", "limit_id": "spend_usd",
             "value": 99.5, "unit": "USD"}' \
    --actor-kind host_adapter --actor-identity bats-meter \
    --trust observed --evidence-path analysis_results/meter.json
  run python3 "$SCHED" authorize "$PLAN" --json \
    '{"type": "adapt", "kind": "change_strategy",
      "trigger_observation": 2, "evidence_artifact": "a.md",
      "hypothesis": "costly variant", "action": "expand the search",
      "rationale": "coverage", "authority": "recorded observation",
      "affected_tasks": ["T-build"], "affected_criteria": [],
      "evidence_invalidated": [], "evidence_preserved": [],
      "resource_impact": {"declared": 5, "unit": "USD"}}'
  [ "$status" -eq 10 ]
  grep -q '"rule": "envelope-exceeded"' <<<"$output"
  grep -q 'commit-plus-pending' <<<"$output"
}

@test "starvation aging on the journal clock records a valid selection boost (A11)" {
  _approve; _inv
  _start T-prepare
  _gate_ok T-prepare AC-prepare
  # T-build became eligible; grow the journal past the threshold (2)
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "aging filler 1"}' --actor-kind helper \
    --actor-identity "$SCHED" --trust asserted
  python3 "$LEDGER" --plan "$PLAN" append --type observation \
    --json '{"statement": "aging filler 2"}' --actor-kind helper \
    --actor-identity "$SCHED" --trust asserted
  run python3 "$SCHED" ready "$PLAN"
  [ "$status" -eq 0 ]
  grep -q '"priority_boost": true' <<<"$output"
  grep -q '"threshold": "2"' <<<"$output"
  # the boost payload appends as a valid selection event
  python3 "$SCHED" boosts "$PLAN" | python3 -c 'import json,sys;print(json.dumps(json.load(sys.stdin)[0]))' > "$TEST_REPO/boost.json"
  run python3 "$LEDGER" --plan "$PLAN" append --type selection \
    --json "$(cat "$TEST_REPO/boost.json")" \
    --actor-kind helper --actor-identity "$SCHED"
  [ "$status" -eq 0 ]
}

@test "the core is read-only: authorize, ready and boosts never write" {
  _approve; _inv
  _start T-prepare
  BEFORE=$(md5sum "$PLAN/journal.ndjson" | cut -d' ' -f1)
  run _select T-build          # refused (prerequisite open) AND read-only
  [ "$status" -eq 10 ]
  run _select T-docs           # accepted AND read-only
  [ "$status" -eq 0 ]
  python3 "$SCHED" ready "$PLAN" >/dev/null
  python3 "$SCHED" boosts "$PLAN" >/dev/null
  AFTER=$(md5sum "$PLAN/journal.ndjson" | cut -d' ' -f1)
  [ "$BEFORE" = "$AFTER" ]
  [ ! -e "$PLAN/state.json" ]   # the projector is the only state writer
}

@test "static and adaptive scheduling pass the same acceptance contracts" {
  # Two identical plans. A walks contract order (static). B reorders docs
  # ahead of build after a recorded discovery (adaptive). Both complete the
  # same work; the final criterion satisfaction must be identical.
  B="$TEST_REPO/.dwp/plans/PLAN_scheduler_bats_b"
  cp -r "$PLAN" "$B"
  _b_append() {  # append to plan B through the real writer
    python3 "$LEDGER" --plan "$B" append "$@"
  }
  _b() {
    python3 "$LEDGER" --plan "$B" "$@"
  }
  # shared prologue in both plans: approval, invariant, T-prepare complete
  _approve; _inv
  _start T-prepare
  _gate_ok T-prepare AC-prepare
  _b_append --type approval \
    --json "$(python3 -c 'import json,sys;print(json.dumps({"authority":"bats","mechanism":"plan_authorship","plan_digest":sys.argv[1]}))' "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]+"/contract.json"))["contract_id"])' "$B")")" \
    --actor-kind human --actor-identity bats --idempotent
  _b_append --type observation \
    --json '{"statement": "INV-closed-objects: pass"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/inv.log
  _b_append --type task_start --json '{"task": "T-prepare"}' \
    --actor-kind helper --actor-identity "$SCHED" --idempotent
  _b_append --type observation \
    --json '{"statement": "INV-closed-objects: pass"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/inv.log
  _b gate --task T-prepare --json '"true"' --criterion AC-prepare --no-reuse

  # A (static, contract order): build, then docs, then docs2
  run _select T-build
  [ "$status" -eq 0 ]
  _start T-build
  _gate_ok T-build AC-build
  _start T-docs
  _gate_ok T-docs AC-docs
  _start T-docs2
  _gate_ok T-docs2 AC-docs2

  # B (adaptive): a discovery motivates reordering docs ahead of build
  echo 'the doc generator must ship before the build freeze' \
    > "$B/analysis_results/discovery.log"
  _b_append --type observation \
    --json '{"statement": "the doc generator must ship before the build freeze"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/discovery.log
  TRIGGER=$(python3 -c 'import json,sys;print(json.loads(open(sys.argv[1]).readlines()[-1])["seq"])' "$B/journal.ndjson")
  REORDER="{\"type\": \"adapt\", \"kind\": \"reorder\",
    \"trigger_observation\": $TRIGGER, \"evidence_artifact\": \"analysis_results/discovery.log\",
    \"hypothesis\": \"docs-first avoids a rebuild\", \"action\": \"do T-docs before T-build\",
    \"rationale\": \"the discovery\", \"authority\": \"recorded observation\",
    \"affected_tasks\": [\"T-build\", \"T-docs\"], \"affected_criteria\": [],
    \"evidence_invalidated\": [], \"evidence_preserved\": [],
    \"resource_impact\": {\"declared\": 0, \"unit\": \"USD\"}}"
  run python3 "$SCHED" authorize "$B" --json "$REORDER"
  [ "$status" -eq 0 ]
  python3 "$SCHED" authorize "$B" --json "$REORDER" | \
    python3 -c 'import json,sys;d=json.load(sys.stdin);e=d["event"];body={k:v for k,v in e.items() if k not in ("schema","type","seq","ts","plan","contract_id","actor")};print(json.dumps(body))' > "$TEST_REPO/reorder.json"
  _b_append --type adaptation --json "$(cat "$TEST_REPO/reorder.json")" \
    --actor-kind agent --actor-identity "$SCHED"

  # B's reordered walk: docs, then docs2, then build — the SAME authorize
  # decides every select, and every gate is the real observed executor.
  run python3 "$SCHED" authorize "$B" --json '{"type": "select", "task": "T-docs"}'
  [ "$status" -eq 0 ]
  _b_append --type task_start --json '{"task": "T-docs"}' \
    --actor-kind helper --actor-identity "$SCHED" --idempotent
  run python3 "$SCHED" authorize "$B" --json '{"type": "select", "task": "T-docs2"}'
  [ "$status" -eq 10 ]   # docs is in progress: serialization still binds
  _b_append --type observation \
    --json '{"statement": "INV-closed-objects: pass"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/inv.log
  _b gate --task T-docs --json '"true"' --criterion AC-docs --no-reuse
  # docs complete by its criteria: the sibling surface becomes selectable
  run python3 "$SCHED" authorize "$B" --json '{"type": "select", "task": "T-docs2"}'
  [ "$status" -eq 0 ]
  _b_append --type task_start --json '{"task": "T-docs2"}' \
    --actor-kind helper --actor-identity "$SCHED" --idempotent
  _b_append --type observation \
    --json '{"statement": "INV-closed-objects: pass"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/inv.log
  _b gate --task T-docs2 --json '"true"' --criterion AC-docs2 --no-reuse
  run python3 "$SCHED" authorize "$B" --json '{"type": "select", "task": "T-build"}'
  [ "$status" -eq 0 ]
  _b_append --type task_start --json '{"task": "T-build"}' \
    --actor-kind helper --actor-identity "$SCHED" --idempotent
  _b_append --type observation \
    --json '{"statement": "INV-closed-objects: pass"}' \
    --actor-kind helper --actor-identity "$SCHED" --trust asserted \
    --evidence-path analysis_results/inv.log
  _b gate --task T-build --json '"true"' --criterion AC-build --no-reuse

  # the final criterion satisfaction (task:criterion:trust) is IDENTICAL
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  python3 "$LEDGER" --plan "$B" project >/dev/null
  python3 -c 'import json,sys
s = json.load(open(sys.argv[1] + "/state.json"))
pairs = sorted("%s:%s:%s" % (t["id"], c["criterion"], c.get("trust", "open"))
               for t in s["tasks"] for c in t["criteria"])
print("\n".join(pairs))' "$PLAN" > "$TEST_REPO/sat_a.txt"
  python3 -c 'import json,sys
s = json.load(open(sys.argv[1] + "/state.json"))
pairs = sorted("%s:%s:%s" % (t["id"], c["criterion"], c.get("trust", "open"))
               for t in s["tasks"] for c in t["criteria"])
print("\n".join(pairs))' "$B" > "$TEST_REPO/sat_b.txt"
  cmp "$TEST_REPO/sat_a.txt" "$TEST_REPO/sat_b.txt"
  # every criterion closed by the same trust label in both walks
  [ "$(wc -l < "$TEST_REPO/sat_a.txt")" -eq 4 ]
  grep -q 'T-build:AC-build:observed' "$TEST_REPO/sat_b.txt"
  grep -q 'T-docs:AC-docs:observed' "$TEST_REPO/sat_b.txt"
  ! grep -q ':open' "$TEST_REPO/sat_b.txt"
}
