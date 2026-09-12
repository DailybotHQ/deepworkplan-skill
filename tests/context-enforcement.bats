#!/usr/bin/env bash
# Contract tests for Context-section enforcement (task 14):
# the verifier now enforces what the spec already mandates — task-level
# Context for v2+ tasks not yet completed (DWP_SPECIFICATION §5: "the agent
# MUST be able to start from this section alone") and the v2 plan-level
# Goal+Context pair — without retroactively failing completed task records
# or pre-v2 legacy plans.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    CONTRACT="$SK/verify/plan_contract.py"
    SPEC="$SK/spec/DWP_SPECIFICATION.md"
    AUTH="$SK/guide/authoring.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
c_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "spec and guide already mandate the Context the verifier now enforces" {
    c_doc_has "$SPEC" "the agent **MUST** be able to start from this section alone"
    c_doc_has "$AUTH" "**Context**"
    grep -qF '## 1. Context' "$AUTH"
    # Plan-level pair is taught in the README structure (4.1 items 1-2).
    c_doc_has "$AUTH" "**Plan Title and Goal**"
}

@test "plan_contract requires Context for tasks not yet completed, quoting the spec" {
    # The rendered finding text (with "start from this section alone" intact)
    # is asserted behaviorally in tests/lifecycle_contract_test.py.
    c_doc_has "$CONTRACT" "task['status'] != 'completed' and not field_content(body, 'Context')"
    c_doc_has "$CONTRACT" "MUST be able to start from this section"
    # The Lite branch carries the same status-scoped requirement.
    c_doc_has "$CONTRACT" "status != 'completed' and not field_content(body[1], 'Context')"
}

@test "completed task records stay as authored — the exemption is explicit" {
    c_doc_has "$CONTRACT" "Context is a starting requirement, not a history requirement"
    c_doc_has "$CONTRACT" "completed task's record stays as authored"
}

@test "the v2 plan-level Goal+Context pair is required for v2+ plans" {
    c_doc_has "$CONTRACT" "field_content(clean, 'Goal')) and bool(field_content(clean, 'Context'))"
    c_doc_has "$CONTRACT" "plan README carries the Goal+Context pair (v2 shape restored)"
    c_doc_has "$CONTRACT" "plan README lacks a non-empty Context section alongside Goal"
}

@test "legacy acceptance untouched — no Context requirement on the legacy paths" {
    # The legacy era (pre-v2 state layer) keeps the shape it was authored
    # under; neither legacy function gains a Context check.
    run bash -c "awk '/^def legacy\(/,/^def legacy_state\(/' '$CONTRACT' | grep -F 'Context'"
    [ "$status" -ne 0 ]
    run bash -c "awk '/^def legacy_state\(/,/^if __name__/' '$CONTRACT' | grep -c 'lacks.*Context'"
    [ "$status" -ne 0 ]
}

@test "task templates teach the section the verifier requires" {
    grep -qF '## 1. Context' "$SK/examples/TEAM_AGENTS_TASK_TEMPLATE.md"
    grep -qF '## 2. Context' "$SK/examples/ORCHESTRATOR_TASK_TEMPLATE_create_child_dwp.md"
}
