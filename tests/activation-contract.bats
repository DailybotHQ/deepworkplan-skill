#!/usr/bin/env bats

# Flow-activation and portability regressions: a repository onboarded by this
# pack must expose a usable explicit plan/execute/resume path from its local
# index, direct edits must not silently become plans, and hosts lacking slash
# commands, subprocess agents, parallel teams or persistent sessions must have
# stated fallbacks. Tests 1-3 are behavioral oracles over real artifacts (the
# delegator templates and this repo's own generated command kit must route to
# sub-skills that actually ship). Tests 4-8 are labeled contract-presence
# checks: they prove the flows and docs teach the contract, NOT that any model
# routes a live request correctly - routing reliability is deferred to
# recorded live-agent acceptance evidence (docs/COMPATIBILITY.md, "Flow
# activation"), never claimed from these strings.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    ROUTER="$SK/SKILL.md"
    ONBOARD="$SK/onboard/SKILL.md"
    TPL="$SK/onboard/command-templates"
    TROUBLE="$SK/shared/troubleshooting.md"
    WORK="$(mktemp -d)"
}

teardown() { rm -rf "$WORK"; }

@test "every delegator template routes to a sub-skill that ships in the pack" {
    n=0
    for f in "$TPL"/dwp-create.md "$TPL"/dwp-execute.md "$TPL"/dwp-refine.md \
             "$TPL"/dwp-resume.md "$TPL"/dwp-status.md "$TPL"/dwp-verify.md \
             "$TPL"/dwp-upgrade.md "$TPL"/skill-create.md "$TPL"/agent-create.md; do
        [ -f "$f" ]
        sub="$(sed -n 's/.*<skill-path>\/deepworkplan\/\([a-z-]*\)\/SKILL\.md.*/\1/p' "$f" | head -1)"
        [ -n "$sub" ]
        [ -f "$SK/$sub/SKILL.md" ]
        # Host-portable invocation: the same flow is reachable without the
        # slash command, by sub-skill name.
        grep -qF "#deepworkplan-$sub" "$f"
        # Thinness: no copied flow body inside a delegator.
        lines="$(wc -l < "$f")"
        [ "$lines" -le 40 ]
        run grep -qE '^#+ (Step|Phase) [0-9]' "$f"
        [ "$status" -ne 0 ]
        n=$((n + 1))
    done
    [ "$n" -eq 9 ]
}

@test "this repo's generated command kit routes to the installed skill, placeholder-free" {
    DOGFOOD="$REPO_ROOT/.agents/commands"
    run grep -rqF '<skill-path>' "$DOGFOOD"
    [ "$status" -ne 0 ]
    n=0
    for c in dwp-create dwp-execute dwp-refine dwp-resume dwp-status dwp-verify dwp-upgrade skill-create agent-create; do
        f="$DOGFOOD/$c.md"
        [ -f "$f" ]
        sub="$(sed -n 's/.*\.agents\/skills\/deepworkplan\/\([a-z-]*\)\/SKILL\.md.*/\1/p' "$f" | head -1)"
        [ -n "$sub" ]
        [ -f "$REPO_ROOT/.agents/skills/deepworkplan/$sub/SKILL.md" ]
        n=$((n + 1))
    done
    [ "$n" -eq 9 ]
    # The command reference keeps discovery local and host-portable: it states
    # all three invocation forms, not just the slash command.
    REF="$REPO_ROOT/.agents/docs/COMMANDS_REFERENCE.md"
    [ -f "$REF" ]
    grep -qF '#<name>' "$REF"
    grep -qF 'plain text' "$REF"
}

@test "read-only routes are labeled read-only in the delegator surface" {
    grep -qi 'read-only' "$TPL/dwp-verify.md"
    grep -qi 'without executing' "$TPL/dwp-status.md"
    grep -qi 'read-only' "$TPL/dwp-upgrade.md"
}

@test "Phase 3 installs an intent-to-flow routing block with every activation property" {
    # Extract the canonical fenced block the onboard flow installs (behavioral
    # oracle over the real skill text, not a paraphrase).
    python3 - "$ONBOARD" "$WORK/block.md" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding='utf-8').read().splitlines()
block, inside = [], False
for line in lines:
    if not inside and line.strip() == '```markdown' :
        inside, buf = True, []
        continue
    if inside:
        if line.strip() == '```':
            if any('dwp-create' in l for l in buf):
                block = buf
            inside = False
            continue
        buf.append(line)
assert block, 'canonical routing block not found in onboard/SKILL.md'
open(dst, 'w', encoding='utf-8').write('\n'.join(block) + '\n')
PY
    BLOCK="$WORK/block.md"
    [ -s "$BLOCK" ]
    # Local discovery: the block cites local paths only, no network service.
    run grep -qF 'http' "$BLOCK"
    [ "$status" -ne 0 ]
    grep -qF '.agents/commands/dwp-*' "$BLOCK"
    grep -qF '.agents/skills/deepworkplan/' "$BLOCK"
    # The install rule reconciles instead of intercepting.
    grep -qF 'interception policy' "$ONBOARD"
    tr '\n' ' ' < "$ONBOARD" | tr -s ' ' | grep -qF 'merge, never replace'
}

@test "representative intents map to the right route in the canonical block (static contract)" {
    python3 - "$ONBOARD" <<'PY'
import sys
lines = open(sys.argv[1], encoding='utf-8').read().splitlines()
block, inside, buf = [], False, None
for line in lines:
    if not inside and line.strip() == '```markdown':
        inside, buf = True, []
        continue
    if inside:
        if line.strip() == '```':
            if buf and any('dwp-create' in l for l in buf):
                block = buf
            inside = False
            continue
        buf.append(line)
assert block, 'canonical routing block not found'
rows = [l for l in block if l.lstrip().startswith('|')]
cases = [
    ('plan this work', '/dwp-create'),
    ('create a plan', '/dwp-create'),
    ('execute', '/dwp-execute'),
    ('resume', '/dwp-resume'),
    ('plan status', '/dwp-status'),
    ('verify', '/dwp-verify'),
    ('ordinary direct edit', 'never silently becomes a plan'),
]
for intent, route in cases:
    assert any(intent in r and route in r for r in rows), (intent, route)
joined = '\n'.join(block)
assert 'trust' in joined.lower() and 'not a flow' in joined, 'trust selector rule missing'
assert joined.lower().count('read-only') >= 2, 'read-only must label status and verify'
assert '#deepworkplan-create' in joined, 'by-name invocation missing'
print(f'{len(cases)} intent cases mapped; trust/read-only/by-name properties present')
PY
}

@test "Phase 8 verifies the block and requires the exact post-onboarding next command" {
    phase8="$(sed -n '/## Phase 8/,$p' "$ONBOARD" | tr '\n' ' ' | tr -s ' ')"
    printf '%s\n' "$phase8" | grep -qF 'DWP flow routing block'
    printf '%s\n' "$phase8" | grep -qF 'trust is not a flow selector'
    printf '%s\n' "$phase8" | grep -qF 'dwp-create "<one-line'
    printf '%s\n' "$phase8" | grep -qF '#deepworkplan-create'
    printf '%s\n' "$phase8" | grep -qF 'run deepworkplan-create'
    # The generated-outcome list promises the same exact command.
    grep -qF 'exact post-onboarding next command' "$ONBOARD"
    # The harness upgrade reconciles the block when an onboarded repo lacks it.
    tr '\n' ' ' < "$ONBOARD" | tr -s ' ' | grep -qF 'DWP flow routing block in `AGENTS.md`'
}

@test "router and docs state the activation rules and capability fallbacks" {
    grep -qF 'never become plans silently' "$ROUTER"
    grep -qF 'Trust is not a flow selector' "$ROUTER"
    grep -qF 'stay read-only' "$ROUTER"
    grep -qF '#deepworkplan-create' "$ROUTER"
    grep -qF 'nothing routes through a network service' "$ROUTER"
    # Troubleshooting carries a fallback per missing capability plus the
    # parity honesty rule.
    grep -qF '| Slash commands |' "$TROUBLE"
    grep -qF 'Subprocess agents' "$TROUBLE"
    grep -qF 'Parallel team agents' "$TROUBLE"
    grep -qF 'Persistent sessions' "$TROUBLE"
    grep -qF 'native parallel parity' "$TROUBLE"
    # The team-agents branches degrade honestly when the host lacks teams and
    # never hardcode a vendor model in the agent-neutral core.
    flat_exec="$(tr '\n' ' ' < "$SK/execute/team-agents.md" | tr -s ' ')"
    printf '%s\n' "$flat_exec" | grep -qF 'Host capability check'
    printf '%s\n' "$flat_exec" | grep -qF 'honest degradation'
    printf '%s\n' "$flat_exec" | grep -qF 'do not attempt them and do not simulate them'
    flat_create_ta="$(tr '\n' ' ' < "$SK/create/team-agents.md" | tr -s ' ')"
    printf '%s\n' "$flat_create_ta" | grep -qF 'never hardcodes a vendor model'
    # Contributor docs carry the same boundary: static contract, not routing
    # reliability, and no parallel-parity claim from the sequential path.
    flat_compat="$(tr '\n' ' ' < "$REPO_ROOT/docs/COMPATIBILITY.md" | tr -s ' ')"
    printf '%s\n' "$flat_compat" | grep -qF '**not** native parallel parity'
    printf '%s\n' "$flat_compat" | grep -qF 'reliably routes'
    flat_install="$(tr '\n' ' ' < "$REPO_ROOT/docs/INSTALLATION.md" | tr -s ' ')"
    printf '%s\n' "$flat_install" | grep -qF 'it is not a flow selector'
    printf '%s\n' "$flat_install" | grep -qF 'never silently become a plan'
}

@test "the activation surface is vendor-model-neutral and claims no 4.x implementation" {
    run grep -rniE '\b(sonnet|opus|haiku)\b|gpt-[0-9]' \
        "$ROUTER" "$ONBOARD" "$TPL" "$TROUBLE" \
        "$SK/create/team-agents.md" "$SK/execute/team-agents.md"
    [ "$status" -ne 0 ]
    # The router and the onboard flow implement the 5.x standard; 2.x and 4.x
    # are historical series, not what this skill implements.
    run grep -rn '4\.x this skill implements' "$SK"
    [ "$status" -ne 0 ]
    grep -qF '5.x this skill' "$ROUTER"
    grep -qF '5.x this skill' "$ONBOARD"
    grep -qF 'historical series' "$ROUTER"
    grep -qF 'historical series' "$ONBOARD"
}

@test "install docs enumerate exactly the sub-skills setup.sh links" {
    # The activation surface a user verifies after install must match the
    # installer's real symlink set, not a stale count.
    subs="$(sed -n 's/^SKILLS=(\(.*\))/\1/p' "$REPO_ROOT/setup.sh" \
        | tr -d '"' | tr ' ' '\n' | grep -v '^$' | sort -u)"
    [ -n "$subs" ]
    n=0
    for s in $subs; do
        grep -qF "deepworkplan-$s" "$REPO_ROOT/docs/INSTALLATION.md"
        n=$((n + 1))
    done
    [ "$n" -eq 9 ]
    grep -qF 'nine sub-skills' "$REPO_ROOT/docs/INSTALLATION.md"
    grep -qF 'nine sub-skill symlinks' "$REPO_ROOT/docs/COMPATIBILITY.md"
    run grep -qF 'six sub-skill' "$REPO_ROOT/docs/INSTALLATION.md" "$REPO_ROOT/docs/COMPATIBILITY.md"
    [ "$status" -ne 0 ]
}

@test "an unattended run records a stale harness instead of stopping to offer" {
    # Found by the L2 acceptance run (tests/reliability/PROTOCOL.md): the
    # harness-upgrade branch told an unattended agent to *offer* an upgrade,
    # which is exactly the confirmation trust removes. The agent recorded the
    # gap in writing and routed on — correct behavior the router had not
    # authorized. It does now, and the rule names where the record goes, so
    # "record it" is actionable rather than advice.
    flat="$(sed 's/^[[:space:]]*>[[:space:]]\{0,1\}//' "$ROUTER" | tr '\n' ' ' | tr -s ' ')"
    echo "$flat" | grep -qF -- "Unattended runs record the gap; they never stop to offer."
    echo "$flat" | grep -qF -- "do **not** ask"
    echo "$flat" | grep -qF -- "write it down where the work will see it"
    echo "$flat" | grep -qF -- "never a question, and never a silent omission either"
}

@test "a partially AI-first repository is reconciled, never re-onboarded" {
    # Found by the L1 acceptance run: a workspace with AGENTS.md but no
    # .agents/ matched neither documented branch, so the flow had no rule.
    # The dangerous default would be treating it as a fresh repository and
    # onboarding over handwritten work.
    flat="$(sed 's/^[[:space:]]*>[[:space:]]\{0,1\}//' "$ROUTER" | tr '\n' ' ' | tr -s ' ')"
    echo "$flat" | grep -qF -- "A partially AI-first repository takes this same branch."
    echo "$flat" | grep -qF -- "Any repository with **some** of the harness and not the rest"
    echo "$flat" | grep -qF -- "Never re-onboard from scratch over a repository"
}
