#!/usr/bin/env bats
# Tests for skills/deepworkplan/verify/conformance.sh
#
# Run with:  bats tests/
# Requires:  bats-core (brew install bats-core / apt install bats)

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    CONFORMANCE_SH="$REPO_ROOT/skills/deepworkplan/verify/conformance.sh"
    TMPDIR_TEST="$(mktemp -d)"
    cd "$TMPDIR_TEST"
}

teardown() {
    cd "$BATS_TEST_DIRNAME"
    rm -rf "$TMPDIR_TEST"
}

# Build a minimal conformant repo fixture in the current directory.
make_conformant_repo() {
    git init -q .
    printf '# AGENTS.md\n\n## Quick Commands\n\n- `make test`\n' > AGENTS.md
    ln -s AGENTS.md CLAUDE.md
    mkdir -p .agents/agents .agents/commands .agents/skills .agents/docs docs
    ln -s .agents .claude
    mkdir -p .dwp/plans .dwp/drafts
    echo '.dwp/' > .gitignore
}

# Build a minimal well-formed plan fixture under .dwp/plans/.
make_conformant_plan() {
    local plan=".dwp/plans/PLAN_test_fixture"
    mkdir -p "$plan/analysis_results"
    cat > "$plan/README.md" <<'EOF'
# PLAN_test_fixture

## Goal
Test fixture.

## Tasks
- [x] Task 1
- [ ] Task 2
- [ ] Task 3

Plan Status: 1/3 completed
EOF
    echo 'prompts' > "$plan/PROMPTS.md"
    echo 'progress' > "$plan/PROGRESS.md"
    printf '# Task 1\n\n## Validation\n\n- `make test`\n' > "$plan/1.task_first_thing.md"
    printf '# Task 2\n\n## Validation\n\n- manual checklist\n' > "$plan/2.task_skills_agents_discovery.md"
    printf '# Task 3\n\n## Validation\n\n- manual checklist\n' > "$plan/3.task_executive_report.md"
}

@test "conformant repo with no plans passes (exit 0)" {
    make_conformant_repo
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Verdict: CONFORMANT" ]]
}

@test "missing AGENTS.md fails (exit 1)" {
    make_conformant_repo
    rm AGENTS.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
    [[ "$output" =~ "NOT CONFORMANT" ]]
}

@test "AGENTS.md without Quick Commands fails" {
    make_conformant_repo
    printf '# AGENTS.md\n\nno commands here\n' > AGENTS.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
}

@test ".dwp not gitignored fails" {
    make_conformant_repo
    rm .gitignore
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
    [[ "$output" =~ ".dwp/ gitignored" ]]
}

@test "well-formed plan passes all plan checks" {
    make_conformant_repo
    make_conformant_plan
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PLAN_test_fixture" ]]
    [[ "$output" =~ "mandatory task: executive report" ]]
}

@test "plan missing the mandatory final tasks fails" {
    make_conformant_repo
    make_conformant_plan
    rm .dwp/plans/PLAN_test_fixture/3.task_executive_report.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
}

@test "task without a Validation section fails" {
    make_conformant_repo
    make_conformant_plan
    printf '# Task 1\n\nNo gate at all.\n' > .dwp/plans/PLAN_test_fixture/1.task_first_thing.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Validation section" ]]
}

@test "state.json in sync with README passes" {
    make_conformant_repo
    make_conformant_plan
    echo '{"completed_count": 1}' > .dwp/plans/PLAN_test_fixture/state.json
    echo '{"name": "PLAN_test_fixture"}' > .dwp/plans/PLAN_test_fixture/manifest.json
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "in sync with README" ]]
}

@test "state.json desync against README is detected and fails" {
    make_conformant_repo
    make_conformant_plan
    echo '{"completed_count": 3}' > .dwp/plans/PLAN_test_fixture/state.json
    echo '{"name": "PLAN_test_fixture"}' > .dwp/plans/PLAN_test_fixture/manifest.json
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "desync" ]]
}

@test "state.json without manifest.json fails" {
    make_conformant_repo
    make_conformant_plan
    echo '{"completed_count": 1}' > .dwp/plans/PLAN_test_fixture/state.json
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "manifest.json" ]]
}

@test "truncated state.json fails the parse check" {
    make_conformant_repo
    make_conformant_plan
    echo '{"completed_count":' > .dwp/plans/PLAN_test_fixture/state.json
    echo '{}' > .dwp/plans/PLAN_test_fixture/manifest.json
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "state.json parses" ]]
}

@test "no git + no state layer fails (agent-workspace rule)" {
    # Same structure but never `git init`: PLAN_STATE.md is REQUIRED.
    printf '# AGENTS.md\n\n## Quick Commands\n\n- `make test`\n' > AGENTS.md
    mkdir -p .agents/agents .agents/commands .agents/skills .agents/docs docs
    mkdir -p .dwp/plans .dwp/drafts
    make_conformant_plan
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "REQUIRED in a workspace without git" ]]
}

@test "--plan targets a single named plan" {
    make_conformant_repo
    make_conformant_plan
    run bash "$CONFORMANCE_SH" --plan PLAN_test_fixture
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PLAN_test_fixture" ]]
    [[ ! "$output" =~ "Repository" ]]
}

@test "--plan with a missing plan fails" {
    make_conformant_repo
    run bash "$CONFORMANCE_SH" --plan PLAN_does_not_exist
    [ "$status" -eq 1 ]
}

@test "--help prints usage and exits 0" {
    run bash "$CONFORMANCE_SH" --help
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Usage" ]]
}
