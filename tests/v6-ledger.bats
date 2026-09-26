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
doc.pop('contract_id', None)
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
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  # array form: exec'd without a shell — a missing binary never ran
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --json '["definitely-not-a-command-xyz"]'
  [ "$status" -eq 1 ]
  grep -q 'no event is recorded' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  ! grep -q 'gate_run' <<<"$output"
  # string form runs through a shell: a 127 IS an execution, recorded honestly
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
    --json '"definitely-not-a-command-xyz"'
  [ "$status" -eq 1 ]
  run python3 "$LEDGER" --plan "$PLAN" inspect
  grep -q 'gate_run' <<<"$output"
}

@test "projection is deterministic and carries v6 positions" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
  grep -q 'zero-test control' <<<"$output"
  run python3 "$LEDGER" --plan "$PLAN" inspect
  [ "$(grep -c 'refusal' <<<"$output")" -eq 1 ]
}

@test "pre-start evidence is stale and never satisfies" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --actor-identity bats --idempotent
  # observed without a recoverable pointer is refused at the record level
  run python3 "$LEDGER" --plan "$PLAN" append --type gate_run \
    --json '{"command": "cat src/check.txt", "cwd": ".", "timeout_seconds": 30,
             "exit_code": 0, "criterion": "AC-valid-contract-shape"}' \
    --actor-kind helper --actor-identity dwp-ledger/6.0 --trust observed
  [ "$status" -eq 1 ]
  grep -q 'evidence_path: required' <<<"$output"
  # gate_run BEFORE task_start with its pointer: recorded (history) but
  # stale for the task — it can never satisfy an in-window criterion
  python3 "$LEDGER" --plan "$PLAN" append --type gate_run \
    --json '{"command": "cat src/check.txt", "cwd": ".", "timeout_seconds": 30,
             "exit_code": 0, "criterion": "AC-valid-contract-shape"}' \
    --actor-kind helper --actor-identity dwp-ledger/6.0 \
    --trust observed --evidence-path 'gates/prestart.log' \
    --note 'pre-start evidence probe'
  python3 "$LEDGER" --plan "$PLAN" append --type task_start \
    --json '{"task": "T-publish-schemas"}' --idempotent
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
  grep -q 'lack in-window accepted evidence' <<<"$output"
  # the stale event is carried as stale, visible in the projection
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  python3 - "$PLAN/state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
crit = [c for t in state['tasks'] if t['id'] == 'T-publish-schemas'
        for c in t['criteria']]
assert crit and crit[0].get('stale_seqs') == [2], crit
print('stale carried:', crit[0]['stale_seqs'])
PY
}

@test "observed evidence after task_start satisfies completion" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111111"}' 2>/dev/null \
    || python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
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
    --actor-kind human --actor-identity bats --idempotent
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

@test "generated-wins reconciliation preserves the human copy and records authority" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --actor-identity bats --idempotent
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

@test "export copies journal, snapshot and contract with verified digests" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --actor-identity bats --idempotent
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" export --dest "$TEST_REPO/export"
  [ "$status" -eq 0 ]
  ls "$TEST_REPO/export/journal.ndjson" >/dev/null
  ls "$TEST_REPO/export/state.json" >/dev/null
  ls "$TEST_REPO/export/EXPORT_MANIFEST.json" >/dev/null
  python3 - "$TEST_REPO/export" <<'PY'
import hashlib, json, os, sys
d = sys.argv[1]
m = json.load(open(os.path.join(d, 'EXPORT_MANIFEST.json')))
for name, digest in m['files'].items():
    raw = open(os.path.join(d, name), 'rb').read()
    assert hashlib.sha256(raw).hexdigest() == digest, name
print('digests verified')
PY
}

@test "roll archives without deleting and continues the sequence" {
  python3 "$LEDGER" --plan "$PLAN" append --type approval \
    --json '{"authority": "bats", "mechanism": "plan_authorship",
             "plan_digest": "1111111111111111111111111111111111111111111111111111111111111111"}' \
    --actor-kind human --actor-identity bats --idempotent
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
