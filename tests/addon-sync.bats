#!/usr/bin/env bash
# The all-addons planner (shared/addon_sync.py, onboard/all-addons.md): for
# each addon it reads detection, the vendored skill, the registry and the
# dev-container layout, and names one action. Scenarios on fixture repos —
# a fresh repository, one from an old v7.0.x install, one with a hand-written
# docker setup — and idempotency: the planner writes nothing, and a finished
# repository plans nothing on a second run. Pins come from the descriptors,
# so moving a pin never edits this file.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SYNC="$SK/shared/addon_sync.py"
CFG="$SK/shared/config.py"
PY="$(command -v python3)"
export PYTHONDONTWRITEBYTECODE=1

setup() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"
  STUBS="$WORK/bin"
  mkdir -p "$HOME" "$STUBS" "$WORK/repo"
  REPO="$WORK/repo"
  # Hermetic PATH: only the stubs a scenario writes, plus the base system.
  export PATH="$STUBS:/usr/bin:/bin"
}

teardown() { rm -rf "$WORK"; }

pin() { "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["product"]["tag"])' "$SK/addons/$1/addon.json"; }
bare() { pin "$1" | sed 's/^v//'; }

stub() {  # stub <name> <stdout>
  printf '#!/bin/sh\ncat <<'"'"'EOF'"'"'\n%s\nEOF\n' "$2" > "$STUBS/$1"
  chmod +x "$STUBS/$1"
}

skill() {  # skill <name> <version>
  mkdir -p "$REPO/.agents/skills/$1"
  printf -- '---\nname: %s\nversion: "%s"\n---\n' "$1" "$2" > "$REPO/.agents/skills/$1/SKILL.md"
}

plan_json() { "$PY" "$SYNC" plan --repo "$REPO" --json; }
action() {  # action <key>  (from plan_json)
  plan_json | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print([r["action"] for r in d["rows"] if r["key"]==sys.argv[1]][0])' "$1"
}
field() {  # field <key> <field>
  plan_json | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print([r.get(sys.argv[2]) for r in d["rows"] if r["key"]==sys.argv[1]][0])' "$1" "$2"
}
tree_digest() { (cd "$REPO" && find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256); }

@test "self-test passes" {
  run "$PY" "$SYNC" self-test
  [ "$status" -eq 0 ]
  [ "$output" = "OK: addon_sync self-test" ]
}

@test "fresh repository: every addon is install, evaluate or not-applicable" {
  printf '{}\n' > "$REPO/package.json"
  [ "$(action ai-diff-reviewer)" = install ]
  [ "$(action dependency-upgrade)" = install ]
  [ "$(action design-system)" = evaluate ]
  [ "$(action dailybot)" = install ]
  [ "$(field dailybot cli)" = absent ]
  [ "$(action agentkit)" = install ]
  [ "$(action herdr)" = install ]
  [ "$(action vim)" = install ]
  [ "$(action devcontainer)" = install ]
  [ "$(field devcontainer layout)" = none ]
}

@test "fresh repository without a manifest: dependency-upgrade is not applicable" {
  [ "$(action dependency-upgrade)" = not-applicable ]
}

@test "the planner writes nothing and prints the same plan twice" {
  printf '{}\n' > "$REPO/package.json"
  before="$(tree_digest)"
  run "$PY" "$SYNC" plan --repo "$REPO"
  [ "$status" -eq 0 ]
  first="$output"
  run "$PY" "$SYNC" plan --repo "$REPO"
  [ "$output" = "$first" ]
  [ "$(tree_digest)" = "$before" ]
  [ ! -e "$REPO/.dwp" ]
}

old_v70_repo() {
  printf '{}\n' > "$REPO/package.json"
  skill deepworkplan 7.0.3
  skill ai-diff-reviewer 3.1.0
  skill dailybot 3.20.0
  mkdir -p "$REPO/.agents/commands" "$REPO/.dwp" "$REPO/.devcontainer" "$REPO/docker/local/app/dck"
  printf '# /lib-upgrade\n' > "$REPO/.agents/commands/lib-upgrade.md"
  printf 'interface = 2\nservice = "app"\nflavour = "node-24"\n' > "$REPO/.devcontainer/dck.toml"
  printf 'devcontainer-kit v0.2.5\n' > "$REPO/docker/local/app/dck/VERSION"
  cat > "$REPO/.dwp/config.json" <<'EOF'
{"addons": {"ai-diff-reviewer": {"enabled": true, "version": "v3.1.0"},
            "dailybot": {"enabled": true, "version": "v3.20.0"},
            "devcontainer": {"enabled": true, "version": "v0.2.5"},
            "agentkit": {"enabled": true, "version": "v0.3.0"}}}
EOF
  stub ak '{"interface": 1, "version": "0.3.0", "permissions": "auto"}'
  stub dck '{"interface": 2, "version": "0.2.5"}'
  stub herdr-peers "herdr-peers $(bare herdr) (protocol 1)"
  stub dailybot 'dailybot 3.9.1'
}

@test "old v7.0.x install: older addons are upgrade, never install over them" {
  old_v70_repo
  [ "$(action ai-diff-reviewer)" = upgrade ]
  [ "$(field ai-diff-reviewer version)" = v3.1.0 ]
  [ "$(action dailybot)" = upgrade ]
  [ "$(field dailybot cli)" = present ]
  [ "$(action agentkit)" = upgrade ]
  [ "$(action devcontainer)" = upgrade ]
  [ "$(field devcontainer layout)" = dck ]
  [ "$(field devcontainer stamp)" = v0.2.5 ]
  [ "$(action dependency-upgrade)" = record ]   # present, not in the registry
  [ "$(action herdr)" = record ]                # at the pin, not in the registry
  run plan_json
  printf '%s' "$output" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); assert d["pack_action"]=="upgrade", d'
}

@test "old v7.0.x install: after the upgrade every row is current, and a second pass changes nothing" {
  old_v70_repo
  # The addon flows ran: each product now at the pack's pin.
  skill ai-diff-reviewer "$(bare ai-diff-reviewer)"
  skill dailybot "$(bare dailybot)"
  stub ak "{\"interface\": 1, \"version\": \"$(bare agentkit)\", \"permissions\": \"auto\"}"
  stub dck "{\"interface\": 2, \"version\": \"$(bare devcontainer)\"}"
  printf 'devcontainer-kit %s\n' "$(pin devcontainer)" > "$REPO/docker/local/app/dck/VERSION"
  mkdir -p "$HOME/.config/nvim/addon"
  printf '{"interface": 1, "version": "%s"}\n' "$(bare vim)" > "$HOME/.config/nvim/addon/surface.json"
  skill deepworkplan "$(grep -m1 '^version:' "$SK/SKILL.md" | tr -d '"' | awk '{print $2}')"
  # Each row's record command, as the planner prints it.
  run plan_json
  printf '%s' "$output" | "$PY" -c 'import json,sys
for r in json.load(sys.stdin)["rows"]:
    if r.get("record"): print(r["record"])' > "$WORK/records"
  [ -s "$WORK/records" ]
  while IFS= read -r line; do
    eval "${line/<pack>/$SK}"
  done < "$WORK/records"
  run "$PY" "$SYNC" plan --repo "$REPO"
  [[ "$output" == *"pending: nothing"* ]] || { echo "$output"; return 1; }
  run plan_json
  printf '%s' "$output" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); assert d["pack_action"]=="current", d'
  run "$PY" "$SYNC" plan --repo "$REPO"
  # Second pass: the same records change no byte, the plan is identical.
  cfg_before="$(shasum -a 256 < "$REPO/.dwp/config.json")"
  first="$output"
  while IFS= read -r line; do
    eval "${line/<pack>/$SK}"
  done < "$WORK/records"
  [ "$(shasum -a 256 < "$REPO/.dwp/config.json")" = "$cfg_before" ]
  run "$PY" "$SYNC" plan --repo "$REPO"
  [ "$output" = "$first" ]
}

@test "hand-written docker setup: devcontainer is reconcile and nothing is touched" {
  printf '{}\n' > "$REPO/package.json"
  mkdir -p "$REPO/.devcontainer"
  printf 'FROM node:24\n' > "$REPO/Dockerfile"
  printf 'services:\n  web:\n    build: .\n' > "$REPO/docker-compose.yml"
  printf '{"name": "mine", "dockerComposeFile": "../docker-compose.yml"}\n' > "$REPO/.devcontainer/devcontainer.json"
  before="$(tree_digest)"
  [ "$(action devcontainer)" = reconcile ]
  [ "$(field devcontainer layout)" = handwritten ]
  [[ "$(field devcontainer reason)" == *"--dry-run"* ]]
  [ "$(tree_digest)" = "$before" ]
}

@test "a recorded decline is respected; a newer install is never downgraded" {
  mkdir -p "$REPO/.dwp"
  printf '{"addons": {"dailybot": {"enabled": false}}}\n' > "$REPO/.dwp/config.json"
  skill ai-diff-reviewer 99.0.0
  [ "$(action dailybot)" = declined ]
  [ "$(action ai-diff-reviewer)" = record ]
  [[ "$(field ai-diff-reviewer record)" == *"--version v99.0.0"* ]]
}

@test "an unreadable registry is a warning, never a crash or a write" {
  mkdir -p "$REPO/.dwp"
  printf 'not json' > "$REPO/.dwp/config.json"
  run "$PY" "$SYNC" plan --repo "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"warning:"* ]]
  [ "$(cat "$REPO/.dwp/config.json")" = "not json" ]
}

@test "onboard wires the planner: all-addons.md is linked and names every action" {
  grep -qF '[`all-addons.md`](all-addons.md)' "$SK/onboard/SKILL.md"
  grep -qF '[`all-addons.md`](all-addons.md)' "$SK/onboard/addons.md"
  for a in install upgrade record current newer reconcile verify declined evaluate not-applicable; do
    grep -qF "| \`$a\` |" "$SK/onboard/all-addons.md" || { echo "no row for $a"; return 1; }
  done
  grep -qF 'python3 ../shared/addon_sync.py plan --repo <repo>' "$SK/onboard/all-addons.md"
  grep -qF 'never downgrade' "$SK/onboard/all-addons.md"
  grep -qF 'bash dev.sh up' "$SK/onboard/all-addons.md"
  grep -qF '[`../addons/machine-installs.md`](../addons/machine-installs.md)' "$SK/onboard/all-addons.md"
  grep -qF 'shasum -a 256 -c --ignore-missing' "$SK/addons/machine-installs.md"
  grep -qF 'describe --tags --exact-match' "$SK/addons/machine-installs.md"
}
