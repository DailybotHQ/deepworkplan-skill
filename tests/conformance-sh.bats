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
    printf '# Security\n\nNo secrets in this fixture.\n' > docs/SECURITY.md
    ln -s .agents .claude
    ln -s .agents .cursor
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
- [ ] Task 4

Plan Status: 1/4 completed
EOF
    echo 'prompts' > "$plan/PROMPTS.md"
    echo 'progress' > "$plan/PROGRESS.md"
    printf '# Task 1\n\n## Validation\n\n- `make test`\n' > "$plan/1.task_first_thing.md"
    printf '# Task 2\n\n## Validation\n\n- manual checklist\n' > "$plan/2.task_security_review.md"
    printf '# Task 3\n\n## Validation\n\n- manual checklist\n' > "$plan/3.task_skills_agents_discovery.md"
    printf '# Task 4\n\n## Validation\n\n- manual checklist\n' > "$plan/4.task_executive_report.md"
}

# Build a minimal well-formed 2.3.0-shape plan (single Final Review last).
make_new_plan() {
    local plan=".dwp/plans/PLAN_new_fixture"
    mkdir -p "$plan/analysis_results"
    cat > "$plan/README.md" <<'EOF'
# PLAN_new_fixture

## Goal
Test fixture (2.3.0 shape).

**Standard:** DWP spec 2.3.0

## Tasks
- [x] Task 1
      See: [1.task_first_thing.md](./1.task_first_thing.md)
- [ ] Task 2
      See: [2.task_final_review.md](./2.task_final_review.md)

Plan Status: 1/2 completed
EOF
    echo 'prompts' > "$plan/PROMPTS.md"
    echo 'progress' > "$plan/PROGRESS.md"
    echo '# candidates' > "$plan/analysis_results/SKILLS_CANDIDATES.md"
    printf '# Task 1\n\n## Touched Surface\n\n- src/a.py\n\n## Validation\n\n- `make test`\n' > "$plan/1.task_first_thing.md"
    printf '# Task 2: Final review\n\n## Instructions\n\n1. Security pass.\n2. Final-state validation (full suite).\n3. Skills reconciliation.\n\n## Validation\n\n- `make test`\n' > "$plan/2.task_final_review.md"
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
    [[ "$output" =~ "mandatory task: security review" ]]
    [[ "$output" =~ "mandatory task: executive report" ]]
}

@test "plan missing the mandatory final tasks fails" {
    make_conformant_repo
    make_conformant_plan
    rm .dwp/plans/PLAN_test_fixture/4.task_executive_report.md
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
    [[ "$output" =~ "completed_count matches README" ]]
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

# ---------------------------------------------------------------- lifecycle shapes (2.3.0)

@test "2.3.0 plan with a single Final Review last passes" {
    make_conformant_repo
    make_new_plan
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Final Review is task 2 (last)" ]]
    [[ "$output" =~ "names its three parts" ]]
}

@test "legacy three-final-task plan still passes (declared 2.2.0 via manifest)" {
    make_conformant_repo
    make_conformant_plan
    echo '{"completed_count": 1, "task_count": 4, "tasks": [{"id":1,"file":"1.task_first_thing.md","status":"completed"},{"id":2,"file":"2.task_security_review.md","status":"pending"},{"id":3,"file":"3.task_skills_agents_discovery.md","status":"pending"},{"id":4,"file":"4.task_executive_report.md","status":"pending"}]}' > .dwp/plans/PLAN_test_fixture/state.json
    echo '{"name": "PLAN_test_fixture", "spec_version": "2.2.0"}' > .dwp/plans/PLAN_test_fixture/manifest.json
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "plan standard: DWP spec 2.2.0" ]]
    [[ "$output" =~ "mandatory task: executive report" ]]
}

@test "plan with neither shape fails naming both accepted shapes" {
    make_conformant_repo
    make_new_plan
    mv .dwp/plans/PLAN_new_fixture/2.task_final_review.md .dwp/plans/PLAN_new_fixture/2.task_other.md
    sed -i.bak 's/2.task_final_review.md/2.task_other.md/g' .dwp/plans/PLAN_new_fixture/README.md && rm -f .dwp/plans/PLAN_new_fixture/README.md.bak
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "task_final_review.md last" ]]
    [[ "$output" =~ "task_executive_report.md" ]]
}

@test "mixed lifecycle (Final Review plus legacy executive report) fails" {
    make_conformant_repo
    make_new_plan
    printf '# Task 3\n\n## Validation\n\n- x\n' > .dwp/plans/PLAN_new_fixture/3.task_executive_report.md
    sed -i.bak 's/^- \[ \] Task 2/- [ ] Task 2\n- [ ] Task 3\n      See: [3.task_executive_report.md](.\/3.task_executive_report.md)/' .dwp/plans/PLAN_new_fixture/README.md && rm -f .dwp/plans/PLAN_new_fixture/README.md.bak
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "mixed lifecycle" ]]
}

@test "Final Review not last (ids above 9, numeric order) fails" {
    make_conformant_repo
    make_new_plan
    # add tasks 3..12 so the final review (2) is no longer the highest id
    local i
    for i in 3 4 5 6 7 8 9 10 11 12; do
        printf '# Task %s\n\n## Touched Surface\n\n- x\n\n## Validation\n\n- x\n' "$i" > ".dwp/plans/PLAN_new_fixture/$i.task_t$i.md"
        printf -- '- [ ] Task %s\n      See: [%s.task_t%s.md](./%s.task_t%s.md)\n' "$i" "$i" "$i" "$i" "$i" >> .dwp/plans/PLAN_new_fixture/README.md
    done
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "must be the last task (found id 2, highest id 12)" ]]
    [[ "$output" =~ "contiguous 1..12" ]]
}

@test "duplicate task ids fail" {
    make_conformant_repo
    make_new_plan
    cp .dwp/plans/PLAN_new_fixture/1.task_first_thing.md .dwp/plans/PLAN_new_fixture/1.task_dup.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "duplicate id" ]]
}

@test "gap in task ids fails" {
    make_conformant_repo
    make_new_plan
    mv .dwp/plans/PLAN_new_fixture/2.task_final_review.md .dwp/plans/PLAN_new_fixture/3.task_final_review.md
    sed -i.bak 's/2.task_final_review.md/3.task_final_review.md/g' .dwp/plans/PLAN_new_fixture/README.md && rm -f .dwp/plans/PLAN_new_fixture/README.md.bak
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "contiguous 1..N" ]]
}

@test "plan declaring 2.3.0 with the legacy three-task ending fails" {
    make_conformant_repo
    make_conformant_plan
    printf '\n**Standard:** DWP spec 2.3.0\n' >> .dwp/plans/PLAN_test_fixture/README.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "declares DWP spec 2.3.0 but carries the pre-2.3.0" ]]
}

@test "plan declaring a newer standard than the checker fails with an upgrade message" {
    make_conformant_repo
    make_new_plan
    sed -i.bak 's/DWP spec 2.3.0/DWP spec 9.9.9/' .dwp/plans/PLAN_new_fixture/README.md && rm -f .dwp/plans/PLAN_new_fixture/README.md.bak
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "newer than this checker supports" ]]
    [[ "$output" =~ "upgrade the installed skill" ]]
}

@test "declared migration keeping a completed security review before the Final Review passes" {
    make_conformant_repo
    make_new_plan
    mv .dwp/plans/PLAN_new_fixture/2.task_final_review.md .dwp/plans/PLAN_new_fixture/3.task_final_review.md
    printf '# Task 2\n\n## Validation\n\n- x\n' > .dwp/plans/PLAN_new_fixture/2.task_security_review.md
    cat > .dwp/plans/PLAN_new_fixture/README.md <<'EOF'
# PLAN_new_fixture

**Standard:** DWP spec 2.3.0 (migrated from 2.2.0 on 2026-09-01 — test)

## Tasks
- [x] Task 1
      See: [1.task_first_thing.md](./1.task_first_thing.md)
- [x] Task 2
      See: [2.task_security_review.md](./2.task_security_review.md)
- [ ] Task 3
      See: [3.task_final_review.md](./3.task_final_review.md)

Plan Status: 2/3 completed
EOF
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "declared migration" ]]
    [[ "$output" =~ "migrated plan keeps its completed Security Review" ]]
}

@test "Final Review whose body does not name its parts fails (filename alone proves nothing)" {
    make_conformant_repo
    make_new_plan
    printf '# Task 2\n\n## Validation\n\n- x\n' > .dwp/plans/PLAN_new_fixture/2.task_final_review.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "does not mention" ]]
}

@test "missing Touched Surface is a finding, not a failure" {
    make_conformant_repo
    make_new_plan
    printf '# Task 1\n\n## Validation\n\n- `make test`\n' > .dwp/plans/PLAN_new_fixture/1.task_first_thing.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "without a Touched Surface section (finding" ]]
}

@test "README link to a missing task file fails the correspondence check" {
    make_conformant_repo
    make_new_plan
    printf -- '- [ ] Task 9\n      See: [9.task_ghost.md](./9.task_ghost.md)\n' >> .dwp/plans/PLAN_new_fixture/README.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "README link(s) broken" ]]
}

@test "state.json task_count that differs from the files fails" {
    make_conformant_repo
    make_new_plan
    echo '{"completed_count": 1, "task_count": 7, "tasks": [{"id":1,"file":"1.task_first_thing.md","status":"completed"},{"id":2,"file":"2.task_final_review.md","status":"pending"}]}' > .dwp/plans/PLAN_new_fixture/state.json
    echo '{"name": "PLAN_new_fixture", "spec_version": "2.3.0"}' > .dwp/plans/PLAN_new_fixture/manifest.json
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "task_count (7) differs" ]]
}

# ---------------------------------------------------------------- repository standard

@test "legacy TESTING_GUIDE without scoped content is a harness-version finding, not a failure" {
    make_conformant_repo
    printf '# Testing\n\nRun `make test`.\n' > docs/TESTING_GUIDE.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "harness-version finding" ]]
}

@test "repo declaring 2.3.0 with a TESTING_GUIDE lacking §3.4 content fails" {
    make_conformant_repo
    printf 'DWP standard: 2.3.0 (onboarded 2026-09-01; skill 2.18.0)\n' >> AGENTS.md
    printf '# Testing\n\nRun `make test`.\n' > docs/TESTING_GUIDE.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
    [[ "$output" =~ "lacks the §3.4 content" ]]
}

@test "repo declaring 2.3.0 with scoped content passes" {
    make_conformant_repo
    printf 'DWP standard: 2.3.0 (onboarded 2026-09-01; skill 2.18.0)\n' >> AGENTS.md
    printf '# Testing\n\nFull: `make test`. Scoped: `pytest tests/test_x.py`. Fallback: `make test`.\n' > docs/TESTING_GUIDE.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ "$output" =~ "carries scoped-invocation content" ]]
}

@test "repo declaring a newer standard than the checker fails" {
    make_conformant_repo
    printf 'DWP standard: 9.9.9 (onboarded 2026-09-01)\n' >> AGENTS.md
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 1 ]
    [[ "$output" =~ "upgrade the installed skill" ]]
}

@test "paths with spaces and metacharacters are handled" {
    mkdir -p "dir with spaces & (parens)"
    cd "dir with spaces & (parens)"
    make_conformant_repo
    make_new_plan
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Verdict: CONFORMANT" ]]
}

# State correspondence must compare task identity and status, not only totals.
make_new_state() {
    cat > .dwp/plans/PLAN_new_fixture/state.json <<'EOF'
{"completed_count":1,"task_count":2,"tasks":[{"id":1,"file":"1.task_first_thing.md","status":"completed"},{"id":2,"file":"2.task_final_review.md","status":"pending"}]}
EOF
    echo '{"spec_version":"2.3.0"}' > .dwp/plans/PLAN_new_fixture/manifest.json
}

@test "per-task state agrees with README, including an in-progress unchecked task" {
    make_conformant_repo
    make_new_plan
    make_new_state
    python3 - <<'PYEOF'
import json
from pathlib import Path
p = Path('.dwp/plans/PLAN_new_fixture/state.json')
s = json.loads(p.read_text())
s['tasks'][1]['status'] = 'in_progress'
p.write_text(json.dumps(s))
PYEOF
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "statuses match README" ]]
}

@test "swapped completed tasks fail even when completed_count is unchanged" {
    make_conformant_repo
    make_new_plan
    make_new_state
    python3 - <<'PYEOF'
import json
from pathlib import Path
p = Path('.dwp/plans/PLAN_new_fixture/state.json')
s = json.loads(p.read_text())
s['tasks'][0]['status'] = 'pending'
s['tasks'][1]['status'] = 'completed'
p.write_text(json.dumps(s))
PYEOF
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "task status disagrees with README: Task 1" ]]
}

@test "duplicate state entries fail despite matching file sets and task_count" {
    make_conformant_repo
    make_new_plan
    make_new_state
    python3 - <<'PYEOF'
import json
from pathlib import Path
p = Path('.dwp/plans/PLAN_new_fixture/state.json')
s = json.loads(p.read_text())
s['tasks'].append(s['tasks'][1].copy())
p.write_text(json.dumps(s))
PYEOF
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "duplicate task entries" ]]
}

@test "state ids must match their filenames" {
    make_conformant_repo
    make_new_plan
    make_new_state
    python3 - <<'PYEOF'
import json
from pathlib import Path
p = Path('.dwp/plans/PLAN_new_fixture/state.json')
s = json.loads(p.read_text())
s['tasks'][1]['id'] = 1
p.write_text(json.dumps(s))
PYEOF
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "duplicate task ids" ]]
    [[ "$output" =~ "task id disagrees with file" ]]
}

@test "stale README summary fails despite accurate state and checkboxes" {
    make_conformant_repo
    make_new_plan
    make_new_state
    sed -i.bak 's/Plan Status: 1\/2/Plan Status: 0\/2/' .dwp/plans/PLAN_new_fixture/README.md
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "README Plan Status count disagrees" ]]
}

@test "DWP_DIR applies to named plans, all plans and repository checks" {
    make_conformant_repo
    make_new_plan
    mv .dwp "custom state & (plans)"
    echo 'custom state & (plans)/' > .gitignore
    export DWP_DIR="$PWD/custom state & (plans)"
    run bash "$CONFORMANCE_SH" --plan PLAN_new_fixture
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Plan: PLAN_new_fixture" ]]
    run bash "$CONFORMANCE_SH"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Plan: PLAN_new_fixture" ]]
    run bash "$CONFORMANCE_SH" --repo-only
    [ "$status" -eq 0 ]
    [[ ! "$output" =~ "Plan: PLAN_new_fixture" ]]
}

@test "external DWP_DIR is not required to be gitignored in the repository" {
    make_conformant_repo
    make_new_plan
    mv .dwp "$TMPDIR_TEST/external-state"
    mkdir repo
    cd repo
    make_conformant_repo
    cd ..
    export DWP_DIR="$TMPDIR_TEST/external-state"
    run bash "$CONFORMANCE_SH" --plan PLAN_new_fixture repo
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Plan: PLAN_new_fixture" ]]
    run bash "$CONFORMANCE_SH" --repo-only repo
    [ "$status" -eq 0 ]
    [[ "$output" =~ "outside the repository" ]]
}

@test "running from a repository subdirectory finds plans at its git root" {
    make_conformant_repo
    make_new_plan
    mkdir src
    run bash "$CONFORMANCE_SH" --plan PLAN_new_fixture src
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Plan: PLAN_new_fixture" ]]
}
