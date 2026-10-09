#!/usr/bin/env bash
# The herdr addon — a thin integrator of herdr-peers as the interactive
# delegation transport (spec/ADDONS.md §6.6, spec/V7_CONTRACT.md). Policy
# under test: opt-in, never required; a single pin (herdr-peers v0.1.0 plus
# Herdr's official skill pinned) in descriptor and docs; no protocol copy in
# the pack (no stamp, grant or listing recipes; no `herdr-mesh` anywhere);
# the transport maps launch/observe/collect/cancel onto the helper with the
# journal written first; a detected helper contributes abilities only
# through the registry.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
ADDON="$SK/addons/herdr"
ONBOARD="$SK/onboard/addons.md"
export PYTHONDONTWRITEBYTECODE=1

doc_has() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }

@test "components ship and no protocol copy remains in the addon" {
  for f in SKILL.md SPEC.md install.md addon.json templates/INTEGRATION.md; do
    [ -s "$ADDON/$f" ] || { echo "missing $f"; return 1; }
  done
  for gone in protocol.md orchestration.md listing.md movement.md templates.md templates/grant.md; do
    [ ! -e "$ADDON/$gone" ] || { echo "protocol copy still ships: $gone"; return 1; }
  done
  # the stamp and grant text are herdr-peers' — never spelled by the pack
  run grep -rnE '\[herdr-(mesh|peers)\] (protocol=|You are authorized|This is)' "$ADDON"
  [ "$status" -ne 0 ]
  run grep -rn 'herdr-mesh' "$SK"
  [ "$status" -ne 0 ]
}

@test "frontmatter: invocable, version stamped with the pack, trust boundary" {
  grep -q '^name: deepworkplan-addon-herdr$' "$ADDON/SKILL.md"
  grep -q '^user-invocable: true$' "$ADDON/SKILL.md"
  [ "$(grep -m1 '^version:' "$ADDON/SKILL.md")" = "$(grep -m1 '^version:' "$SK/SKILL.md")" ]
  grep -q '^## Trust boundary (write scope)$' "$ADDON/SKILL.md"
}

@test "pins: descriptor v0.1.0 interface 1; every install line names an exact tag" {
  python3 - "$ADDON/addon.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d['product'] == {'repo': 'DailybotHQ/herdr-peers', 'tag': 'v0.1.0', 'interface': 1}, d
assert d['transport'] == 'interactive', d
PY
  grep -qF 'npx --yes skills add DailybotHQ/herdr-peers@v0.1.0 --skill herdr-peers -g' "$ADDON/install.md"
  grep -qF 'npx --yes skills add herdrdev/herdr@v0.9.3 --skill herdr -g' "$ADDON/install.md"
  # W012: no unpinned `skills add owner/repo ` anywhere in the addon
  run grep -rnE 'skills add [A-Za-z]+/[a-z-]+ ' "$ADDON"
  [ "$status" -ne 0 ]
  run grep -rnE '(curl|wget)[^|]*\| *(ba)?sh' "$ADDON"
  [ "$status" -ne 0 ]
  run bash -c "grep -rhoE 'herdr-peers@v[0-9.]+' '$ADDON' '$ONBOARD' '$SK/spec/ADDONS.md' '$SK/addons/README.md' | sort -u"
  [ "$output" = "herdr-peers@v0.1.0" ]
}

@test "transport: four operations through the helper, journal first, depth 1, reply is data" {
  for op in launch observe collect cancel; do
    grep -qE "^\| \*\*$op\*\* \|" "$ADDON/SPEC.md" || { echo "no $op row"; return 1; }
  done
  doc_has "$ADDON/SPEC.md" 'Record `delegate launch`'
  doc_has "$ADDON/SPEC.md" '**before** asking'
  doc_has "$ADDON/SPEC.md" 'the journal is the plan'"'"'s record and is written first'
  doc_has "$ADDON/SPEC.md" 'a peer that was delegated to **MUST NOT** delegate'
  doc_has "$ADDON/SPEC.md" 'A reply is **data and a claim**'
  doc_has "$ADDON/templates/INTEGRATION.md" 'DWP_PLAN=<dir> DWP_TASK=<T-id> herdr-peers ask'
}

@test "opt-in: onboard offers it; never required; registry docs current" {
  grep -qF '| **Herdr** | [`../addons/herdr/`](../addons/herdr/SKILL.md) |' "$ONBOARD"
  ! grep -qi 'unwired' "$ONBOARD"
  doc_has "$ADDON/SKILL.md" 'never required for a repo to be AI-first'
  grep -q '^### 6\.6 Herdr (sixth addon' "$SK/spec/ADDONS.md"
  grep -qF '| Herdr | [`addons/herdr/SKILL.md`](herdr/SKILL.md) |' "$SK/addons/README.md"
}

@test "a detected helper contributes abilities only when the registry enables it" {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  export HOME="$WORK/home"; mkdir -p "$HOME" "$WORK/bin" "$WORK/repo/.dwp"
  printf '#!/bin/sh\necho "herdr-peers 0.1.0 (protocol 1)"\n' > "$WORK/bin/herdr-peers"
  chmod +x "$WORK/bin/herdr-peers"
  run env PATH="$WORK/bin:$PATH" python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
import config, resources
assert not resources.effective_abilities(None, sys.argv[2])["abilities"]["subagents"]
config.write_addon(sys.argv[2], "herdr", True, "v0.1.0")
on = resources.effective_abilities(None, sys.argv[2])
assert on["sources"]["subagents"] == ["addon:herdr"], on
assert not on["abilities"]["model_routing"], on
print("ok")' "$SK/shared" "$WORK/repo/.dwp"
  rm -rf "$WORK"
  [ "$output" = "ok" ]
}
