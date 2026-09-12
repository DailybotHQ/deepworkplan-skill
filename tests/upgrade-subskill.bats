#!/usr/bin/env bash
# Contract tests for the /dwp-upgrade sub-skill (task 16): check → consent →
# upgrade, with the documented channel, explicit acceptance, adaptations
# surfaced before any overwrite, .dwp/ never migrated, offline-safe, and
# onboarding re-executed as a fresh init.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    UP="$SK/upgrade/SKILL.md"
    ROUTER="$SK/SKILL.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
up_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "frontmatter validates and the sub-skill is user-invocable" {
    grep -q '^name: deepworkplan-upgrade$' "$UP"
    grep -q '^user-invocable: true$' "$UP"
    grep -q 'documentation_url: https://deepworkplan.com' "$UP"
    run python3 "$REPO_ROOT/scripts/validate-frontmatter.py"
    [ "$status" -eq 0 ]
    # The new file rides the pack version; the bot owns the number.
    grep -q '^version: "4.0.3"$' "$UP"
    grep -q '^version: "4.0.3"$' "$ROUTER"
}

@test "the router routes to it and stays inside the pack boundary" {
    grep -q '| "upgrade DWP", "update the skill", "is there a newer version?", "/dwp-upgrade" | \*\*Upgrade\*\* → read \[`upgrade/SKILL.md`\](upgrade/SKILL.md) |' "$ROUTER"
    # Never reach outside skills/deepworkplan at runtime.
    run bash -c "grep -n '\.\./\.\.' '$UP'"
    [ "$status" -ne 0 ]
}

@test "check phase is read-only, versioned via the documented channel, offline-safe" {
    up_has "$UP" "Read \`version:\` from the installed pack's \`SKILL.md\` frontmatter — read it, never edit it"
    up_has "$UP" "git ls-remote --tags https://github.com/DailybotHQ/deepworkplan-skill.git"
    up_has "$UP" "exit cleanly"
    up_has "$UP" "no partial state, no error cascade, no retry loop"
    # The changelog location is reported.
    up_has "$UP" "CHANGELOG.md"
}

@test "consent phase — explicit acceptance, adaptations diffed before overwrite" {
    up_has "$UP" "Only an explicit acceptance starts Phase 3"
    up_has "$UP" "Surface local adaptations before overwriting anything"
    up_has "$UP" "diff -r --brief .agents/skills/deepworkplan"
    up_has "$UP" "local adaptations"
    up_has "$UP" "re-apply the adaptation on top of the new version, or take the new version as-is"
}

@test "upgrade phase uses the documented exact-tag install and verifies it" {
    up_has "$UP" "npx --yes skills add DailybotHQ/deepworkplan-skill@vX.Y.Z --skill deepworkplan --force -y"
    up_has "$UP" "installed \`version:\` now equals the accepted tag"
    up_has "$UP" "a mismatch aborts the phase"
    up_has "$UP" "openclaw skills update deepworkplan"
}

@test "re-onboarding runs as a fresh init, not the Phase 0 targeted branch" {
    up_has "$UP" "https://deepworkplan.com/init.md"
    up_has "$UP" "not** its Phase 0 targeted-upgrade branch"
    up_has "$UP" "non-destructive, reconcile-don't-overwrite, idempotent on a second run"
}

@test ".dwp/ is never migrated and plans keep their authored standard" {
    up_has "$UP" "An upgrade never touches \`.dwp/\`"
    up_has "$UP" "No plan, state file, gate record or evidence file is migrated, rewritten or invalidated by an upgrade"
    up_has "$UP" "an old plan declaring 2.x stays valid as historical"
    up_has "$UP" "separate, explicit \`refine migrate\` decision"
}

@test "the provenance line is re-stamped with the upgrade variant" {
    up_has "$UP" "upgraded YYYY-MM-DD; skill x.y.z"
    up_has "$UP" "Never edit the skill's own \`version:\` fields or \`CHANGELOG.md\`"
}

@test "the guide mentions the upgrade flow" {
    up_has "$SK/guide/GUIDE.md" "**Upgrade** the installed skill"
    up_has "$SK/guide/GUIDE.md" "download needs explicit acceptance, \`.dwp/\` is never migrated"
}

@test "progressive loading — no other flow reads upgrade/SKILL.md" {
    # create/execute/resume/onboard/refine must not load the new file; only
    # the router names it.
    run bash -c "grep -rn 'upgrade/SKILL.md' '$SK' --include='SKILL.md' | grep -v '^\$SK/upgrade/SKILL.md' | grep -vE 'SKILL.md:[0-9]+:.*(onboard|create|execute|resume|refine|status)/SKILL.md'"
    [ "$status" -eq 0 ]
    run bash -c "grep -rln 'upgrade/SKILL' '$SK/create' '$SK/execute' '$SK/resume' '$SK/refine' '$SK/status' 2>/dev/null"
    [ "$status" -ne 0 ]
}
