#!/usr/bin/env bats
# Contract tests for the v6-aware onboarding guidance (DWP v6 campaign,
# task 19): bounded-autonomy records taught by a trigger-gated companion,
# never by growing the v5 entry bundle. These pins are the STATIC
# contract — presence, triggers, vocabulary sync, routing and honesty
# wording. They are not evidence that any model performed an onboarding;
# behavioral onboarding evidence belongs to the recorded campaigns and is
# claimed nowhere here.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    V6="$SK/onboard/v6.md"
    ON="$SK/onboard/SKILL.md"
    WP="$SK/shared/working-principles.md"
    FIX="$REPO_ROOT/tests/evaluation/v6/fixtures"
}

@test "the v6 guidance ships and is gated by a literal trigger in both surfaces" {
    [ -s "$V6" ]
    # Shared-resources tier entry carries the literal only-when form.
    section="$(sed -n '/^## Shared resources/,/^## [A-Z]/p' "$ON")"
    printf '%s' "$section" | grep -q 'v6\.md'
    printf '%s' "$section" | grep -qF 'read only when the trigger fires'
    # The companion restates its own trigger and the activation rule.
    grep -qF 'only when' "$V6"
    doc_has "$V6" "pack's line is 6+ or the developer explicitly requested"
    # Phase 2c exists, is v6-only, and skips cleanly for v5-only repos.
    doc_has "$ON" "Phase 2c — Bounded-autonomy records (v6 repositories only)"
    doc_has "$ON" "A v5-only repository skips this phase entirely"
}

@test "the capability guidance is the closed set resources.py negotiates" {
    # Every ability key the shipped negotiator accepts appears in the
    # guidance; the guidance invents none (the count check below pins
    # the closed set from the runtime, not from this file).
    while IFS= read -r ability; do
        grep -qF "$ability" "$V6" || {
            echo "ability missing from the guidance: $ability"; return 1
        }
    done < <(grep -oE "'(stop_agent|meter_spend|meter_tokens|meter_wall_clock|cancel_children|model_routing|subagents|telemetry)'" \
                 "$SK/shared/resources.py" | tr -d "'" | sort -u)
    [ "$(grep -oE "'(stop_agent|meter_spend|meter_tokens|meter_wall_clock|cancel_children|model_routing|subagents|telemetry)'" \
          "$SK/shared/resources.py" | tr -d "'" | sort -u | wc -l | tr -d ' ')" -eq 8 ]
    doc_has "$V6" 'An unstated ability is `false`'
    doc_has "$V6" 'advisory, not enforced'
    doc_has "$V6" 'opt-in only'
    doc_has "$V6" 'supported posture'

}

@test "authority, mapping and context records are honest, not boilerplate" {
    doc_has "$V6" 'never boilerplate'
    doc_has "$V6" 'an invented or aspirational command'
    doc_has "$V6" 'unverified against the repo'
    doc_has "$V6" 'must not undo that by'
    # Authority records the v6 mechanisms and the human checkpoints.
    grep -qF 'plan_authorship' "$V6"
    grep -qF 'pre_authorization' "$V6"
}

@test "upgrade scenarios: reconcile, never re-onboard; migration is explicit" {
    doc_has "$V6" 'reconcile — never re-onboard from scratch'
    doc_has "$V6" 'keep their recorded lifecycle'
    grep -qF 'migrate_v6.py' "$V6"
    doc_has "$V6" 'preview first'
    doc_has "$V6" 'never a silent conversion'
    doc_has "$V6" 'no diff'

}

@test "the mapping procedure cites the fixture families' real commands" {
    # The three campaign families each record a real, runnable check;
    # v6 guidance maps outcomes onto exactly this class of command.
    doc_has "$FIX/astro/README.md" 'pnpm run check'
    doc_has "$FIX/service/README.md" 'python3 -m unittest discover'
    doc_has "$FIX/legacy/README.md" 'run-checks.sh'
    doc_has "$V6" "the repo's own commands"
}

@test "working principles extend without replacing the ten behaviors" {
    grep -qF '## Bounded-autonomy records (v6 repositories)' "$WP"
    grep -qF 'onboard/v6.md' "$WP"
    doc_has "$WP" 'The ten behaviors above are unchanged by any of this'
    doc_has "$WP" 'A v5-only repository gets none of these sections'

}

@test "a v5-only repo pays nothing: the entry set stays flat, the path is gated" {
    run bash "$REPO_ROOT/tests/efficiency/measure-instruction-load.sh" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    # The compulsory set carries no v6 file.
    line="$(printf '%s' "$output" | awk '/^onboard /{print}')"
    [ -n "$line" ]
    case "$line" in
        *v6.md*) echo "v6.md leaked into the compulsory set: $line"; return 1 ;;
    esac
    # The named path exists, its entry column equals the compulsory set,
    # and the gated path is larger than the entry.
    # The path table's row has a numeric entry column; the phase-trigger
    # rows below it share the id prefix, so anchor on the number.
    entry="$(printf '%s' "$output" | awk '/^onboard-v6[[:space:]]+[0-9]+[[:space:]]/{print $2}')"
    path="$(printf '%s' "$output" | awk '/^onboard-v6[[:space:]]+[0-9]+[[:space:]]/{print $3}')"
    [ -n "$entry" ] && [ -n "$path" ]
    [ "$path" -gt "$entry" ]
    comp="$(printf '%s' "$line" | sed 's/.*bytes.*<- //')"
    [ "$(printf '%s' "$comp" | wc -w)" -eq 4 ]
}

@test "the guidance is registered across spec, testing guide and pack guide" {
    grep -qF '## 10. Onboarding guidance' "$SK/spec/V6_LIFECYCLE.md"
    grep -qF 'onboard/v6.md' "$SK/spec/V6_LIFECYCLE.md"
    grep -q 'v6 onboarding' "$REPO_ROOT/docs/TESTING_GUIDE.md"
    grep -qF 'onboard/v6.md' "$SK/guide/GUIDE.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
