#!/usr/bin/env bats
# Contract test: create states the micro-tier rule of spec §11, not a rival one.
#
# The 2026 methodology debate found the pack contradicting itself: spec §11
# says an interactive request for a micro-tier plan gets the inline offer and
# no folder unless the developer still asks, while create called micro "a
# first-class Lite plan" and forbade routing it inline. These assertions read
# both documents, so the rule cannot drift apart again.
#
# Run with:  bats tests/micro-tier.bats
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    SPEC="$SK/spec/DWP_SPECIFICATION.md"
    CREATE="$SK/create/SKILL.md"
}

# Whitespace- and blockquote-insensitive containment, as in claims-consistency.
doc_has() {
    sed 's/^[[:space:]]*>[[:space:]]\{0,1\}//' "$1" | tr '\n' ' ' | tr -s ' ' | grep -qF -- "$2"
}

@test "spec §11 still carries the interactive micro rule create defers to" {
    doc_has "$SPEC" "**MUST** say that a plan is disproportionate and offer the inline form instead"
    doc_has "$SPEC" "unless the developer, having been told, still asks for one"
    doc_has "$SPEC" "record the micro judgment and the inline alternative in the plan README"
}

@test "create states the same micro rule for guided and trust modes" {
    doc_has "$CREATE" "§11 is normative for it"
    doc_has "$CREATE" "say that a plan is disproportionate and offer the inline form"
    doc_has "$CREATE" "create a plan folder only if the developer, having been told, still asks"
    doc_has "$CREATE" "record the micro judgment and the inline alternative in the README and materialize"
}

@test "the contradicting micro wording does not return to create" {
    run grep -nF "is **micro** tier and is
  a first-class Lite plan" "$CREATE"
    [ "$status" -ne 0 ]
    ! doc_has "$CREATE" "a first-class Lite plan: record a concise goal"
    ! doc_has "$CREATE" "never route it to an inline non-DWP alternative merely because it is small"
}
