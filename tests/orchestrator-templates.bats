#!/usr/bin/env bats
# Contract tests for the ORCHESTRATOR_TASK_TEMPLATE examples.
#
# These tests execute the ACTUAL validation blocks embedded in the templates:
# the fenced bash blocks are extracted from the Markdown, their {placeholders}
# are substituted, and the result runs against an isolated nested-git fixture —
# a Core Hub repo with a child repo under repositories/. The child repo carries
# a real copy of the skill, so the child-conformance invocation in the
# execute-child template runs the true checker.
#
# These are scripted replays of the template checks against fixtures — NOT
# independent agent replays.
#
# Run with:  bats tests/
# Requires:  bats-core, git, python3

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    TPL_DIR="$REPO_ROOT/skills/deepworkplan/examples"
    EXEC_TPL="$TPL_DIR/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md"
    CREATE_TPL="$TPL_DIR/ORCHESTRATOR_TASK_TEMPLATE_create_child_dwp.md"
    CHECKPOINT_TPL="$TPL_DIR/ORCHESTRATOR_TASK_TEMPLATE_integration_checkpoint.md"
    TMPDIR_TEST="$(mktemp -d)"
    HUB="$TMPDIR_TEST/hub"
    CHILD="$HUB/repositories/childrepo"
    CHILD_PLAN="$CHILD/.dwp/plans/PLAN_feat_child"
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

# ---------------------------------------------------------------- helpers

# Print the first fenced ```bash block found between two anchors of a Markdown
# file. $1=file $2=start anchor regex $3=end anchor regex.
extract_bash_block() {
    awk -v start="$2" -v end="$3" '
        $0 ~ start { in_sec = 1 }
        in_sec && $0 ~ end { exit }
        in_sec && /^```bash$/ { in_code = 1; next }
        in_code && /^```$/ { exit }
        in_code { print }
    ' "$1"
}

# Substitute the templates' placeholders with fixture names. Longest
# placeholders first: {repo1_short} must be replaced before {repo1}, etc.
render() {
    sed -e 's/{repo_name}/childrepo/g' \
        -e 's/{repo1_short}/child/g' \
        -e 's/{repo2_short}/other/g' \
        -e 's/{repo_short}/child/g' \
        -e 's/{feature}/feat/g' \
        -e 's/{declared_artifact}/artifact.txt/g' \
        -e 's/{parent_plan_name}/parent/g' \
        -e 's/{validation_command}/make test/g' \
        -e 's/{repo1}/childrepo/g' \
        -e 's/{repo2}/otherrepo/g'
}

# Render a template block to a runnable script file. $1=file $2=start $3=end $4=out.
render_block() {
    extract_bash_block "$1" "$2" "$3" | render > "$4"
}

write_child_plan_files() {
    mkdir -p "$CHILD_PLAN/analysis_results"
    cat > "$CHILD_PLAN/README.md" <<'EOF'
# PLAN_feat_child

**Standard:** DWP spec 2.4.0

## Goal
Fixture child plan for template contract tests.

## Tasks
- [x] Task 1: [Build feature](./1.task_build_feature.md)
- [x] Task 2: [Final Review](./2.task_final_review.md)

Plan Status: 2/2 completed
EOF
    echo 'prompts' > "$CHILD_PLAN/PROMPTS.md"
    echo 'progress' > "$CHILD_PLAN/PROGRESS.md"
    echo 'candidates' > "$CHILD_PLAN/analysis_results/SKILLS_CANDIDATES.md"
    echo 'artifact data' > "$CHILD_PLAN/analysis_results/artifact.txt"
    printf '# Security Review\n\nNo findings (fixture).\n' > "$CHILD_PLAN/analysis_results/SECURITY_REVIEW.md"
    cat > "$CHILD_PLAN/1.task_build_feature.md" <<'EOF'
# Task 1: Build feature

## Goal
Build the fixture feature.

## Touched Surface
- src/feature.py

## Acceptance Criteria
- Feature works.

## Validation
- `make test`

## Completion & Log
Completed in fixture.
EOF
    cat > "$CHILD_PLAN/2.task_final_review.md" <<'EOF'
# Task 2: Final Review

## Goal
Close the plan: security pass, final-state validation, skills reconciliation.

## Touched Surface
- whole plan

## Acceptance Criteria
- Security pass clean; final-state validation green; skills reconciled.

## Validation
- `make test`

## Completion & Log
Completed in fixture.
EOF
}

write_child_state_completed() {
    cat > "$CHILD_PLAN/state.json" <<'EOF'
{
  "schema": "https://deepworkplan.com/schema/plan-state/v2.json",
  "plan": "PLAN_feat_child",
  "updated_at": "2026-09-12T00:00:00+00:00",
  "status": "completed",
  "completed_count": 2,
  "task_count": 2,
  "format": "full",
  "materialization": "ready",
  "approval": "approved",
  "promotion": null,
  "tasks": [
    {
      "id": 1,
      "locator": {"kind": "file", "value": "1.task_build_feature.md"},
      "title": "Build feature",
      "status": "completed",
      "started_at": "2026-09-12T00:00:00+00:00",
      "completed_at": "2026-09-12T00:01:00+00:00",
      "commit": "0123456789abcdef0123456789abcdef01234567",
      "outcome": {"worked": "fixture feature built and gated"},
      "gates": [
        {"command": "make test", "passes": true, "exit_code": 0,
         "last_run": "2026-09-12T00:01:00+00:00", "evidence": "2/2 checks green"}
      ]
    },
    {
      "id": 2,
      "locator": {"kind": "file", "value": "2.task_final_review.md"},
      "title": "Final Review",
      "status": "completed",
      "started_at": "2026-09-12T00:02:00+00:00",
      "completed_at": "2026-09-12T00:03:00+00:00",
      "commit": "123456789abcdef0123456789abcdef012345678",
      "outcome": {"worked": "fixture review closed"},
      "gates": [
        {"command": "make test", "passes": true, "exit_code": 0,
         "last_run": "2026-09-12T00:03:00+00:00", "evidence": "2/2 checks green"}
      ]
    }
  ]
}
EOF
    cat > "$CHILD_PLAN/manifest.json" <<'EOF'
{
  "schema": "https://deepworkplan.com/schema/plan-manifest/v2.json",
  "spec_version": "2.4.0",
  "name": "PLAN_feat_child",
  "title": "Feat child",
  "archetype": "individual",
  "rigor": "deep",
  "created_at": "2026-09-12T00:00:00+00:00",
  "task_count": 2,
  "plan_format": "full"
}
EOF
}

# Core Hub repo + nested child repo (+ a real skill copy in the child when
# $1 = "with-skill") + parent plan referencing the child.
build_fixture() {
    mkdir -p "$HUB/.dwp/plans/PLAN_parent" "$CHILD"
    git -C "$HUB" init -q
    echo '.dwp/' > "$HUB/.gitignore"
    git -C "$CHILD" init -q
    echo '.dwp/' > "$CHILD/.gitignore"
    if [ "${1:-}" = "with-skill" ]; then
        mkdir -p "$CHILD/.agents/skills"
        cp -R "$REPO_ROOT/skills/deepworkplan" "$CHILD/.agents/skills/"
    fi
    cat > "$HUB/.dwp/plans/PLAN_parent/ORCHESTRATOR_MANIFEST.md" <<'EOF'
# Orchestrator manifest

## Execution State
| # | Plan | Created | Executed |
|---|------|---------|----------|
| 1 | PLAN_feat_child | [x] | [x] Executed |
EOF
    cat > "$HUB/.dwp/plans/PLAN_parent/README.md" <<'EOF'
# PLAN_parent

## Tasks
- [x] Task 1: Hand Off Execution of Child DWP — PLAN_feat_child [x] Executed
EOF
    write_child_plan_files
}

# Mutate a completed v2 child state into: top-level in_progress, task 1 still
# completed. The OLD template check (bare grep for '"status": "completed"')
# false-passed here on the nested task-level status.
make_nested_completed_variant() {
    python3 - "$CHILD_PLAN/state.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
s['status'] = 'in_progress'
s['completed_count'] = 1
json.dump(s, open(sys.argv[1], 'w'), indent=2)
PY
}

make_pending_task_variant() {
    python3 - "$CHILD_PLAN/state.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
s['tasks'][1]['status'] = 'pending'
s['completed_count'] = 1
json.dump(s, open(sys.argv[1], 'w'), indent=2)
PY
}

# ------------------------------------------------- execute-child: Step 4

@test "execute-child Step 4 block passes for a completed v2 child (status, conformance, artifact)" {
    build_fixture with-skill
    write_child_state_completed
    render_block "$EXEC_TPL" '^### Step 4' '^### Step 5' "$TMPDIR_TEST/step4.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/step4.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PASS: child plan status and all tasks completed" ]]
    [[ "$output" =~ "PASS: child conformance green" ]]
    [[ "$output" =~ "PASS: declared artifact present" ]]
}

@test "execute-child Step 4 block FAILS when a nested task is completed but the top-level plan is not" {
    build_fixture with-skill
    write_child_state_completed
    make_nested_completed_variant
    render_block "$EXEC_TPL" '^### Step 4' '^### Step 5' "$TMPDIR_TEST/step4.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/step4.sh"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "child plan is not complete" ]]
}

@test "execute-child Step 4 block FAILS when the top-level status is completed but a task is pending" {
    build_fixture with-skill
    write_child_state_completed
    make_pending_task_variant
    render_block "$EXEC_TPL" '^### Step 4' '^### Step 5' "$TMPDIR_TEST/step4.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/step4.sh"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "child tasks are incomplete" ]]
}

@test "execute-child Step 4 block ignores a hub DWP_DIR override when checking the child" {
    build_fixture with-skill
    write_child_state_completed
    render_block "$EXEC_TPL" '^### Step 4' '^### Step 5' "$TMPDIR_TEST/step4.sh"
    cd "$HUB"
    export DWP_DIR="$TMPDIR_TEST/fake-dwp"
    run bash "$TMPDIR_TEST/step4.sh"
    unset DWP_DIR
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PASS: child conformance green" ]]
}

@test "execute-child Step 4 block accepts a legacy child (no state.json) via its recorded lifecycle" {
    build_fixture with-skill
    render_block "$EXEC_TPL" '^### Step 4' '^### Step 5' "$TMPDIR_TEST/step4.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/step4.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "legacy child tasks all executed (recorded)" ]]
    [[ "$output" =~ "PASS: declared artifact present" ]]
}

@test "execute-child Step 4 block FAILS a legacy child that still has an open task" {
    build_fixture with-skill
    sed 's/^- \[x\] Task 2:/- [ ] Task 2:/' "$CHILD_PLAN/README.md" > "$CHILD_PLAN/README.md.tmp"
    mv "$CHILD_PLAN/README.md.tmp" "$CHILD_PLAN/README.md"
    render_block "$EXEC_TPL" '^### Step 4' '^### Step 5' "$TMPDIR_TEST/step4.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/step4.sh"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "legacy child still has open tasks" ]]
}

# ------------------------------------------------- execute-child: section 7

@test "execute-child section 7 validation passes for a completed v2 child with manifest and README" {
    build_fixture with-skill
    write_child_state_completed
    render_block "$EXEC_TPL" '^## 7. Validation' '^## 8. Execution' "$TMPDIR_TEST/sec7.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/sec7.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PASS: child plan completed" ]]
    [[ "$output" =~ "PASS: Manifest has child entry" ]]
}

@test "execute-child section 7 rejects a nested-completed child with incomplete top-level status" {
    build_fixture with-skill
    write_child_state_completed
    make_nested_completed_variant
    render_block "$EXEC_TPL" '^## 7. Validation' '^## 8. Execution' "$TMPDIR_TEST/sec7.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/sec7.sh"
    [ "$status" -eq 1 ]
}

# ------------------------------------------------- static template contracts

@test "all three templates: every FAIL branch exits 1 (no false-pass '|| echo FAIL' survives)" {
    local tpl
    for tpl in "$EXEC_TPL" "$CREATE_TPL" "$CHECKPOINT_TPL"; do
        # A 'echo "FAIL"' line must carry exit 1 itself, or the very next
        # line must be a bare 'exit 1' (multi-line else-branch form).
        run awk '
            /echo "FAIL/ {
                if ($0 !~ /exit 1/) { expect_exit = NR; next }
            }
            expect_exit {
                if ($0 !~ /^[[:space:]]*exit 1/) {
                    print "false-pass FAIL branch at line " expect_exit ": " $0
                    bad = 1
                }
                expect_exit = 0
            }
            /echo "FAIL/ { seen = 1 }
            END { if (!seen) { print "no FAIL branch found"; bad = 1 } exit bad ? 1 : 0 }
        ' "$tpl"
        [ "$status" -eq 0 ]
    done
}

@test "execute-child template tells the agent to run the child's conformance check" {
    grep -q 'verify/conformance.sh' "$EXEC_TPL"
    grep -q -- '--plan' "$EXEC_TPL"
    grep -q 'UNVERIFIED' "$EXEC_TPL"
}

@test "execute-child template documents the legacy fallback explicitly" {
    grep -q 'Legacy child plan' "$EXEC_TPL"
    grep -q 'never re-derive' "$EXEC_TPL"
    grep -q 'stays authoritative' "$EXEC_TPL"
}

# ------------------------------------------------- create-child template

@test "create-child section 7 validation passes on a created child and fails when a file is missing" {
    build_fixture
    # The create template checks the child README references the repo's own
    # validation command and the parent plan by name.
    printf '\nValidation command: `make test` — Parent plan: PLAN_parent\n' >> "$CHILD_PLAN/README.md"
    render_block "$CREATE_TPL" '^## 7. Validation' '^## 8. Execution' "$TMPDIR_TEST/create7.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/create7.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PASS: Uses repo validation" ]]
    rm "$CHILD_PLAN/PROMPTS.md"
    run bash "$TMPDIR_TEST/create7.sh"
    [ "$status" -eq 1 ]
}

# ------------------------------------------------- integration-checkpoint template

@test "integration-checkpoint section 6 validation passes with both children and fails when one README is missing" {
    build_fixture
    mkdir -p "$HUB/repositories/otherrepo/.dwp/plans/PLAN_feat_other"
    echo '# PLAN_feat_other' > "$HUB/repositories/otherrepo/.dwp/plans/PLAN_feat_other/README.md"
    render_block "$CHECKPOINT_TPL" '^## 6. Validation' '^## 7. Execution' "$TMPDIR_TEST/checkpoint6.sh"
    cd "$HUB"
    run bash "$TMPDIR_TEST/checkpoint6.sh"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "PASS: childrepo child DWP exists" ]]
    rm "$HUB/repositories/otherrepo/.dwp/plans/PLAN_feat_other/README.md"
    run bash "$TMPDIR_TEST/checkpoint6.sh"
    [ "$status" -eq 1 ]
}
