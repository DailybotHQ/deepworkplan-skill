#!/usr/bin/env bash
# v6 opt-in benchmark field metrics + learnings (spec/BENCHMARK.md): config
# discovery and fail-closed precedence, journal-derived derivation, the
# no-imputation rule for metered quantities, determinism, the never-blocking
# emission contract, v5 refusal, the aggregate report, and the learnings
# lifecycle (nested sub-flag, written-once curated half, render parity,
# aggregate learnings digest and CSV columns).
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
import hashlib, json, os
plan_dir, metered = os.environ['PLAN_DIR'], os.environ['METERED']
name = os.path.basename(plan_dir.rstrip('/'))
# distinct contract identity per plan: the aggregate joins records to
# learnings by contract_id, so two probe plans must never share one
cid = hashlib.sha256(name.encode()).hexdigest()
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

# The raw text of a learnings file's top-level curated array, extracted with
# the shipped scanner - written-once probes compare these bytes directly.
_curated_slice() {
  LRN_PATH="$1" BENCHMARK_MODULE="$BENCHMARK" python3 - <<'PY'
import importlib.util, os
spec = importlib.util.spec_from_file_location('benchmark', os.environ['BENCHMARK_MODULE'])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
raw = open(os.environ['LRN_PATH'], encoding='utf-8').read()
print(module._extract_top_level_array(raw, 'curated'))
PY
}

# Author curated entries into a learnings file the way the completing agent
# would: parsed, edited, written back in its own hand format.
_author_curated() {
  LRN_PATH="$1" CURATED="$2" python3 - <<'PY'
import json, os
doc = json.load(open(os.environ['LRN_PATH']))
doc['curated'] = json.loads(os.environ['CURATED'])
with open(os.environ['LRN_PATH'], 'w', encoding='utf-8') as fh:
    json.dump(doc, fh, indent=4)
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
  # exactly one line: the refusal itself, nothing else
  [ "$(printf '%s\n' "$output" | wc -l | tr -d ' ')" = "1" ]
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

@test "nested learnings config: metrics-only, malformed sub-flag, disabled writes nothing" {
  _write_plan "$PLAN" no
  # enabled without learnings: the record ships, the learnings artifact never
  _enable_repo
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"record emitted"* ]]
  [ -e "$PLAN/analysis_results/benchmark.json" ]
  [ -e "$PLAN/analysis_results/DWP_REPORT.md" ]
  [ ! -e "$PLAN/analysis_results/learnings.json" ]
  # malformed learnings value: one warning, learnings off, metrics unaffected
  printf '{"benchmark": {"enabled": true, "learnings": "yes"}}\n' > "$TEST_REPO/.dwp/config.json"
  rm -f "$PLAN/analysis_results/"*
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"not a boolean"* ]]
  [[ "$output" == *"record emitted"* ]]
  [ -e "$PLAN/analysis_results/benchmark.json" ]
  [ ! -e "$PLAN/analysis_results/learnings.json" ]
  # enabled false forces learnings off too: no benchmark, no learnings, no report
  printf '{"benchmark": {"enabled": false, "learnings": true}}\n' > "$TEST_REPO/.dwp/config.json"
  rm -f "$PLAN/analysis_results/"*
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"disabled"* ]]
  [ ! -e "$PLAN/analysis_results/benchmark.json" ]
  [ ! -e "$PLAN/analysis_results/learnings.json" ]
  [ ! -e "$PLAN/analysis_results/DWP_REPORT.md" ]
}

@test "learnings emission: template created with the invitation, derived populated" {
  _write_plan "$PLAN" no
  printf '{"benchmark": {"enabled": true, "learnings": true}}\n' > "$TEST_REPO/.dwp/config.json"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"learnings record created"* ]]
  [[ "$output" == *"spec section 10"* ]]
  LRN="$PLAN/analysis_results/learnings.json"
  [ -e "$LRN" ]
  [ "$(_field "$LRN" curated)" = "[]" ]
  # the derived half explains the journal's friction, reasons verbatim
  DERIVED_N="$LRN" python3 -c 'import json,os;print(len(json.load(open(os.environ["DERIVED_N"]))["derived"]))' > "$TEST_REPO/derived_n"
  [ "$(cat "$TEST_REPO/derived_n")" = "3" ]
  grep -q 'first gate run failed; rerun after fix' "$LRN"
  grep -q 'criteria lacked in-window evidence' "$LRN"
  grep -q 'exit_code=1' "$LRN"
}

@test "written-once: curated entries survive a rerun byte-identically while derived regenerates" {
  _write_plan "$PLAN" no
  printf '{"benchmark": {"enabled": true, "learnings": true}}\n' > "$TEST_REPO/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  LRN="$PLAN/analysis_results/learnings.json"
  _author_curated "$LRN" '[
        {"id": "LRN-001", "category": "instruction-gap",
         "anchor": {"seq": 3, "section": "Validation gates"},
         "finding": "hand authored finding",
         "proposal": "hand authored proposal"}]'
  _curated_slice "$LRN" > "$TEST_REPO/curated_before.txt"
  # the journal grows (a later refusal), then the report reruns
  printf '%s\n' '{"type": "refusal", "ts": "2026-03-01T11:00:00Z", "seq": 9, "subject": "scheduler", "stage": "dispatch", "reason": "invariant evaluated before task start"}' >> "$PLAN/journal.ndjson"
  run python3 "$BENCHMARK" report --plan "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"curated preserved byte-for-byte"* ]]
  _curated_slice "$LRN" > "$TEST_REPO/curated_after.txt"
  cmp "$TEST_REPO/curated_before.txt" "$TEST_REPO/curated_after.txt"
  # the derived half regenerated from the grown journal
  DERIVED_N="$LRN" python3 -c 'import json,os;print(len(json.load(open(os.environ["DERIVED_N"]))["derived"]))' > "$TEST_REPO/derived_n"
  [ "$(cat "$TEST_REPO/derived_n")" = "4" ]
  grep -q 'invariant evaluated before task start' "$LRN"
}

@test "render parity: DWP_REPORT.md carries only what the JSON sources carry" {
  _write_plan "$PLAN" yes
  printf '{"benchmark": {"enabled": true, "learnings": true}}\n' > "$TEST_REPO/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  LRN="$PLAN/analysis_results/learnings.json"
  REPORT="$PLAN/analysis_results/DWP_REPORT.md"
  _author_curated "$LRN" '[
        {"id": "LRN-001", "category": "spec-gap",
         "anchor": {"seq": 3, "section": "Validation gates"},
         "finding": "parity probe finding",
         "proposal": "parity probe proposal"}]'
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  # curated entry and anchor render from learnings.json only
  grep -q 'LRN-001' "$REPORT"
  grep -q 'spec-gap' "$REPORT"
  grep -q 'seq 3 / Validation gates' "$REPORT"
  grep -q 'parity probe finding' "$REPORT"
  # derived reasons render verbatim from the journal's recorded words
  grep -q 'first gate run failed; rerun after fix' "$REPORT"
  # honesty footer: the report names itself a rendering
  grep -q 'never a second' "$REPORT"
  # metrics-only repository: no learnings section may appear in the report
  printf '{"benchmark": {"enabled": true}}\n' > "$TEST_REPO/.dwp/config.json"
  rm -f "$LRN"
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  run ! grep -q 'Learnings (curated)' "$REPORT"
  run ! grep -q 'Friction explained' "$REPORT"
}

@test "aggregate learnings digest: version groups, not_collected, unanchored separation" {
  # root A: learnings on - curated entries incl. one unanchored, one
  # section-anchored and one seq-only anchor
  _write_plan "$PLAN" no
  printf '{"benchmark": {"enabled": true, "learnings": true}}\n' > "$TEST_REPO/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  _author_curated "$PLAN/analysis_results/learnings.json" '[
        {"id": "LRN-001", "category": "spec-gap",
         "anchor": {"section": "Validation gates"}, "finding": "f1", "proposal": "p1"},
        {"id": "LRN-002", "category": "spec-gap", "anchor": null,
         "finding": "f2", "proposal": "p2"},
        {"id": "LRN-003", "category": "docs-gap", "anchor": {"seq": 2},
         "finding": "f3", "proposal": "p3"}]'
  # root B: metrics only - learnings never collected
  ROOT_B="$TEST_REPO/repos/b-repo"
  _write_plan "$ROOT_B/.dwp/plans/PLAN_103_twin_probe" no
  printf '{"benchmark": {"enabled": true}}\n' > "$ROOT_B/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$ROOT_B/.dwp/plans/PLAN_103_twin_probe" >/dev/null
  run python3 "$BENCHMARK" aggregate --roots "$TEST_REPO" "$ROOT_B" \
      --csv "$TEST_REPO/agg.csv" --out "$TEST_REPO/agg.md"
  [ "$status" -eq 0 ]
  grep -q '## Learnings digest' "$TEST_REPO/agg.md"
  # the non-causality note rides the digest too
  grep -q 'not a causal comparison' "$TEST_REPO/agg.md"
  # categories counted within the version group
  grep -q 'Curated: 3 total' "$TEST_REPO/agg.md"
  # section ranking counts section anchors only, seq-only never folds in
  grep -q '`Validation gates` (1)' "$TEST_REPO/agg.md"
  # the unanchored entry is counted separately, never dropped
  grep -q 'Unanchored: 1' "$TEST_REPO/agg.md"
  # plans without learnings are named, never guessed
  grep -q 'learnings: "not_collected"' "$TEST_REPO/agg.md"
  grep -q 'PLAN_103_twin_probe' "$TEST_REPO/agg.md"
  grep -q 'with ≥1 spec-gap: 1' "$TEST_REPO/agg.md"
}

@test "aggregate CSV: learnings columns match the curated sources; absent learnings are zeros" {
  _write_plan "$PLAN" no
  printf '{"benchmark": {"enabled": true, "learnings": true}}\n' > "$TEST_REPO/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$PLAN" >/dev/null
  _author_curated "$PLAN/analysis_results/learnings.json" '[
        {"id": "LRN-001", "category": "spec-gap",
         "anchor": {"section": "Validation gates"}, "finding": "f1", "proposal": "p1"},
        {"id": "LRN-002", "category": "context-miss", "anchor": null,
         "finding": "f2", "proposal": "p2"}]'
  ROOT_B="$TEST_REPO/repos/b-repo"
  _write_plan "$ROOT_B/.dwp/plans/PLAN_103_twin_probe" no
  printf '{"benchmark": {"enabled": true}}\n' > "$ROOT_B/.dwp/config.json"
  python3 "$BENCHMARK" report --plan "$ROOT_B/.dwp/plans/PLAN_103_twin_probe" >/dev/null
  run python3 "$BENCHMARK" aggregate --roots "$TEST_REPO" "$ROOT_B" \
      --csv "$TEST_REPO/agg.csv" --out "$TEST_REPO/agg.md"
  [ "$status" -eq 0 ]
  AGG="$TEST_REPO/agg.csv" python3 - <<'PY'
import csv, os
rows = list(csv.reader(open(os.environ['AGG'])))
header = rows[0]
for column in ('learnings_total', 'lrn_spec_gap', 'lrn_instruction_gap',
               'lrn_tooling_gap', 'lrn_docs_gap', 'lrn_gate_false_positive',
               'lrn_gate_false_negative', 'lrn_context_miss', 'lrn_unanchored'):
    assert column in header, f'missing learnings column {column}'
def cell(plan, column):
    row = next(r for r in rows[1:] if r[header.index('plan')] == plan)
    return row[header.index(column)]
got = {c: cell('PLAN_101_bats_probe', c) for c in
       ('learnings_total', 'lrn_spec_gap', 'lrn_context_miss', 'lrn_docs_gap', 'lrn_unanchored')}
want = {'learnings_total': '2', 'lrn_spec_gap': '1', 'lrn_context_miss': '1',
        'lrn_docs_gap': '0', 'lrn_unanchored': '1'}
assert got == want, f'row A learnings columns disagree with the curated JSON: {got}'
for column in ('learnings_total', 'lrn_spec_gap', 'lrn_unanchored'):
    assert cell('PLAN_103_twin_probe', column) == '0', \
        f'plan without learnings must carry zeros, not blanks ({column})'
PY
  # determinism: rerunning the aggregate rewrites identical bytes
  cp "$TEST_REPO/agg.csv" "$TEST_REPO/agg1.csv"
  cp "$TEST_REPO/agg.md" "$TEST_REPO/agg1.md"
  python3 "$BENCHMARK" aggregate --roots "$TEST_REPO" "$ROOT_B" \
      --csv "$TEST_REPO/agg.csv" --out "$TEST_REPO/agg.md" >/dev/null
  cmp "$TEST_REPO/agg1.csv" "$TEST_REPO/agg.csv"
  cmp "$TEST_REPO/agg1.md" "$TEST_REPO/agg.md"
}

@test "the shipped benchmark self-test passes" {
  run python3 "$BENCHMARK" self-test
  [ "$status" -eq 0 ]
  # the probe count is pinned: losing or silently shrinking probes is a regression
  [[ "$output" == *"self-test: OK (67 probes)"* ]]
}
