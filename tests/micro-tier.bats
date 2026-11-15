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
    CREATE_V6="$SK/create/v6.md"
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
    doc_has "$CREATE" "Proportional rigor (§11, normative)"
    doc_has "$CREATE" "say a plan is disproportionate and offer the inline form"
    doc_has "$CREATE" "a folder only if the developer, told, still asks"
    doc_has "$CREATE" "record the micro judgment and inline alternative in the README and materialize"
}

@test "the contradicting micro wording does not return to create" {
    run grep -nF "is **micro** tier and is
  a first-class Lite plan" "$CREATE"
    [ "$status" -ne 0 ]
    run doc_has "$CREATE" "a first-class Lite plan: record a concise goal"
    [ "$status" -ne 0 ]
    # Small-but-real work keeps its protection; micro is the named §11 exception.
    doc_has "$CREATE" "Micro work is the §11 exception"
}

@test "the live 7.x create path (create/v6.md) states the micro rule before allocation" {
    # 7.x create runs create/v6.md, not the retained Steps 1+ of SKILL.md.
    doc_has "$CREATE_V6" "Proportion before allocation (spec §11, normative)"
    doc_has "$CREATE_V6" "say a plan is disproportionate and offer the inline form"
    doc_has "$CREATE_V6" "a folder only if the developer, told, still asks"
    doc_has "$CREATE_V6" "record the micro judgment and inline alternative in the README and materialize"
    # and it comes before the folder is claimed
    micro="$(grep -n 'Proportion before allocation' "$CREATE_V6" | head -1 | cut -d: -f1)"
    alloc="$(grep -n 'plan_paths.py --plans-dir' "$CREATE_V6" | head -1 | cut -d: -f1)"
    [ "$micro" -lt "$alloc" ]
    doc_has "$CREATE_V6" "No smuggled how."
}
