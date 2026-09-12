#!/usr/bin/env bats
# Contract tests for the execute flow's tiered read path — the context diet
# that answers round-1's central counter-finding (arm B loaded 11 instruction
# files / 124,703 B, ~6.4x v2's single 19,618 B file, because companions were
# marked essential and read upfront).
#
# The contract under test (execute/SKILL.md "Shared resources"):
#   - essential-now is the router + the execute contract itself; the only
#     t0 action besides reading this file is RUNNING context.sh (a script,
#     not a doc) — no guide/spec/shared .md companion is compulsory at t0;
#   - every companion is trigger-conditional and its entry carries a literal
#     "only when" trigger sentence naming the moment it loads;
#   - a never-by-default tier forbids speculative reads and links nothing
#     (a linked file there would silently count as compulsory again);
#   - no capability is lost: the Final Review contracts, the state-layer
#     needs and the local-review pass all keep their triggers and their
#     inline operative rules;
#   - the declared execute bundle (measure-instruction-load.sh) stays
#     materially below v5.1.0's 85,016 B and v2.17.1's 142,506 B.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    EX="$REPO_ROOT/skills/deepworkplan/execute/SKILL.md"
    SECTION="$(sed -n '/^## Shared resources/,/^## Parameter Support/p' "$EX")"
}

@test "shared resources names the three tiers and the not-upfront rule" {
    doc_has "$EX" "## Shared resources (read at their moment, not upfront)"
    doc_has "$EX" "**Essential now (before the first task):**"
    doc_has "$EX" "**Conditional — read only when the trigger fires:**"
    doc_has "$EX" "**Never by default:**"
}

@test "the essential-now tier runs context.sh and links no companion doc" {
    local essential
    essential="$(printf '%s' "$SECTION" | sed -n '/^- \*\*Essential now/,/^- \*\*Conditional/p' | sed '$d')"
    [ -n "$essential" ]
    printf '%s' "$essential" | grep -qF 'shared/context.sh'
    doc_has "$EX" "That is the whole t0 set"
    # No .md companion may be linked as compulsory: the declared bundle is
    # the router + execute/SKILL.md, nothing else.
    if printf '%s' "$essential" | grep -qE '\]\(\.\./[^)]*\.md\)'; then
        echo "essential tier links a companion doc:"
        printf '%s\n' "$essential" | grep -E '\]\(\.\./[^)]*\.md\)'
        return 1
    fi
}

@test "every conditional entry carries a literal only-when trigger" {
    local cond offenders
    cond="$(printf '%s' "$SECTION" | sed -n '/^- \*\*Conditional/,/^- \*\*Never/p' | sed '$d')"
    [ -n "$cond" ]
    # Each sub-bullet (with its wrapped continuation lines) must contain
    # "only when" — the trigger is a sentence, not a label.
    offenders="$(printf '%s' "$cond" | awk '
        /^- /{next}
        /^  - /{if (b != "" && b !~ /only +when/) print b; b = $0; next}
        {gsub(/ +/, " "); b = b " " $0}
        END{if (b != "" && b !~ /only +when/) print b}')"
    if [ -n "$offenders" ]; then
        echo "conditional entries without a literal trigger:"
        printf '%s\n' "$offenders"
        return 1
    fi
}

@test "the key companions keep their named moments" {
    doc_has "$EX" 'read only when the plan README declares `Plan Format: Lite`'
    doc_has "$EX" 'when `state.json` and the README disagree (markdown wins — regenerate)'
    doc_has "$EX" "read §6.1 only when the Final Review task begins"
    doc_has "$EX" "read only when judging a task's test or security discipline"
    doc_has "$EX" "read only when a resume scenario arises mid-execution"
    doc_has "$EX" "read only when adapting a pack example"
    doc_has "$EX" "read only when a plan folder cannot be located"
    doc_has "$EX" "read only when something is already wrong"
    doc_has "$EX" "read only when Step 2.1 detects an orchestrator plan"
    doc_has "$EX" "read only when Step 2.2 finds a Team Agents Configuration"
    doc_has "$EX" "read only when the Final Review runs its required local-review pass"
    doc_has "$EX" "read only when a task's gate must be widened or derived"
}

@test "the never-by-default tier forbids speculative reads and links nothing" {
    local never
    never="$(printf '%s' "$SECTION" | sed -n '/^- \*\*Never by default/,$p')"
    [ -n "$never" ]
    printf '%s' "$never" | grep -qF 'not defensively, not "to be safe"'
    # A markdown link here would be counted as a compulsory read by
    # measure-instruction-load.sh — the tier must stay link-free.
    if printf '%s' "$never" | grep -q '](' ; then
        echo "never-by-default tier contains a markdown link:"
        printf '%s\n' "$never" | grep ']('
        return 1
    fi
}

@test "no capability lost: the Final Review and state-layer needs stay inline" {
    # Final Review contracts (task 4's sweep included) and the reviewer pass.
    doc_has "$EX" "load it even if the reviewer is not yet installed"
    doc_has "$EX" "(d) Documentation reconciliation:"
    # State layer: bookkeeping order, closed gate record, updater path.
    doc_has "$EX" "shared/update-state.py"
    doc_has "$EX" "whole-file rewrite"
    doc_has "$EX" 'log → README → PROGRESS → commit → `state.json`'
}

@test "declared execute bundle is materially below v5.1.0 and v2.17.1" {
    # v5.1.0 declared 85,016 B; v2.17.1 declared 142,506 B. The bound has
    # headroom below the v5.1.0 number so an accidental re-added essential
    # companion (any guide/spec .md) trips it.
    run bash "$REPO_ROOT/tests/efficiency/measure-instruction-load.sh" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    bytes="$(printf '%s' "$output" | awk '/^execute /{print $2}')"
    [ -n "$bytes" ]
    [ "$bytes" -le 55000 ]
}

# Sentence-level assertion that tolerates the source file's own line wrapping:
# normalize to one line, then match the phrase.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
