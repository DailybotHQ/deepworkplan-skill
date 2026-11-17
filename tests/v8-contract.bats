#!/usr/bin/env bash
# The v8 contract generation (spec/LOOP_ENGINEERING.md): a v8 contract is a
# v7 contract plus an optional, closed `autonomy` block. The block is
# refused on any other generation; its five keys are checked; an absent key
# means its one recorded default; a v8 plan keeps every v7 task rule
# (parallel_safe) and records delegation like a v7 plan; it is materialized
# into the v7 manifest line with its own journal generation
# (journal-event/v8, the v7 events plus `blocker`).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SHARED="$SK/shared"
CONTRACT="$SHARED/contract_v6.py"
LEDGER="$SHARED/ledger.py"
CFG="$SHARED/config.py"
SPEC="$SK/spec/LOOP_ENGINEERING.md"
FIX="$REPO_ROOT/tests/fixtures/v7/contract-minimal-v7.json"
V8="https://deepworkplan.com/schema/plan-contract/v8.json"
export PYTHONDONTWRITEBYTECODE=1

setup() { WORK="$(cd "$(mktemp -d)" && pwd -P)"; }
teardown() { rm -rf "$WORK"; }

# _doc OUT [python mutation]: the v7 fixture made v8 (no id), then mutated.
_doc() {
  python3 - "$FIX" "$1" "$V8" "${2:-}" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['schema'] = sys.argv[3]
if sys.argv[4]:
    exec(sys.argv[4])
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
}
_valid() { python3 "$CONTRACT" validate-contract "$1"; }

@test "a v8 contract with a full autonomy block validates; v8 keeps v7's task rules (parallel_safe)" {
  _doc "$WORK/c.json" "doc['autonomy'] = {'stall_budget': 5, 'promptable': ['local:w1:p2', 'box-1:w2:p3'], 'notify': ['dailybot'], 'brain': True, 'queue': 'prompt-lead'}
assert any(t.get('parallel_safe') for t in doc['tasks'])"
  run _valid "$WORK/c.json"
  [ "$status" -eq 0 ]
  # no block at all is valid too: every key takes its default
  _doc "$WORK/bare.json"
  run _valid "$WORK/bare.json"
  [ "$status" -eq 0 ]
}

@test "the autonomy block belongs to v8 only (generations never mix)" {
  python3 - "$FIX" "$WORK/v7.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1])); doc.pop('contract_id', None)
doc['autonomy'] = {'brain': False}
json.dump(doc, open(sys.argv[2], 'w'))
PY
  run _valid "$WORK/v7.json"
  [ "$status" -ne 0 ]
  [[ "$output" == *"only the v8 generation carries the autonomy block"* ]]
}

@test "each autonomy key is checked, the block is closed, and a pane address cannot start with '-'" {
  local bad
  for bad in \
    "{'stall_budget': 0}" "{'stall_budget': 11}" "{'stall_budget': True}" "{'stall_budget': '3'}" \
    "{'promptable': []}" "{'promptable': ['w1:p2']}" "{'promptable': ['-x:w1:p2']}" "{'promptable': ['local:w1:p2;rm']}" \
    "{'notify': []}" "{'notify': ['slack']}" \
    "{'brain': 'yes'}" "{'queue': 'auto'}" "{'unknown': 1}" "['brain']"; do
    _doc "$WORK/bad.json" "doc['autonomy'] = $bad"
    run _valid "$WORK/bad.json"
    [ "$status" -ne 0 ] || { echo "accepted: $bad"; return 1; }
  done
  for good in "{'promptable': ['local:w1:p2']}" "{'promptable': ['a.b_c-d:w1:p2']}" "{'stall_budget': 1}" "{'stall_budget': 10}" "{'queue': 'none'}"; do
    _doc "$WORK/good.json" "doc['autonomy'] = $good"
    run _valid "$WORK/good.json"
    [ "$status" -eq 0 ] || { echo "refused: $good: $output"; return 1; }
  done
}

@test "the five defaults are pinned: the spec's table names exactly the validator's keys, each with its one default" {
  python3 - "$SHARED" "$SPEC" <<'PY'
import re, sys
sys.path.insert(0, sys.argv[1])
import contract_v6 as C
spec = open(sys.argv[2], encoding='utf-8').read()
# the autonomy table is section 2; section 3's blocker table is another table
spec = spec[spec.index('## 2. '):spec.index('## 3. ')]
rows = {}
for line in spec.splitlines():
    m = re.match(r'^\| `([a-z_]+)` \|', line)
    if m:
        cells = [c.strip() for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
        rows[m.group(1)] = cells[-1]
assert tuple(sorted(rows)) == tuple(sorted(C.AUTONOMY_KEYS)), (sorted(rows), C.AUTONOMY_KEYS)
want = {'stall_budget': '`3`', 'promptable': '**lead only**', 'notify': 'no target', 'brain': '`false`', 'queue': '`none`'}
for key, word in want.items():
    assert word in rows[key], (key, rows[key])
assert C.AUTONOMY_QUEUE_STARTS == ('prompt-lead', 'launch', 'none')
assert C.AUTONOMY_NOTIFY_TARGETS == ('dailybot',)
PY
}

@test "a v8 plan materializes into the v7 manifest line and the v8 journal, and records delegation like a v7 plan" {
  REPO="$WORK/repo"; PLAN="$REPO/.dwp/plans/PLAN_v8_fixture"
  mkdir -p "$PLAN/analysis_results" "$REPO/src" "$WORK/bin" "$WORK/home"
  export HOME="$WORK/home"
  printf '# Goal\n\nv8.\n' > "$PLAN/README.md"
  git -C "$REPO" init -q
  printf '.dwp/\n' > "$REPO/.gitignore"
  git -C "$REPO" add -A && git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init
  printf '#!/bin/sh\ncase "$1" in doctor) echo %s ;; esac\n' "'{\"interface\": 1, \"version\": \"0.1.0\"}'" > "$WORK/bin/ak"
  chmod +x "$WORK/bin/ak"
  _doc "$PLAN/draft.json" "doc['plan'] = 'PLAN_v8_fixture'
doc['invariants'] = []
doc['scope']['allowed_command_classes'] = ['python3', 'test']
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/']; t['prerequisites'] = []
doc['autonomy'] = {'brain': False, 'queue': 'prompt-lead'}"
  run python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" --authority bats --mechanism pre_authorization
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  grep -q 'plan-manifest/v7.json' "$PLAN/manifest.json"
  grep -q "\"schema\": \"$V8\"" "$PLAN/contract.json"
  grep -q 'journal-event/v8.json' "$PLAN/journal.ndjson"
  run grep -q 'journal-event/v7.json' "$PLAN/journal.ndjson"
  [ "$status" -ne 0 ] || return 1
  # the conformance checker pairs the v7 manifest with the v8 contract (not a torn pair)
  run python3 "$SK/verify/plan_contract.py" "$PLAN"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"manifest pairs with a"* ]]
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  python3 "$LEDGER" --plan "$PLAN" project >/dev/null
  grep -qF '"generated_by": "dwp-ledger/8.0"' "$PLAN/state.json"
  grep -qF '"schema": "https://deepworkplan.com/schema/plan-snapshot/v8.json"' "$PLAN/state.json"
  mkdir -p "$WORK/wt"
  digest="sha256:$(printf 'x' | shasum -a 256 | cut -c1-64)"
  run env PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-publish-schemas \
      --json "{\"delegation_id\": \"d1\", \"transport\": \"headless\", \"via\": \"agentkit\", \"kind\": \"claude\", \"target\": \"$WORK/wt\", \"worktree\": \"$WORK/wt\", \"prompt_digest\": \"$digest\"}"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  grep -q '"type": "delegation"' "$PLAN/journal.ndjson" || grep -q '"delegation' "$PLAN/journal.ndjson"
}

@test "the v8 spec is indexed, in the generation table, normative, and its blocker rules are stated" {
  grep -q '\[`LOOP_ENGINEERING.md`\](LOOP_ENGINEERING.md)' "$SK/spec/README.md"
  grep -q '^| v8 | `plan-contract/v8` | `journal-event/v8` | `plan-manifest/v7` |' "$SK/spec/V6_LIFECYCLE.md"
  grep -q 'RFC 2119' "$SPEC"
  [ "$(grep -c 'MUST' "$SPEC")" -ge 8 ]
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  # the status paragraph is lifted: the fields ship with their schemas
  run grep -q 'a writer MUST NOT add these fields' "$SPEC"
  [ "$status" -ne 0 ] || return 1
  run grep -q 'Status: specified for the 8.0.0 line' "$SPEC"
  [ "$status" -ne 0 ] || return 1
  c "$SPEC" '`resolver: "lead"` MUST be refused for `C1`, `C2`, `C5` and `C6`'
  c "$SPEC" 'At most one blocker MUST be active per plan'
  c "$SPEC" 'While a blocker is unresolved its task MUST NOT complete'
  c "$SPEC" 'A v8 plan MUST record its events under `journal-event/v8`'
  c "$SPEC" 'A v8 plan MUST keep the v7 manifest line (`plan-manifest/v7`)'
  # the retained v5 state stays closed and untouched: v8 blockers live in
  # the v8 snapshot, never in plan-state/v5
  python3 - "$SK/spec/schema/plan-state-v5.schema.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
blocked = doc['properties']['blocked']
alts = blocked.get('anyOf') or blocked.get('oneOf') or [blocked]
objs = [a for a in alts if a.get('type') == 'object' or 'properties' in a]
assert objs and all(o.get('additionalProperties') is False and 'resolver' not in o.get('properties', {}) for o in objs), objs
PY
}

@test "the 8.x pack creates v8 plans by default; explicit v7 and v6 requests are honoured" {
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  c "$SK/create/v6.md" '**v8 is the default for new plans on the 8.x pack**'
  c "$SK/create/v6.md" '`https://deepworkplan.com/schema/plan-contract/v8.json`'
  c "$SK/create/v6.md" 'An explicit `v7` request writes `https://deepworkplan.com/schema/plan-contract/v7.json`'
  c "$SK/create/SKILL.md" 'With this 8.x pack, v8 is the default for new plans'
  c "$SK/spec/V6_LIFECYCLE.md" 'With the current 8.x pack, new plans use the v8 contract generation by default'
  c "$SK/spec/README.md" 'New plans created by the 8.x pack use the v8 contract generation'
  # no surface still names v7 as the default for new plans of the current pack
  run bash -c "grep -rn 'v7 is the default for new' '$SK' | grep -v 'V7_ROADMAP.md'"
  [ "$status" -ne 0 ] || { echo "$output"; return 1; }
}

@test "review: one ordered generation ladder; a promptable address must match whole" {
  python3 - "$SHARED" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import contract_v6 as C
assert C.GENERATION_ORDER == ('v6', 'v7', 'v8')
assert C.generation_at_least('v8', 'v7') and C.generation_at_least('v7', 'v7')
assert not C.generation_at_least('v6', 'v7') and not C.generation_at_least(None, 'v7')
assert 'v8' in C.contract_generation.__doc__
PY
  _doc "$WORK/nl.json" "doc['autonomy'] = {'promptable': ['local:w1:p2\n']}"
  run _valid "$WORK/nl.json"
  [ "$status" -ne 0 ]
}

@test "review of #99: appointment is consistent, the queue rule is readiness, links follow the pin, the router names Lite and Full" {
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  c "$SPEC" 'The daemon MUST NOT write the lead record. A peer outside the recorded succession MAY become lead only through Appointment or Revive below, by its own takeover, never by the daemon.'
  # Revive (herdr-peers v2.2.0) is human-granted, ticketed, never takes over a live lead
  c "$SPEC" 'Revive MUST require a human start of the daemon with `--revive`; that start is the grant.'
  c "$SPEC" "The helper MUST accept that takeover only with the daemon's one-time ticket"
  c "$SPEC" 'A stalled plan whose lead is live MUST NOT be taken over'
  c "$SPEC" 'a revived lead, like an appointed one, MUST run `lead verify` before a merge, tag, or release.'
  ! c "$SPEC" 'or appoint a peer outside the recorded succession'
  c "$SPEC" 'When a queued item is ready (its `after` plan is completed, or it has none)'
  c "$SPEC" 'The daemon MAY read the queue and MUST NOT write it.'
  tag="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product"]["tag"])' "$SK/addons/herdr/addon.json")"
  ! grep -o 'herdr-peers/blob/v[0-9.]*' "$SPEC" | grep -v "blob/$tag\$"
  c "$SK/SKILL.md" 'Plans are Lite (bounded work) or Full (task files, longer work).'
}
