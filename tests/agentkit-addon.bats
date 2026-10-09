#!/usr/bin/env bash
# The agentkit addon — a thin integrator of coding-agents-kit (`ak`) as the
# headless delegation transport (spec/ADDONS.md §6.8, spec/V7_CONTRACT.md).
# Policy under test: opt-in from onboard Phase 7b, never required; a single
# pin (coding-agents-kit v0.1.1 — ecosystem amendment A2) across descriptor
# and docs; install by tagged clone + install.sh only; the pack never spells
# a permission-bypass flag or a fetch-and-execute pipeline; the transport
# maps launch/observe/collect/cancel onto one `ak run` per worktree; and a
# detected kit contributes its abilities only through the registry.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
ADDON="$SK/addons/agentkit"
ONBOARD="$SK/onboard/addons.md"
PIN="v0.1.1"
export PYTHONDONTWRITEBYTECODE=1

doc_has() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }

@test "the four components and the descriptor ship" {
  for f in SKILL.md SPEC.md addon.json templates/INTEGRATION.md; do
    [ -s "$ADDON/$f" ] || { echo "missing $f"; return 1; }
  done
  run python3 "$SK/shared/config.py" descriptors
  [ "$status" -eq 0 ]
  printf '%s\n' "$output" | grep -qx 'OK   agentkit'
}

@test "frontmatter: kebab name, invocable, version stamped with the pack, trust boundary present" {
  grep -q '^name: deepworkplan-addon-agentkit$' "$ADDON/SKILL.md"
  grep -q '^user-invocable: true$' "$ADDON/SKILL.md"
  [ "$(grep -m1 '^version:' "$ADDON/SKILL.md")" = "$(grep -m1 '^version:' "$SK/SKILL.md")" ]
  grep -q '^## Trust boundary (write scope)$' "$ADDON/SKILL.md"
  ! grep -q '^homepage:' "$ADDON/SKILL.md"
}

@test "single pin: the descriptor and every spelled ref name coding-agents-kit $PIN (amendment A2)" {
  grep -qF "\"tag\": \"$PIN\"" "$ADDON/addon.json"
  run bash -c "grep -rhoE '(coding-agents-kit@|--branch )v[0-9]+\.[0-9]+\.[0-9]+' '$ADDON' '$ONBOARD' '$SK/spec/ADDONS.md' '$SK/addons/README.md' | sed -E 's/.*(v[0-9.]+)$/\1/' | sort -u"
  [ "$status" -eq 0 ]
  [ "$output" = "$PIN" ]
  grep -qF "| \`agentkit\` | \`DailybotHQ/coding-agents-kit\` \`$PIN\`, interface 1 |" "$SK/spec/ADDONS.md"
}

@test "security: no bypass flag, no fetch-and-execute text, install by tagged clone only" {
  run grep -rnE 'dangerously|--yolo|--force|--approve|--always-approve|skip-permissions' "$ADDON"
  [ "$status" -ne 0 ]
  run grep -rnE '(curl|wget)[^|]*\| *(ba)?sh|irm .*iex|iwr .*iex' "$ADDON"
  [ "$status" -ne 0 ]
  grep -qF "git clone --branch $PIN https://github.com/DailybotHQ/coding-agents-kit" "$ADDON/SKILL.md"
  grep -qF './coding-agents-kit/install.sh' "$ADDON/SKILL.md"
  doc_has "$ADDON/SPEC.md" 'The addon **MUST NOT** add `--auto` (or any CLI permission-bypass flag) by default.'
  doc_has "$ADDON/SPEC.md" '**MUST NOT** carry a secret value'
}

@test "transport: the four operations map onto one ak run per dedicated worktree" {
  for op in launch observe collect cancel; do
    grep -qE "^\| \*\*$op\*\* \|" "$ADDON/SPEC.md" || { echo "no $op row"; return 1; }
  done
  doc_has "$ADDON/SPEC.md" 'record `delegate launch` (prompt digest) **before** starting'
  doc_has "$ADDON/SPEC.md" 'SIGTERM to `ak run` (the kit kills the process tree and exits 5)'
  doc_has "$ADDON/SPEC.md" 'the delegation result is `asserted` until the parent'"'"'s gate runner observes it'
  doc_has "$ADDON/templates/INTEGRATION.md" 'git worktree add'
  doc_has "$ADDON/templates/INTEGRATION.md" '--timeout <seconds> --output-format json'
}

@test "opt-in: onboard offers it explicitly; enabling grants nothing; never required" {
  grep -qF '| **agentkit** | [`../addons/agentkit/`](../addons/agentkit/SKILL.md) |' "$ONBOARD"
  doc_has "$ONBOARD" 'Enabling it authorizes nothing by itself'
  doc_has "$ADDON/SKILL.md" 'never required for a repo to be AI-first and never a conformance gate'
  grep -q '^### 6\.8 agentkit' "$SK/spec/ADDONS.md"
  grep -qF '| agentkit | [`addons/agentkit/SKILL.md`](agentkit/SKILL.md) |' "$SK/addons/README.md"
}

@test "a detected kit contributes abilities only when the registry enables it" {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"; mkdir -p "$HOME" "$WORK/bin" "$WORK/repo/.dwp"
  printf '#!/bin/sh\necho "{\\"interface\\": 1}"\n' > "$WORK/bin/ak"; chmod +x "$WORK/bin/ak"
  run env PATH="$WORK/bin:$PATH" python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
import resources
off = resources.effective_abilities(None, sys.argv[2])
assert not off["abilities"]["subagents"], off
import config
config.write_addon(sys.argv[2], "agentkit", True, "v0.1.1")
on = resources.effective_abilities(None, sys.argv[2])
assert on["sources"]["model_routing"] == ["addon:agentkit"], on
print("ok")' "$SK/shared" "$WORK/repo/.dwp"
  rm -rf "$WORK"
  [ "$status" -eq 0 ]
  [ "$output" = "ok" ]
}
