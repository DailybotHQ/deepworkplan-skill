#!/usr/bin/env bash
# The configuration file and the addon registry (spec/CONFIG.md): one
# stdlib parser (shared/config.py) for two keys, per-key precedence for
# addons, fail-closed with exactly one warning, unknown keys ignored, a
# reconciling consent-gated writer, and the readers/writers wired into
# onboard and status. The benchmark key keeps its BENCHMARK.md behaviour
# (tests/v6-benchmark.bats pins it; this file pins the shared reader).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
CFG="$SK/shared/config.py"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  mkdir -p "$HOME/.dwp" "$WORK/repo/.dwp/plans/PLAN_x"
  REPO="$WORK/repo"
}

teardown() { rm -rf "$WORK"; }

_show() { python3 "$CFG" show --repo "$REPO"; }
_field() { # _field <key> <field>  from the last show output
  printf '%s' "$output" | python3 -c 'import json,sys; v=json.load(sys.stdin)["addons"][sys.argv[1]][sys.argv[2]]; print(json.dumps(v))' "$1" "$2"
}

@test "self-test passes with its pinned probe count" {
  run python3 "$CFG" self-test
  [ "$status" -eq 0 ]
  [[ "$output" == "OK: config self-test ("*" probes)" ]] || return 1
}

@test "the key set is exactly the in-pack addon directory names" {
  run python3 "$CFG" keys
  [ "$status" -eq 0 ]
  expected="$(find "$SK/addons" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)"
  [ "$output" = "$expected" ]
}

@test "absent everywhere: nothing enabled, no warning" {
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ -z "$stderr" ]
}

@test "precedence is per addon key: repo wins for its keys, defers for the rest" {
  printf '%s\n' '{"addons": {"vim": {"enabled": true, "version": "v0.4.0"}, "herdr": {"enabled": true}}}' > "$HOME/.dwp/config.json"
  printf '%s\n' '{"addons": {"vim": {"enabled": false}}}' > "$REPO/.dwp/config.json"
  run --separate-stderr _show
  [ "$status" -eq 0 ]
  [ "$(_field vim enabled)" = "false" ]
  [ "$(_field vim source)" = '".dwp/config.json"' ]
  [ "$(_field herdr enabled)" = "true" ]
  [ "$(_field herdr source)" = '"~/.dwp/config.json"' ]
}

@test "--plan resolves the repository that owns the plan, not the working directory" {
  printf '%s\n' '{"addons": {"vim": {"enabled": true}}}' > "$REPO/.dwp/config.json"
  cd "$WORK"
  run python3 "$CFG" enabled --plan "$REPO/.dwp/plans/PLAN_x"
  [ "$status" -eq 0 ]
  [ "$output" = "vim" ]
}

@test "fail-closed: a wrong-typed entry is not enabled, one warning naming file, key and reason, no fall-through" {
  printf '%s\n' '{"addons": {"vim": {"enabled": true}}}' > "$HOME/.dwp/config.json"
  printf '%s\n' '{"addons": {"vim": {"enabled": "yes"}}}' > "$REPO/.dwp/config.json"
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ "$(printf '%s\n' "$stderr" | grep -c WARNING)" -eq 1 ]
  [[ "$stderr" == *".dwp/config.json"*"'vim'"*'"enabled" is not a boolean'* ]] || return 1
}

@test "fail-closed: invalid JSON warns once and never aborts; the user file still applies" {
  printf '%s\n' '{"addons": {"herdr": {"enabled": true}}}' > "$HOME/.dwp/config.json"
  printf '%s\n' '{"addons": {"vim": {"enabled": tru' > "$REPO/.dwp/config.json"
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ "$status" -eq 0 ]
  [ "$output" = "herdr" ]
  [ "$(printf '%s\n' "$stderr" | grep -c WARNING)" -eq 1 ]
  [[ "$stderr" == *"unreadable"* ]] || return 1
}

@test "unknown addon keys are ignored with exactly one warning each" {
  printf '%s\n' '{"addons": {"teleport": {"enabled": true}, "vim": {"enabled": true}}}' > "$REPO/.dwp/config.json"
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ "$status" -eq 0 ]
  [ "$output" = "vim" ]
  [ "$(printf '%s\n' "$stderr" | grep -c WARNING)" -eq 1 ]
  [[ "$stderr" == *"'teleport' is not an addon this pack ships; ignored"* ]] || return 1
}

@test "a floating or unprefixed version is refused by reader and writer" {
  printf '%s\n' '{"addons": {"vim": {"enabled": true, "version": "main"}}}' > "$REPO/.dwp/config.json"
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ -z "$output" ]
  run python3 "$CFG" enable vim --version latest --repo "$REPO"
  [ "$status" -eq 2 ]
}

@test "writer: enable reconciles, preserving benchmark and other addon entries" {
  printf '%s\n' '{"benchmark": {"enabled": true}, "addons": {"herdr": {"enabled": false}}, "x-local": 1}' > "$REPO/.dwp/config.json"
  run python3 "$CFG" enable vim --version v0.4.0 --repo "$REPO"
  [ "$status" -eq 0 ]
  python3 - "$REPO/.dwp/config.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d['benchmark'] == {'enabled': True}, d
assert d['x-local'] == 1, d
assert d['addons'] == {'herdr': {'enabled': False},
                       'vim': {'enabled': True, 'version': 'v0.4.0'}}, d
PY
  run python3 "$CFG" disable vim --repo "$REPO"
  [ "$status" -eq 0 ]
  run python3 "$CFG" enabled --repo "$REPO"
  [ -z "$output" ]
}

@test "writer refuses unknown keys and never clobbers an unreadable file" {
  run python3 "$CFG" enable teleport --repo "$REPO"
  [ "$status" -eq 2 ]
  [ ! -e "$REPO/.dwp/config.json" ]
  printf '%s' '{broken' > "$REPO/.dwp/config.json"
  run python3 "$CFG" enable vim --repo "$REPO"
  [ "$status" -eq 2 ]
  [ "$(cat "$REPO/.dwp/config.json")" = '{broken' ]
}

@test "benchmark resolution runs through the shared reader with unchanged warnings" {
  grep -q '^import config as dwp_config' "$SK/shared/benchmark.py"
  ! grep -q 'def _read_config' "$SK/shared/benchmark.py"
  printf '%s\n' '{"benchmark": {"enabled": "yes"}, "addons": {"vim": {"enabled": true}}}' > "$REPO/.dwp/config.json"
  run --separate-stderr _show
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["benchmark"]=={"enabled":False,"learnings":False}, d; assert d["addons"]["vim"]["enabled"] is True, d'
  [[ "$stderr" == *'"benchmark.enabled" is not a boolean; benchmark disabled'* ]] || return 1
}

@test "onboard writes on consent only; status reads read-only" {
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  c "$SK/onboard/addons.md" 'python3 ../shared/config.py enable <key> [--version <pinned-tag>] --repo <repo>'
  c "$SK/onboard/addons.md" 'A **decline writes nothing** (absent = not enabled)'
  c "$SK/onboard/SKILL.md" 'Each acceptance is recorded with `python3 ../shared/config.py enable <key> --repo <repo>`'
  c "$SK/status/SKILL.md" 'python3 ../shared/config.py enabled --plan <dir>'
  c "$SK/status/SKILL.md" 'Never write the file from this flow.'
}

@test "spec: CONFIG.md states the contract and is indexed; the schema is published" {
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  c "$SK/spec/CONFIG.md" 'The registry keys are the **in-pack addon directory names**'
  c "$SK/spec/CONFIG.md" '**Absent = not enabled.**'
  c "$SK/spec/CONFIG.md" '**`version` is informative in 7.0.0.**'
  grep -qF '[`CONFIG.md`](CONFIG.md)' "$SK/spec/README.md"
  grep -qF '"$id": "https://deepworkplan.com/schema/dwp-config/v1.json"' "$SK/spec/schema/dwp-config-v1.schema.json"
}

# ------------------------------------------- F-04 / F-05 / F-15 (v7.0.0)

@test "a one-line note records a decision; malformed notes fail closed (F-05)" {
  run python3 "$CFG" enable agentkit --version v0.3.0 --note "accepted; machine-level install deferred" --repo "$REPO"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  run _show
  [ "$(_field agentkit note)" = '"accepted; machine-level install deferred"' ] || return 1
  run python3 "$CFG" enable vim --note "$(printf 'two\nlines')" --repo "$REPO"
  [ "$status" -eq 2 ] && [[ "$output" == *"one line of 1-200 characters"* ]] || return 1
  printf '{"addons": {"vim": {"enabled": true, "note": ""}}}\n' > "$REPO/.dwp/config.json"
  run python3 "$CFG" enabled --repo "$REPO"
  [[ "$output" == *'"note" is not a one-line string'* ]] && [[ "$output" != *$'\nvim'* ]]
}

@test "an enabled, undetected addon with a note is deferred, not warned (F-05)" {
  python3 "$CFG" enable agentkit --note "install deferred: \$HOME excluded" --repo "$REPO" >/dev/null
  python3 "$CFG" enable herdr --repo "$REPO" >/dev/null
  plan="$REPO/.dwp/plans/PLAN_x"
  run python3 - "$SK/shared" "$REPO/.dwp" <<'PY'
import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import resources
eff = resources.effective_abilities({}, sys.argv[2], timeout=2)
print(json.dumps({'deferred': eff['deferred'], 'warnings': eff['warnings']}))
PY
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  python3 -c '
import json, sys
d = json.loads(sys.argv[1])
assert d["deferred"] == {"agentkit": "install deferred: $HOME excluded"}, d
assert not any("agentkit" in w for w in d["warnings"]), d
assert any("herdr" in w for w in d["warnings"]), d' "$output"
}

@test "backfill records present addons with observed versions, never re-deciding (F-15)" {
  mkdir -p "$REPO/.agents/skills/ai-diff-reviewer" "$REPO/docs" "$WORK/bin"
  printf -- '---\nname: ai-diff-reviewer\nversion: "3.3.0"\n---\n' > "$REPO/.agents/skills/ai-diff-reviewer/SKILL.md"
  printf '# Design\n' > "$REPO/docs/DESIGN.md"
  printf '#!/bin/sh\necho "{\\"interface\\": 1, \\"version\\": \\"0.1.1\\"}"\n' > "$WORK/bin/ak"
  chmod +x "$WORK/bin/ak"
  python3 "$CFG" disable design-system --repo "$REPO" >/dev/null
  before="$(cat "$REPO/.dwp/config.json")"
  run env PATH="$WORK/bin:$PATH" python3 "$CFG" backfill --repo "$REPO"
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  [[ "$output" == *"WOULD addons.ai-diff-reviewer = enabled v3.3.0"* ]] || return 1
  # a machine-level install (a command on PATH) is reported, never back-filled
  [[ "$output" == *"SKIP  addons.agentkit: present on this machine only"* ]] || return 1
  [[ "$output" != *"design-system"* ]] || return 1
  [ "$before" = "$(cat "$REPO/.dwp/config.json")" ] || return 1
  run env PATH="$WORK/bin:$PATH" python3 "$CFG" backfill --repo "$REPO" --write
  [ "$status" -eq 0 ] || { echo "$output"; return 1; }
  run _show
  [ "$(_field ai-diff-reviewer version)" = '"v3.3.0"' ] || return 1
  [[ "$(_field ai-diff-reviewer note)" == *"back-filled on upgrade"* ]] || return 1
  [ "$(_field design-system enabled)" = "false" ] || return 1
  [ "$(_field agentkit source)" = "null" ] || return 1
  run env PATH="$WORK/bin:$PATH" python3 "$CFG" backfill --repo "$REPO"
  [[ "$output" == *"nothing to back-fill"* ]]
}

@test "the registry is trackable while plans stay ignored; both rules are conformant (F-04)" {
  cd "$REPO"
  git init -q .
  printf '.dwp/*\n!.dwp/config.json\n' > .gitignore
  python3 "$CFG" enable vim --repo "$REPO" >/dev/null
  ! git check-ignore -q .dwp/config.json || return 1
  git check-ignore -q .dwp/plans/PLAN_x/README.md || return 1
  run bash "$SK/verify/conformance.sh" --repo-only "$REPO"
  [[ "$output" == *"[x] .dwp/ plans gitignored"* ]] || { echo "$output"; return 1; }
  printf '.dwp/\n' > .gitignore
  run bash "$SK/verify/conformance.sh" --repo-only "$REPO"
  [[ "$output" == *"[x] .dwp/ plans gitignored"* ]] || return 1
  printf 'node_modules/\n' > .gitignore
  run bash "$SK/verify/conformance.sh" --repo-only "$REPO"
  [[ "$output" == *"[ ] .dwp/ plans gitignored"* ]] || return 1
  grep -qF '`.dwp/*` and `!.dwp/config.json`' "$SK/onboard/SKILL.md" || return 1
  grep -qF '!.dwp/config.json' "$SK/shared/dwp-paths.md" "$SK/spec/CONFIG.md"
}
