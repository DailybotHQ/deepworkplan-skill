#!/usr/bin/env bash
# Addon-provided abilities (spec/V7_ABILITIES.md): effective abilities are
# the host declaration united with what enabled, valid, detected and
# interface-compatible addons provide — computed per call through the
# shipped resources.py against the REAL in-pack descriptors, with fake
# `ak` and `herdr-peers` binaries on PATH, and never written to the plan.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
RES="$SK/shared/resources.py"
CFG="$SK/shared/config.py"
LEDGER="$SK/shared/ledger.py"
FIXTURE="$REPO_ROOT/tests/fixtures/v6/contract-minimal.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  mkdir -p "$HOME" "$WORK/bin"
  REPO="$WORK/repo"
  PLAN="$REPO/.dwp/plans/PLAN_abilities_bats"
  mkdir -p "$PLAN/analysis_results" "$REPO/src"
  printf '# Goal\n\nAbilities.\n' > "$PLAN/README.md"
  printf 'x = 1\n' > "$REPO/src/product.py"
  python3 - "$FIXTURE" "$PLAN" "${GRANT:-}" <<'PY'
import json, os, sys
doc = json.load(open(sys.argv[1]))
doc['plan'] = 'PLAN_abilities_bats'
for task in doc['tasks']:
    task['touched_surface'] = ['src/product.py']
doc.pop('contract_id', None)
json.dump(doc, open(os.path.join(sys.argv[2], 'draft.json'), 'w'), indent=2)
PY
  python3 "$LEDGER" --plan "$PLAN" materialize --contract "$PLAN/draft.json" \
      --authority bats --mechanism plan_authorship >/dev/null
  # Fakes answering the products' documented detect surfaces.
  printf '#!/bin/sh\necho "{\\"interface\\": ${AK_INTERFACE:-1}, \\"version\\": \\"0.1.0\\"}"\n' > "$WORK/bin/ak"
  printf '#!/bin/sh\necho "herdr-peers 0.1.0 (protocol ${HP_PROTOCOL:-1})"\n' > "$WORK/bin/herdr-peers"
  chmod +x "$WORK/bin/ak" "$WORK/bin/herdr-peers"
  BASE_PATH="$PATH"
}

teardown() { rm -rf "$WORK"; }

_abilities() { python3 "$RES" --plan "$PLAN" abilities "$@"; }
_ability() { printf '%s' "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["abilities"][sys.argv[1]])' "$1"; }
_source() { printf '%s' "$output" | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["sources"][sys.argv[1]]))' "$1"; }

@test "minimal host, no registry: the v6 all-False floor, nothing persisted" {
  run --separate-stderr _abilities
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert not any(d["abilities"].values()), d; assert d["persisted"] is False'
  [ -z "$stderr" ]
}

@test "an enabled, detected agentkit contributes subagents, cancel_children and model_routing" {
  python3 "$CFG" enable agentkit --version v0.1.0 --repo "$REPO" >/dev/null
  PATH="$WORK/bin:$BASE_PATH" run --separate-stderr _abilities
  [ "$status" -eq 0 ]
  [ "$(_ability subagents)" = "True" ]
  [ "$(_ability cancel_children)" = "True" ]
  [ "$(_ability model_routing)" = "True" ]
  [ "$(_source subagents)" = "addon:agentkit" ]
  [ -z "$stderr" ]
}

@test "herdr contributes through its regex interface; host abilities survive the union" {
  python3 "$CFG" enable herdr --repo "$REPO" >/dev/null
  PATH="$WORK/bin:$BASE_PATH" run --separate-stderr _abilities --caps '{"telemetry": true}'
  [ "$status" -eq 0 ]
  [ "$(_ability subagents)" = "True" ]
  [ "$(_ability model_routing)" = "False" ]
  [ "$(_source telemetry)" = "host" ]
  [ "$(_source subagents)" = "addon:herdr" ]
}

@test "enabled but not installed: one warning, no contribution, exit 0" {
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  PATH="/usr/bin:/bin" run --separate-stderr python3 "$RES" --plan "$PLAN" abilities
  [ "$status" -eq 0 ]
  [ "$(_ability subagents)" = "False" ]
  [ "$(printf '%s\n' "$stderr" | grep -c '^WARNING')" -eq 1 ]
  [[ "$stderr" == *"addon agentkit: enabled but contributes nothing"*"not installed"* ]] || return 1
}

@test "an unknown interface major is treated as not available with one warning" {
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  AK_INTERFACE=2 PATH="$WORK/bin:$BASE_PATH" run --separate-stderr _abilities
  [ "$status" -eq 0 ]
  [ "$(_ability subagents)" = "False" ]
  [ "$(printf '%s\n' "$stderr" | grep -c '^WARNING')" -eq 1 ]
  [[ "$stderr" == *"unknown interface major 2 (pinned 1)"* ]] || return 1
}

@test "disabling the addon removes exactly what it contributed" {
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  python3 "$CFG" enable herdr --repo "$REPO" >/dev/null
  PATH="$WORK/bin:$BASE_PATH" run _abilities
  [ "$(_source subagents)" = "addon:agentkit,addon:herdr" ]
  python3 "$CFG" disable agentkit --repo "$REPO" >/dev/null
  PATH="$WORK/bin:$BASE_PATH" run _abilities
  [ "$(_source subagents)" = "addon:herdr" ]
  [ "$(_ability model_routing)" = "False" ]
}

@test "--host-only ignores the registry entirely" {
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  PATH="$WORK/bin:$BASE_PATH" run --separate-stderr python3 "$RES" --plan "$PLAN" abilities --host-only
  [ "$status" -eq 0 ]
  [ "$(_ability subagents)" = "False" ]
}

@test "routing names the source of each ability; abilities never grant authority" {
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  PATH="$WORK/bin:$BASE_PATH" run --separate-stderr python3 "$RES" --plan "$PLAN" routing
  [ "$status" -eq 0 ]
  printf '%s' "$output" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["ability_sources"]["subagents"] == ["addon:agentkit"], d
# the fixture contract does not grant agent_delegation: still sequential
assert d["parallel"]["posture"] == "sequential_only", d
assert d["parallel"]["missing"] == ["contract grant agent_delegation"], d
'
}

@test "never persisted: abilities, routing and report leave every plan byte unchanged" {
  python3 "$CFG" enable agentkit --repo "$REPO" >/dev/null
  before="$(find "$PLAN" -type f ! -name '.ledger.lock*' -exec shasum -a 256 {} + | sort)"
  PATH="$WORK/bin:$BASE_PATH" python3 "$RES" --plan "$PLAN" abilities >/dev/null
  PATH="$WORK/bin:$BASE_PATH" python3 "$RES" --plan "$PLAN" routing >/dev/null
  PATH="$WORK/bin:$BASE_PATH" python3 "$RES" --plan "$PLAN" report >/dev/null
  after="$(find "$PLAN" -type f ! -name '.ledger.lock*' -exec shasum -a 256 {} + | sort)"
  [ "$before" = "$after" ]
  ! grep -rq 'addon:agentkit' "$PLAN"
}

@test "an unknown host ability is still refused (no capability invented)" {
  run python3 "$RES" --plan "$PLAN" abilities --caps '{"teleport": true}'
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown host capability 'teleport'"* ]] || return 1
}

@test "spec: V7_ABILITIES.md states the union, the four conditions and never-persisted; indexed" {
  c() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }
  c "$SK/spec/V7_ABILITIES.md" "An addon that is not enabled MUST NOT be consulted"
  c "$SK/spec/V7_ABILITIES.md" "They MUST NOT be written to a plan"
  c "$SK/spec/V7_ABILITIES.md" "An ability never implies consent."
  grep -qF '[`V7_ABILITIES.md`](V7_ABILITIES.md)' "$SK/spec/README.md"
}

# ------------------------------------------------ F-17 / F-16 (v7.0.0)

_declared() { printf '%s' "$output" | python3 -c 'import json,sys; print(json.load(sys.stdin)["host_declared"].get(sys.argv[1], "-"))' "$1"; }

@test "the host capability record is read; --caps overrides it per capability (F-17)" {
  python3 "$CFG" host subagents true --repo "$REPO" >/dev/null || return 1
  python3 "$CFG" host cancel_children true --repo "$REPO" >/dev/null || return 1
  run --separate-stderr _abilities
  [ "$status" -eq 0 ] && [ -z "$stderr" ] || { echo "$stderr"; return 1; }
  [ "$(_ability subagents)" = "True" ] && [ "$(_ability cancel_children)" = "True" ] || return 1
  [ "$(_source subagents)" = "host" ] || return 1
  [ "$(_declared subagents)" = "record:.dwp/config.json" ] || return 1
  run --separate-stderr _abilities --caps '{"subagents": false}'
  [ "$(_ability subagents)" = "False" ] && [ "$(_declared subagents)" = "declared" ] || return 1
  [ "$(_ability cancel_children)" = "True" ] || return 1
  # the user file applies where the repository file is silent
  mkdir -p "$HOME/.dwp" && printf '{"host": {"model_routing": true, "subagents": false}}\n' > "$HOME/.dwp/config.json"
  run --separate-stderr _abilities
  [ "$(_ability model_routing)" = "True" ] && [ "$(_ability subagents)" = "True" ] || return 1
  [ "$(_declared model_routing)" = "record:~/.dwp/config.json" ]
}

@test "the host record never invents a capability; the writer refuses unknown names (F-17)" {
  printf '{"host": {"time_travel": true, "subagents": "yes", "telemetry": true}}\n' > "$REPO/.dwp/config.json"
  run --separate-stderr _abilities
  [ "$status" -eq 0 ] || return 1
  [[ "$stderr" == *"capability 'time_travel' is not in the closed set; ignored"* ]] || return 1
  [[ "$stderr" == *"capability 'subagents' is not a boolean; ignored"* ]] || return 1
  [ "$(_ability subagents)" = "False" ] && [ "$(_ability telemetry)" = "True" ] || return 1
  printf 'x' > /dev/null
  rm "$REPO/.dwp/config.json"
  run python3 "$CFG" host time_travel true --repo "$REPO"
  [ "$status" -eq 2 ] && [[ "$output" == *"is not a host capability"* ]] || return 1
  [ ! -e "$REPO/.dwp/config.json" ]
}

@test "vim installed without its surface is reported with one warning, never as absent (F-16)" {
  python3 "$CFG" enable vim --repo "$REPO" >/dev/null
  run --separate-stderr _abilities
  [[ "$stderr" != *"vim"* ]] || { echo "$stderr"; return 1; }
  mkdir -p "$HOME/.config/nvim/lua"
  printf -- '-- install\n' > "$HOME/.config/nvim/install.lua"
  printf -- 'return {}\n' > "$HOME/.config/nvim/lua/plugins.lua"
  run --separate-stderr _abilities
  [ "$status" -eq 0 ] || return 1
  [ "$(printf '%s\n' "$stderr" | grep -c 'addon vim: installed without its interface surface')" -eq 1 ] || { echo "$stderr"; return 1; }
  printf '%s' "$output" | python3 -c 'import json,sys; v=json.load(sys.stdin)["addons"]["vim"]; assert v["state"] == "installed-without-surface" and not v["compatible"], v' || return 1
  mkdir -p "$HOME/.config/nvim/addon"
  printf '{"interface": 1, "version": "v0.4.2"}\n' > "$HOME/.config/nvim/addon/surface.json"
  run --separate-stderr _abilities
  [[ "$stderr" != *"vim"* ]] || return 1
  printf '%s' "$output" | python3 -c 'import json,sys; v=json.load(sys.stdin)["addons"]["vim"]; assert v["compatible"] and "state" not in v, v'
}
