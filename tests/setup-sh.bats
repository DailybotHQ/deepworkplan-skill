#!/usr/bin/env bats
# Tests for setup.sh — the symlink installer for non-skills.sh users.
#
# Run with:  bats tests/

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    SETUP_SH="$REPO_ROOT/setup.sh"
    # Use a fake HOME so we don't touch the contributor's real agent installs.
    FAKE_HOME="$(mktemp -d)"
    export HOME="$FAKE_HOME"
}

teardown() {
    rm -rf "$FAKE_HOME"
}

@test "--help prints usage and exits 0" {
    run bash "$SETUP_SH" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ Usage: ]]
}

@test "rejects --host without value" {
    run bash "$SETUP_SH" --host
    [ "$status" -ne 0 ]
}

@test "creates pack and sub-skill symlinks for claude target" {
    mkdir -p "$FAKE_HOME/.claude"
    run bash "$SETUP_SH" --host claude
    [ "$status" -eq 0 ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-create" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-execute" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-refine" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-resume" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-status" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-onboard" ]
}

@test "is idempotent: running twice produces same symlinks without error" {
    mkdir -p "$FAKE_HOME/.claude"
    run bash "$SETUP_SH" --host claude
    [ "$status" -eq 0 ]
    run bash "$SETUP_SH" --host claude
    [ "$status" -eq 0 ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-create" ]
}

@test "--host=cursor (equals form) creates cursor symlinks" {
    mkdir -p "$FAKE_HOME/.cursor"
    run bash "$SETUP_SH" --host=cursor
    [ "$status" -eq 0 ]
    [ -L "$FAKE_HOME/.cursor/skills/deepworkplan" ]
    [ -L "$FAKE_HOME/.cursor/skills/deepworkplan-onboard" ]
}

@test "rejects unknown --host value with non-zero exit" {
    run bash "$SETUP_SH" --host nonsense
    [ "$status" -ne 0 ]
}

@test "auto mode exits cleanly even when no agents are detected" {
    # FAKE_HOME has no ~/.claude, ~/.cursor, etc. detect_agents may still find a
    # codex binary on the developer's PATH — that's fine; we only want to
    # confirm setup.sh doesn't error in auto mode and reports the empty case.
    if command -v codex >/dev/null 2>&1; then
        skip "codex is on PATH — auto-detect can't reach the 'no agents' branch on this machine"
    fi
    run bash "$SETUP_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No known agent platforms detected" ]]
}

# ─── Every declared --host route (Task 20: installation support matrix) ──────
# setup.sh --help advertises nine host names. A route that is advertised but
# never exercised is an untested promise, so each one gets a fixture here.

@test "every advertised --host route creates its documented skills directory" {
    # agent:relative-skills-dir, mirroring resolve_skills_dir() in setup.sh
    routes=(
        "claude:.claude/skills"
        "cursor:.cursor/skills"
        "codex:.codex/skills"
        "windsurf:.codeium/windsurf/skills"
        "copilot:.copilot/skills"
        "cline:.cline/skills"
        "gemini:.gemini/skills"
        "opencode:.config/opencode/skills"
        "antigravity:.antigravity/skills"
    )
    for route in "${routes[@]}"; do
        agent="${route%%:*}"
        reldir="${route#*:}"
        run bash "$SETUP_SH" --host "$agent"
        [ "$status" -eq 0 ]
        [ -L "$FAKE_HOME/$reldir/deepworkplan" ]
        for skill in create execute refine resume status onboard; do
            [ -L "$FAKE_HOME/$reldir/deepworkplan-$skill" ]
        done
    done
}

@test "--help advertises exactly the host routes setup.sh can resolve" {
    run bash "$SETUP_SH" --help
    [ "$status" -eq 0 ]
    for agent in claude cursor codex windsurf copilot cline gemini opencode antigravity; do
        [[ "$output" == *"$agent"* ]]
    done
}

@test "an existing real file at a skill path is never clobbered" {
    mkdir -p "$FAKE_HOME/.claude/skills"
    echo "user content" > "$FAKE_HOME/.claude/skills/deepworkplan-create"
    run bash "$SETUP_SH" --host claude
    [ "$status" -eq 0 ]
    [ ! -L "$FAKE_HOME/.claude/skills/deepworkplan-create" ]
    [ "$(cat "$FAKE_HOME/.claude/skills/deepworkplan-create")" = "user content" ]
    # The remaining routes still link, so one collision does not abort install.
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan-execute" ]
}

@test "the installed pack resolves its runtime references without the contributor checkout" {
    # The shipped artifact must be self-contained: no runtime file may point at
    # repo-only infrastructure (tests/, scripts/, docs/, .github/) that never ships.
    run bash -c "grep -rInE '\\]\\((\\.\\./)*(tests|scripts|docs|\\.github)/' '$REPO_ROOT/skills/deepworkplan' --include='*.md' || true"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "installing into a fresh HOME needs no network and no preexisting agent dir" {
    # No mkdir of ~/.claude first: setup.sh must create the tree it targets.
    run bash "$SETUP_SH" --host claude
    [ "$status" -eq 0 ]
    [ -d "$FAKE_HOME/.claude/skills" ]
    [ -L "$FAKE_HOME/.claude/skills/deepworkplan" ]
    # Router resolves through the symlink alone.
    [ -f "$FAKE_HOME/.claude/skills/deepworkplan/SKILL.md" ]
}
