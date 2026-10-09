#!/usr/bin/env bash
# Regression tests for the v7 security pass (Task 14 of the v7 beta plan):
# each finding of the independent review is pinned against the shipped
# helpers — the read-only delegate bypass, result_path containment, the
# config writer refusing links, detect binaries resolved to absolute paths,
# machine-level-only file-json interfaces, touched-surface hashing never
# following links or leaving the repository, and the published TRUST.md
# self-audit actually passing on the shipped tree.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SHARED="$SK/shared"
LEDGER="$SHARED/ledger.py"
CFG="$SHARED/config.py"
FIX="$REPO_ROOT/tests/fixtures/v7/contract-minimal-v7.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  mkdir -p "$HOME" "$WORK/bin"
  REPO="$WORK/repo"
  PLAN="$REPO/.dwp/plans/PLAN_v7_fixture_minimal"
  mkdir -p "$PLAN/analysis_results" "$REPO/src"
  git -C "$REPO" init -q
  printf '.dwp/\n' > "$REPO/.gitignore"
  printf 'x = 1\n' > "$REPO/src/product.py"
  git -C "$REPO" add -A && git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init
  printf '# Goal\n\nSecurity.\n' > "$PLAN/README.md"
  printf '#!/bin/sh\necho "{\\"interface\\": 1}"\n' > "$WORK/bin/ak"; chmod +x "$WORK/bin/ak"
  DIGEST="sha256:$(printf 'p' | shasum -a 256 | cut -c1-64)"
}
teardown() { rm -rf "$WORK"; }

_plan() {
  python3 - "$FIX" "$PLAN/draft.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1])); doc.pop('contract_id', None)
doc['scope']['allowed_command_classes'] = ['python3']
for t in doc['tasks']:
    t['touched_surface'] = ['src/']
json.dump(doc, open(sys.argv[2], 'w'))
PY
  python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" --authority bats >/dev/null
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
}

@test "a read-only delegate that changed the tree is recorded failed and refused" {
  _plan
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-ship-validator \
    --json "{\"delegation_id\": \"r1\", \"transport\": \"headless\", \"via\": \"agentkit\", \"worktree\": null, \"prompt_digest\": \"$DIGEST\"}" >/dev/null
  printf 'x = 2\n' > "$REPO/src/product.py"       # the "read-only" delegate wrote
  run python3 "$LEDGER" --plan "$PLAN" delegate collect --task T-ship-validator --json '{"delegation_id": "r1", "state": "completed"}'
  [ "$status" -eq 5 ]
  [[ "$output" == *"launched read-only but the working tree changed"* ]] || return 1
  run python3 "$LEDGER" --plan "$PLAN" delegate observe
  [[ "$output" == *'"state": "failed"'* ]] || return 1
}

@test "a read-only delegate that left the tree alone collects normally" {
  _plan
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-ship-validator \
    --json "{\"delegation_id\": \"r2\", \"transport\": \"headless\", \"via\": \"agentkit\", \"worktree\": null, \"prompt_digest\": \"$DIGEST\"}" >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" delegate collect --task T-ship-validator --json '{"delegation_id": "r2", "state": "completed"}'
  [ "$status" -eq 0 ]
}

@test "result_path is validated before any read and must stay inside plan or repository" {
  _plan
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-publish-schemas \
    --json "{\"delegation_id\": \"p1\", \"transport\": \"headless\", \"via\": \"agentkit\", \"prompt_digest\": \"$DIGEST\"}" >/dev/null
  for bad in /etc/hosts ../../../etc/hosts; do
    run python3 "$LEDGER" --plan "$PLAN" delegate collect --task T-publish-schemas \
      --json "{\"delegation_id\": \"p1\", \"state\": \"completed\", \"result_path\": \"$bad\"}"
    [ "$status" -ne 0 ]
  done
  # a link inside analysis_results to a file outside is recorded without a digest
  printf 'outside\n' > "$WORK/outside.txt"
  ln -s "$WORK/outside.txt" "$PLAN/analysis_results/link.txt"
  run python3 "$LEDGER" --plan "$PLAN" delegate collect --task T-publish-schemas \
    --json '{"delegation_id": "p1", "state": "completed", "result_path": "analysis_results/link.txt"}'
  [ "$status" -eq 0 ]
  ! grep -q 'result_digest' "$PLAN/journal.ndjson"
}

@test "the config writer refuses to write through a symbolic link" {
  mkdir -p "$WORK/elsewhere"
  printf '{}\n' > "$WORK/elsewhere/config.json"
  mkdir -p "$REPO/.dwp"
  ln -s "$WORK/elsewhere/config.json" "$REPO/.dwp/config.json"
  run python3 "$CFG" enable vim --repo "$REPO"
  [ "$status" -eq 2 ]
  [[ "$output" == *"symbolic link"* ]] || return 1
  [ "$(cat "$WORK/elsewhere/config.json")" = '{}' ]
}

@test "a detect binary found through a relative PATH entry is refused" {
  mkdir -p "$WORK/cwd"
  printf '#!/bin/sh\necho "{\\"interface\\": 1}"\n' > "$WORK/cwd/ak"; chmod +x "$WORK/cwd/ak"
  cd "$WORK/cwd"
  run env PATH=".:/usr/bin:/bin" python3 -c '
import sys; sys.path.insert(0, sys.argv[1])
import resources
ok, out, reason = resources._run_detect("ak doctor --json")
print(ok, reason)' "$SHARED"
  [[ "$output" == "False "*"relative PATH entry"* ]] || return 1
}

@test "file-json interfaces are machine-level only (never a repository file)" {
  run python3 -c '
import sys; sys.path.insert(0, sys.argv[1])
import config
base = {"schema": config.DESCRIPTOR_SCHEMA_URL, "key": "vim", "provides_abilities": [], "requires_grants": [],
        "detect": {"paths": ["~/.config/nvim/addon/surface.json"]}}
base["detect"]["interface_from"] = "file-json:addon/surface.json#interface"
assert config.descriptor_errors(base, "vim"), "repo-relative file-json accepted"
base["detect"]["interface_from"] = "file-json:~/.config/nvim/addon/surface.json#interface"
assert not config.descriptor_errors(base, "vim"), config.descriptor_errors(base, "vim")
print("ok")' "$SHARED"
  [ "$output" = "ok" ]
}

@test "touched-surface hashing names links without following them and never leaves the repository" {
  run python3 -c '
import os, sys, tempfile
sys.path.insert(0, sys.argv[1])
import ledger
root = tempfile.mkdtemp()
os.makedirs(os.path.join(root, "src"))
outside = os.path.join(tempfile.mkdtemp(), "big.txt")
open(outside, "w").write("A")
os.symlink(outside, os.path.join(root, "src", "link"))
h1 = ledger._hash_surface(os.path.join(root, "src"))
open(outside, "w").write("B")   # the target changes; the link does not
h2 = ledger._hash_surface(os.path.join(root, "src"))
assert h1 == h2, "followed a link"
print("ok")' "$SHARED"
  [ "$output" = "ok" ]
}

@test "the published TRUST.md self-audit passes on the shipped tree" {
  awk '/^```bash$/{f=1;next} /^```$/{f=0} f' "$SK/TRUST.md" > "$WORK/selfaudit.sh"
  [ -s "$WORK/selfaudit.sh" ]
  run bash -c 'cd "$1" && bash "$2"' _ "$REPO_ROOT" "$WORK/selfaudit.sh"
  [ "$status" -eq 0 ]
  for ok in 'OK: no network calls in the core skill' 'OK: both read local files, git and env only' \
            'OK: no installer pipes, no bypass flags' 'OK: every install path is tag-pinned or package-managed'; do
    [[ "$output" == *"$ok"* ]] || { echo "self-audit did not print: $ok"; echo "$output"; return 1; }
  done
}
