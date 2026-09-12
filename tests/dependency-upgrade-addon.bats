#!/usr/bin/env bash
# Contract tests for the dependency-upgrade addon "near-default" tier
# (user direction 2026-09-12) across its surfaces: the addon's SKILL.md +
# SPEC.md + templates, spec/ADDONS.md (§4 + §6.3), addons/README.md,
# onboard/SKILL.md, onboard/addons.md.
#
# The policy: the offer is mandatory for every repo with declared dependencies
# (any manifest or lockfile); the /lib-upgrade delegator installs under the
# Phase 0 onboarding consent UNLESS EXPLICITLY DECLINED; the delegator is
# inert - installing it runs no upgrade, and an upgrade always runs as
# explicit, gated work. A decline leaves a baseline-conformant repo with no
# command. The execution-safety MUSTs (snapshots, batched tiers, real gate,
# revert, no auto-commit) stay pinned alongside.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    ADDON="$REPO_ROOT/skills/deepworkplan/addons/dependency-upgrade"
    SPEC="$REPO_ROOT/skills/deepworkplan/spec/ADDONS.md"
    README="$REPO_ROOT/skills/deepworkplan/addons/README.md"
    ONBOARD_SKILL="$REPO_ROOT/skills/deepworkplan/onboard/SKILL.md"
    ONBOARD="$REPO_ROOT/skills/deepworkplan/onboard/addons.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
dep_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "the addon is near-default: offered for every repo with declared dependencies" {
    dep_doc_has "$ADDON/SKILL.md" "offered for every repo with declared dependencies"
    grep -qF "methodology's **third addon**" "$ADDON/SKILL.md"
    dep_doc_has "$ADDON/SPEC.md" "offered for every repo with declared dependencies, its delegator installed under the onboarding consent unless explicitly declined"
    dep_doc_has "$SPEC" "offer the addon for every repo with"
    dep_doc_has "$ONBOARD" "any manifest or lockfile, any ecosystem"
    dep_doc_has "$ONBOARD" "near-default"
    # The onboard table row carries the same tier.
    grep -F '| **Dependency upgrade** |' "$ONBOARD" | grep -qF 'declared dependencies'
    grep -F '| **Dependency upgrade** |' "$ONBOARD" | grep -qF 'explicitly declined'
}

@test "the delegator installs under the onboarding consent unless explicitly declined" {
    dep_doc_has "$ADDON/SPEC.md" "unless the developer explicitly declines"
    dep_doc_has "$ADDON/SPEC.md" "a prior explicit acceptance is never re-asked"
    dep_doc_has "$SPEC" "delegator installs under that same onboarding consent"
    dep_doc_has "$ONBOARD" "unless the developer explicitly declines"
    dep_doc_has "$ADDON/templates/lib-upgrade-command.md" "under the Phase 0 onboarding consent"
    dep_doc_has "$ADDON/templates/lib-upgrade-command.md" "unless the addon is explicitly declined"
}

@test "installing the delegator is inert - no upgrade runs at install time" {
    dep_doc_has "$ADDON/SKILL.md" "Installing the delegator changes no dependencies"
    dep_doc_has "$ADDON/SKILL.md" "an upgrade itself always runs as explicit, gated work"
    dep_doc_has "$ADDON/SPEC.md" "run any upgrade at install time"
    dep_doc_has "$ADDON/SPEC.md" "Installing the delegator only adds the"
    dep_doc_has "$SPEC" "while every upgrade stays explicit, gated work"
    dep_doc_has "$SPEC" "installing it runs no upgrade"
    dep_doc_has "$README" "no upgrade ever runs from an install"
    dep_doc_has "$ONBOARD" "an install runs no upgrade"
    dep_doc_has "$ONBOARD" "an upgrade always starts from an explicit request"
    dep_doc_has "$ONBOARD_SKILL" "no upgrade ever runs from an install"
}

@test "a decline is safe and the old lockfile-only tier wording does not return" {
    dep_doc_has "$ADDON/SPEC.md" "a decline leaves a baseline-conformant repo with no command"
    dep_doc_has "$SPEC" "command and leaves a baseline-conformant repo"
    dep_doc_has "$ONBOARD" "a decline leaves a baseline-conformant repo with no command"
    # The old signal-gated tier ("lockfile + dependency-heavy stack", "never
    # auto-install for everyone") must not survive on this addon's surfaces.
    run grep -rn 'third opt-in addon' "$ADDON"
    [ "$status" -ne 0 ]
    run grep -rn -F 'Opt-in, never required' "$ADDON/SKILL.md"
    [ "$status" -ne 0 ]
    run bash -c "grep -F '| **Dependency upgrade** |' '$ONBOARD' | grep -F 'dependency-heavy'"
    [ "$status" -ne 0 ]
    run bash -c "grep -F '| **Dependency upgrade** |' '$ONBOARD' | grep -F 'never auto-install'"
    [ "$status" -ne 0 ]
    run grep -F 'only when the addon is accepted' "$ADDON/templates/lib-upgrade-command.md"
    [ "$status" -ne 0 ]
}

@test "execution safety: snapshots, approved-set-only mutations, exact revert, bounded retries, no auto-commit" {
    dep_doc_has "$ADDON/SPEC.md" "capture a recoverable snapshot of owned files"
    dep_doc_has "$ADDON/SPEC.md" "restore the exact pre-batch snapshot, preserving earlier successful batches"
    dep_doc_has "$ADDON/SPEC.md" "is valid only when proven identical to that snapshot"
    dep_doc_has "$ADDON/SPEC.md" "block further batches"
    dep_doc_has "$ADDON/SKILL.md" "never use a broad latest/all-packages command"
    dep_doc_has "$ADDON/SKILL.md" "after two attempts without progress, stop blind retries"
    dep_doc_has "$ADDON/SKILL.md" "If restore or its gate fails, stop with the snapshot and blocker recorded"
    dep_doc_has "$ADDON/SKILL.md" "surface the diff and let the developer commit"
    dep_doc_has "$ADDON/SPEC.md" "surfaces the diff and lets the developer commit"
}

@test "risk-tiered order and major approval stay stated" {
    dep_doc_has "$ADDON/SKILL.md" "A reasonable order: patch batch"
    dep_doc_has "$ADDON/SPEC.md" "require explicit developer approval before inclusion"
    dep_doc_has "$ADDON/SPEC.md" "retry the batch one package at a time"
    dep_doc_has "$ADDON/SKILL.md" "A failing major is set aside, not forced"
}

@test "ecosystems.md revert rows carry the snapshot caveat" {
    dep_doc_has "$ADDON/templates/ecosystems.md" "pre-batch snapshot is proven identical to"
    dep_doc_has "$ADDON/templates/ecosystems.md" "restrict actual mutations to the batch's approved set"
    dep_doc_has "$ADDON/templates/ecosystems.md" "Revert from the recorded pre-batch snapshot"
}
