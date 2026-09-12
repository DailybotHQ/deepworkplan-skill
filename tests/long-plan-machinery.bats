#!/usr/bin/env bash
# Contract tests for the long-plan README machinery (task 13):
# Stage Gates — an OPTIONAL README section for long Full plans only, with the
# corpus-proven shape and always-sequential semantics — and the enriched
# Plan Variables example rows (guide/authoring.md §4.2–§4.3).
#
# Progressive loading contract: small-plan and Lite flows author (and pay
# attention to) none of it; the only always-read growth is the bounded §4.3
# guide block and the one create trigger line.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    AUTH="$SK/guide/authoring.md"
    CREATE="$SK/create/SKILL.md"
    CONTRACT="$SK/verify/plan_contract.py"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
l_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "guide 4.3 documents Stage Gates as long-plan-only with the corpus shape" {
    grep -qF '### 4.3. Stage Gates (optional — long Full plans only)' "$AUTH"
    grep -qF '| Gate | After task | Evidence required |' "$AUTH"
    l_doc_has "$AUTH" "Full plan with 20 or more task"
    l_doc_has "$AUTH" "A **Lite plan never carries Stage"
    l_doc_has "$AUTH" "one gate per coherent phase"
    l_doc_has "$AUTH" "never evidence invented for the checkpoint"
}

@test "stage gates are always-sequential barriers and never replace the Final Review" {
    l_doc_has "$AUTH" "always-sequential barrier"
    l_doc_has "$AUTH" "Final"
    l_doc_has "$AUTH" "never listed as a stage-gate row"
    l_doc_has "$AUTH" "adjacent to the Execution Rules"
}

@test "small and Lite plans gain nothing: omit by default, Lite never" {
    l_doc_has "$AUTH" "omits them by default"
    # The small-plan example structure (4.2) carries no stage gates
    # (the range excludes the 4.3 heading line itself).
    run bash -c "awk '/### 4.2. Example structure/{f=1} /### 4.3./{f=0} f' '$AUTH' | grep -F 'Stage Gate'"
    [ "$status" -ne 0 ]
    # The Lite README anatomy block in create/SKILL.md stays gate-free.
    run bash -c "awk '/Lite README anatomy/,/Anchor rules/' '$CREATE' | grep -F 'Stage Gate'"
    [ "$status" -ne 0 ]
}

@test "create carries one conditional trigger, threshold and both exclusions" {
    l_doc_has "$CREATE" "Stage Gates** table"
    l_doc_has "$CREATE" "20 or more task files"
    l_doc_has "$CREATE" "Lite plans never carry it"
    l_doc_has "$CREATE" "shorter"
    l_doc_has "$CREATE" "omit it by default"
    l_doc_has "$CREATE" "one named checkpoint per coherent phase"
}

@test "Plan Variables guidance gains the corpus-proven example rows as examples" {
    grep -qF '| Rigor |' "$AUTH"
    grep -qF '| Primary scope |' "$AUTH"
    grep -qF '| Evidence bar |' "$AUTH"
    grep -qF '| Quality commands |' "$AUTH"
    grep -qF '| Forbidden |' "$AUTH"
    grep -qF '| {custom_variable} | {value} |' "$AUTH"
    l_doc_has "$AUTH" "add only the rows this plan needs"
}

@test "no mandatory-field regression: conformance never requires Stage Gates or Plan Variables" {
    run grep -F 'Stage Gate' "$CONTRACT"
    [ "$status" -ne 0 ]
    run grep -F 'Plan Variables' "$CONTRACT"
    [ "$status" -ne 0 ]
    # create still marks Plan Variables optional.
    l_doc_has "$AUTH" "Plan Variables** (optional"
}
