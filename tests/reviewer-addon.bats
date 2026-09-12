#!/usr/bin/env bash
# Contract tests for the AI Diff Reviewer addon mirror set (DWP-side addon
# only: SKILL.md + SPEC.md + templates/INTEGRATION.md — never the upstream
# vendored skill under .agents/skills/).
#
# Pins the reconciled wording: local install + extension proceed under the
# onboarding authorization with no second Flow A/B question; the CI surface is
# a separate offer an unanswered offer does not block or authorize; every pin
# names the documented version (v2.0.1); parity claims say methodology and
# severity parity, never identical findings; invocation soft-fail wording.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    ADDON="$REPO_ROOT/skills/deepworkplan/addons/ai-diff-reviewer"
    MECH="$REPO_ROOT/skills/deepworkplan/addons/README.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
rev_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "local install proceeds under onboarding authorization with no second flow question" {
    rev_doc_has "$ADDON/SKILL.md" "Local-only is automatic under onboarding authorization."
    rev_doc_has "$ADDON/SKILL.md" "without asking the developer to choose Flow A"
    rev_doc_has "$ADDON/SKILL.md" "An unanswered offer means Flow A, not a blocker."
    rev_doc_has "$ADDON/templates/INTEGRATION.md" "without a second flow-choice confirmation"
}

@test "the CI surface is a separate explicit authorization" {
    rev_doc_has "$ADDON/SKILL.md" "only after an explicit request or acceptance"
    rev_doc_has "$ADDON/templates/INTEGRATION.md" "only an explicit request or accepted offer authorizes Flow B"
    rev_doc_has "$ADDON/templates/INTEGRATION.md" "is not CI authorization."
}

@test "no mirror still carries the interactive flow-choice script" {
    run grep -rn -F 'Which flow?' "$ADDON"
    [ "$status" -ne 0 ]
    run grep -rn -F 'Ask the flow question' "$ADDON"
    [ "$status" -ne 0 ]
}

@test "every pin names the documented version; no stale v2.0.0 pin remains" {
    rev_doc_has "$ADDON/SKILL.md" "pinned **v2.0.1**"
    rev_doc_has "$ADDON/SPEC.md" "pinned **v2.0.1**"
    # The only acceptable v2.0.0 references are the Action's historical tags
    # in frozen-pin EXAMPLES — there are none left; the example is v2.0.1.
    # The mechanism README mirror carries the same pin.
    rev_doc_has "$MECH" "currently **v2.0.1**"
    run grep -rn 'v2\.0\.0' "$ADDON" "$MECH"
    [ "$status" -ne 0 ]
    # Install commands are tag-pinned to the documented version.
    grep -qF 'ai-diff-reviewer@v2.0.1' "$ADDON/SKILL.md"
}

@test "parity claims say methodology and severity parity, never identical findings" {
    rev_doc_has "$ADDON/SKILL.md" "aligns the review methodology, not"
    rev_doc_has "$ADDON/SPEC.md" "methodology and severity parity, not identical findings"
    # The byte-identical claim stays scoped to the prompt bytes (an upstream
    # CI invariant), never to review output.
    rev_doc_has "$ADDON/SKILL.md" "**byte-identical** to the Action's shipped"
    run grep -rn -F 'guarantees identical' "$ADDON"
    [ "$status" -ne 0 ]
    # Every "identical findings" collocation must be negated ("not identical
    # findings"); compare counts on whitespace-normalized text so a line wrap
    # between "not" and "identical" cannot fake a violation.
    local total negated
    total=$(cat "$ADDON/SKILL.md" "$ADDON/SPEC.md" "$ADDON/templates/INTEGRATION.md" \
        | tr '\n' ' ' | tr -s ' ' | grep -oF 'identical findings' | wc -l)
    negated=$(cat "$ADDON/SKILL.md" "$ADDON/SPEC.md" "$ADDON/templates/INTEGRATION.md" \
        | tr '\n' ' ' | tr -s ' ' | grep -oF 'not identical findings' | wc -l)
    [ "$total" -gt 0 ]
    [ "$total" -eq "$negated" ]
}

@test "invocation soft-fail stays scoped to invocation, not absence" {
    rev_doc_has "$ADDON/SPEC.md" "Soft-fail applies to **invocation** of the local review pass only"
    rev_doc_has "$ADDON/SPEC.md" "is not an invocation failure"
}

@test "gh is not a local requirement" {
    # The local review runs git + the vendored skill; gh was never needed for
    # Flow A and the frontmatter must not demand it.
    run grep -F 'anyBins":["git","gh"]' "$ADDON/SKILL.md"
    [ "$status" -ne 0 ]
    grep -qF '"anyBins":["git"]' "$ADDON/SKILL.md"
}

@test "the reviewer augmentation reviews the plan's explicit diff, not the tracking ref" {
    local aug="$REPO_ROOT/skills/deepworkplan/create/addon-augmentations.md"
    rev_doc_has "$aug" "supply the plan's recorded starting revision"
    rev_doc_has "$aug" "An empty default diff is not evidence of a completed review."
}
