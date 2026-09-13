#!/usr/bin/env bash
# Contract tests for the AGENTS.md lean-index budget + feature-tier docs
# architecture (spec/DOCUMENTATION_STANDARD.md §2.1.1 + §4.1, onboard
# Phases 1/3/5/8, verify/SKILL.md documentation, and the mechanical checks in
# verify/conformance.sh's check_docs_architecture).
#
# The unit of the guarantee: what the harness generates stays within the
# 150–500-line budget by moving detail into docs/ and linking it (an existing
# handwritten overweight AGENTS.md gets a migration proposal, never a silent
# rewrite); major feature/capability areas get their own docs/ next to their
# code, decided from triggers reasoned per repo and recorded in the onboarding
# docs registry; the checker verifies both where mechanically knowable, with
# honest severities (budget = SHOULD advisory, dead index link = MUST failure,
# registry = the repo's own recorded judgment).
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    CONFORMANCE_SH="$REPO_ROOT/skills/deepworkplan/verify/conformance.sh"
    TMPDIR_TEST="$(mktemp -d)"
    cd "$TMPDIR_TEST"
}

teardown() {
    cd "$BATS_TEST_DIRNAME"
    rm -rf "$TMPDIR_TEST"
}

# ------------------------------------------------------------- prose contracts

@test "standard 2.1.1 enforces the lean-index budget on what the harness generates" {
    local std="$REPO_ROOT/skills/deepworkplan/spec/DOCUMENTATION_STANDARD.md"
    doc_has "$std" "### 2.1.1. Budget enforcement — the lean index is a guarantee, not a hope"
    doc_has "$std" "MUST** stay within the budget"
    doc_has "$std" "MUST** link every doc that received displaced content"
    doc_has "$std" "never silently rewritten**: onboarding and upgrade report the overweight with a concrete migration proposal"
    doc_has "$std" "detail moves, it is not deleted"
    doc_has "$std" 'A conformance checker treats an over-budget `AGENTS.md` as an advisory'
}

@test "standard 4.1 defines the feature tier with testable triggers" {
    local std="$REPO_ROOT/skills/deepworkplan/spec/DOCUMENTATION_STANDARD.md"
    doc_has "$std" '### 4.1. The feature tier — per-feature `docs/` for major capability areas'
    doc_has "$std" "spans 2+ major modules"
    doc_has "$std" "owns a sub-app or subsystem directory"
    doc_has "$std" "carries its own contracts"
    doc_has "$std" "heuristics, not bureaucracy"
    doc_has "$std" "An area deliberately left undocumented carries a recorded reason — a decision, not an oversight"
    doc_has "$std" "never copy another repo's folder layout"
    doc_has "$std" "The feature tier complements the per-module tier, never replaces it"
}

@test "onboard Phase 1 detects feature areas and records the docs registry" {
    local on="$REPO_ROOT/skills/deepworkplan/onboard/SKILL.md"
    doc_has "$on" "Feature areas (the feature tier)"
    doc_has "$on" "using the triggers of"
    doc_has "$on" "Heuristics, not bureaucracy — judge per repo and record the trigger with"
    doc_has "$on" "machine-readable docs registry"
    doc_has "$on" "feature-area: <path> (trigger: …)"
    doc_has "$on" "so Phase 5 and the conformance checker"
    doc_has "$on" "(no docs — <reason>)"
}

@test "onboard Phase 3 enforces the budget and the migration proposal" {
    local on="$REPO_ROOT/skills/deepworkplan/onboard/SKILL.md"
    doc_has "$on" "Budget — the lean index is enforced, not hoped for (§2.1.1)"
    doc_has "$on" "MUST stay within the 150–500-line budget"
    doc_has "$on" "MUST link every doc that received displaced content, so nothing"
    doc_has "$on" "never silently rewritten**: report the overweight with a concrete migration proposal"
}

@test "onboard Phase 5 and Phase 8 carry the feature tier and lean-index checks" {
    local on="$REPO_ROOT/skills/deepworkplan/onboard/SKILL.md"
    doc_has "$on" "For each feature area the RECON registry recorded as"
    doc_has "$on" "The feature tier sits above, never instead of, the"
    doc_has "$on" "lean index within the"
    doc_has "$on" 'every relative `.md` link in its index resolves'
    doc_has "$on" "feature area the RECON registry recorded as major has"
}

@test "verify SKILL documents the docs-architecture checks and their severities" {
    local vf="$REPO_ROOT/skills/deepworkplan/verify/SKILL.md"
    doc_has "$vf" "verifies the documentation architecture where it is mechanically knowable"
    doc_has "$vf" "over the 500-line lean-index budget is reported as an advisory"
    doc_has "$vf" "index link to a file that does not exist **fails**"
    doc_has "$vf" 'registered module without its `README.md` **fails**'
    doc_has "$vf" "the registry is the repository's own recorded judgment"
}

# ------------------------------------------------- conformance.sh behavior

# Minimal conformant repo fixture (same shape as conformance-sh.bats).
make_conformant_repo() {
    git init -q .
    printf '# AGENTS.md\n\n## Quick Commands\n\n- `make test`\n' > AGENTS.md
    ln -s AGENTS.md CLAUDE.md
    mkdir -p .agents/agents .agents/commands .agents/skills .agents/docs docs
    printf '# Security\n\nNo secrets in this fixture.\n' > docs/SECURITY.md
    ln -s .agents .claude
    ln -s .agents .cursor
    mkdir -p .dwp/plans
    echo '.dwp/' > .gitignore
}

@test "lean fixture passes the budget and index-link checks" {
    make_conformant_repo
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "AGENTS.md within the lean-index budget" ]]
    [[ "$output" =~ "AGENTS.md index .md links resolve" ]]
}

@test "overweight AGENTS.md is a SHOULD advisory, not a failure" {
    make_conformant_repo
    local i
    for i in $(seq 1 520); do printf 'filler line %s\n' "$i"; done >> AGENTS.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "over the 500-line budget" ]]
    [[ "$output" =~ "Verdict: CONFORMANT" ]]
}

@test "dead relative .md index link fails (DOCUMENTATION_STANDARD 2.2)" {
    make_conformant_repo
    printf '\nSee [the guide](docs/GONE.md).\n' >> AGENTS.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
    [[ "$output" =~ "dead index link: docs/GONE.md" ]]
    [[ "$output" =~ "do not exist (DOCUMENTATION_STANDARD §2.2 MUST NOT)" ]]
    [[ "$output" =~ "NOT CONFORMANT" ]]
}

@test "links inside fenced code blocks are not read as the index" {
    make_conformant_repo
    printf '\n```\n[example](docs/NEVER_CHECKED.md)\n```\n' >> AGENTS.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "AGENTS.md index .md links resolve" ]]
}

@test "registry module without README.md fails" {
    make_conformant_repo
    mkdir -p app/api .dwp/onboard
    printf '# docs registry\nmodule: app/api\n' > .dwp/onboard/RECON.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
    [[ "$output" =~ "docs registry: module 'app/api' has no README.md" ]]
}

@test "registry module with README passes; feature area without docs/ is advisory" {
    make_conformant_repo
    mkdir -p app/api .dwp/onboard
    printf '# module\n' > app/api/README.md
    mkdir -p app/domain
    printf '# docs registry\nmodule: app/api\nfeature-area: app/domain (trigger: spans 2+ modules)\n' > .dwp/onboard/RECON.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "docs registry: feature area 'app/domain' recorded major has no docs/" ]]
    [[ "$output" =~ "Verdict: CONFORMANT" ]]
}

@test "stale registry paths warn and the no-docs marker is respected" {
    make_conformant_repo
    mkdir -p .dwp/onboard
    printf '# docs registry\nmodule: app/gone\nfeature-area: mailtron (trigger: sub-app directory; no docs — kept in root docs/)\n' > .dwp/onboard/RECON.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "stale onboarding registry entry" ]]
    [[ ! "$output" =~ "mailtron" ]]
}

@test "no registry means no registry findings (nothing false is reported)" {
    make_conformant_repo
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "docs registry" ]]
}

# Sentence-level assertion that tolerates the source file's own line wrapping:
# normalize to one line, then match the phrase.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
