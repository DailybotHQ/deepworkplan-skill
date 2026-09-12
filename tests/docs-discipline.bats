#!/usr/bin/env bash
# Contract tests for the boy-scout documentation discipline
# (guide/authoring.md §5.5, mirrored in spec/DWP_SPECIFICATION.md §5 row 7 +
# §6.6, create Step 3.6 / Step 4.4 item 2 / Step 4.0 Lite anatomy, execute
# per-task rule 2 + close rule 5, and spec/LITE_PLANS.md completion evidence).
#
# The rule's unit is the TASK, not the end of the plan: a task that changes
# behavior, structure, commands, configuration, or agent surface must, in the
# same task, update the documentation that registers that surface, and must
# carry a documentation decision in its Completion & Log — exactly parallel
# to the task-local skills decision (§6.2). The rule must not decay into a
# final catch-up docs task, and must stay proportional (exemptions + the
# one-line rule).
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

@test "authoring 5.5 states the boy-scout documentation discipline with its MUSTs" {
    local auth="$REPO_ROOT/skills/deepworkplan/guide/authoring.md"
    doc_has "$auth" "### 5.5. Documentation Discipline — Boy-Scout (MANDATORY)"
    doc_has "$auth" "MUST**, in that same task, update the documentation that registers"
    doc_has "$auth" "Put it in the task's **Acceptance Criteria**"
    doc_has "$auth" "planned docs surface"
    doc_has "$auth" "Proportional, not bureaucratic."
    doc_has "$auth" "documentation debt is context debt"
    doc_has "$auth" "Review's documentation sweep reports it — it does not silently absorb it."
}

@test "spec 5 anatomy requires doc currency among Acceptance Criteria" {
    local spec="$REPO_ROOT/skills/deepworkplan/spec/DWP_SPECIFICATION.md"
    doc_has "$spec" "MUST** include the currency of the documentation that registers that surface among its criteria (§6.6)"
}

@test "spec 6.6 defines the task-local documentation decision" {
    local spec="$REPO_ROOT/skills/deepworkplan/spec/DWP_SPECIFICATION.md"
    doc_has "$spec" "### 6.6. Task-Local Documentation Decisions (boy-scout)"
    doc_has "$spec" "MUST** carry a **documentation decision**"
    doc_has "$spec" "not applicable — <reason>"
    doc_has "$spec" "MUST NOT** be deferred past the Final Review"
    doc_has "$spec" "decided task-locally, exactly like skills decisions (§6.2)"
}

@test "create Step 3.6 names all three disciplines and the docs task shape" {
    local create="$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
    doc_has "$create" "3.6 Test, security, and documentation discipline."
    doc_has "$create" "documentation discipline (boy-scout)"
    doc_has "$create" "N.task_document_{feature}.md"
    doc_has "$create" "never deferred past the Final Review's documentation sweep"
}

@test "create Step 4.4 template carries both decision lines and the three log lines" {
    local create="$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
    doc_has "$create" "Documentation decision: docs updated for the touched surface —"
    doc_has "$create" 'MUST** carry a `Skills disposition:` line, a `Documentation decision:` line, and a `Gate record:` line'
}

@test "create Lite anatomy carries the planned docs surface and the documentation decision" {
    local create="$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
    doc_has "$create" "planned surface, planned docs surface, risk class, test"
    doc_has "$create" "documentation decision, gate record)."
}

@test "execute makes and reconciles the documentation decision per task" {
    local exec="$REPO_ROOT/skills/deepworkplan/execute/SKILL.md"
    doc_has "$exec" "make the **documentation decision**"
    doc_has "$exec" "a doc named in the plan but left stale by close is a reconciliation miss, never a follow-up"
    doc_has "$exec" "Reconcile the documentation decision** the same way"
    doc_has "$exec" "gate records, skills disposition, documentation decision, notes)"
}

@test "LITE_PLANS includes the documentation decision in completion evidence" {
    local lite="$REPO_ROOT/skills/deepworkplan/spec/LITE_PLANS.md"
    doc_has "$lite" "documentation decision included"
}

@test "the authoring example template carries both decisions in checklist and log" {
    local auth="$REPO_ROOT/skills/deepworkplan/guide/authoring.md"
    doc_has "$auth" "Make the skills decision (§6.2) and the documentation decision (§5.5)"
    doc_has "$auth" '**Skills disposition:** (`none` / `update <existing>` / `create <name>` / `defer — <reason, owner>`)'
    doc_has "$auth" '**Documentation decision:** (docs updated for the touched surface — list, or `not applicable — <reason>`)'
    doc_has "$auth" "**Gate record:** (command, cwd, scope/reason, revision or fingerprint, result, evidence path)"
}

@test "the authoring example task list reads docs currency as by-design" {
    local auth="$REPO_ROOT/skills/deepworkplan/guide/authoring.md"
    doc_has "$auth" "keeps its integration docs current in-task"
    doc_has "$auth" "substantial docs surface — its own task by design, not a catch-up"
}

# Sentence-level assertion that tolerates the source file's own line wrapping:
# normalize to one line, then match the phrase.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
