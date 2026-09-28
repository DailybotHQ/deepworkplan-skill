#!/usr/bin/env bats
# User-facing plan identity: allocation, legacy coexistence, and selection.

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    PATHS="$REPO_ROOT/skills/deepworkplan/shared/plan_paths.py"
    PLAN_DIR="$(mktemp -d)/plans"
}

teardown() {
    rm -rf "$(dirname "$PLAN_DIR")"
}

@test "new plans are numbered without renaming legacy folders or reusing IDs" {
    mkdir -p "$PLAN_DIR/PLAN_old_project"
    run python3 "$PATHS" --plans-dir "$PLAN_DIR" allocate improve_release_docs
    [ "$status" -eq 0 ]
    [ "$output" = "$PLAN_DIR/PLAN_001_improve_release_docs" ]
    rm -r "$output"

    run python3 "$PATHS" --plans-dir "$PLAN_DIR" allocate repair_install_flow
    [ "$status" -eq 0 ]
    [ "$output" = "$PLAN_DIR/PLAN_002_repair_install_flow" ]
    [ -d "$PLAN_DIR/PLAN_old_project" ]

    run python3 "$PATHS" --plans-dir "$PLAN_DIR" resolve latest
    [ "$status" -eq 0 ]
    [ "$output" = "$PLAN_DIR/PLAN_002_repair_install_flow" ]
}

@test "selection supports IDs and legacy names and refuses ambiguous slugs" {
    mkdir -p "$PLAN_DIR/PLAN_old_project" \
        "$PLAN_DIR/PLAN_001_improve_release_docs" \
        "$PLAN_DIR/PLAN_002_improve_release_docs"

    run python3 "$PATHS" --plans-dir "$PLAN_DIR" resolve 002
    [ "$status" -eq 0 ]
    [ "$output" = "$PLAN_DIR/PLAN_002_improve_release_docs" ]
    run python3 "$PATHS" --plans-dir "$PLAN_DIR" resolve old_project
    [ "$status" -eq 0 ]
    [ "$output" = "$PLAN_DIR/PLAN_old_project" ]
    run python3 "$PATHS" --plans-dir "$PLAN_DIR" resolve improve_release_docs
    [ "$status" -eq 2 ]
    [[ "$output" == *"ambiguous plan"* ]]
}

@test "v5 allocation rejects a fifth slug word before creating a folder" {
    run python3 "$PATHS" --plans-dir "$PLAN_DIR" allocate \
        improve_the_release_process_docs --max-words 4
    [ "$status" -eq 2 ]
    [ ! -d "$PLAN_DIR" ]
}

@test "allocation expands naturally beyond three digits" {
    mkdir -p "$PLAN_DIR/PLAN_999_previous_project"
    run python3 "$PATHS" --plans-dir "$PLAN_DIR" allocate improve_release_docs
    [ "$status" -eq 0 ]
    [ "$output" = "$PLAN_DIR/PLAN_1000_improve_release_docs" ]
}
