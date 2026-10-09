#!/usr/bin/env bash
# The gate runtime (field report F-21, F-25, F-18, F-19): gates run through
# a declared container wrapper and stay observed; evidence reuse keys on the
# whole working tree, so a fix outside the planned surface never replays a
# failing run; `start` summarizes a dirty tree; `project` is byte-identical
# across renders.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
LEDGER="$SK/shared/ledger.py"
VIEWS="$SK/shared/views.py"
CV6="$SK/shared/contract_v6.py"
FIX="$REPO_ROOT/tests/fixtures/v7/contract-minimal-v7.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  REPO="$WORK/repo"
  PLAN="$REPO/.dwp/plans/PLAN_gates_bats"
  mkdir -p "$HOME" "$WORK/bin" "$PLAN/analysis_results" "$REPO/src"
  printf '# Goal\n\nGates.\n' > "$PLAN/README.md"
  printf 'x = 1\n' > "$REPO/src/product.py"
  git -C "$REPO" init -q
  printf '.dwp/\n' > "$REPO/.gitignore"
  git -C "$REPO" add -A
  git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init
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

# _draft <classes-json> <check for AC-valid-contract-shape>
_draft() {
  python3 - "$FIX" "$WORK/draft.json" "$1" "$2" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
doc.pop('contract_id', None)
doc['plan'] = 'PLAN_gates_bats'
doc['invariants'] = []
doc['scope']['allowed_command_classes'] = json.loads(sys.argv[3])
doc['scope']['allowed_paths'] = ['src/']
for t in doc['tasks']:
    t['touched_surface'] = ['src/product.py']
    for i in t['gate_intent']:
        i['check'] = sys.argv[4] if i['criterion'] == 'AC-valid-contract-shape' else 'python3 -V'
json.dump(doc, open(sys.argv[2], 'w'), indent=2)
PY
}

@test "gates run through a declared container wrapper and stay observed (F-21)" {
  # a stand-in for `dck exec -- <cmd>`: runs the command after `--`
  printf '#!/bin/sh\n[ "$1" = exec ] && [ "$2" = -- ] || exit 64\nshift 2\necho "[container] $*"\nexec "$@"\n' > "$WORK/bin/dck"
  chmod +x "$WORK/bin/dck"
  export PATH="$WORK/bin:$PATH"
  _draft '["python3"]' 'dck exec -- python3 -V'
  run python3 "$CV6" validate-contract "$WORK/draft.json"
  [ "$status" -eq 1 ] && [[ "$output" == *"starts with 'dck'"* ]] || { echo "$output"; return 1; }
  _draft '["python3", "dck"]' 'dck exec -- python3 -V'
  _L materialize --contract "$WORK/draft.json" --authority bats >/dev/null || return 1
  _L start --task T-publish-schemas >/dev/null || return 1
  run _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"dck exec -- python3 -V"'
  [ "$status" -eq 0 ] && [[ "$output" == "RAN: exit 0"* ]] || { echo "$output"; return 1; }
  grep -rqF '[container] python3 -V' "$PLAN/gates/T-publish-schemas/" || return 1
  tail -n 1 "$PLAN/journal.ndjson" | grep -qF '"trust":"observed"' || return 1
  _L complete --task T-publish-schemas >/dev/null
}

@test "a fix outside the touched surface is never answered by a replay (F-25)" {
  _draft '["python3", "test"]' 'test -f docs/fixed.txt'
  _L materialize --contract "$WORK/draft.json" --authority bats >/dev/null || return 1
  _L start --task T-publish-schemas >/dev/null || return 1
  run _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"test -f docs/fixed.txt"'
  [ "$status" -eq 1 ] && [[ "$output" == "RAN: exit 1"* ]] || { echo "$output"; return 1; }
  # the unchanged tree replays honestly
  run _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"test -f docs/fixed.txt"'
  [[ "$output" == "REUSED: exit 1"* ]] || { echo "$output"; return 1; }
  # the fix lands OUTSIDE src/product.py (the planned surface)
  mkdir -p docs && printf 'fixed\n' > docs/fixed.txt
  run _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"test -f docs/fixed.txt"'
  [ "$status" -eq 0 ] && [[ "$output" == "RAN: exit 0"* ]] || { echo "$output"; return 1; }
  # editing it again (still outside the surface) is a new tree, too
  printf 'fixed twice\n' > docs/fixed.txt
  run _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"test -f docs/fixed.txt"'
  [[ "$output" == "RAN: exit 0"* ]] || { echo "$output"; return 1; }
  # a commit moves HEAD: also fresh
  git add -A && git -c user.email=t@t -c user.name=t commit -qm fix
  run _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"test -f docs/fixed.txt"'
  [[ "$output" == "RAN: exit 0"* ]]
}

@test "start summarizes a dirty tree; the event keeps the full comparison string (F-18)" {
  _draft '["python3"]' 'python3 -V'
  _L materialize --contract "$WORK/draft.json" --authority bats >/dev/null || return 1
  for n in 1 2 3; do printf 'tmp\n' > "src/new$n.py"; done
  run _L start --task T-publish-schemas
  [ "$status" -eq 0 ] || return 1
  [[ "$output" == *"dirty: 3 path(s)"* ]] || { echo "$output"; return 1; }
  [[ "$output" != *"new1.py"* ]] || return 1
  grep '"type":"task_start"' "$PLAN/journal.ndjson" | grep -qF 'src/new1.py' || return 1
  rm src/new*.py
  run _L start --task T-ship-validator
  [[ "$output" == *", clean)"* ]]
}

@test "project is byte-identical across renders (F-19)" {
  _draft '["python3"]' 'python3 -V'
  _L materialize --contract "$WORK/draft.json" --authority bats >/dev/null || return 1
  _L start --task T-publish-schemas >/dev/null
  _L gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 -V"' >/dev/null
  _L project >/dev/null && cp "$PLAN/state.json" "$WORK/first.json"
  python3 "$VIEWS" --plan "$PLAN" render --all >/dev/null || return 1
  grep -qF '"type":"view_render"' "$PLAN/journal.ndjson" || return 1
  _L project >/dev/null
  cmp "$WORK/first.json" "$PLAN/state.json"
}
