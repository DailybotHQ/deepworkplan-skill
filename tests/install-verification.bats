#!/usr/bin/env bats
# Contract tests for the skills-CLI install defenses (round-1 defects 1–2,
# both upstream, both reproduced in the benchmark install ledgers):
#   - defect 1: the `@tag` pin is display-only — `skills add <repo>@<tag>`
#     prints the requested tag while delivering the latest bytes (arm A:
#     requested @v2.17.1, `diff -rq` proved the install identical to the
#     v5.0.0 export);
#   - defect 2: a parallel-mkdir race reports "Done!"/exit 0 with no content
#     placed (five false successes across the arms; pre-creating the target
#     dir fixed every occurrence).
#
# Until both are fixed upstream, the skill defends its own users at every
# install site: pre-create the target, verify what landed (installed
# `version:` == requested tag AND directory non-empty), retry once, then
# fall back to the byte-exact `git archive` install — never proceed silently.
# This file pins that contract in the three install surfaces and in the
# troubleshooting entry that documents both defects.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    ONBOARD="$REPO_ROOT/skills/deepworkplan/onboard/SKILL.md"
    IV="$REPO_ROOT/skills/deepworkplan/shared/install-verification.md"
    UPGRADE="$REPO_ROOT/skills/deepworkplan/upgrade/SKILL.md"
    TROUBLE="$REPO_ROOT/skills/deepworkplan/shared/troubleshooting.md"
}

@test "onboard Phase 7 carries the mandatory install-verification contract" {
    # The mandate and the site-specific anchors stay at the install site; the
    # step-by-step procedure lives in shared/install-verification.md (the
    # phase-local contract, read at Phase 7/7a time — task 11's tiering).
    doc_has "$ONBOARD" "Verify every skills-CLI install — mandatory"
    doc_has "$ONBOARD" "an \`@tag\` pin can be display-only"
    doc_has "$ONBOARD" "install-verification"
    doc_has "$ONBOARD" "never proceed silently on a mismatched or empty install"
    doc_has "$IV" 'frontmatter `version:`'
    doc_has "$IV" "equals the requested tag"
    doc_has "$IV" "directory is non-empty"
    doc_has "$IV" "retry the identical command once"
    doc_has "$IV" "git archive <tag> skills/deepworkplan"
    doc_has "$IV" "diff -rq"
    doc_has "$IV" "never proceed silently on a mismatched or empty install"
}

@test "onboard Phase 7 pre-creates the target before every CLI call" {
    # The documented race workaround must sit at the install site itself.
    doc_has "$ONBOARD" "Pre-create the target"
    doc_has "$ONBOARD" '.agents/skills/deepworkplan/'
    doc_has "$ONBOARD" "documented race workaround"
}

@test "onboard Phase 7a extends the contract to the reviewer install" {
    doc_has "$ONBOARD" "applies verbatim to the reviewer's"
    doc_has "$ONBOARD" '.agents/skills/ai-diff-reviewer/'
    doc_has "$ONBOARD" "equals the pinned"
}

@test "upgrade Phase 3 verifies, aborts and falls back the same way" {
    doc_has "$UPGRADE" "install-verification contract"
    doc_has "$UPGRADE" 'pre-create `.agents/skills/deepworkplan/` before the call'
    doc_has "$UPGRADE" "equals the accepted tag"
    doc_has "$UPGRADE" "directory is non-empty"
    doc_has "$UPGRADE" "aborts the phase with the difference stated"
    doc_has "$UPGRADE" "git archive <tag>"
    doc_has "$UPGRADE" "never continue on a wrong or empty install"
}

@test "troubleshooting documents both defects with symptoms and remedies" {
    doc_has "$TROUBLE" "## 2. A skills-CLI install delivered the wrong tag or no content"
    doc_has "$TROUBLE" "display-only"
    doc_has "$TROUBLE" "parallel-mkdir race"
    doc_has "$TROUBLE" "pre-create the target directory"
    doc_has "$TROUBLE" "retry the identical command once"
    doc_has "$TROUBLE" "git archive <tag> skills/<name>"
    doc_has "$TROUBLE" "diff -rq"
    doc_has "$TROUBLE" "round-1 benchmark"
}

# Sentence-level assertion that tolerates the source file's own line wrapping:
# normalize to one line, then match the phrase.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
