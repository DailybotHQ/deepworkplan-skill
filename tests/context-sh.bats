#!/usr/bin/env bats
# Tests for skills/deepworkplan/shared/context.sh
#
# Run with:  bats tests/
# Requires:  bats-core (brew install bats-core / apt install bats)

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    CONTEXT_SH="$REPO_ROOT/skills/deepworkplan/shared/context.sh"
    # Drop any overrides leaking from the contributor's shell so tests are
    # deterministic regardless of where they run.
    unset DWP_AGENT_TOOL DWP_DIR
    # Each test runs in a fresh tempdir (not a git repo) so detection falls
    # back to the documented defaults.
    TMPDIR_TEST="$(mktemp -d)"
    cd "$TMPDIR_TEST"
}

teardown() {
    cd "$BATS_TEST_DIRNAME"
    rm -rf "$TMPDIR_TEST"
}

@test "emits valid JSON in a regular directory" {
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
    # Confirm it parses as JSON
    echo "$output" | python3 -c 'import json,sys; json.loads(sys.stdin.read())'
}

@test "JSON has all five required fields" {
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \"repo\":\" ]]
    [[ "$output" =~ \"repo_root\":\" ]]
    [[ "$output" =~ \"branch\":\" ]]
    [[ "$output" =~ \"agent_tool\":\" ]]
    [[ "$output" =~ \"dwp_dir\":\" ]]
}

@test "DWP_AGENT_TOOL env var overrides detection" {
    export DWP_AGENT_TOOL="my-custom-agent"
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \"agent_tool\":\"my-custom-agent\" ]]
}

@test "DWP_DIR env var overrides the .dwp/ location" {
    export DWP_DIR="/tmp/custom-dwp"
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \"dwp_dir\":\"/tmp/custom-dwp\" ]]
}

@test "defaults dwp_dir to <repo_root>/.dwp" {
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    # repo_root falls back to $PWD (the tempdir) outside a git work tree.
    [[ "$output" =~ \"dwp_dir\":\"$TMPDIR_TEST/.dwp\" ]]
}

@test "uses CLAUDECODE env var to detect Claude Code" {
    export CLAUDECODE="1"
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \"agent_tool\":\"claude-code\" ]]
}

@test "falls back to current directory name as repo when not in a git repo" {
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    expected_repo=$(basename "$PWD")
    [[ "$output" =~ \"repo\":\"$expected_repo\" ]]
}

@test "branch is 'unknown' when not in a git repo" {
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \"branch\":\"unknown\" ]]
}

@test "agent_tool is 'unknown' when no detection signal is present" {
    # Run via env -i so no inherited harness env var (CLAUDECODE, CURSOR_*, …)
    # pins an agent identity. PATH/HOME are kept so git still resolves.
    run env -i HOME="$HOME" PATH="$PATH" bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ \"agent_tool\":\"unknown\" ]]
}
