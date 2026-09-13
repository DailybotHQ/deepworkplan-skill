#!/usr/bin/env bats
# Contract tests for the resume flow's tiered read path — the context diet
# that answers round-1's resume counter-finding (declared resume bundle
# +106.2% vs v2.17.1: 38,186 -> 78,754 B at v5.0.0, 79,565 B at v5.1.0)
# caused by companions and the execution contract being read upfront,
# including a stale parenthetical that linked execution.md wholesale.
#
# The contract under test (resume/SKILL.md "Shared resources"):
#   - essential-now is the router + the resume contract itself; the only t0
#     action besides reading this file is RUNNING context.sh (a script, not
#     a doc) — no guide/spec/shared .md companion, and not even the execute
#     contract, is compulsory during assessment (Steps 1-4);
#   - every companion is trigger-conditional and its entry carries a literal
#     "only when" trigger sentence naming the moment it loads — execute/
#     SKILL.md loads when Step 5 resumes into the execution loop;
#   - a never-by-default tier forbids speculative reads and links nothing
#     (a linked file there would silently count as compulsory again);
#   - no capability is lost: the resume protocol (compact-index-first,
#     markdown-wins reconciliation, the interruption-boundary table,
#     takeover, the smoke test, the handoff artifact) stays inline;
#   - the declared resume bundle (measure-instruction-load.sh) stays
#     materially below v5.1.0's 79,565 B and v2.17.1's 38,186 B.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    RS="$REPO_ROOT/skills/deepworkplan/resume/SKILL.md"
    SECTION="$(sed -n '/^## Shared resources/,/^## Parameter Support/p' "$RS")"
}

@test "shared resources names the three tiers and the not-upfront rule" {
    doc_has "$RS" "## Shared resources (read at their moment, not upfront)"
    doc_has "$RS" "**Essential now (before the first task):**"
    doc_has "$RS" "**Conditional — read only when the trigger fires:**"
    doc_has "$RS" "**Never by default:**"
}

@test "the essential-now tier runs context.sh and links no companion doc" {
    local essential
    essential="$(printf '%s' "$SECTION" | sed -n '/^- \*\*Essential now/,/^- \*\*Conditional/p' | sed '$d')"
    [ -n "$essential" ]
    printf '%s' "$essential" | grep -qF 'shared/context.sh'
    doc_has "$RS" "That is the whole t0 set"
    # No .md companion may be linked as compulsory: the declared bundle is
    # the router + resume/SKILL.md, nothing else — the execute contract
    # included (it loads at its Step 5 moment below).
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
    doc_has "$RS" "read only when Step 5 resumes into the execution loop"
    doc_has "$RS" "its execution-time companions"
    doc_has "$RS" "a desync, a takeover, or a standard question needs the normative rule"
    doc_has "$RS" "read only when the interruption is unusual enough that the Step 2.5 boundary table does not classify it"
    doc_has "$RS" "read only when a plan folder cannot be located or the \`DWP_DIR\` override is in play"
    doc_has "$RS" "read only when something is already wrong"
    doc_has "$RS" "consult only when a need is not covered by a section named above"
}

@test "the never-by-default tier forbids speculative reads and links nothing" {
    local never
    never="$(printf '%s' "$SECTION" | sed -n '/^- \*\*Never by default/,$p')"
    [ -n "$never" ]
    printf '%s' "$never" | grep -qF 'not defensively, not "to be safe"'
    # The two files the stale v5.1.0 parenthetical pulled in wholesale are
    # explicitly disowned here, by name.
    printf '%s' "$never" | grep -qF 'are not resume reads'
    # A markdown link here would be counted as a compulsory read by
    # measure-instruction-load.sh — the tier must stay link-free.
    if printf '%s' "$never" | grep -q '](' ; then
        echo "never-by-default tier contains a markdown link:"
        printf '%s\n' "$never" | grep ']('
        return 1
    fi
}

@test "no capability lost: the resume protocol and handoff stay inline" {
    doc_has "$RS" 'NEVER redo `[x]` tasks'
    doc_has "$RS" 'NEVER skip `[ ]` tasks'
    doc_has "$RS" "compact index first"
    doc_has "$RS" "at its interruption boundary"
    doc_has "$RS" "Smoke-test before building"
    doc_has "$RS" "Takeover from another agent or model"
    doc_has "$RS" "only in a prior conversation"
    # The stale v5.1.0 parenthetical that linked execution.md wholesale in a
    # non-conditional bullet is gone.
    if doc_has "$RS" "none beyond what"; then
        echo "stale Guide-essential parenthetical is back:"
        grep -n "none beyond what" "$RS"
        return 1
    fi
}

@test "declared resume bundle is materially below v5.1.0 and v2.17.1" {
    # v5.1.0 declared 79,565 B; v2.17.1 declared 38,186 B. The bound keeps
    # the flow below v2's number even with drift, while tripping if a whole
    # companion (execute/SKILL.md ~36.7 KB or execution.md ~18.5 KB) is ever
    # re-linked as compulsory.
    run bash "$REPO_ROOT/tests/efficiency/measure-instruction-load.sh" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    bytes="$(printf '%s' "$output" | awk '/^resume /{print $2}')"
    [ -n "$bytes" ]
    [ "$bytes" -le 30000 ]
}

# Sentence-level assertion that tolerates the source file's own line wrapping:
# normalize to one line, then match the phrase.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
