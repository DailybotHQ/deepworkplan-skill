#!/usr/bin/env bash
# v6 lifecycle wiring (task 17): the plan-generation flows around the v6
# core. These tests drive the SHIPPED surface end to end — markdown plan +
# contract draft -> ledger materialize (manifest -> contract -> approval)
# -> scheduler ready -> start -> gate -> complete -> project -> views ->
# receipt -> export — plus the flow wiring itself (create/v6.md,
# execute/v6.md, the SKILL.md branches, spec/V6_LIFECYCLE.md) and the
# refusals that make a hand-copied plan not-a-plan.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SHARED="$SK/shared"
LEDGER="$SHARED/ledger.py"
SCHED="$SHARED/scheduler.py"
OUT="$SHARED/outcomes.py"
VIEWS="$SHARED/views.py"
CM="$SHARED/context_manifest.py"
RES="$SHARED/resources.py"
CV6="$SHARED/contract_v6.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_lifecycle_bats"
  mkdir -p "$PLAN" "$PLAN/analysis_results" "$TEST_REPO/src"
  printf '# Goal\n\nWire the v6 lifecycle end to end.\n' > "$PLAN/README.md"
  printf 'def product(x):\n    return x\n' > "$TEST_REPO/src/product.py"
}

teardown() {
  rm -rf "$TEST_REPO"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    find "$SK" -name '__pycache__' -o -name '*.pyc'
    return 1
  fi
}

# Build a two-task contract draft for THIS plan folder: python3-class gates
# only, both criteria observed, prerequisites forming a chain.
_draft() { # _draft [plan_name]
  PLAN_NAME="${1:-PLAN_lifecycle_bats}" PLAN_DIR="$PLAN" \
    python3 - "$FIXTURE" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
doc = json.load(open(sys.argv[1]))
doc['plan'] = os.environ['PLAN_NAME']
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
doc.pop('contract_id', None)
json.dump(doc, open(os.path.join(os.environ['PLAN_DIR'], 'draft.json'), 'w'),
          indent=2, sort_keys=True)
PY
}

_materialize() { # _materialize [extra args...]
  python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" "$@"
}

_journal_types() { python3 -c '
import json, sys
print(" ".join(json.loads(l)["type"] for l in open(sys.argv[1])))' \
  "$PLAN/journal.ndjson"; }

# ---------------------------------------------------------------- lifecycle

@test "the full v6 lifecycle runs through the shipped surface" {
  _draft
  run _materialize --authority developer --mechanism plan_authorship
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'OK: materialized'
  # A12 order landed: manifest pointer -> stamped contract -> first event
  python3 - "$PLAN" <<'PY'
import json, os, sys
plan = sys.argv[1]
man = json.load(open(os.path.join(plan, 'manifest.json')))
con = json.load(open(os.path.join(plan, 'contract.json')))
assert man['schema'] == 'https://deepworkplan.com/schema/plan-manifest/v6.json'
assert man['plan'] == 'PLAN_lifecycle_bats'
assert man['contract']['id'] == con['contract_id']
first = json.loads(open(os.path.join(plan, 'journal.ndjson')).readline())
assert first['type'] == 'approval', first
assert first['contract_id'] == con['contract_id']
assert first['mechanism'] == 'plan_authorship'
PY
  # selection is the scheduler's decision, not the model's
  run python3 "$SCHED" ready "$PLAN"
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF '"task": "T-publish-schemas"'
  # the per-task context manifest re-anchors cheaply
  run python3 "$CM" --plan "$PLAN" manifest --task T-publish-schemas --md
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'T-publish-schemas'
  # start records the starting fingerprint
  run python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'OK: task_start'
  # gate through the runner: observed evidence, bound to the criterion
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
      --criterion AC-valid-contract-shape \
      --json '"python3 --version"'
  [ "$status" -eq 0 ]
  # guarded closure holds until the task's own criteria are satisfied
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
  # task 2 dispatches; completion refuses BEFORE its gate runs (exit 4)
  run python3 "$SCHED" ready "$PLAN"
  printf '%s' "$output" | grep -qF '"task": "T-ship-validator"'
  run python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-ship-validator
  [ "$status" -eq 4 ]
  printf '%s' "$output" | grep -qiF 'refus'
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-ship-validator \
      --criterion AC-journal-catalog-closed \
      --json '"python3 --version"'
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-ship-validator
  [ "$status" -eq 0 ]
  # derived completion projects into the snapshot
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  python3 - "$PLAN" <<'PY'
import json, os, sys
state = json.load(open(os.path.join(sys.argv[1], 'state.json')))
st = {t['id']: t['status'] for t in state['tasks']}
assert st == {'T-publish-schemas': 'completed',
              'T-ship-validator': 'completed'}, st
PY
  # zero work remaining: the scheduler has nothing to dispatch
  run python3 "$SCHED" ready "$PLAN"
  [ "$status" -eq 0 ]
  [ "$(printf '%s' "$output" | python3 -c \
      'import json,sys; print(len(json.load(sys.stdin)))')" -eq 0 ]
  # views render from the records; the receipt recomputes; export persists
  run python3 "$VIEWS" --plan "$PLAN" render --all
  [ "$status" -eq 0 ]
  [ -f "$PLAN/views/tasks.md" ]
  run python3 "$OUT" --plan "$PLAN" receipt
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" export --dest "$PLAN/analysis_results"
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'OK: exported'
}

@test "trust mode is mode-uniform: pre_authorization opens the same gate" {
  _draft
  run _materialize --authority developer --mechanism pre_authorization
  [ "$status" -eq 0 ]
  python3 - "$PLAN" <<'PY'
import json, os, sys
plan = sys.argv[1]
first = json.loads(open(os.path.join(plan, 'journal.ndjson')).readline())
assert first['mechanism'] == 'pre_authorization', first
PY
  run python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas
  [ "$status" -eq 0 ]
}

@test "an interrupted materialization resumes; nothing is hand-written" {
  _draft
  # crash window 1: manifest kept, contract + journal lost
  _materialize >/dev/null
  mv "$PLAN/manifest.json" "$TEST_REPO/manifest.before"
  rm "$PLAN/contract.json" "$PLAN/journal.ndjson"
  run _materialize
  [ "$status" -eq 0 ]
  cmp "$TEST_REPO/manifest.before" "$PLAN/manifest.json"
  [ -f "$PLAN/contract.json" ]
  [ "$(_journal_types)" = 'approval' ]
  # crash window 2: contract kept, approval lost — re-run appends it
  rm "$PLAN/journal.ndjson"
  run _materialize
  [ "$status" -eq 0 ]
  [ "$(_journal_types)" = 'approval' ]
  cmp "$TEST_REPO/manifest.before" "$PLAN/manifest.json"
  # a full re-run is idempotent and says it resumed
  run _materialize
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'resumed an interrupted materialization'
  [ "$(_journal_types)" = 'approval' ]
}

@test "a different contract never rewrites a materialized plan" {
  _draft
  _materialize >/dev/null
  before="$(cat "$PLAN/contract.json")"
  python3 - "$PLAN/draft.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc['outcome']['statement'] += ' (changed acceptance is a revision)'
json.dump(doc, open(sys.argv[1], 'w'), indent=2, sort_keys=True)
PY
  run _materialize
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'never rewrite'
  [ "$(cat "$PLAN/contract.json")" = "$before" ]
}

@test "direct edits never become plans: no approval means no start" {
  # hand-copied contract, no materialization -> the gate stays shut
  python3 - "$FIXTURE" "$PLAN" "$SHARED" <<'PY'
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[3])
import contract_v6  # noqa: E402
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_lifecycle_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
doc.pop('contract_id', None)
cid = contract_v6.compute_contract_id(doc)
json.dump(dict(doc, contract_id=cid),
          open(os.path.join(sys.argv[2], 'contract.json'), 'w'))
PY
  run python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas
  [ "$status" -eq 3 ]
  rm "$PLAN/contract.json"
  # a manifest pointer without a contract is discoverable but not executable
  _draft
  _materialize >/dev/null
  rm "$PLAN/contract.json"
  run python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas
  [ "$status" -ne 0 ]
}

@test "a v5-generation manifest is refused and left untouched" {
  _draft
  printf '{"schema": "https://deepworkplan.com/schema/plan-manifest/v5.json", "spec_version": "5.0.0"}\n' \
    > "$PLAN/manifest.json"
  run _materialize
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'never rewritten'
  grep -qF 'plan-manifest/v5.json' "$PLAN/manifest.json"
  [ ! -f "$PLAN/contract.json" ]
}

@test "a plan folder with no markdown is not approvable" {
  _draft
  rm "$PLAN/README.md"
  run _materialize
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'not approvable'
  [ ! -f "$PLAN/contract.json" ]
}

@test "a contract naming another folder is refused at materialization" {
  _draft PLAN_someone_else
  run _materialize
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'does not match the plan folder'
  [ ! -f "$PLAN/manifest.json" ]
}

@test "a missing gate binary is a recorded failure, never a pass" {
  _draft
  _materialize >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  # a command in-class that cannot succeed: recorded as a FAILED gate run,
  # never rounded up to a pass
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
      --criterion AC-valid-contract-shape \
      --json '"python3 /definitely/missing/probe_gate.py"'
  [ "$status" -eq 1 ]
  printf '%s' "$output" | grep -qF 'RAN: exit 2'
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
}

@test "status and verify surfaces are read-only over a live plan" {
  _draft
  _materialize >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  before="$(find "$PLAN" -type f ! -path '*.ledger.lock*' \
            -exec sha256sum {} + | sort)"
  run python3 "$LEDGER" --plan "$PLAN" inspect; [ "$status" -eq 0 ]
  run python3 "$SCHED" ready "$PLAN"; [ "$status" -eq 0 ]
  run python3 "$RES" --plan "$PLAN" report;  [ "$status" -eq 0 ]
  run python3 "$RES" --plan "$PLAN" routing; [ "$status" -eq 0 ]
  run python3 "$RES" --plan "$PLAN" hold;    [ "$status" -eq 0 ]
  run python3 "$OUT" --plan "$PLAN" receipt; [ "$status" -eq 0 ]
  run python3 "$CV6" validate-contract "$PLAN/contract.json"
  [ "$status" -eq 0 ]
  run python3 "$CV6" validate-journal "$PLAN/journal.ndjson" \
      --contract "$PLAN/contract.json"; [ "$status" -eq 0 ]
  after="$(find "$PLAN" -type f ! -path '*.ledger.lock*' \
           -exec sha256sum {} + | sort)"
  [ "$before" = "$after" ]
}

@test "a v6 plan folder next to a v5 plan folder: no cross-generation writes" {
  _draft
  _materialize >/dev/null
  V5="$TEST_REPO/.dwp/plans/PLAN_v5_neighbor"
  mkdir -p "$V5"
  printf '# Old plan\n\nPlan Status: 1/2 completed\n' > "$V5/README.md"
  printf '{"schema": "https://deepworkplan.com/schema/plan-state/v5.json", "spec_version": "5.0.0", "plan": "PLAN_v5_neighbor"}\n' \
    > "$V5/manifest.json"
  before="$(sha256sum "$V5/manifest.json")"
  # the v6 ledger serves v6 contracts only: the v5 folder is refused read
  run python3 "$LEDGER" --plan "$V5" inspect
  [ "$status" -ne 0 ]
  [ "$(sha256sum "$V5/manifest.json")" = "$before" ]
  # materializing a v6 contract INTO the v5 folder is refused (RFC 9.2)
  python3 - "$PLAN/draft.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_v5_neighbor'
json.dump(doc, open(sys.argv[1] + '.v5', 'w'))
PY
  run python3 "$LEDGER" --plan "$V5" materialize \
      --contract "$PLAN/draft.json.v5"
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'never rewritten'
  [ "$(sha256sum "$V5/manifest.json")" = "$before" ]
}

# ------------------------------------------------------------- flow wiring

@test "execute/SKILL.md gates the v6 loop behind Step 2.0 detection" {
  grep -qF '**Step 2.0 — Detect plan generation (v6).**' "$SK/execute/SKILL.md"
  grep -qF 'read only when Step 2.0 detects a' "$SK/execute/SKILL.md"
  # the conditional bullet is INDENTED: the entry bundle stays flat
  grep -qE '^  - \[`v6\.md`\]\(v6\.md\)' "$SK/execute/SKILL.md"
  # the v5 loop is never applied to a v6 plan, nor vice versa
  grep -qF 'never migrated to v6' "$SK/execute/SKILL.md"
  grep -qF '`contracts/` revision chain, this is a **v6 plan**' \
    "$SK/execute/SKILL.md"
}

@test "create/SKILL.md gates the v6 candidate behind Step 0.3 activation" {
  grep -qF '**0.3 Detect the v6 candidate:**' "$SK/create/SKILL.md"
  grep -qE '^  - \[`v6\.md`\]\(v6\.md\)' "$SK/create/SKILL.md"
  grep -qF 'never produce a v6 plan silently' "$SK/create/SKILL.md"
  # the activation rule is stated both ways (override + never-default)
  grep -qF 'explicit candidate request overrides a 5.x line' \
    "$SK/create/SKILL.md"
}

@test "the router carries the generation rule; status/verify/refine route v6" {
  grep -qF '**Plan generation is detected, never assumed.**' "$SK/SKILL.md"
  grep -qF 'Both generations can coexist' "$SK/SKILL.md"
  grep -qF 'v6 plans first' "$SK/status/SKILL.md"
  grep -qF 'stays read-only' "$SK/status/SKILL.md"
  grep -qF 'v6 generation check' "$SK/verify/SKILL.md"
  grep -qF 'contract amendments' "$SK/refine/SKILL.md"
  grep -qF 'V6_LIFECYCLE.md' "$SK/refine/SKILL.md"
}

@test "spec/V6_LIFECYCLE.md states the normative wiring and is indexed" {
  [ -f "$SK/spec/V6_LIFECYCLE.md" ]
  for section in 'Generation detection' 'Activation' 'Materialization order' \
                 'The execution boundary' 'Amendment' 'Read-only surfaces' \
                 'Coexistence'; do
    grep -qE "^## [0-9]+\. $section" "$SK/spec/V6_LIFECYCLE.md" || {
      echo "missing section: $section"; return 1; }
  done
  grep -qF 'manifest → contract → approval' "$SK/spec/V6_LIFECYCLE.md"
  grep -qF 'V6_LIFECYCLE.md' "$SK/spec/README.md"
  grep -qF 'Materialization order' "$SK/spec/PLAN_STATE.md"
  grep -qF 'plan-manifest/v6.json' "$SK/spec/PLAN_STATE.md"
}

@test "the manifest schema exists, is closed, and pins the pointer shape" {
  [ -f "$SK/spec/schema/plan-manifest-v6.schema.json" ]
  grep -qF '"additionalProperties": false' \
    "$SK/spec/schema/plan-manifest-v6.schema.json"
  grep -qF '"const": "contract.json"' \
    "$SK/spec/schema/plan-manifest-v6.schema.json"
}

@test "paths.tsv models the two v6 paths with flat entry bundles" {
  for pid in create-v6 execute-v6; do
    grep -qE "^$pid	entry	" tests/efficiency/paths.tsv
  done
  grep -qF 'create-v6	v6-candidate' tests/efficiency/paths.tsv
  grep -qF 'execute-v6	v6-loop' tests/efficiency/paths.tsv
  # entry phases are the flows' compulsory sets — v6.md is a triggered read
  [ "$(grep -cE '^create-v6	entry	' tests/efficiency/paths.tsv)" -eq 4 ]
  [ "$(grep -cE '^execute-v6	entry	' tests/efficiency/paths.tsv)" -eq 2 ]
}

@test "the v6 loop prose commands match the shipped CLIs" {
  # every command the v6 flow files name exists with that subcommand
  grep -qF 'ledger.py --plan <dir> materialize' "$SK/create/v6.md"
  grep -qF 'scheduler.py ready <dir>' "$SK/execute/v6.md"
  grep -qF 'start --task <T-id>' "$SK/execute/v6.md"
  grep -qF -e '--criterion <AC-id>' "$SK/execute/v6.md"
  grep -qF 'closure' "$SK/execute/v6.md"
  grep -qF 'complete --task <T-id>' "$SK/execute/v6.md"
  grep -qF 'render --all' "$SK/execute/v6.md"
  grep -qF 'receipt' "$SK/execute/v6.md"
  grep -qF 'export --dest' "$SK/execute/v6.md"
  grep -qF 'exhaust --limit <id>' "$SK/execute/v6.md"
  grep -qF 'settle --key <seq-key>' "$SK/execute/v6.md"
  grep -qF 'routing' "$SK/execute/v6.md"
  # ...and the CLIs really expose them
  python3 "$LEDGER" --help | grep -qF 'materialize'
  python3 "$VIEWS" --help | grep -qF 'render'
  python3 "$OUT" --help | grep -qF 'receipt'
}
