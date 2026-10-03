#!/usr/bin/env bash
# v6 opt-in benchmark field metrics (spec/BENCHMARK.md): config discovery
# and fail-closed precedence, journal-derived derivation, the no-imputation
# rule for metered quantities, determinism, the never-blocking emission
# contract, v5 refusal, and the aggregate report.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
BENCHMARK="$SK/shared/benchmark.py"

export PYTHONDONTWRITEBYTECODE=1

setup() {
  TEST_REPO="$(mktemp -d)"
  HOME="$TEST_REPO/home"
  mkdir -p "$HOME"
  PLAN="$TEST_REPO/.dwp/plans/PLAN_101_bats_probe"
  mkdir -p "$PLAN"
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

# A synthetic v6 plan: minimal manifest/contract/state plus a journal with
# two tasks, a failed gate retried to success, an adaptation, a refusal and
# (optionally) metered samples. Written through python so the JSON is exact.
_write_plan() {
  local dir="$1" metered="$2"
  mkdir -p "$dir"
  PLAN_DIR="$dir" METERED="$metered" python3 - <<'PY'
import json, os
plan_dir, metered = os.environ['PLAN_DIR'], os.environ['METERED']
name = os.path.basename(plan_dir.rstrip('/'))
cid = 'd' * 64
json.dump({'schema': 'https://deepworkplan.com/schema/plan-manifest/v6.json',
           'plan': name,
           'contract': {'path': 'contract.json', 'id': cid}},
          open(os.path.join(plan_dir, 'manifest.json'), 'w'))
json.dump({'schema': 'https://deepworkplan.com/schema/plan-contract/v6.json',
           'plan': name, 'title': 'bats probe',
           'contract_id': cid, 'spec_version': '6.0.0', 'revision': 1,
           'tasks': [
               {'id': 'T-one', 'title': 'one', 'prerequisites': [],
                'gate_intent': [{'criterion': 'AC-one', 'check': 'true'}]},
               {'id': 'T-two', 'title': 'two', 'prerequisites': ['T-one'],
                'gate_intent': [{'criterion': 'AC-two', 'check': 'true'}]}],
           'acceptance': [{'criterion': 'AC-one'}, {'criterion': 'AC-two'}],
           'invariants': [{'id': 'INV-one', 'statement': 's'}]},
          open(os.path.join(plan_dir, 'contract.json'), 'w'))
json.dump({'schema': 'https://deepworkplan.com/schema/plan-state/v5.json',
           'plan': name, 'contract_id': cid, 'blocker': None,
           'tasks': [{'id': 'T-one', 'status': 'completed', 'title': 'one'},
                     {'id': 'T-two', 'status': 'completed', 'title': 'two'}]},
          open(os.path.join(plan_dir, 'state.json'), 'w'))
events = [
    {'type': 'approval', 'ts': '2026-03-01T09:00:00Z', 'seq': 1},
    {'type': 'task_start', 'ts': '2026-03-01T09:05:00Z', 'seq': 2,
     'task': 'T-one', 'fingerprint': {'revision': '0' * 40, 'dirty': ''}},
    {'type': 'gate_run', 'ts': '2026-03-01T09:20:00Z', 'seq': 3, 'task': 'T-one',
     'criterion': 'AC-one', 'exit_code': 1, 'trust': 'observed'},
    {'type': 'adaptation', 'ts': '2026-03-01T09:25:00Z', 'seq': 4,
     'kind': 'retry', 'rationale': 'first gate run failed; rerun after fix'},
    {'type': 'gate_run', 'ts': '2026-03-01T09:40:00Z', 'seq': 5, 'task': 'T-one',
     'criterion': 'AC-one', 'exit_code': 0, 'trust': 'observed'},
    {'type': 'task_start', 'ts': '2026-03-01T10:00:00Z', 'seq': 6,
     'task': 'T-two', 'fingerprint': {'revision': '1' * 40, 'dirty': ''}},
    {'type': 'gate_run', 'ts': '2026-03-01T10:30:00Z', 'seq': 7, 'task': 'T-two',
     'criterion': 'AC-two', 'exit_code': 0, 'trust': 'imported'},
    {'type': 'refusal', 'ts': '2026-03-01T10:35:00Z', 'seq': 8,
     'subject': 'ledger', 'stage': 'complete',
     'reason': 'criteria lacked in-window evidence'},
]
if metered == 'yes':
    events += [
        {'type': 'resource_sample', 'ts': '2026-03-01T10:36:00Z', 'seq': 9,
         'limit_id': 'spend_usd', 'value': 4.5, 'unit': 'USD'},
        {'type': 'resource_sample', 'ts': '2026-03-01T10:37:00Z', 'seq': 10,
         'limit_id': 'tokens', 'value': 25000, 'unit': 'tokens'},
    ]
with open(os.path.join(plan_dir, 'journal.ndjson'), 'w') as fh:
    for event in events:
        fh.write(json.dumps(event) + '\n')
PY
}

_write_v5_plan() {
  local dir="$1"
  mkdir -p "$dir"
  printf '# v5 plan\n' > "$dir/README.md"
  json_like='{"schema": "https://deepworkplan.com/schema/plan-manifest/v5.json", "spec_version": "5.0.0"}'
  printf '%s\n' "$json_like" > "$dir/manifest.json"
}

_enable_repo() { printf '{"benchmark": {"enabled": true}}\n' > "$TEST_REPO/.dwp/config.json"; }
_enable_home() { mkdir -p "$HOME/.dwp"; printf '{"benchmark": {"enabled": true}}\n' > "$HOME/.dwp/config.json"; }

_field() {
  REC="$1" KEY="$2" python3 - <<'PY'
import json, os
rec = json.load(open(os.environ['REC']))
node = rec
for part in os.environ['KEY'].split('.'):
    node = node[part]
print(node)
PY
}

@test "disabled by default: no config anywhere means nothing emitted" {
  _write_plan "$PLAN" no
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"disabled"* ]]
  [ ! -e "$PLAN/analysis_results/benchmark.json" ]
  [ ! -e "$PLAN/analysis_results/DWP_REPORT.md" ]
}

@test "config precedence: repo enables, repo overrides global, global fills an absent repo key" {
  _write_plan "$PLAN" no
  # repo config alone enables
  _enable_repo
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"record emitted"* ]]
  rm "$TEST_REPO/.dwp/config.json" "$PLAN/analysis_results/benchmark.json" "$PLAN/analysis_results/DWP_REPORT.md"
  # repo 'false' overrides a global 'true' (per-key wholesale override)
  _enable_home
  printf '{"benchmark": {"enabled": false}}\n' > "$TEST_REPO/.dwp/config.json"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"disabled"* ]]
  rm "$TEST_REPO/.dwp/config.json"
  # no repo file at all: the global enables
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"record emitted"* ]]
}

@test "malformed config fails closed: disabled, warned, exit 0" {
  _write_plan "$PLAN" no
  printf '{broken json\n' > "$TEST_REPO/.dwp/config.json"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"unreadable"* ]]
  [[ "$output" == *"disabled"* ]]
  [ ! -e "$PLAN/analysis_results/benchmark.json" ]
  printf '{"benchmark": {"enabled": "yes"}}\n' > "$TEST_REPO/.dwp/config.json"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"not a boolean"* ]]
  [ ! -e "$PLAN/analysis_results/benchmark.json" ]
}

@test "journal-derived metrics: span, friction, gate and evidence histograms" {
  _write_plan "$PLAN" no
  _enable_repo
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  REC="$PLAN/analysis_results/benchmark.json"
  # calendar span 09:00 -> 10:35 = 5700 s, both started tasks counted once
  [ "$(_field "$REC" timing.span_seconds)" = "5700" ]
  [ "$(_field "$REC" timing.task_count_spanned)" = "2" ]
  [ "$(_field "$REC" timing.first_event_ts)" = "2026-03-01T09:00:00Z" ]
  # friction: one adaptation, one refusal, one retry after the failed gate
  [ "$(_field "$REC" friction.adaptations)" = "1" ]
  [ "$(_field "$REC" friction.refusals)" = "1" ]
  [ "$(_field "$REC" friction.retries)" = "1" ]
  # gates: 3 runs, 2 ok / 1 nonzero; trust labels split observed/imported
  [ "$(_field "$REC" gates.runs)" = "3" ]
  [ "$(_field "$REC" gates.exit_0)" = "2" ]
  [ "$(_field "$REC" gates.exit_nonzero)" = "1" ]
  [ "$(_field "$REC" gates.evidence_histogram.observed)" = "2" ]
  [ "$(_field "$REC" gates.evidence_histogram.imported)" = "1" ]
  [ "$(_field "$REC" gates.evidence_histogram.asserted)" = "0" ]
  # shape: contract identity counts, not journal guesses
  [ "$(_field "$REC" shape.tasks)" = "2" ]
  [ "$(_field "$REC" shape.criteria)" = "2" ]
  [ "$(_field "$REC" shape.events)" = "8" ]
}

@test "no resource samples: tokens and spend stay null, never imputed" {
  _write_plan "$PLAN" no
  _enable_repo
  python3 "$BENCHMARK" report --plan "$PLAN"
  REC="$PLAN/analysis_results/benchmark.json"
  [ "$(_field "$REC" metered.flag)" = "False" ]
  [ "$(_field "$REC" metered.tokens)" = "None" ]
  [ "$(_field "$REC" metered.spend_usd)" = "None" ]
  grep -q 'Not metered' "$PLAN/analysis_results/DWP_REPORT.md"
}

@test "metered samples: values summed per unit and the flag flips" {
  _write_plan "$PLAN" yes
  _enable_repo
  python3 "$BENCHMARK" report --plan "$PLAN"
  REC="$PLAN/analysis_results/benchmark.json"
  [ "$(_field "$REC" metered.flag)" = "True" ]
  [ "$(_field "$REC" metered.tokens)" = "25000" ]
  [ "$(_field "$REC" metered.spend_usd)" = "4.5" ]
}

@test "determinism: two report runs rewrite byte-identical artifacts" {
  _write_plan "$PLAN" yes
  _enable_repo
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  cp "$PLAN/analysis_results/benchmark.json" "$TEST_REPO/first.json"
  cp "$PLAN/analysis_results/DWP_REPORT.md" "$TEST_REPO/first.md"
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  cmp "$TEST_REPO/first.json" "$PLAN/analysis_results/benchmark.json"
  cmp "$TEST_REPO/first.md" "$PLAN/analysis_results/DWP_REPORT.md"
}

@test "non-blocking: an unwritable analysis_results degrades to a warning" {
  _write_plan "$PLAN" no
  _enable_repo
  mkdir -p "$PLAN/analysis_results"
  chmod 555 "$PLAN/analysis_results"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  status=$?
  chmod 755 "$PLAN/analysis_results"
  [ "$status" -eq 0 ]
  [[ "$output" == *"benchmark:"* ]]
}

@test "non-blocking: a torn journal tail derives from the valid prefix" {
  _write_plan "$PLAN" no
  _enable_repo
  printf '{"type": "gate_run", "ts": "2026-03-01T1' >> "$PLAN/journal.ndjson"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"torn"* ]]
  [ "$(_field "$PLAN/analysis_results/benchmark.json" shape.events)" = "8" ]
}

@test "v5 plans are refused with one line and nothing is written" {
  _write_v5_plan "$TEST_REPO/.dwp/plans/PLAN_102_v5_left_alone"
  _enable_repo
  run python3 "$BENCHMARK" report --plan "$TEST_REPO/.dwp/plans/PLAN_102_v5_left_alone"
  [ "$status" -eq 0 ]
  [[ "$output" == *"v5 line is frozen"* ]]
  [ ! -e "$TEST_REPO/.dwp/plans/PLAN_102_v5_left_alone/analysis_results" ]
}

@test "aggregate: groups both roots, lists v5 as not collected, CSV matches" {
  # root A: the metered probe; root B: an unmetered twin under another repo name
  _write_plan "$PLAN" yes
  _enable_repo
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  ROOT_B="$TEST_REPO/repos/b-repo"
  _write_plan "$ROOT_B/.dwp/plans/PLAN_103_twin_probe" no
  printf '{"benchmark": {"enabled": true}}\n' > "$ROOT_B/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$ROOT_B/.dwp/plans/PLAN_103_twin_probe" >/dev/null
  _write_v5_plan "$ROOT_B/.dwp/plans/PLAN_104_v5_twin"
  run python3 "$BENCHMARK" aggregate --roots "$TEST_REPO" "$ROOT_B" \
      --csv "$TEST_REPO/agg.csv" --out "$TEST_REPO/agg.md"
  [ "$status" -eq 0 ]
  grep -q 'PLAN_101_bats_probe\|a-repo\|tmp' "$TEST_REPO/agg.md"
  grep -q 'Not collected' "$TEST_REPO/agg.md"
  grep -q 'PLAN_104_v5_twin' "$TEST_REPO/agg.md"
  # the non-causality note rides every aggregate
  grep -q 'not a causal comparison' "$TEST_REPO/agg.md"
  # CSV: header + exactly the two v6 records, v5 absent
  [ "$(tail -n +2 "$TEST_REPO/agg.csv" | wc -l | tr -d ' ')" = "2" ]
  grep -q 'PLAN_101_bats_probe' "$TEST_REPO/agg.csv"
  grep -q 'PLAN_103_twin_probe' "$TEST_REPO/agg.csv"
  run ! grep -q 'PLAN_104_v5_twin' "$TEST_REPO/agg.csv"
}

@test "emitted records validate against the shipped schema" {
  python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
  _write_plan "$PLAN" yes
  _enable_repo
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  SCHEMA="$SK/spec/schema/benchmark-record.schema.json" \
    REC="$PLAN/analysis_results/benchmark.json" python3 - <<'PY'
import json, os, sys
import jsonschema
schema = json.load(open(os.environ['SCHEMA']))
record = json.load(open(os.environ['REC']))
jsonschema.Draft202012Validator(schema).validate(record)
PY
}

@test "the shipped benchmark self-test passes" {
  run python3 "$BENCHMARK" self-test
  [ "$status" -eq 0 ]
  [[ "$output" == *"self-test: OK"* ]]
}
