#!/usr/bin/env bats
# Tests for this repo's own .agents/ dogfood kit.
#
# This repo dogfoods the onboarding methodology it ships: it carries its own
# .agents/ kit + .claude -> .agents symlink + a symlink to the pack, exactly as
# the `onboard` sub-skill generates for a target repo. These tests lock that
# structure in so a future change can't silently break the dogfood — the same
# integrity the `verify` sub-skill checks, made a CI gate (test & validation
# discipline, DWP_SPECIFICATION.md 5.1.1).
#
# Run with:  bats tests/

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    AGENTS_DIR="$REPO_ROOT/.agents"
    DOCS_DIR="$AGENTS_DIR/docs"
}

@test ".claude symlink resolves to .agents and reaches the pack" {
    [ -L "$REPO_ROOT/.claude" ]
    [ "$(readlink "$REPO_ROOT/.claude")" = ".agents" ]
    [ -f "$REPO_ROOT/.claude/skills/deepworkplan/SKILL.md" ]
}

@test ".cursor symlink resolves to .agents and reaches the pack" {
    [ -L "$REPO_ROOT/.cursor" ]
    [ "$(readlink "$REPO_ROOT/.cursor")" = ".agents" ]
    [ -f "$REPO_ROOT/.cursor/skills/deepworkplan/SKILL.md" ]
}

@test ".agents/skills/deepworkplan contains the dogfooded skill pack" {
    [ -d "$AGENTS_DIR/skills/deepworkplan" ]
    [ -f "$AGENTS_DIR/skills/deepworkplan/SKILL.md" ]
    [ -f "$AGENTS_DIR/skills/deepworkplan/create/SKILL.md" ]
    [ -f "$AGENTS_DIR/skills/deepworkplan/execute/SKILL.md" ]
    [ -f "$AGENTS_DIR/skills/deepworkplan/author/SKILL.md" ]
}

@test ".agents/ has the canonical layout (agents, commands, skills, docs, settings, README)" {
    [ -d "$AGENTS_DIR/agents" ]
    [ -d "$AGENTS_DIR/commands" ]
    [ -d "$AGENTS_DIR/skills" ]
    [ -d "$AGENTS_DIR/docs" ]
    [ -f "$AGENTS_DIR/settings.json" ]
    [ -f "$AGENTS_DIR/README.md" ]
}

@test "the six dwp-* delegators plus skill-create/agent-create exist" {
    for c in dwp-create dwp-execute dwp-refine dwp-resume dwp-status dwp-verify skill-create agent-create; do
        [ -f "$AGENTS_DIR/commands/$c.md" ]
    done
}

@test "dwp-* delegators are thin and route to the deepworkplan skill" {
    for f in "$AGENTS_DIR"/commands/dwp-*.md; do
        lines="$(wc -l < "$f")"
        [ "$lines" -le 40 ]
        grep -qi 'deepworkplan' "$f"
    done
}

@test "settings.json is valid JSON" {
    if command -v python3 >/dev/null 2>&1; then
        run python3 -c "import json,sys; json.load(open('$AGENTS_DIR/settings.json'))"
        [ "$status" -eq 0 ]
    else
        skip "python3 not available to parse JSON"
    fi
}

@test "every command on disk is listed in COMMANDS_REFERENCE.md (no orphans)" {
    for f in "$AGENTS_DIR"/commands/*.md; do
        name="$(basename "$f" .md)"
        grep -q "$name" "$DOCS_DIR/COMMANDS_REFERENCE.md"
    done
}

@test "every agent on disk is listed in the skills/agents catalog (no orphans)" {
    for f in "$AGENTS_DIR"/agents/*.md; do
        name="$(basename "$f" .md)"
        grep -q "$name" "$DOCS_DIR/skills_agents_catalog.md"
    done
}

@test "every repo-dev skill on disk is listed in the catalog (no orphans)" {
    # Includes the dogfooded DeepWorkPlan pack and the vendored third-party
    # skills (dailybot, ai-diff-reviewer) — all must appear in the catalog
    # so the inventory stays complete. Vendored packs are documented under
    # the "Vendored third-party skills" section.
    for d in "$AGENTS_DIR"/skills/*/; do
        name="$(basename "$d")"
        grep -q "$name" "$DOCS_DIR/skills_agents_catalog.md"
    done
}

@test "each repo-dev skill carries name + description frontmatter" {
    for d in "$AGENTS_DIR"/skills/*/; do
        skill="$d/SKILL.md"
        [ -f "$skill" ]
        grep -qE '^name:' "$skill"
        grep -qE '^description:' "$skill"
    done
}

@test "the documented addon install pin matches the vendored addon version" {
    # The release workflow refreshes `.agents/skills/ai-diff-reviewer/` to the
    # latest upstream tag, but the install command the pack *teaches* is prose
    # and is not rewritten with it. Those two drifted a patch apart once (the
    # pack taught @v2.0.0 while the vendored copy was 2.0.1), which hands every
    # adopter a stale reviewer. Make the invariant a CI gate instead of a habit.
    #
    # Only the exact pin is checked. `DailybotHQ/ai-diff-reviewer@v2` is the
    # GitHub Action's floating major tag and is deliberately left floating so
    # patch fixes flow automatically — it must NOT be pinned to a patch.
    local vendored pins
    vendored="$(grep -m1 '^version:' "$AGENTS_DIR/skills/ai-diff-reviewer/SKILL.md" \
        | sed -E 's/.*"([^"]+)".*/\1/')"
    [ -n "$vendored" ]

    pins="$(grep -rhoE 'ai-diff-reviewer@v[0-9]+\.[0-9]+\.[0-9]+' "$REPO_ROOT/skills" \
        | sed 's/.*@v//' | sort -u)"
    [ -n "$pins" ]
    # Every exact pin in the shipped pack names exactly the vendored version.
    [ "$pins" = "$vendored" ]
}

@test "the provenance version onboard writes matches the standard the checker enforces" {
    # `DWP standard: X` is stamped into every onboarded repo by `onboard` and
    # read back by `conformance.sh`, which compares it against SUPPORTED_SPEC —
    # the DWP_SPECIFICATION version. Those drifted once: onboard wrote 2.3.0
    # (the DOCUMENTATION_STANDARD version) while the checker enforced 2.4.0, so
    # every freshly onboarded repo declared a standard older than the one it had
    # just received. Spec documents version independently, so the three sources
    # have to be pinned together deliberately.
    local pack spec supported written
    pack="$REPO_ROOT/skills/deepworkplan"

    spec="$(grep -m1 -E '^\| \*\*Version\*\* \|' "$pack/spec/DWP_SPECIFICATION.md" \
        | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    supported="$(grep -m1 -E '^SUPPORTED_SPEC=' "$pack/verify/conformance.sh" \
        | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    [ -n "$spec" ]
    [ "$supported" = "$spec" ]

    # Every documented `DWP standard: X` example names that same version.
    written="$(grep -rhoE 'DWP standard: [0-9]+\.[0-9]+\.[0-9]+' "$pack" \
        | sed 's/.*: //' | sort -u)"
    [ -n "$written" ]
    [ "$written" = "$spec" ]
}
