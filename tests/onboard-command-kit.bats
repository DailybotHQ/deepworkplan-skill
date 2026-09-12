#!/usr/bin/env bash
# Contract tests for the onboarding command kit (findings F3-1, F4-1, F3-4 of
# PLAN_v5_phase2_validation): every dwp-* command Phase 6 names must ship a
# ready delegator template (the released v5.0.0 kit shipped five templates for
# six named commands and none for /dwp-upgrade, so a freshly onboarded repo
# had no command-file path to the upgrade flow), Phase 8's checklist must
# require the same set, and the Phase 6 existing-repo note must cover the
# zero-loss conversion of tool-created symlink-only directories.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    ONBOARD="$SK/onboard/SKILL.md"
    TPL="$SK/onboard/command-templates"
}

@test "every dwp-* command Phase 6 names ships a delegator template" {
    # Extract the kit enumeration itself (the parenthesized list after "short
    # DWP commands"), not every dwp- token in the file — prose mentions like
    # `dwp-*` or shared/dwp-paths.md are not commands.
    flat="$(tr '\n' ' ' < "$ONBOARD" | tr -s ' ')"
    names="$(printf '%s\n' "$flat" \
        | sed 's/.*short DWP commands (\([^)]*\)).*/\1/' \
        | tr -d '\`,' | tr ' ' '\n' | grep -v '^$' | sort -u)"
    [ -n "$names" ]
    n=0
    for c in $names; do
        [ -f "$TPL/$c.md" ]
        n=$((n + 1))
    done
    [ "$n" -ge 7 ]
}

@test "dwp-verify.md template exists, is thin and routes to the verify sub-skill" {
    [ -f "$TPL/dwp-verify.md" ]
    lines="$(wc -l < "$TPL/dwp-verify.md")"
    [ "$lines" -le 40 ]
    grep -q '^description: ' "$TPL/dwp-verify.md"
    grep -q '\*\*verify\*\* sub-skill' "$TPL/dwp-verify.md"
    grep -q '<skill-path>/deepworkplan/verify/SKILL.md' "$TPL/dwp-verify.md"
    grep -qi 'read-only' "$TPL/dwp-verify.md"
}

@test "dwp-upgrade.md template exists, is thin and routes to the upgrade sub-skill" {
    [ -f "$TPL/dwp-upgrade.md" ]
    lines="$(wc -l < "$TPL/dwp-upgrade.md")"
    [ "$lines" -le 40 ]
    grep -q '^description: ' "$TPL/dwp-upgrade.md"
    grep -q '\*\*upgrade\*\* sub-skill' "$TPL/dwp-upgrade.md"
    grep -q '<skill-path>/deepworkplan/upgrade/SKILL.md' "$TPL/dwp-upgrade.md"
    grep -qi 'explicit' "$TPL/dwp-upgrade.md"
}

@test "Phase 6 names dwp-upgrade among the kit commands and Phase 8 checks it" {
    grep -q 'dwp-upgrade' "$ONBOARD"
    # Phase 8's self-check must require the full set including dwp-upgrade.
    phase8="$(sed -n '/## Phase 8/,$p' "$ONBOARD")"
    echo "$phase8" | grep -q 'dwp-upgrade'
    # And the kit count must match reality, not a stale "six".
    echo "$phase8" | grep -q 'seven `dwp-\*` commands'
}

@test "Phase 6 existing-repo note covers zero-loss conversion of symlink-only tool dirs" {
    # F3-4: a tool-created .claude/ holding only symlinks into .agents/ converts
    # to the canonical root symlink — that is reconciliation, not deletion.
    tr '\n' ' ' < "$ONBOARD" | tr -s ' ' | grep -qF 'only content is symlinks'
    tr '\n' ' ' < "$ONBOARD" | tr -s ' ' | grep -qF 'zero-loss'
}
