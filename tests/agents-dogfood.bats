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
