#!/usr/bin/env bash
# The governing principle as a test: the DeepWorkPlan methodology works
# alone. No addon is installed, enabled or required for the plan lifecycle,
# and the addon registry (.dwp/config.json "addons") can only amplify —
# never change — what the methodology does.
#
# One lifecycle driver runs the shipped surface end to end (materialize ->
# scheduler ready -> start -> gate -> guarded complete, twice -> project ->
# views -> receipt -> export -> read-only verify surfaces -> resources
# report/routing -> benchmark report) under four configurations:
#
#   none       no .dwp/config.json anywhere (repo or user)
#   disabled   every in-pack addon key present with "enabled": false
#   unknown    only addon keys the pack does not ship, at repo AND user level
#   malformed  an unparseable repo config and a wrong-typed user config
#
# and asserts (1) every run exits 0, (2) the outcomes are identical after
# normalizing timestamps and digests (same journal event types and counts,
# same task statuses, same receipt verdicts), and (3) no file under the
# pack's addons/ tree was opened by any helper — traced with a Python audit
# hook, not inferred from output.
#
# Run with:  bats tests/standalone-methodology.bats
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SHARED="$SK/shared"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"

export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  TRACE="$WORK/addon-opens.log"
  : > "$TRACE"
  # Every helper runs under an audit hook that records any open() of a
  # path inside an addons/ directory (descriptors, SKILL.md, templates).
  cat > "$WORK/traced.py" <<'PY'
import os, runpy, sys
sys.dont_write_bytecode = True
LOG = os.environ['DWP_ADDON_TRACE']
def _hook(event, args):
    if event == 'open' and args and isinstance(args[0], (str, bytes)):
        path = os.fsdecode(args[0]).replace(os.sep, '/')
        if '/addons/' in path:
            with open(LOG, 'a', encoding='utf-8') as fh:
                fh.write(path + '\n')
sys.addaudithook(_hook)
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name='__main__')
PY
}

teardown() {
  rm -rf "$WORK"
  if find "$SK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
    echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
    return 1
  fi
}

# _py <helper> [args...] — run a shipped helper under the trace hook.
_py() {
  local helper="$1"; shift
  DWP_ADDON_TRACE="$TRACE" python3 "$WORK/traced.py" "$SHARED/$helper" "$@"
}

# The in-pack addon keys are the addon directory names (contract A1).
_addon_keys() {
  find "$SK/addons" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
}

# _configure <label> <repo> <home> — write the label's config variant.
_configure() {
  local label="$1" repo="$2" home="$3"
  mkdir -p "$repo/.dwp" "$home"
  case "$label" in
    none) ;;
    disabled)
      _addon_keys | python3 -c '
import json, sys
keys = [k.strip() for k in sys.stdin if k.strip()]
assert keys, "no addon directories found"
json.dump({"addons": {k: {"enabled": False} for k in keys}},
          open(sys.argv[1], "w"), indent=2)' "$repo/.dwp/config.json" ;;
    unknown)
      mkdir -p "$home/.dwp"
      printf '%s\n' '{"addons": {"not-an-addon": {"enabled": true, "version": "v9.9.9"}, "Herdr ": {"enabled": true}}}' \
        > "$repo/.dwp/config.json"
      printf '%s\n' '{"addons": {"teleport": {"enabled": true}}}' \
        > "$home/.dwp/config.json" ;;
    malformed)
      mkdir -p "$home/.dwp"
      printf '%s\n' '{"addons": {"vim": {"enabled": tru' > "$repo/.dwp/config.json"
      printf '%s\n' '{"addons": ["agentkit"], "benchmark": "yes"}' \
        > "$home/.dwp/config.json" ;;
    *) echo "unknown label $label" >&2; return 2 ;;
  esac
}

# _lifecycle <label> — drive the full shipped lifecycle in a fresh repo and
# write a normalized outcome summary to $WORK/<label>.summary.
_lifecycle() {
  local label="$1"
  local repo="$WORK/$label/repo" home="$WORK/$label/home"
  local plan="$repo/.dwp/plans/PLAN_standalone_bats"
  mkdir -p "$plan/analysis_results" "$repo/src"
  printf '# Goal\n\nThe methodology runs alone.\n' > "$plan/README.md"
  printf 'def product(x):\n    return x\n' > "$repo/src/product.py"
  _configure "$label" "$repo" "$home"
  python3 - "$FIXTURE" "$plan" <<'PY'
import json, os, sys
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_standalone_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc['scope']['allowed_command_classes'] = ['python3']
doc['scope']['allowed_paths'] = ['src/']
doc.pop('contract_id', None)
json.dump(doc, open(os.path.join(sys.argv[2], 'draft.json'), 'w'),
          indent=2, sort_keys=True)
PY
  (
    set -e
    export HOME="$home"
    cd "$repo"
    _py ledger.py --plan "$plan" materialize --contract "$plan/draft.json" \
        --authority developer --mechanism plan_authorship
    _py scheduler.py ready "$plan"
    _py ledger.py --plan "$plan" start --task T-publish-schemas
    _py ledger.py --plan "$plan" gate --task T-publish-schemas \
        --criterion AC-valid-contract-shape --json '"python3 --version"'
    _py ledger.py --plan "$plan" complete --task T-publish-schemas
    _py ledger.py --plan "$plan" start --task T-ship-validator
    _py ledger.py --plan "$plan" gate --task T-ship-validator \
        --criterion AC-journal-catalog-closed --json '"python3 --version"'
    _py ledger.py --plan "$plan" complete --task T-ship-validator
    _py ledger.py --plan "$plan" project
    _py views.py --plan "$plan" render --all
    _py outcomes.py --plan "$plan" receipt --out "$WORK/$label.receipt.json"
    _py ledger.py --plan "$plan" export --dest "$plan/analysis_results/export"
    _py contract_v6.py validate-contract "$plan/contract.json"
    _py contract_v6.py validate-journal "$plan/journal.ndjson" \
        --contract "$plan/contract.json"
    _py resources.py --plan "$plan" report
    _py resources.py --plan "$plan" routing
    _py benchmark.py report --plan "$plan"
  ) > "$WORK/$label.out" 2>&1 || { cat "$WORK/$label.out"; return 1; }
  python3 - "$plan" "$WORK/$label.receipt.json" > "$WORK/$label.summary" <<'PY'
import json, os, sys
plan, receipt_path = sys.argv[1], sys.argv[2]
events = [json.loads(l) for l in open(os.path.join(plan, 'journal.ndjson'))]
state = json.load(open(os.path.join(plan, 'state.json')))
receipt = json.load(open(receipt_path))
VOLATILE = {'ts', 'at', 'last_run', 'generated_at', 'digest', 'digests',
            'journal_sha256', 'snapshot', 'fingerprint', 'evidence_path',
            'log', 'duration_s', 'starting_fingerprint', 'plan_digest'}
def norm(value):
    if isinstance(value, dict):
        return {k: norm(v) for k, v in sorted(value.items())
                if k not in VOLATILE}
    if isinstance(value, list):
        return [norm(v) for v in value]
    return value
print(json.dumps({
    'event_types': [e['type'] for e in events],
    'task_status': {t['id']: t['status'] for t in state['tasks']},
    'receipt': norm({'closure': receipt['closure'],
                     'totals': receipt['totals']}),
    'files': sorted(os.path.relpath(os.path.join(d, f), plan)
                    for d, _, fs in os.walk(plan) for f in fs
                    if not f.startswith('.ledger.lock')
                    and not d.startswith(os.path.join(plan, 'analysis_results', 'export'))),
}, indent=1, sort_keys=True))
PY
}

@test "baseline: the lifecycle runs alone with no config anywhere" {
  run _lifecycle none
  [ "$status" -eq 0 ]
  python3 - "$WORK/none.summary" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
assert s['task_status'] == {'T-publish-schemas': 'completed',
                            'T-ship-validator': 'completed'}, s['task_status']
assert s['event_types'][0] == 'approval', s['event_types']
assert s['event_types'].count('gate_run') == 2, s['event_types']
PY
}

@test "every addon disabled: identical outcome" {
  _lifecycle none
  run _lifecycle disabled
  [ "$status" -eq 0 ]
  diff "$WORK/none.summary" "$WORK/disabled.summary"
}

@test "unknown addon keys at repo and user level: identical outcome" {
  _lifecycle none
  run _lifecycle unknown
  [ "$status" -eq 0 ]
  diff "$WORK/none.summary" "$WORK/unknown.summary"
}

@test "malformed and wrong-typed configs fail closed: identical outcome, never an abort" {
  _lifecycle none
  run _lifecycle malformed
  [ "$status" -eq 0 ]
  diff "$WORK/none.summary" "$WORK/malformed.summary"
}

@test "no helper opened any file under an addons/ directory in any configuration" {
  for label in none disabled unknown malformed; do
    _lifecycle "$label"
  done
  if [ -s "$TRACE" ]; then
    echo "addon files opened by the methodology:"; sort -u "$TRACE"
    return 1
  fi
}

@test "the trace hook is live: it records an addons/ open when one happens" {
  # Control for the previous test: a helper run that does read an addon
  # file must be caught, or an empty trace would prove nothing.
  printf "open('%s/addons/README.md').read()\n" "$SK" > "$WORK/reads_addon.py"
  run env DWP_ADDON_TRACE="$TRACE" python3 "$WORK/traced.py" "$WORK/reads_addon.py"
  [ "$status" -eq 0 ]
  grep -qF "/addons/README.md" "$TRACE"
}

@test "no shipped flow names an addon as a requirement of the lifecycle" {
  # Static half of the principle: the flows offer addons, never require
  # them. Phrases that would make an addon a precondition are absent.
  run grep -rniE 'requires? the [a-z-]+ addon|addon (is )?required to (create|execute|verify)' \
      "$SK/create" "$SK/execute" "$SK/verify" "$SK/status" "$SK/resume" "$SK/refine"
  [ "$status" -ne 0 ]
}
