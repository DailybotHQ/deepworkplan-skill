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
  [[ "$output" == "OK: config self-test ("*" probes)" ]]
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
  [[ "$stderr" == *".dwp/config.json"*"'vim'"*'"enabled" is not a boolean'* ]]
}

@test "fail-closed: invalid JSON warns once and never aborts; the user file still applies" {
  printf '%s\n' '{"addons": {"herdr": {"enabled": true}}}' > "$HOME/.dwp/config.json"
  printf '%s\n' '{"addons": {"vim": {"enabled": tru' > "$REPO/.dwp/config.json"
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ "$status" -eq 0 ]
  [ "$output" = "herdr" ]
  [ "$(printf '%s\n' "$stderr" | grep -c WARNING)" -eq 1 ]
  [[ "$stderr" == *"unreadable"* ]]
}

@test "unknown addon keys are ignored with exactly one warning each" {
  printf '%s\n' '{"addons": {"teleport": {"enabled": true}, "vim": {"enabled": true}}}' > "$REPO/.dwp/config.json"
  run --separate-stderr python3 "$CFG" enabled --repo "$REPO"
  [ "$status" -eq 0 ]
  [ "$output" = "vim" ]
  [ "$(printf '%s\n' "$stderr" | grep -c WARNING)" -eq 1 ]
  [[ "$stderr" == *"'teleport' is not an addon this pack ships; ignored"* ]]
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
  [[ "$stderr" == *'"benchmark.enabled" is not a boolean; benchmark disabled'* ]]
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
