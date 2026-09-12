#!/usr/bin/env bash
# Cross-addon consent-matrix contract tests (task 11).
#
# ONE consent matrix, no contradictions across every addon surface:
#   - ai-diff-reviewer: required LOCAL review installed under the onboarding
#     consent (Phase 7a); CI surface = explicit opt-in; Final Review never
#     surprise-bootstraps a missing reviewer (honest degradation instead).
#   - design-system: detection makes evaluation+offer mandatory; installation
#     acceptance-gated in both modes; no profile auto-applied.
#   - dependency-upgrade: near-default — offered for every repo with declared
#     dependencies; the inert delegator installs under the onboarding consent
#     unless explicitly declined; installs run no upgrade.
#   - devcontainer + dailybot: explicit opt-ins; never auto-installed for
#     everyone; never required.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    A="$REPO_ROOT/skills/deepworkplan/addons"
    SPEC="$REPO_ROOT/skills/deepworkplan/spec/ADDONS.md"
    ONBOARD="$REPO_ROOT/skills/deepworkplan/onboard/addons.md"
    MECH="$REPO_ROOT/skills/deepworkplan/addons/README.md"
    DAILY="$REPO_ROOT/skills/deepworkplan/addons/dailybot/SKILL.md"
    DAILY_SPEC="$REPO_ROOT/skills/deepworkplan/addons/dailybot/SPEC.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
c_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "reviewer: required local review under onboarding consent; CI stays explicit" {
    c_doc_has "$SPEC" "under the same consent that covers the rest of the onboarding"
    c_doc_has "$SPEC" "stays an **explicit opt-in**"
    c_doc_has "$SPEC" "never installs it unrequested"
    c_doc_has "$SPEC" "Final Review never surprise-bootstraps it"
    c_doc_has "$SPEC" "local reviewer not installed"
}

@test "reviewer: no blanket 'each addon is opt-in' rule contradicts the two declared exceptions" {
    # §4 names BOTH exceptions to the opt-in pattern: the required baseline
    # reviewer and the near-default dependency-upgrade tier.
    c_doc_has "$SPEC" "with two declared exceptions"
    c_doc_has "$SPEC" "near-default tier"
}

@test "design-system: mandatory offer, acceptance-gated install, no auto-apply" {
    c_doc_has "$A/design-system/SKILL.md" "Offer mandatorily, accept explicitly."
    c_doc_has "$A/design-system/SKILL.md" "no profile is auto-applied, even in trust mode"
    c_doc_has "$A/design-system/SPEC.md" "Installation is acceptance-gated in both guided and trust modes."
}

@test "dependency-upgrade: near-default and inert across surfaces" {
    c_doc_has "$A/dependency-upgrade/SKILL.md" "Installing the delegator changes no dependencies"
    c_doc_has "$SPEC" "while every upgrade stays explicit, gated work"
    c_doc_has "$MECH" "no upgrade ever runs from an install"
}

@test "devcontainer and dailybot stay explicit opt-ins, never auto-installed" {
    c_doc_has "$A/devcontainer/SKILL.md" "never required"
    c_doc_has "$DAILY" "never auto-install it for"
    c_doc_has "$DAILY_SPEC" "MUST NOT** auto-install it for everyone"
    # Dailybot reporting additionally requires authorization, not just presence.
    c_doc_has "$DAILY" "authenticated and reporting is authorized"
}

@test "every optional addon stays never-required; zero-optional conformance holds" {
    for f in devcontainer dailybot design-system; do
        c_doc_has "$A/$f/SKILL.md" "never required"
    done
    # dependency-upgrade phrases it with bold-split emphasis in both files.
    c_doc_has "$A/dependency-upgrade/SKILL.md" "required for a repo to be AI-first"
    c_doc_has "$A/dependency-upgrade/SPEC.md" "required for baseline AI-first conformance"
    c_doc_has "$SPEC" "a repo with zero optional addons is fully conformant"
    c_doc_has "$MECH" "zero optional addons"
    c_doc_has "$ONBOARD" "fully conformant with zero optional addons"
}

@test "Phase 7b wording matches the matrix (no blanket explicit-opt-in claim)" {
    run grep -F 'offer each as an **explicit opt-in** step' "$ONBOARD"
    [ "$status" -ne 0 ]
    c_doc_has "$ONBOARD" "Three are **explicit opt-ins**"
    c_doc_has "$ONBOARD" "The fourth, **dependency upgrade**, is"
}

@test "the design-system exclusivity note acknowledges the near-default tier" {
    run grep -F 'only automatically installed baseline addon' "$A/design-system/SKILL.md"
    [ "$status" -ne 0 ]
    c_doc_has "$A/design-system/SKILL.md" "installs inert under the onboarding consent"
    c_doc_has "$A/design-system/SKILL.md" "neither applies a design profile"
}
