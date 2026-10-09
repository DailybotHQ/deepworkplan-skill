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

# --- Final Review local-review fixes ---------------------------------------

@test "a read-only delegate cancelled after the tree changed is recorded failed, not cancelled" {
  _plan
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-ship-validator \
    --json "{\"delegation_id\": \"c1\", \"transport\": \"headless\", \"via\": \"agentkit\", \"worktree\": null, \"prompt_digest\": \"$DIGEST\"}" >/dev/null
  printf 'x = 3\n' > "$REPO/src/product.py"
  run python3 "$LEDGER" --plan "$PLAN" delegate cancel --task T-ship-validator --json '{"delegation_id": "c1"}'
  [ "$status" -eq 5 ]
  run python3 "$LEDGER" --plan "$PLAN" delegate observe
  [[ "$output" == *'"state": "failed"'* ]] || return 1
}

@test "completion is refused while a delegation of the task is still open" {
  _plan
  python3 "$LEDGER" --plan "$PLAN" start --task T-publish-schemas >/dev/null
  PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-publish-schemas \
    --json "{\"delegation_id\": \"o1\", \"transport\": \"headless\", \"via\": \"agentkit\", \"prompt_digest\": \"$DIGEST\"}" >/dev/null
  python3 "$LEDGER" --plan "$PLAN" gate --task T-publish-schemas --criterion AC-valid-contract-shape --json '"python3 --version"' >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 4 ]
  [[ "$output" == *"still open"* ]] || return 1
  python3 "$LEDGER" --plan "$PLAN" delegate cancel --task T-publish-schemas --json '{"delegation_id": "o1"}' >/dev/null
  run python3 "$LEDGER" --plan "$PLAN" complete --task T-publish-schemas
  [ "$status" -eq 0 ]
}

@test "outside a git work tree a read-only delegate on an unmarked task is refused (unverifiable)" {
  _plan
  rm -rf "$REPO/.git"
  python3 "$LEDGER" --plan "$PLAN" start --task T-ship-validator >/dev/null
  run env PATH="$WORK/bin:$PATH" python3 "$LEDGER" --plan "$PLAN" delegate launch --task T-ship-validator \
    --json "{\"transport\": \"headless\", \"via\": \"agentkit\", \"worktree\": null, \"prompt_digest\": \"$DIGEST\"}"
  [ "$status" -eq 5 ]
  [[ "$output" == *"needs a git work tree"* ]] || return 1
}

@test "a glob surface never hashes a match that resolves outside the repository" {
  run python3 -c '
import os, sys, tempfile
sys.path.insert(0, sys.argv[1])
import ledger
root = os.path.realpath(tempfile.mkdtemp())
outside = os.path.realpath(tempfile.mkdtemp())
os.makedirs(os.path.join(root, "src"))
open(os.path.join(outside, "secret.txt"), "w").write("A")
os.symlink(outside, os.path.join(root, "src", "linkdir"))   # a directory link inside the repo
pattern = os.path.join(root, "src", "*", "*.txt")
h1 = ledger._hash_surface(pattern, root)
open(os.path.join(outside, "secret.txt"), "w").write("B")
h2 = ledger._hash_surface(pattern, root)
assert h1 == h2, "a glob read a file outside the repository"
print("ok")' "$SHARED"
  [ "$output" = "ok" ]
}

@test "the config writer keeps the file readable (0644 new, existing mode preserved)" {
  python3 "$CFG" enable vim --repo "$REPO" >/dev/null
  [ "$(python3 -c 'import os,sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777))' "$REPO/.dwp/config.json")" = "0o644" ]
  chmod 640 "$REPO/.dwp/config.json"
  python3 "$CFG" disable vim --repo "$REPO" >/dev/null
  [ "$(python3 -c 'import os,sys; print(oct(os.stat(sys.argv[1]).st_mode & 0o777))' "$REPO/.dwp/config.json")" = "0o640" ]
}

@test "descriptor detect paths may not traverse with .." {
  run python3 -c '
import sys; sys.path.insert(0, sys.argv[1])
import config
d = {"schema": config.DESCRIPTOR_SCHEMA_URL, "key": "x", "provides_abilities": [], "requires_grants": [],
     "detect": {"paths": ["docs/../../etc/hosts"]}}
assert config.descriptor_errors(d, "x"), "a traversing detect path was accepted"
print("ok")' "$SHARED"
  [ "$output" = "ok" ]
}

@test "the herdr install lines are non-interactive (-y) for agent shells" {
  for f in "$SK/addons/herdr/install.md" "$SK/addons/herdr/SPEC.md"; do
    run grep -E 'skills add [^`]*-g' "$f"
    [ "$status" -eq 0 ]
    ! printf '%s\n' "$output" | grep -vE -- '-g -y'
  done
}

@test "third-party installers run only in a job without a write token" {
  python3 - "$REPO_ROOT/.github/workflows" <<'PY'
import sys, yaml, os
for name, publisher in (('auto-release.yml', 'release'), ('prerelease.yml', 'prerelease')):
    wf = yaml.safe_load(open(os.path.join(sys.argv[1], name)))
    jobs = wf['jobs']
    smoke = jobs['pin-smoke']
    assert smoke['permissions'] == {'contents': 'read'}, (name, smoke.get('permissions'))
    co = smoke['steps'][0]
    assert co['uses'].startswith('actions/checkout') and co['with']['persist-credentials'] is False, (name, co)
    assert any('smoke-ecosystem-pins.sh' in (s.get('run') or '') for s in smoke['steps']), name
    assert jobs[publisher]['needs'] == 'pin-smoke', (name, jobs[publisher].get('needs'))
    assert not any('smoke-ecosystem-pins.sh' in (s.get('run') or '') for s in jobs[publisher]['steps']), name
print('ok')
PY
}
