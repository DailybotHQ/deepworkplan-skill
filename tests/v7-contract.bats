#!/usr/bin/env bash
# Contract generation v7 (spec/V7_CONTRACT.md): v7 = v6 + the parallel_safe
# task marker + the delegation journal event, detected by schema URL, never
# mixed, driven end to end through the SHIPPED helpers: materialize routing
# (v7 and v6), the record-layer delegation gate and its recorded refusals,
# launch -> collect/cancel transitions, a delegation never closing a
# criterion, the v6 loop helpers (scheduler, views, receipt, export,
# benchmark) on a v7 plan, and the ledger fingerprint covering directory
# entries of a touched surface.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SHARED="$SK/shared"
LEDGER="$SHARED/ledger.py"
CV6="$SHARED/contract_v6.py"
CFG="$SHARED/config.py"
FIX="$REPO_ROOT/tests/fixtures/v7"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  mkdir -p "$HOME" "$WORK/bin"
  REPO="$WORK/repo"
  PLAN="$REPO/.dwp/plans/PLAN_v7_fixture_minimal"
  mkdir -p "$PLAN/analysis_results" "$REPO/src"
  printf '# Goal\n\nv7 records.\n' > "$PLAN/README.md"
  printf 'x = 1\n' > "$REPO/src/product.py"
  printf '#!/bin/sh\necho "{\\"interface\\": 1}"\n' > "$WORK/bin/ak"
  chmod +x "$WORK/bin/ak"
  DIGEST="sha256:$(printf 'prompt' | shasum -a 256 | cut -c1-64)"
}

teardown() { rm -rf "$WORK"; }

# _draft [generation] [jq-like python mutation]
_draft() {
  python3 - "$FIX/contract-minimal-v7.json" "$PLAN/draft.json" "${1:-v7}" "${2:-}" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
if sys.argv[3] == 'v6':
    doc['schema'] = 'https://deepworkplan.com/schema/plan-contract/v6.json'
    for t in doc['tasks']:
        t.pop('parallel_safe', None)
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
if sys.argv[4]:
    exec(sys.argv[4])
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
}
_materialize() { python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" --authority bats --mechanism plan_authorship; }
_launch() { # _launch <task> [extra-json-fields]
  PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task "$1" \
    --json "{\"transport\": \"headless\", \"via\": \"agentkit\", \"prompt_digest\": \"$DIGEST\"${2:+, $2}}"
}
_types() { python3 -c 'import json,sys; print(" ".join(json.loads(l)["type"] for l in open(sys.argv[1])))' "$PLAN/journal.ndjson"; }

@test "fixtures: the ledger-generated v7 contract and journal validate at runtime" {
  run python3 "$CV6" validate-contract "$FIX/contract-minimal-v7.json"
  [ "$status" -eq 0 ]
  run python3 "$CV6" validate-journal "$FIX/journal-delegation-v7.ndjson" --contract "$FIX/contract-minimal-v7.json"
  [ "$status" -eq 0 ]
  [[ "$output" == *"delegation x2"* ]] || return 1
}

@test "materialize routes by contract URL: v7 manifest and v7 events" {
  _draft v7; run _materialize
  [ "$status" -eq 0 ]
  grep -qF '"schema": "https://deepworkplan.com/schema/plan-manifest/v7.json"' "$PLAN/manifest.json"
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  python3 - "$PLAN/journal.ndjson" <<'PY'
import json, sys
urls = {json.loads(l)['schema'] for l in open(sys.argv[1])}
assert urls == {'https://deepworkplan.com/schema/journal-event/v7.json'}, urls
PY
}

@test "an explicit v6 contract still materializes v6, and a v6 contract cannot carry parallel_safe" {
  _draft v6; run _materialize
  [ "$status" -eq 0 ]
  grep -qF 'plan-manifest/v6.json' "$PLAN/manifest.json"
  grep -qF 'journal-event/v6.json' "$PLAN/journal.ndjson"
  rm -rf "$PLAN"/{manifest.json,contract.json,journal.ndjson}
  _draft v6 "doc['tasks'][0]['parallel_safe'] = True"
  run _materialize
  [ "$status" -ne 0 ]
  [[ "$output" == *"parallel_safe"* ]] || return 1
}

@test "a v6 plan never records delegation: refused and the refusal recorded" {
  _draft v6; _materialize >/dev/null
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  run _launch T-publish-schemas
  [ "$status" -eq 5 ]
  [[ "$output" == *"only v7 plans record delegation"* ]] || return 1
  [ "$(_types)" = "approval task_start refusal" ]
}

@test "gate: no agent_delegation grant refuses" {
  _draft v7 "doc['permissions']['granted'].remove('agent_delegation'); doc['permissions']['not_granted'].append('agent_delegation')"
  _materialize >/dev/null
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  run _launch T-publish-schemas
  [ "$status" -eq 5 ]
  [[ "$output" == *"does not grant agent_delegation"* ]] || return 1
}

@test "gate: an unstarted task, an unmarked task, an unenabled or mismatched addon refuse" {
  _draft v7; _materialize >/dev/null
  run _launch T-publish-schemas
  [ "$status" -eq 5 ]; [[ "$output" == *"has not started"* ]] || return 1
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  # registry does not enable agentkit yet
  run _launch T-publish-schemas
  [ "$status" -eq 5 ]; [[ "$output" == *"is not enabled and detected"* ]] || return 1
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  # transport mismatch: agentkit is headless
  run env PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-publish-schemas \
      --json "{\"transport\": \"interactive\", \"via\": \"agentkit\", \"prompt_digest\": \"$DIGEST\"}"
  [ "$status" -eq 5 ]; [[ "$output" == *"carries transport 'headless'"* ]] || return 1
  # unmarked task (T-ship-validator is not parallel_safe), writing delegate
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  run _launch T-ship-validator '"worktree": "../wt"'
  [ "$status" -eq 5 ]; [[ "$output" == *"not marked parallel_safe"* ]] || return 1
  # every refusal is a recorded event
  [ "$(_types | tr ' ' '\n' | grep -c refusal)" -eq 4 ]
}

@test "a read-only delegate (worktree null) may run on an unmarked task" {
  _draft v7; _materialize >/dev/null
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  run _launch T-ship-validator '"worktree": null'
  [ "$status" -eq 0 ]
  [[ "$output" == *"launched"* ]] || return 1
}

@test "transitions: launch -> collect once; terminal states refuse; observe is read-only" {
  _draft v7; _materialize >/dev/null
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  run _launch T-publish-schemas '"delegation_id": "d1", "kind": "claude", "worktree": "../wt-d1"'
  [ "$status" -eq 0 ]
  run _launch T-publish-schemas '"delegation_id": "d1"'
  [ "$status" -eq 5 ]; [[ "$output" == *"already recorded"* ]] || return 1
  echo done > "$PLAN/analysis_results/d1.txt"
  run python3 "$LEDGER" --plan "$PLAN" delegate collect --task T-publish-schemas \
      --json '{"delegation_id": "d1", "state": "completed", "result_path": "analysis_results/d1.txt"}'
  [ "$status" -eq 0 ]
  grep -qF '"result_digest":"sha256:' "$PLAN/journal.ndjson"
  run python3 "$LEDGER" --plan "$PLAN" delegate cancel --task T-publish-schemas --json '{"delegation_id": "d1"}'
  [ "$status" -eq 5 ]; [[ "$output" == *"already completed"* ]] || return 1
  before="$(shasum -a 256 "$PLAN/journal.ndjson")"
  run python3 "$LEDGER" --plan "$PLAN" delegate observe
  [ "$status" -eq 0 ]
  [[ "$output" == *'"state": "completed"'* ]] || return 1
  [ "$before" = "$(shasum -a 256 "$PLAN/journal.ndjson")" ]
}

@test "a raw append cannot write a delegation event" {
  _draft v7; _materialize >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" append --type delegation \
      --json '{"task": "T-publish-schemas", "delegation_id": "x", "transport": "headless", "via": "agentkit", "state": "completed"}'
  [ "$status" -ne 0 ]
  [[ "$output" == *"produced only by"* ]] || return 1
}

@test "a completed delegation never closes a criterion: the parent's runner does" {
  _draft v7; _materialize >/dev/null
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  _launch T-publish-schemas '"delegation_id": "d2"' >/dev/null
  python3 "$LEDGER" --plan "$PLAN" delegate collect --task T-publish-schemas \
      --json '{"delegation_id": "d2", "state": "completed"}' >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas \
      --criterion AC-valid-contract-shape --json '"python3 --version"'
  [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
}

@test "the v6 loop helpers serve a v7 plan: scheduler, views, receipt, export, verify" {
  _draft v7; _materialize >/dev/null
  run python3 "$SHARED/scheduler.py" ready "$PLAN"
  [ "$status" -eq 0 ]; [[ "$output" == *'"task": "T-publish-schemas"'* ]] || return 1
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"' >/dev/null
  python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" project;               [ "$status" -eq 0 ]
  grep -qF 'plan-snapshot/v6.json' "$PLAN/state.json"
  run python3 "$SHARED/views.py" --plan "$PLAN" render --all;  [ "$status" -eq 0 ]
  run python3 "$SHARED/outcomes.py" --plan "$PLAN" receipt;    [ "$status" -eq 0 ]
  run python3 "$LEDGER" --plan "$PLAN" export --dest "$WORK/export"; [ "$status" -eq 0 ]
  run python3 "$CV6" validate-journal "$PLAN/journal.ndjson" --contract "$PLAN/contract.json"
  [ "$status" -eq 0 ]
  run python3 "$SHARED/context_manifest.py" --plan "$PLAN" manifest --task T-ship-validator --md
  [ "$status" -eq 0 ]
}

@test "benchmark reports a v7 plan as not measured, never mislabelled as v6 or v5" {
  _draft v7; _materialize >/dev/null
  mkdir -p "$REPO/.dwp"
  printf '%s\n' '{"benchmark": {"enabled": true}}' > "$REPO/.dwp/config.json"
  run python3 "$SHARED/benchmark.py" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"plan is v7-generation"*"not measured"* ]] || return 1
  [ ! -f "$PLAN/analysis_results/benchmark.json" ]
}

@test "the gate fingerprint covers files inside a directory touched surface" {
  _draft v7 "doc['tasks'][0]['touched_surface'] = ['src/']"
  _materialize >/dev/null
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"'
  [[ "$output" == RAN:* ]] || return 1
  first="$(printf '%s' "$output" | sed -E 's/.*fingerprint ([0-9a-f]+).*/\1/')"
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"'
  [[ "$output" == REUSED:* ]] || return 1
  printf 'x = 2\n' > "$REPO/src/product.py"
  run python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"'
  [[ "$output" == RAN:* ]] || return 1
  second="$(printf '%s' "$output" | sed -E 's/.*fingerprint ([0-9a-f]+).*/\1/')"
  [ "$first" != "$second" ]
}

@test "docs: V7_CONTRACT.md is normative and indexed; create and the router route v7" {
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  c "$SK/spec/V7_CONTRACT.md" 'A delegation is **not evidence**.'
  c "$SK/spec/V7_CONTRACT.md" 'A raw `append --type delegation` MUST be refused'
  grep -qF '[`V7_CONTRACT.md`](V7_CONTRACT.md)' "$SK/spec/README.md"
  c "$SK/create/v6.md" '**v7 is the default for new plans on the 7.x pack**'
  c "$SK/SKILL.md" '(contract generation v6 or v7, `spec/V7_CONTRACT.md`)'
  c "$SK/spec/V6_LIFECYCLE.md" 'A plan never changes generation'
}

@test "benchmark never labels a pre-release pack as a release: not measured, one line" {
  PACK="$WORK/pack"
  cp -R "$SK" "$PACK"
  sed -i.bak 's/^version: ".*"/version: "7.0.0-beta.1"/' "$PACK/SKILL.md" && rm -f "$PACK/SKILL.md.bak"
  run python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import benchmark; print(benchmark.pack_version())' "$PACK/shared"
  [ "$output" = "7.0.0-beta.1" ]
  _draft v6; _materialize >/dev/null
  mkdir -p "$REPO/.dwp"
  printf '%s\n' '{"benchmark": {"enabled": true}}' > "$REPO/.dwp/config.json"
  run python3 "$PACK/shared/benchmark.py" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"this pack is a pre-release (7.0.0-beta.1)"*"not measured"* ]] || return 1
  [ ! -f "$PLAN/analysis_results/benchmark.json" ]
  find "$PACK" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
}
