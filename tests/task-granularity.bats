#!/usr/bin/env bash
# Contract tests for the one-purpose-per-task decomposition rule
# (spec/DWP_SPECIFICATION.md §6.4, mirrored in create Step 3.3, the refine
# split trigger, and guide/authoring.md task-file structure).
#
# The rule's unit is the OBJECTIVE, not the action: a task may perform
# several steps that serve its single granular objective; it must never
# bundle several objectives. Prefer N one-objective tasks over fewer
# multi-objective ones. The rule must not decay in either direction —
# no quota of single actions, no padding to inflate the count, and no
# "fewer-but-broader is the default" reading.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

@test "spec 6.4 states one-task-one-objective with the both-ways anti-decay guard" {
    local spec="$REPO_ROOT/skills/deepworkplan/spec/DWP_SPECIFICATION.md"
    gran_doc_has "$spec" "One task, one objective."
    gran_doc_has "$spec" "MUST NOT** bundle several objectives"
    gran_doc_has "$spec" "prefer N tasks with one objective each over fewer tasks carrying several"
    gran_doc_has "$spec" "several objectives with different failure modes, evidence or authorization"
    gran_doc_has "$spec" "keep tightly coupled edits that serve the same objective together"
    gran_doc_has "$spec" "task-count quota and no quota of single actions"
    gran_doc_has "$spec" "never split to inflate the count, never merge to shrink it"
}

@test "create Step 3.3 mirrors the objective-granularity rule" {
    local create="$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
    gran_doc_has "$create" "One task,"
    gran_doc_has "$create" "one objective"
    gran_doc_has "$create" "must never bundle several objectives"
    gran_doc_has "$create" "prefer N tasks with one objective each over fewer tasks carrying several"
    gran_doc_has "$create" "no ritual of a separate task per minor edit, and no padding to inflate the count"
}

@test "refine splits along objective boundaries" {
    local ref="$REPO_ROOT/skills/deepworkplan/refine/SKILL.md"
    gran_doc_has "$ref" "one objective per child"
}

@test "guide authoring teaches one objective per task file" {
    local auth="$REPO_ROOT/skills/deepworkplan/guide/authoring.md"
    gran_doc_has "$auth" "Every task carries **one objective**"
    gran_doc_has "$auth" "prefer N one-objective tasks over fewer multi-objective ones"
}

@test "the unqualified coupled-edits phrasing is gone everywhere" {
    # The old wording ("keep tightly coupled edits together", no objective
    # qualifier) read as fewer-but-broader being the safe default.
    run grep -rF 'keep tightly coupled edits together' "$REPO_ROOT/skills/deepworkplan"
    [ "$status" -ne 0 ]
}

# Sentence-level assertion that tolerates the source file's own line wrapping:
# normalize to one line, then match the phrase.
gran_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
