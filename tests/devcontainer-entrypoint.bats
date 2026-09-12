#!/usr/bin/env bash
# Regression tests for the reworked link_persist() embedded in the devcontainer
# addon's entrypoint template (addons/devcontainer/templates/entrypoint.md).
#
# These run the ACTUAL function extracted from the markdown fence — not a
# copy — against temp files/dirs, so template drift breaks the extraction
# guard instead of silently testing stale code.
#
# Covered behaviors (task 10 acceptance criteria):
#   1. A fresh missing .claude.json becomes a FILE containing {} (not a dir).
#   2. Copying a directory into an empty volume adds no extra directory level.
#   3. A rebuild with an existing populated volume preserves it (idempotent).
#   4. A failed copy propagates the error BEFORE any removal; a type mismatch
#      never deletes data.
# Plus: plain-file seeding and the already-a-symlink no-op.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    ENTRY="$REPO_ROOT/skills/deepworkplan/addons/devcontainer/templates/entrypoint.md"
    T="$(mktemp -d)"
    # Extract the fenced bash skeleton, keep everything up to (not including)
    # setup_ai_cli_persistence, and drop the set -euo pipefail line so a
    # sourcing test shell keeps bats semantics.
    awk '/^```bash$/{f=1;next} /^```$/{f=0} f' "$ENTRY" \
        | sed -n '1,/^setup_ai_cli_persistence() {/p' | sed '$d' \
        | grep -v '^set -euo pipefail$' > "$T/entry_lib.sh"
}

teardown() {
    rm -rf "$T"
}

# The extraction must really have found the function — a template re-format
# that breaks extraction fails here instead of testing nothing.
@test "extraction finds the real link_persist in the template" {
    grep -q '^link_persist() {' "$T/entry_lib.sh"
    . "$T/entry_lib.sh"
    type link_persist >/dev/null
}

@test "a fresh missing .claude.json becomes a FILE containing {}" {
    . "$T/entry_lib.sh"
    H="$T/home"; mkdir -p "$H"
    link_persist "$H/.claude.json" "$H/.claude_data/claude.json" json
    [ -f "$H/.claude.json" ]            # a file...
    [ ! -d "$H/.claude.json" ]          # ...not a directory
    [ "$(cat "$H/.claude_data/claude.json")" = "{}" ]
    [ -L "$H/.claude.json" ]            # symlinked at the real path
}

@test "directory seeding introduces no extra directory level" {
    . "$T/entry_lib.sh"
    H="$T/home"; mkdir -p "$H/.claude/projects/foo"
    echo session > "$H/.claude/projects/foo/state"
    mkdir -p "$T/vol"                                    # empty volume
    link_persist "$H/.claude" "$T/vol"
    [ -f "$T/vol/projects/foo/state" ]                   # contents at level 0
    [ ! -e "$T/vol/.claude" ]                            # no nested copy of the source dir itself
    [ -L "$H/.claude" ]
    [ "$(readlink "$H/.claude")" = "$T/vol" ]
}

@test "a populated volume wins over the container's fresh copy" {
    . "$T/entry_lib.sh"
    H="$T/home"; mkdir -p "$H/.claude"
    echo fresh-container-state > "$H/.claude/.claude.json"
    mkdir -p "$T/vol/persisted"                          # volume already has auth
    echo persisted-auth > "$T/vol/persisted/auth"
    link_persist "$H/.claude" "$T/vol"
    [ -f "$T/vol/persisted/auth" ]
    [ "$(cat "$T/vol/persisted/auth")" = "persisted-auth" ]
    [ ! -e "$T/vol/.claude.json" ]                       # fresh copy NOT seeded over
    [ -L "$H/.claude" ]
}

@test "a failed copy propagates the error BEFORE any removal" {
    . "$T/entry_lib.sh"
    # cp stub that always fails with 42 — proves the error code propagates and
    # that rm -rf of the original never runs on a failed seed.
    mkdir -p "$T/stub"
    printf '#!/bin/sh\nexit 42\n' > "$T/stub/cp"
    chmod +x "$T/stub/cp"
    H="$T/home"; mkdir -p "$H/.claude/projects"
    echo state > "$H/.claude/projects/state"
    mkdir -p "$T/vol"                                    # empty volume -> seed path runs cp
    PATH="$T/stub:$PATH" run link_persist "$H/.claude" "$T/vol"
    [ "$status" -eq 42 ]
    [ -d "$H/.claude" ]                                  # original untouched
    [ -f "$H/.claude/projects/state" ]
    [ ! -L "$H/.claude" ]                                # no symlink left behind
}

@test "a type mismatch never deletes data" {
    . "$T/entry_lib.sh"
    # Directory real path vs FILE target -> wrong-type refusal.
    H="$T/home"; mkdir -p "$H/.claude"
    echo keep > "$H/.claude/state"
    echo volfile > "$T/vol"
    run link_persist "$H/.claude" "$T/vol"
    [ "$status" -eq 1 ]
    [ -d "$H/.claude" ] && [ -f "$H/.claude/state" ]     # original survives
    [ "$(cat "$T/vol")" = "volfile" ]                    # target survives
    # File real path vs DIRECTORY target -> must-be-a-file refusal.
    H2="$T/home2"; mkdir -p "$H2"
    echo json > "$H2/.claude.json"
    mkdir -p "$T/vol2"                                   # the target itself is a directory
    run link_persist "$H2/.claude.json" "$T/vol2"
    [ "$status" -eq 1 ]
    [ -f "$H2/.claude.json" ]                            # original survives
    [ "$(cat "$H2/.claude.json")" = "json" ]
    [ -d "$T/vol2" ]                                     # target survives
}

@test "plain-file seeding copies the file once and symlinks it" {
    . "$T/entry_lib.sh"
    H="$T/home"; mkdir -p "$H/.config/gh"
    echo '{"host":"github.com"}' > "$H/.config/gh/hosts.yml"
    link_persist "$H/.config/gh/hosts.yml" "$H/.gh_data/hosts.yml"
    [ -f "$H/.gh_data/hosts.yml" ]
    [ "$(cat "$H/.gh_data/hosts.yml")" = '{"host":"github.com"}' ]
    [ -L "$H/.config/gh/hosts.yml" ]
}

@test "an existing symlink is a no-op (idempotent relink on rebuild)" {
    . "$T/entry_lib.sh"
    H="$T/home"; mkdir -p "$H"
    link_persist "$H/.claude.json" "$H/.claude_data/claude.json" json
    before="$(readlink "$H/.claude.json")"
    echo mutated > "$H/.claude_data/claude.json"          # simulate live state changes
    link_persist "$H/.claude.json" "$H/.claude_data/claude.json" json
    [ "$(readlink "$H/.claude.json")" = "$before" ]       # link untouched
    [ "$(cat "$H/.claude_data/claude.json")" = "mutated" ] # data preserved
}
