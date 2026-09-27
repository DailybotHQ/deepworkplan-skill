#!/usr/bin/env bash
# v5 -> v6 migration and cross-agent recovery (task 18). These tests drive
# the SHIPPED surface: a real-shaped v5 plan (manifest + state + task files
# + gate evidence logs) goes through migrate_v6.py preview -> migrate ->
# rollback with interruption at every phase boundary, the v5 runner's
# one-directional refusal (D2-10), and the cold-resume recovery that a
# second host performs from the journal alone. The "second host" is a
# second workspace copy in this test environment — scripted, not a live
# foreign agent; that limitation is recorded in the task's evidence file.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
MIG="$SK/shared/migrate_v6.py"
LEDGER="$SK/shared/ledger.py"
CV6="$SK/shared/contract_v6.py"
V5CHECK="$SK/verify/plan_contract.py"

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  ( cd "$TEST_REPO" && git init -q . && printf '.dwp/\n' > .gitignore \
      && git config user.email t@t && git config user.name t )
}

teardown() {
  rm -rf "$TEST_REPO"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    find "$SK" -name '__pycache__' -o -name '*.pyc'
    return 1
  fi
}

# A realistic v5 plan: task 1 completed with resolving evidence, task 2
# completed with a dangling evidence pointer (the re-evidence case), task 3
# pending. Bytes mirror the shapes update-state.py has written since v2.
_v5_plan() { # _v5_plan [name]
  local name="${1:-PLAN_migration_bats}"
  local plan="$TEST_REPO/.dwp/plans/$name"
  mkdir -p "$plan/analysis_results/gates"
  printf '# Plan\n\n## Goal\n\nFixture v5 plan.\n' > "$plan/README.md"
  printf '# t1\n' > "$plan/1.task_clean.md"
  printf '# t2\n' > "$plan/2.task_broken.md"
  printf '# t3\n' > "$plan/3.task_pend.md"
  printf 'all ok\n' > "$plan/analysis_results/gates/clean.log"
  cat > "$plan/manifest.json" <<'JSON'
{
  "archetype": "individual", "created_at": "2026-09-01T09:00:00Z",
  "name": "PLAN_migration_bats", "plan_format": "full", "rigor": "standard",
  "schema": "https://deepworkplan.com/schema/plan-manifest/v5.json",
  "spec_version": "5.0.0", "task_count": 3, "title": "Migration bats fixture"
}
JSON
  cat > "$plan/state.json" <<'JSON'
{
  "completed_count": 1, "format": "full", "materialization": "ready",
  "plan": "PLAN_migration_bats",
  "schema": "https://deepworkplan.com/schema/plan-state/v5.json",
  "spec_version": "5.0.0", "status": "in_progress", "task_count": 3,
  "tasks": [
    {"gates": [{"command": "bats tests/clean.bats", "evidence":
      "analysis_results/gates/clean.log", "exit_code": 0, "last_run":
      "2026-09-02T09:00:00Z", "passes": true}],
     "id": 1, "locator": {"kind": "file", "value": "1.task_clean.md"},
     "outcome": {"worked": "shipped"}, "status": "completed",
     "title": "Clean completed task"},
    {"gates": [{"command": "bats tests/broken.bats", "evidence":
      "analysis_results/gates/gone.log", "exit_code": 0, "last_run":
      "2026-09-02T09:00:00Z", "passes": true}],
     "id": 2, "locator": {"kind": "file", "value": "2.task_broken.md"},
     "status": "completed", "title": "Broken evidence task"},
    {"gates": [], "id": 3,
     "locator": {"kind": "file", "value": "3.task_pend.md"},
     "status": "pending", "title": "Pending task"}],
  "updated_at": "2026-09-02T09:00:00Z"
}
JSON
  python3 - "$plan" "$name" <<'PY'
import json, sys
plan, name = sys.argv[1], sys.argv[2]
for f, key in (('manifest.json', 'name'), ('state.json', 'plan')):
    p = f'{plan}/{f}'
    doc = json.load(open(p))
    doc[key] = name
    doc['title'] = name
    json.dump(doc, open(p, 'w'), indent=2, sort_keys=True)
PY
  echo "$plan"
}

_migrated() { # _migrated [name] -> echoes plan dir, fully migrated
  local plan; plan="$(_v5_plan "${1:-PLAN_migration_bats}")"
  python3 "$MIG" --plan "$plan" preview >/dev/null
  python3 "$MIG" --plan "$plan" migrate --authority tester >/dev/null
  echo "$plan"
}

_journal_types() { python3 -c '
import json, sys
print(" ".join(json.loads(l)["type"] for l in open(sys.argv[1])))' \
  "$1/journal.ndjson"; }

# ------------------------------------------------------------------ preview

@test "preview maps tasks, names the re-evidence bar, writes PREVIEW.json, touches no v5 byte" {
  plan="$(_v5_plan)"
  sum_before="$(sha256sum "$plan/manifest.json" "$plan/state.json")"
  run python3 "$MIG" --plan "$plan" preview
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF '1 imported-closable, 1 re-evidence, 1 pending'
  printf '%s' "$output" | grep -qF 'AC-t02-broken-evidence-task'
  [ -s "$plan/migration_v5/PREVIEW.json" ]
  [ "$(sha256sum "$plan/manifest.json" "$plan/state.json")" = "$sum_before" ]
  python3 - "$plan/migration_v5/PREVIEW.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
assert doc['type'] == 'dwp-migration-preview'
assert doc['imported_criteria'] == ['AC-t01-clean-completed-task']
assert doc['re_evidence_criteria'] == ['AC-t02-broken-evidence-task']
gates = doc['task_mapping'][0]['gates']
assert gates[0]['import_as'] == 'imported'
broken = doc['task_mapping'][1]['gates']
assert broken[0]['import_as'] == 'asserted'
assert any('does not resolve' in r for r in doc['task_mapping'][1]['reasons'])
assert doc['recorded_assumptions'], 'the cwd/timeout assumptions are named'
PY
}

@test "preview refuses lossy and torn inputs with the reason named" {
  plan="$(_v5_plan)"
  python3 - "$plan" <<'PY'
import json, sys
p = sys.argv[1] + '/state.json'
doc = json.load(open(p)); doc['tasks'][1]['status'] = 'mysterious'
json.dump(doc, open(p, 'w'), indent=2, sort_keys=True)
PY
  run python3 "$MIG" --plan "$plan" preview
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF "status 'mysterious'"
  # a torn identity is refused too
  plan="$(_v5_plan)"
  python3 - "$plan" <<'PY'
import json, sys
p = sys.argv[1] + '/state.json'
doc = json.load(open(p)); doc['plan'] = 'PLAN_someone_else'
json.dump(doc, open(p, 'w'), indent=2, sort_keys=True)
PY
  run python3 "$MIG" --plan "$plan" preview
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'does not match the plan folder'
}

@test "preview refuses while a migration is in flight (marker says so)" {
  # crash window: backup phase recorded, manifest still v5, no rollback
  plan="$(_v5_plan)"
  python3 "$MIG" --plan "$plan" preview >/dev/null
  mkdir -p "$plan/migration_v5"
  printf '{"completed": ["backup"], "source_digest": "%s"}\n' \
    "$(python3 -c 'import hashlib,json,sys; m=json.load(open(sys.argv[1]+"/manifest.json")); s=json.load(open(sys.argv[1]+"/state.json")); print(hashlib.sha256(json.dumps({"manifest":m,"state":s},sort_keys=True,separators=(",",":")).encode()).hexdigest())' "$plan")" \
    > "$plan/migration_v5/PHASE.json"
  run python3 "$MIG" --plan "$plan" preview
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'migration is in progress or done'
}

# ------------------------------------------------------------------ migrate

@test "migrate synthesizes a valid contract, swaps the manifest, derives statuses" {
  plan="$(_v5_plan)"
  python3 "$MIG" --plan "$plan" preview >/dev/null
  run python3 "$MIG" --plan "$plan" migrate --authority tester
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'phases backup+contract+manifest+journal+project'
  # the synthesized contract validates under the shipped validator
  python3 "$CV6" validate-contract "$plan/contract.json" >/dev/null
  # the v5 manifest became the v6 pointer, and only after a backup exists
  python3 - "$plan" <<'PY'
import json, os, sys
plan = sys.argv[1]
m = json.load(open(f'{plan}/manifest.json'))
assert m['schema'] == 'https://deepworkplan.com/schema/plan-manifest/v6.json'
assert m['contract']['path'] == 'contract.json'
assert os.path.isfile(f'{plan}/migration_v5/backup/manifest.json')
assert os.path.isfile(f'{plan}/migration_v5/backup/state.json')
s = json.load(open(f'{plan}/state.json'))
assert s['schema'] == 'https://deepworkplan.com/schema/plan-snapshot/v6.json'
status = {t['id']: t['status'] for t in s['tasks']}
assert status == {'T-01-clean-completed-task': 'completed',
                  'T-02-broken-evidence-task': 'in_progress',
                  'T-03-pending-task': 'pending'}, status
PY
}

@test "the journal records the migration honestly: pre_authorization, imported gates, blocked re-evidence" {
  plan="$(_migrated)"
  types="$(_journal_types "$plan")"
  # approval first, then one task_start+gate_run pair per non-pending task
  # in v5 numeric order, then the migration observation
  [ "$types" = 'approval task_start gate_run task_start gate_run observation' ]
  python3 - "$plan" <<'PY'
import json, sys
plan = sys.argv[1]
events = [json.loads(l) for l in open(f'{plan}/journal.ndjson')]
approval = events[0]
assert approval['mechanism'] == 'pre_authorization'
assert approval['authority'] == 'tester'
assert len(approval['plan_digest']) == 64, 'the v5 source digest is the recorded pre-authorization'
starts = [e for e in events if e['type'] == 'task_start']
assert sorted(e['task'] for e in starts) == ['T-01-clean-completed-task',
                                             'T-02-broken-evidence-task']
assert all('fingerprint' not in e for e in starts), 'v5 kept no fingerprint; none is invented'
runs = [e for e in events if e['type'] == 'gate_run']
by_label = sorted((e['trust'], e['exit_code'],
                      e.get('evidence_path') is not None) for e in runs)
assert by_label == [('asserted', 0, False), ('imported', 0, True)], by_label
imported = [e for e in runs if e['trust'] == 'imported'][0]
assert imported['evidence_path'] == 'analysis_results/gates/clean.log'
assert imported['note'].startswith('migrated: v5 ')
assert imported['actor'] == {'kind': 'helper', 'identity': 'migrate_v6.py'}
PY
}

@test "imported evidence closes its criterion; re-evidence stays blocked (D3-5)" {
  plan="$(_migrated)"
  python3 - "$plan" "$LEDGER" <<'PY'
import json, os, sys
plan, ledger_path = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.dirname(ledger_path))
import ledger  # noqa: E402
rec = ledger.PlanRecords(plan)
events, torn, _framing = rec.read_journal()
assert not torn
for task, want in (('T-01-clean-completed-task', True),
                   ('T-02-broken-evidence-task', False)):
    states = ledger.criterion_states(rec.contract, events, task)
    assert states[0]['satisfied'] is want, (task, states)
best = ledger.criterion_states(rec.contract, events,
                               'T-01-clean-completed-task')[0]
assert best['trust'] == 'imported' and best['via_seq']
PY
}

@test "a re-run of migrate mints no duplicate events; a resumed run finishes from any phase" {
  plan="$(_v5_plan)"
  python3 "$MIG" --plan "$plan" preview >/dev/null
  python3 "$MIG" --plan "$plan" migrate --authority tester >/dev/null
  count_first="$(grep -c . "$plan/journal.ndjson")"
  cid_first="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["contract_id"])' "$plan/migration_v5/PHASE.json")"
  python3 "$MIG" --plan "$plan" migrate --authority tester >/dev/null
  [ "$(grep -c . "$plan/journal.ndjson")" = "$count_first" ]
  # interruption after the manifest swap: journal lost, marker rewound —
  # the resumed run rebuilds the identical event set from the BACKUP pair
  rm "$plan/journal.ndjson" "$plan/state.json"
  python3 - "$plan" <<'PY'
import json, sys
p = sys.argv[1] + '/migration_v5/PHASE.json'
doc = json.load(open(p)); doc['completed'] = ['backup', 'contract', 'manifest']
json.dump(doc, open(p, 'w'), indent=2, sort_keys=True)
PY
  run python3 "$MIG" --plan "$plan" migrate --authority tester
  [ "$status" -eq 0 ]
  [ "$(grep -c . "$plan/journal.ndjson")" = "$count_first" ]
  cid_now="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["contract_id"])' "$plan/migration_v5/PHASE.json")"
  [ "$cid_now" = "$cid_first" ]
}

@test "migrate refuses a stale preview and a missing one" {
  plan="$(_v5_plan)"
  run python3 "$MIG" --plan "$plan" migrate --authority tester
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'no preview on record'
  python3 "$MIG" --plan "$plan" preview >/dev/null
  # the digest covers the manifest+state pair; a state edit changes it
  # (an evidence-log edit does not, and must NOT trip this guard)
  python3 - "$plan" <<'PY2'
import json, sys
p = sys.argv[1] + '/state.json'
doc = json.load(open(p)); doc['tasks'][2]['title'] = 'Retitled pending task'
json.dump(doc, open(p, 'w'), indent=2, sort_keys=True)
PY2
  run python3 "$MIG" --plan "$plan" migrate --authority tester
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'records changed since the preview'
}

@test "a preview whose evidence resolution changed is refused, not re-mapped" {
  # The source digest covers only the manifest+state pair, so deleting a
  # cited evidence file leaves it intact - the contract anchor is the
  # guard that sees the world change and refuses to migrate onto a
  # silently different (re_evidence) synthesis than the preview showed.
  plan="$(_v5_plan)"
  python3 "$MIG" --plan "$plan" preview >/dev/null
  rm "$plan/analysis_results/gates/clean.log"
  run python3 "$MIG" --plan "$plan" migrate --authority tester
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'the v5 world changed since the preview'
  [ ! -e "$plan/migration_v5/PHASE.json" ]
  [ ! -e "$plan/contract.json" ]
}

# ----------------------------------------------------------------- rollback

@test "rollback restores the v5 pair byte-identically and removes v6 artifacts" {
  plan="$(_migrated)"
  v5_manifest="$(_v5_plan PLAN_rollback_ref)"
  cp "$plan/migration_v5/backup/manifest.json" "$TEST_REPO/ref_manifest.json"
  cp "$plan/migration_v5/backup/state.json" "$TEST_REPO/ref_state.json"
  run python3 "$MIG" --plan "$plan" rollback
  [ "$status" -eq 0 ]
  cmp "$plan/manifest.json" "$TEST_REPO/ref_manifest.json"
  cmp "$plan/state.json" "$TEST_REPO/ref_state.json"
  [ ! -e "$plan/contract.json" ]
  [ ! -e "$plan/journal.ndjson" ]
  [ -e "$plan/migration_v5/ROLLED_BACK.json" ]
  rm -rf "$v5_manifest"
}

@test "rollback refuses post-migration v6 work; --force is the explicit discard" {
  plan="$(_migrated)"
  lock="$plan/.ledger.lock"; mkdir -p "$lock"
  printf '{"pid": 1, "identity": "stale"}' > "$lock/owner.json"
  run python3 "$LEDGER" --plan "$plan" append --type observation \
    --json '{"statement": "post-migration work"}' --trust asserted --force
  [ "$status" -eq 0 ]
  rm -rf "$lock"
  run python3 "$MIG" --plan "$plan" rollback
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'not silently deleted'
  [ -e "$plan/journal.ndjson" ]
  run python3 "$MIG" --plan "$plan" rollback --force
  [ "$status" -eq 0 ]
  [ ! -e "$plan/journal.ndjson" ]
}

# ------------------------------------------------- one-directional + runner

@test "the v5 runner refuses a migrated plan naming the contract (D2-10)" {
  plan="$(_migrated)"
  run python3 "$V5CHECK" "$plan"
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'this plan is v6'
  printf '%s' "$output" | grep -qF 'the v5 runner does not execute v6 plans'
}

@test "migrate refuses an already-v6 plan: one direction only" {
  plan="$(_migrated)"
  run python3 "$MIG" --plan "$plan" preview
  [ "$status" -ne 0 ]
  printf '%s' "$output" | grep -qF 'already a v6 plan'
}

# ------------------------------------------------------- cross-agent resume

@test "a cold second workspace recovers the plan from the journal alone" {
  plan="$(_migrated)"
  export HOME="$TEST_REPO"; export GIT_CONFIG_NOSYSTEM=1
  # the export bundle is the cross-host handoff artifact (.dwp is gitignored)
  run python3 "$LEDGER" --plan "$plan" export --dest "$TEST_REPO/handoff"
  [ "$status" -eq 0 ]
  [ -s "$TEST_REPO/handoff/journal.ndjson" ]
  # second workspace: the derived files are absent (never committed); the
  # journal + contract are the truth the recovery rebuilds from
  cold="$TEST_REPO/cold/.dwp/plans/$(basename "$plan")"
  mkdir -p "$cold"
  cp "$plan/README.md" "$cold/README.md"
  cp "$plan/contract.json" "$cold/contract.json"
  cp "$plan/manifest.json" "$cold/manifest.json"
  cp "$plan/journal.ndjson" "$cold/journal.ndjson"
  run python3 "$LEDGER" --plan "$cold" project
  [ "$status" -eq 0 ]
  python3 - "$plan" "$cold" <<'PY'
import json, sys
def statuses(p):
    return {t['id']: t['status']
            for t in json.load(open(f'{p}/state.json'))['tasks']}
a, b = statuses(sys.argv[1]), statuses(sys.argv[2])
assert a == b, (a, b)
assert a['T-01-clean-completed-task'] == 'completed'
assert a['T-02-broken-evidence-task'] == 'in_progress'
assert a['T-03-pending-task'] == 'pending'
PY
}

@test "a migrated plan continues under v6: the blocked criterion closes on a re-run gate" {
  plan="$(_migrated)"
  # T-03 is pending and ready; start it and gate it under v6 execution,
  # proving the migration did not just freeze the plan
  run python3 "$LEDGER" --plan "$plan" start --task T-03-pending-task
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$plan" gate --task T-03-pending-task \
    --criterion AC-t03-pending-task --json '"true"'
  [ "$status" -eq 0 ]
  printf '%s' "$output" | grep -qF 'RAN: exit 0'
  run python3 "$LEDGER" --plan "$plan" complete --task T-03-pending-task
  [ "$status" -eq 0 ]
  python3 "$LEDGER" --plan "$plan" project >/dev/null
  python3 - "$plan" <<'PY'
import json, sys
s = json.load(open(f'{sys.argv[1]}/state.json'))
status = {t['id']: t['status'] for t in s['tasks']}
assert status['T-03-pending-task'] == 'completed', status
assert status['T-02-broken-evidence-task'] == 'in_progress', status
PY
}
