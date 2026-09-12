#!/usr/bin/env bash
# Contract tests for the explicit execution-parallelism declaration (task 12):
# every plan declares its parallelization decision — full Team Agents
# Configuration when parallel groups exist, an explicit minimal
# "Execution: sequential — <rationale>" line when they do not.
#
# Surfaces: create/team-agents.md (Step 2.10 + materialization),
# guide/team-agents.md (§14.2), execute/SKILL.md (Step 2.2),
# examples/TEAM_AGENTS_TASK_TEMPLATE.md (v4 canonical anatomy),
# guide/skills-integration.md §11 (routing consistency, read-only).
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    CREATE="$SK/create/team-agents.md"
    GUIDE="$SK/guide/team-agents.md"
    EXEC="$SK/execute/SKILL.md"
    TMPL="$SK/examples/TEAM_AGENTS_TASK_TEMPLATE.md"
    ROUTE="$SK/guide/skills-integration.md"
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
p_doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

@test "sequential plans are no longer silent: create writes the declaration" {
    # The always-read SKILL.md Step 2.10 carries the one-line instruction, so
    # the declaration is written without loading the conditional file.
    p_doc_has "$SK/create/SKILL.md" "Execution: sequential — {short rationale: shared surface /"
    p_doc_has "$SK/create/SKILL.md" "The decision is never"
    p_doc_has "$CREATE" "Execution: sequential — {short rationale: shared surface / collision risk / single-session audit trail}"
    p_doc_has "$CREATE" "leave the decision silent"
    p_doc_has "$CREATE" "fabricate parallel groups"
    p_doc_has "$CREATE" "agent-neutral"
    # The old silent branch is gone everywhere in the create flow.
    run grep -rn -F 'add nothing, mention nothing' "$SK/create/"
    [ "$status" -ne 0 ]
}

@test "guide 14.2 documents both declaration shapes" {
    p_doc_has "$GUIDE" "The parallelization decision is always declared — never silent."
    p_doc_has "$GUIDE" "Execution: sequential — {short rationale: shared surface / collision risk / single-session audit trail}"
    p_doc_has "$GUIDE" "it is not a missing Team Agents Configuration"
    p_doc_has "$GUIDE" "ALSO list their sequential"
}

@test "the groups table gains Starts after, the conflict rule, and exemptions" {
    grep -qF '| Group | Tasks | Teammates | Starts after | Description |' "$GUIDE"
    p_doc_has "$GUIDE" "Starts after** column names the task, group, or barrier"
    p_doc_has "$GUIDE" "owning the same file is a conflict even when their logical changes are"
    p_doc_has "$GUIDE" "always sequential"
    p_doc_has "$CREATE" "Starts after"
    p_doc_has "$CREATE" "owning the same file"
    p_doc_has "$CREATE" "always"
}

@test "execute Step 2.2 recognizes both shapes" {
    p_doc_has "$EXEC" "If the README instead"
    p_doc_has "$EXEC" "Execution: sequential"
    p_doc_has "$EXEC" "do not treat it as a missing or failed detection"
}

@test "TEAM_AGENTS_TASK_TEMPLATE carries the v4 canonical anatomy" {
    grep -qF '## 4. Touched Surface' "$TMPL"
    grep -qF '## 5. Instructions' "$TMPL"
    grep -qF '## 11. Completion & Log' "$TMPL"
    p_doc_has "$TMPL" "guide/authoring.md"
    # The pre-v4 shape (Instructions at 4, Completion & Log at 10, no Touched
    # Surface) is gone.
    run grep -F '## 10. Completion & Log' "$TMPL"
    [ "$status" -ne 0 ]
    run grep -F '## 4. Instructions' "$TMPL"
    [ "$status" -ne 0 ]
}

@test "tier/model routing stays reachable and consistent (read-only pin)" {
    p_doc_has "$ROUTE" "Complexity:** Tier"
    p_doc_has "$ROUTE" "model"
    grep -qF '| Role | Assigned Tasks | Model | Spawn Prompt |' "$GUIDE"
    p_doc_has "$CREATE" "default model \`sonnet\`"
}
