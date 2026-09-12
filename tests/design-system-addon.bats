#!/usr/bin/env bash
# Contract tests for the design-system addon smart-install policy
# ("mandatory but optional", user direction 2026-09-12) across its four
# surfaces: addons/design-system/SKILL.md + SPEC.md, spec/ADDONS.md,
# onboard/addons.md.
#
# The policy: a detected interface surface (even an ambiguous one) makes the
# evaluation and offer MANDATORY - never skipped, with the detection rationale
# recorded - while installation always requires explicit acceptance; no
# profile is auto-applied, not even visual-ui in trust mode.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    ADDON="$REPO_ROOT/skills/deepworkplan/addons/design-system"
    SPEC="$REPO_ROOT/skills/deepworkplan/spec/ADDONS.md"
    ONBOARD="$REPO_ROOT/skills/deepworkplan/onboard/addons.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
ds_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "detection makes the offer mandatory, ambiguity included, with recorded rationale" {
    ds_doc_has "$ADDON/SPEC.md" "Detection makes the offer mandatory; it never makes the install automatic."
    ds_doc_has "$ADDON/SPEC.md" "even an ambiguous one"
    ds_doc_has "$ADDON/SPEC.md" "skipping the evaluation or the offer"
    ds_doc_has "$ADDON/SPEC.md" "record the detection rationale"
    ds_doc_has "$ADDON/SKILL.md" "the evaluation and offer are not skippable in either mode"
    ds_doc_has "$ADDON/SKILL.md" "an ambiguous signal still gets the"
}

@test "installation stays acceptance-gated in both modes" {
    ds_doc_has "$ADDON/SPEC.md" "Installation is acceptance-gated in both guided and trust modes."
    ds_doc_has "$ADDON/SPEC.md" "no profile is auto-applied"
    ds_doc_has "$ADDON/SPEC.md" "an explicit decline is respected for that run"
    ds_doc_has "$ADDON/SPEC.md" "ask again for an already accepted action"
    ds_doc_has "$ADDON/SKILL.md" "Offer mandatorily, accept explicitly."
    ds_doc_has "$ADDON/SKILL.md" "Every profile still requires explicit acceptance"
}

@test "spec ADDONS.md and onboard state the same policy" {
    ds_doc_has "$SPEC" "makes the evaluation and offer **mandatory** — never skipped"
    ds_doc_has "$SPEC" "explicit acceptance"
    ds_doc_has "$ONBOARD" "the evaluation and offer are **mandatory, not skippable**"
    ds_doc_has "$ONBOARD" "requires explicit acceptance even in trust mode"
    ds_doc_has "$ONBOARD" "Detection makes the evaluation and offer"
}

@test "the default-on-in-trust exception does not return as a blanket rule" {
    run grep -rn 'default-on' "$ADDON" "$ONBOARD" "$SPEC"
    [ "$status" -ne 0 ]
    run grep -rn -F 'apply it automatically' "$ADDON" "$ONBOARD" "$SPEC"
    [ "$status" -ne 0 ]
}

@test "no interface surface still means no offer" {
    ds_doc_has "$ADDON/SPEC.md" "when **no** profile is detected, the flow **MUST NOT** offer the"
    ds_doc_has "$ONBOARD" "Never offer for a repo with no interface surface"
}
