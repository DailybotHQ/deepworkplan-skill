#!/usr/bin/env bash
# The herdr addon — a thin integrator of herdr-peers as the interactive
# delegation transport (spec/ADDONS.md §6.6, spec/V7_CONTRACT.md). Policy
# under test: opt-in, never required; a single pin (herdr-peers v1.1.0 plus
# Herdr's official skill pinned) in descriptor and docs; no protocol copy in
# the pack (no stamp, grant or listing recipes; no `herdr-mesh` anywhere);
# the transport maps launch/observe/collect/cancel onto the helper with the
# journal written first; a detected helper contributes abilities only
# through the registry; decision debates (SPEC §6.4) are the default
# decision mode behind their trigger, with the method left to herdr-peers.
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

@test "pins: descriptor v1.1.0 interface 1; every install line names an exact tag" {
  python3 - "$ADDON/addon.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d['product'] == {'repo': 'DailybotHQ/herdr-peers', 'tag': 'v1.1.0', 'interface': 1}, d
assert d['transport'] == 'interactive', d
PY
  grep -qF 'npx --yes skills add https://github.com/DailybotHQ/herdr-peers/tree/v1.1.0 --skill herdr-peers -g -y' "$ADDON/install.md"
  grep -qF 'npx --yes skills add https://github.com/herdrdev/herdr/tree/v0.9.3 --skill herdr -g' "$ADDON/install.md"
  # W012: no unpinned `skills add owner/repo ` anywhere in the addon
  run grep -rnE 'skills add [A-Za-z]+/[a-z-]+ ' "$ADDON"
  [ "$status" -ne 0 ]
  run grep -rnE '(curl|wget)[^|]*\| *(ba)?sh' "$ADDON"
  [ "$status" -ne 0 ]
  run bash -c "grep -rhoE 'herdr-peers@v[0-9.]+' '$ADDON' '$ONBOARD' '$SK/spec/ADDONS.md' '$SK/addons/README.md' | sort -u"
  [ "$output" = "herdr-peers@v1.1.0" ]
}

@test "native debates: panel contract, helpers, templates, optional agentkit, protocol 1" {
  for doc in "$ADDON/SKILL.md" "$ADDON/SPEC.md"; do
    doc_has "$doc" 'native debate'
    doc_has "$doc" 'decide, research, stress-test, verify'
    doc_has "$doc" '--wait-blocked'
    doc_has "$doc" 'lead never votes'
    doc_has "$doc" '`herdr-peers debate tally`'
    doc_has "$doc" '`claims`'
    doc_has "$doc" '`anon`'
    doc_has "$doc" '`filings`'
    doc_has "$doc" '`panel`'
    doc_has "$doc" 'sixteen templates'
    doc_has "$doc" 'agentkit `v1.0.1` or later'
    doc_has "$doc" 'protocol/interface `1` is unchanged'
  done
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
  printf '#!/bin/sh\necho "herdr-peers 1.1.0 (protocol 1)"\n' > "$WORK/bin/herdr-peers"
  chmod +x "$WORK/bin/herdr-peers"
  run env PATH="$WORK/bin:$PATH" python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
import config, resources
assert not resources.effective_abilities(None, sys.argv[2])["abilities"]["subagents"]
config.write_addon(sys.argv[2], "herdr", True, "v1.1.0")
on = resources.effective_abilities(None, sys.argv[2])
assert on["sources"]["subagents"] == ["addon:herdr"], on
assert not on["abilities"]["model_routing"], on
print("ok")' "$SK/shared" "$WORK/repo/.dwp"
  rm -rf "$WORK"
  [ "$output" = "ok" ]
}

# --- decision debates: the default decision mode (SPEC §6.4) ------------------

@test "decision debates: SPEC §6.4 states the definition, trigger, shape, lead, deliverable, authority and fallback" {
  local spec="$ADDON/SPEC.md"
  doc_has "$spec" '## 6.4. Decision Debates (the default decision mode)'
  doc_has "$spec" 'at least two viable options lead to materially different outcomes'
  doc_has "$spec" '*At plan time* a plan **MAY** list a debate only when'
  doc_has "$spec" 'resolves `decisions.debate` to `auto`'
  doc_has "$spec" 'a plan created without the plan-time trigger **MUST NOT** list debates'
  doc_has "$spec" '*At run time* a listed debate **MUST NOT** start unless'
  doc_has "$spec" 'reports `1.1.0` or later on protocol `1`'
  doc_has "$spec" 'A debate **MUST NOT** be opened on a question the approved plan does not list'
  doc_has "$SK/execute/debate.md" 'A debate for it needs a refine amendment that lists it and the developer'"'"'s approval.'
  doc_has "$spec" 'Quick (3–4 seats, one round'
  doc_has "$spec" 'never Deep by default'
  doc_has "$spec" 'The executing agent is the lead and **MUST NOT** vote.'
  doc_has "$spec" '**read-only** delegation (`worktree` null) recorded with `ledger.py delegate launch` before its brief is sent'
  doc_has "$spec" '`analysis_results/debates/<topic>/DECISION.md`'
  doc_has "$spec" 'it grants no authority'
  doc_has "$spec" '(`debate: not run — <reason>`)'
  doc_has "$spec" 'escalated as C3'
  doc_has "$SK/spec/ADDONS.md" '[`SPEC.md`](../addons/herdr/SPEC.md) §6.4'
  doc_has "$SK/spec/AGENT_PROTOCOL.md" '(`addons/herdr/SPEC.md` §6.4)'
  doc_has "$SK/spec/CONFIG.md" '## 3b. The decision-debate policy (`decisions`)'
}

@test "decision debates: the flow files load only behind their triggers" {
  [ -s "$SK/create/decisions.md" ] && [ -s "$SK/execute/debate.md" ]
  doc_has "$SK/create/SKILL.md" '[`decisions.md`](decisions.md) — read only when the decision-debates trigger in `v6.md` fires.'
  doc_has "$SK/create/v6.md" '**v7: decision debates.** When `config.py enabled` lists `herdr`, `config.py show` resolves `decisions.debate` to `auto`'
  doc_has "$SK/create/v6.md" 'Otherwise read nothing more'
  doc_has "$SK/execute/SKILL.md" '[`debate.md`](debate.md) — read only when a listed decision task runs.'
  doc_has "$SK/execute/v6.md" 'A **decision task** the plan lists under "Decision debates" is run as a debate — read [`debate.md`](debate.md)'
  # nothing else in the flows points at them
  run bash -c "grep -rlF 'decisions.md' '$SK/create' '$SK/execute' | sort"
  [ "$output" = "$(printf '%s\n' "$SK/create/SKILL.md" "$SK/create/v6.md" | sort)" ]
  run bash -c "grep -rlF '](debate.md)' '$SK/create' '$SK/execute' | sort"
  [ "$output" = "$(printf '%s\n' "$SK/execute/SKILL.md" "$SK/execute/delegation.md" "$SK/execute/v6.md" | sort)" ]
}

@test "decision debates: create plans, never runs; execute journals first, never votes, never blocks" {
  local cr="$SK/create/decisions.md" ex="$SK/execute/debate.md"
  doc_has "$cr" 'Never invent a decision to justify a debate'
  doc_has "$cr" 'ordered **before** every task that consumes its result'
  doc_has "$cr" 'The developer'"'"'s approval of the plan is the human consent herdr-peers requires'
  doc_has "$cr" '`create` never runs a debate'
  doc_has "$ex" '**Journal before every ask.**'
  doc_has "$ex" '"worktree": null'
  doc_has "$ex" '**Never vote**'
  doc_has "$ex" '`1.0.x` has no debates'
  doc_has "$ex" '`--fanout N --reason'
  doc_has "$ex" '## 5. Fallback — never block'
  doc_has "$ex" '`debate: not run — <reason>`'
  doc_has "$ex" 'is C3'
  doc_has "$ex" 'Never open a debate the plan did not price.'
}

@test "decision debates: the method stays herdr-peers' own — no format, ballot or counting copy" {
  for f in "$SK/create/decisions.md" "$SK/execute/debate.md" "$ADDON/SPEC.md" "$ADDON/SKILL.md"; do
    run grep -nE 'Borda|Condorcet|ACCEPT / AMEND / REJECT|devil.s-advocate|steelman|cross-exam(ination)?:' "$f"
    [ "$status" -ne 0 ] || { echo "$f restates the debate method: $output"; return 1; }
  done
}

@test "decision debates: the offer names the default, its cost and the off switch" {
  for doc in "$ADDON/SKILL.md" "$ONBOARD"; do
    doc_has "$doc" 'config.py decisions debate off'
  done
  doc_has "$ADDON/SKILL.md" 'for each debate the turns of the agents seated on it'
  doc_has "$ONBOARD" 'each costing the seated agents'"'"' turns'
  doc_has "$SK/addons/README.md" 'Its default decision mode'
}

@test "decision debates: the documented gate rejects an unfilled DECISION.md template" {
  local d="$BATS_TEST_TMPDIR/.dwp/plans/P/analysis_results/debates/cache-store" check
  mkdir -p "$d"
  check="$(python3 -c 'import json,sys; md=open(sys.argv[1]).read(); t=json.loads(md.split("```json")[1].split("```")[0].replace("<plan>","P")); print(t["gate_intent"][0]["check"])' "$ADDON/templates/INTEGRATION.md")"
  printf '## Decisions\n\n| Id | Decision |\n| --- | --- |\n| D-<id>-01 | <...> |\n' > "$d/DECISION.md"
  run bash -c "cd '$BATS_TEST_TMPDIR' && $check"
  [ "$status" -ne 0 ]
  printf '## Decisions\n\n| D-cache-01 | Redis |\n' > "$d/DECISION.md"
  run bash -c "cd '$BATS_TEST_TMPDIR' && $check"
  [ "$status" -eq 0 ]
  printf 'debate: not run — HERDR_ENV unset\n' > "$d/DECISION.md"
  run bash -c "cd '$BATS_TEST_TMPDIR' && $check"
  [ "$status" -eq 0 ]
  # create/decisions.md documents the same pattern
  doc_has "$SK/create/decisions.md" 'grep -Eq "^(\| D-[A-Za-z0-9-]+-[0-9]+ \||debate: not run)"'
}
