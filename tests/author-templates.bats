#!/usr/bin/env bats
# Tests for the author sub-skill templates — the scaffold contract for
# skills, agents, and commands created in host repositories.

AUTHOR_DIR="skills/deepworkplan/author"
TEMPLATES_DIR="$AUTHOR_DIR/templates"

@test "author templates exist for skills, agents, and commands" {
    [ -f "$TEMPLATES_DIR/SKILL_TEMPLATE.md" ]
    [ -f "$TEMPLATES_DIR/AGENT_TEMPLATE.md" ]
    [ -f "$TEMPLATES_DIR/COMMAND_TEMPLATE.md" ]
}

@test "SKILL_TEMPLATE keeps the tool-agnostic core and documents the opt-in fields" {
    run grep -F "name: <skill-name>" "$TEMPLATES_DIR/SKILL_TEMPLATE.md"
    [ "$status" -eq 0 ]
    run grep -F "description:" "$TEMPLATES_DIR/SKILL_TEMPLATE.md"
    [ "$status" -eq 0 ]
    # Per-harness opt-ins are present but commented out — never required.
    for field in "version:" "documentation_url:" "user-invocable:" "allowed-tools:"; do
        run grep -F "# $field" "$TEMPLATES_DIR/SKILL_TEMPLATE.md"
        [ "$status" -eq 0 ] || { echo "opt-in $field not documented as commented placeholder"; return 1; }
    done
    # The legacy homepage field must never appear as live frontmatter.
    run grep -E "^homepage:" "$TEMPLATES_DIR/SKILL_TEMPLATE.md"
    [ "$status" -ne 0 ]
}

@test "AGENT_TEMPLATE keeps tiers abstract — no vendor model IDs" {
    run grep -E "light \| standard \| heavy|light / standard / heavy" "$TEMPLATES_DIR/AGENT_TEMPLATE.md"
    [ "$status" -eq 0 ]
    run grep -Ei "claude-|gpt-|gemini-|o[0-9]" "$TEMPLATES_DIR/AGENT_TEMPLATE.md"
    [ "$status" -ne 0 ]
}

@test "COMMAND_TEMPLATE is a thin delegator with no embedded logic" {
    # Routes to the target skill/agent...
    run grep -F "Read \`" "$TEMPLATES_DIR/COMMAND_TEMPLATE.md"
    [ "$status" -eq 0 ]
    run grep -F "do not embed logic" "$TEMPLATES_DIR/COMMAND_TEMPLATE.md"
    [ "$status" -eq 0 ] || { echo "no-logic rule missing"; return 1; }
    # ...and embeds no commands of its own.
    run grep -E "git |pnpm |npm |python3? |bats " "$TEMPLATES_DIR/COMMAND_TEMPLATE.md"
    [ "$status" -ne 0 ]
}

@test "author SKILL.md documents frontmatter fields and the command template" {
    run grep -F "allowed-tools" "$AUTHOR_DIR/SKILL.md"
    [ "$status" -eq 0 ]
    run grep -F "COMMAND_TEMPLATE.md" "$AUTHOR_DIR/SKILL.md"
    [ "$status" -eq 0 ]
    run grep -F "per-harness opt-in" "$AUTHOR_DIR/SKILL.md"
    [ "$status" -eq 0 ] || { echo "opt-in framing missing"; return 1; }
}
