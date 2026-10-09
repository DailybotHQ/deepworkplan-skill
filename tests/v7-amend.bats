#!/usr/bin/env bash
# Plan-scoped invariants gate completion (field report F-03) and
# `ledger.py amend` is one guarded, resumable amendment (F-12): staged
# revision -> amendment event -> fresh approval -> atomic switch of the live
# contract, with the revised criteria re-evidenced; interrupted amendments
# resume without duplicate events; invalid amendments write nothing.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SHARED="$SK/shared"
LEDGER="$SHARED/ledger.py"
CHECK="$SK/verify/plan_contract.py"
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
  cd "$REPO"
}

teardown() {
  rm -rf "$WORK"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    return 1
  fi
}

_L() { python3 "$LEDGER" --plan "$PLAN" "$@"; }
_inv() { _L append --type observation --json "{\"statement\": \"INV-historical-bytes: $1\"}" --trust asserted >/dev/null; }

# _plan <fixture> <name> — materialized, T-publish-schemas closed on evidence.
_plan() {
  PLAN="$REPO/.dwp/plans/$2"
  mkdir -p "$PLAN/analysis_results"
  printf '# Goal\n\nAmend.\n' > "$PLAN/README.md"
  python3 - "$1" "$WORK/draft.json" "$2" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['plan'] = sys.argv[3]
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
    for i in t['gate_intent']:
        i['check'] = 'python3 -V'
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
  _L materialize --contract "$WORK/draft.json" --authority bats >/dev/null || return 1
  _L start --task T-publish-schemas >/dev/null || return 1
  _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 -V"' >/dev/null || return 1
  _inv pass || return 1
  _L complete --task T-publish-schemas >/dev/null
}

# _revise [extra python] — revision 2 draft: AC-valid-contract-shape's check changes.
_revise() {
  python3 - "$PLAN/contract.json" "$WORK/r2.json" "${1:-}" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
for c in doc['acceptance']['criteria']:
    if c['id'] == 'AC-valid-contract-shape':
        c['observable_check'] = 'the validator exits 0 on the revised fixture'
for t in doc['tasks']:
    for i in t['gate_intent']:
        if i['criterion'] == 'AC-valid-contract-shape':
            i['check'] = 'python3 -c pass'
if sys.argv[3]:
    exec(sys.argv[3])
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
}

_amend() { _L amend --contract "$WORK/r2.json" --authority "Ada Lead" --note "${1:-sharpen the shape check}" --human-note "$NOTE"; }

_count() { grep -c "\"type\":\"$1\"" "$PLAN/journal.ndjson"; }

# ------------------------------------------------------------------ F-03

@test "completion is refused while a declared invariant is unevaluated, stale or failed" {
  _plan "$FIX7" PLAN_amend_invariants || return 1
  _L start --task T-ship-validator >/dev/null
  _L gate --task T-ship-validator --criterion AC-journal-catalog-closed --json '"python3 -V"' >/dev/null
  # the pass recorded during T-publish-schemas predates this task's start
  run _L complete --task T-ship-validator
  [ "$status" -eq 4 ] && [[ "$output" == *"INV-historical-bytes last evaluated at seq"*"before the task start"* ]] || { echo "$output"; return 1; }
  _inv 'fail: schema bytes drifted'
  run _L complete --task T-ship-validator
  [ "$status" -eq 4 ] && [[ "$output" == *"INV-historical-bytes failed"* ]] || { echo "$output"; return 1; }
  grep -qF 'invariant(s) not verified for this attempt' "$PLAN/journal.ndjson" || return 1
  _inv pass
  run _L complete --task T-ship-validator
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
}

@test "a never-evaluated invariant refuses completion" {
  PLAN="$REPO/.dwp/plans/PLAN_amend_never"
  mkdir -p "$PLAN"; printf '# Goal\n' > "$PLAN/README.md"
  python3 - "$FIX6" "$WORK/draft.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1])); doc.pop('contract_id', None)
doc['plan'] = 'PLAN_amend_never'
doc['scope']['allowed_command_classes'] = ['python3']
for t in doc['tasks']:
    for i in t['gate_intent']:
        i['check'] = 'python3 -V'
json.dump(doc, open(sys.argv[2], 'w'))
PY
  _L materialize --contract "$WORK/draft.json" --authority bats >/dev/null
  _L start --task T-publish-schemas >/dev/null
  _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 -V"' >/dev/null
  run _L complete --task T-publish-schemas
  [ "$status" -eq 4 ] && [[ "$output" == *"INV-historical-bytes never evaluated"* ]]
}

# ------------------------------------------------------------------ F-12

@test "amend writes revision, amendment and approval, then switches the live contract (v6 and v7)" {
  for fix in "$FIX6:PLAN_amend_six" "$FIX7:PLAN_amend_seven"; do
    _plan "${fix%%:*}" "${fix##*:}" || return 1
    _revise || return 1
    run _amend
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
    [[ "$output" == *"amended to revision 2"*"re-evidenced: AC-valid-contract-shape"* ]] || return 1
    [ -f "$PLAN/contracts/contract.r1.json" ] && [ -f "$PLAN/contracts/contract.r2.json" ] || return 1
    cmp -s "$PLAN/contract.json" "$PLAN/contracts/contract.r1.json" || return 1
    ! ls -a "$PLAN/contracts" | grep -q pending || return 1
    python3 - "$PLAN" <<'PY' || return 1
import json, sys
sys.dont_write_bytecode = True
plan = sys.argv[1]
r2 = json.load(open(plan + '/contracts/contract.r2.json'))
events = [json.loads(l) for l in open(plan + '/journal.ndjson')]
amend = [e for e in events if e['type'] == 'amendment']
approvals = [e for e in events if e['type'] == 'approval' and e['contract_id'] == r2['contract_id']]
assert len(amend) == 1 and len(approvals) == 1, (amend, approvals)
assert amend[0]['seq'] < approvals[0]['seq']
assert amend[0]['evidence_invalidated'] == ['AC-valid-contract-shape'], amend[0]
assert amend[0]['affected_tasks'] == ['T-publish-schemas'], amend[0]
assert approvals[0]['actor'] == {'kind': 'human', 'identity': 'Ada Lead'}
assert 'human authority marker: note' in approvals[0]['note']
assert r2['revision'] == 2 and r2['parent_contract_id'] == json.load(open(plan + '/contract.json'))['contract_id']
PY
    # the revised criterion's earlier evidence no longer counts
    _L project >/dev/null
    python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); t={x["id"]: x["status"] for x in s["tasks"]}; assert t["T-publish-schemas"] == "in_progress", t' "$PLAN/state.json" || return 1
    _L start --task T-publish-schemas >/dev/null || return 1
    _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 -c pass"' >/dev/null || return 1
    _inv pass
    _L complete --task T-publish-schemas >/dev/null || return 1
    _L project >/dev/null
    run python3 "$CHECK" "$PLAN"
    [ "$status" -eq 0 ] && [[ "$output" == *"revision 2; 2 revision(s) checked"* ]] || { echo "$output"; return 1; }
  done
}

@test "an interrupted amend resumes at the first missing step, never duplicating events" {
  _plan "$FIX7" PLAN_amend_resume || return 1
  _revise || return 1
  # crash 1: after the amendment event, before the approval
  run python3 - "$SHARED" "$PLAN" "$WORK/r2.json" <<'PY'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import ledger
original = ledger.Writer._append_raw
def crash(self, etype, *a, **k):
    if etype == 'approval':
        raise SystemExit('simulated crash before the approval')
    return original(self, etype, *a, **k)
ledger.Writer._append_raw = crash
ledger.main(['--plan', sys.argv[2], 'amend', '--contract', sys.argv[3],
             '--authority', 'Ada Lead', '--note', 'sharpen', '--human-note',
             sys.argv[1] + '/../../../tests/fixtures/v6/human-note.md'])
PY
  [ "$status" -ne 0 ] || return 1
  ls -a "$PLAN/contracts" | grep -q '.contract.r2.json.pending' || return 1
  [ ! -e "$PLAN/contracts/contract.r2.json" ] || return 1
  # the live contract is still revision 1, still approved
  python3 -c 'import sys; sys.dont_write_bytecode=True; sys.path.insert(0,sys.argv[1]); import ledger; r=ledger.PlanRecords(sys.argv[2]); assert r.contract["revision"] == 1' "$SHARED" "$PLAN" || return 1
  # crash 2: on resume, after the approval, before the switch
  run python3 - "$SHARED" "$PLAN" "$WORK/r2.json" <<'PY'
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import ledger
def crash(src, dst):
    raise SystemExit('simulated crash before the switch')
ledger.os.replace = crash
ledger.main(['--plan', sys.argv[2], 'amend', '--contract', sys.argv[3],
             '--authority', 'Ada Lead', '--note', 'sharpen', '--human-note',
             sys.argv[1] + '/../../../tests/fixtures/v6/human-note.md'])
PY
  [ "$status" -ne 0 ] || return 1
  [ "$(_count amendment)" -eq 1 ] && [ "$(_count approval)" -eq 2 ] || return 1
  [ ! -e "$PLAN/contracts/contract.r2.json" ] || return 1
  # a clean resume only switches
  run _amend sharpen
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [ "$(_count amendment)" -eq 1 ] && [ "$(_count approval)" -eq 2 ] || return 1
  [ -f "$PLAN/contracts/contract.r2.json" ]
}

@test "invalid amendments are refused and write nothing" {
  _plan "$FIX7" PLAN_amend_refusals || return 1
  before="$(shasum -a 256 "$PLAN/journal.ndjson")"
  _revise "doc['revision'] = 3" && run _amend
  [ "$status" -ne 0 ] && [[ "$output" == *"must be revision 2"* ]] || { echo "$output"; return 1; }
  _revise "doc['schema'] = 'https://deepworkplan.com/schema/plan-contract/v6.json'
for t in doc['tasks']: t.pop('parallel_safe', None)" && run _amend
  [ "$status" -ne 0 ] && [[ "$output" == *"keeps the plan and its generation"* ]] || { echo "$output"; return 1; }
  _revise "doc['tasks'][0]['gate_intent'][0]['check'] = 'pytest -q'" && run _amend
  [ "$status" -ne 0 ] && [[ "$output" == *"the gate runner would refuse it"* ]] || { echo "$output"; return 1; }
  _revise && run _L amend --contract "$WORK/r2.json" --authority "Ada Lead" --note sharpen < /dev/null
  [ "$status" -ne 0 ] && [[ "$output" == *"human-authority marker"* ]] || { echo "$output"; return 1; }
  [ "$before" = "$(shasum -a 256 "$PLAN/journal.ndjson")" ] || return 1
  [ ! -e "$PLAN/contracts/contract.r2.json" ] || return 1
  ! ls -a "$PLAN/contracts" 2>/dev/null | grep -q pending
}

@test "a different draft is refused while another revision is pending" {
  _plan "$FIX7" PLAN_amend_pending || return 1
  _revise || return 1
  run python3 - "$SHARED" "$PLAN" "$WORK/r2.json" <<'PY'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import ledger
original = ledger.Writer._append_raw
def crash(self, etype, *a, **k):
    if etype == 'amendment':
        raise SystemExit('simulated crash after staging')
    return original(self, etype, *a, **k)
ledger.Writer._append_raw = crash
ledger.main(['--plan', sys.argv[2], 'amend', '--contract', sys.argv[3],
             '--authority', 'Ada Lead', '--note', 'sharpen', '--human-note',
             sys.argv[1] + '/../../../tests/fixtures/v6/human-note.md'])
PY
  _revise "doc['outcome']['statement'] = 'a different revision'" || return 1
  run _amend
  [ "$status" -ne 0 ] && [[ "$output" == *"a different revision 2 is pending"* ]] || { echo "$output"; return 1; }
}

# ------------------------------------------------ pre-merge review fixes

@test "an amend interrupted after creating contracts/ resumes (review W1)" {
  _plan "$FIX7" PLAN_amend_bootstrap || return 1
  _revise || return 1
  mkdir -p "$PLAN/contracts"   # the crash window: directory, no revision 1
  run _amend
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  cmp -s "$PLAN/contract.json" "$PLAN/contracts/contract.r1.json" || return 1
  [ -f "$PLAN/contracts/contract.r2.json" ]
}

@test "re-running a finished amend is a no-op (review I5)" {
  _plan "$FIX7" PLAN_amend_noop || return 1
  _revise && _amend >/dev/null || return 1
  before="$(shasum -a 256 "$PLAN/journal.ndjson")"
  run _amend
  [ "$status" -eq 0 ] && [[ "$output" == *"already is this draft - nothing to amend"* ]] || { echo "$output"; return 1; }
  [ "$before" = "$(shasum -a 256 "$PLAN/journal.ndjson")" ]
}

@test "an unapproved amendment invalidates nothing (review I4)" {
  _plan "$FIX7" PLAN_amend_unapproved || return 1
  _revise || return 1
  python3 - "$SHARED" "$PLAN" "$WORK/r2.json" "$NOTE" <<'PY' || true
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import ledger
original = ledger.Writer._append_raw
def crash(self, etype, *a, **k):
    if etype == 'approval':
        raise SystemExit('crash before approval')
    return original(self, etype, *a, **k)
ledger.Writer._append_raw = crash
ledger.main(['--plan', sys.argv[2], 'amend', '--contract', sys.argv[3],
             '--authority', 'Ada Lead', '--note', 'n', '--human-note', sys.argv[4]])
PY
  [ "$(_count amendment)" -eq 1 ] || return 1
  _L project >/dev/null
  python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); t={x["id"]: x["status"] for x in s["tasks"]}; assert t["T-publish-schemas"] == "completed", t' "$PLAN/state.json"
}

@test "an approved amendment also retires the revised criterion's control pairs (review W2)" {
  run python3 - "$SHARED" <<'PY'
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import ledger, outcomes
cid = 'c' * 64
events = [
    {'type': 'control_pair', 'criterion': 'AC-x', 'seq': 5, 'verdict': 'discriminating', 'trust': 'observed'},
    {'type': 'amendment', 'seq': 6, 'evidence_invalidated': ['AC-x'], 'note': 'amendment to revision 2 contract ' + cid},
]
assert outcomes._control_pairs(events, 'AC-x', 0), 'unapproved: the pair still counts'
events.append({'type': 'approval', 'seq': 7, 'contract_id': cid})
assert not outcomes._control_pairs(events, 'AC-x', 0), 'approved: the pair is retired'
print('ok')
PY
  [ "$status" -eq 0 ] && [ "$output" = "ok" ] || { echo "$output"; return 1; }
}
