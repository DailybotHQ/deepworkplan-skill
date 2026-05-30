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
