#!/usr/bin/env bash
# Contract tests for orchestrator hand-off readiness, child evidence, and the
# manifest requirement (with the legacy fallback).
#
# guide/orchestrator.md §13.10 ("Hand-Off Readiness Gate"), §13.9 ("Fallback
# When Manifest Is Missing"), §13.5 Step 3, and
# examples/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md Step 1 define the
# contract this file pins:
#
#   - readiness is MODE-AWARE: Sequential Runtime-Dependent uses the strict
#     gate (predecessor [x] Executed + Completed Output References entry +
#     declared artifacts on disk); Contract-Parallel and Fully Parallel use the
#     lenient gate (frozen design docs + checkpoint PROCEED + sibling folders)
#     and do NOT require predecessor outputs at hand-off time;
#   - a child counts as executed only on actual child evidence — and parent
#     completion semantics differ: Distributed = created ready plans,
#     Sequential = all children executed with outputs registered;
#   - new orchestrator plans require a manifest; a legacy plan without one
#     proceeds only on equivalent README/output evidence, and BLOCKS when that
#     evidence is insufficient — never silently migrating the plan.
#
# The gate helpers below mirror the documented checklist items one-to-one.
# They are scripted evaluations of the documented algorithm, not independent
# agent replays.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SKILL="$REPO_ROOT/skills/deepworkplan"
    TEMPLATE="$SKILL/examples/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md"
    TMPDIR_TEST="$(mktemp -d)"
    HUB="$TMPDIR_TEST/hub"
    PLAN_DIR="$HUB/.dwp/plans/PLAN_feat"
    MANIFEST="$PLAN_DIR/ORCHESTRATOR_MANIFEST.md"
    API_PLAN="$HUB/repositories/api/.dwp/plans/PLAN_feat_api"
    WEB_PLAN="$HUB/repositories/web/.dwp/plans/PLAN_feat_web"
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

# ---------------------------------------------------------------- helpers

# Baseline fixture: hub plan with manifest (both children pending), a frozen
# design contract and an integration checkpoint on disk, and both child plan
# folders created. Variants below toggle individual documented facts.
build_fixture() {
    mkdir -p "$PLAN_DIR/analysis_results" "$API_PLAN/analysis_results" "$WEB_PLAN"
    printf '# PLAN_feat_api\n' > "$API_PLAN/README.md"
    printf '# PLAN_feat_web\n' > "$WEB_PLAN/README.md"
    printf '# Frozen contract\n' > "$PLAN_DIR/analysis_results/DESIGN_CONTRACT.md"
    printf '# Integration checkpoint\n\nDecision: PROCEED\n' \
        > "$PLAN_DIR/analysis_results/INTEGRATION_CHECKPOINT.md"
    write_manifest pending
}

# $1 = pending|executed   $2 = with_refs|no_refs
write_manifest() {
    local state_row
    if [ "$1" = "executed" ]; then
        state_row='| 1 | PLAN_feat_api | [x] | [x] | Available | API contract |'
    else
        state_row='| 1 | PLAN_feat_api | [ ] | [ ] | — | — |'
    fi
    local refs=''
    if [ "${2:-with_refs}" = "with_refs" ]; then
        refs='#### Child #1: PLAN_feat_api (api)
- **Declared artifacts:** `repositories/api/.dwp/plans/PLAN_feat_api/analysis_results/API_CONTRACT.md`'
    fi
    cat > "$MANIFEST" <<EOF
# Orchestrator Context Manifest: PLAN_feat

## 1. Shared Context

### API Contracts
- Frozen design contract: \`analysis_results/DESIGN_CONTRACT.md\`
- Integration checkpoint decision: \`analysis_results/INTEGRATION_CHECKPOINT.md\`

## 2. Child DWP Registry

| # | Repository | Child Plan | Plan Directory | Role | Status |
|---|-----------|-----------|----------------|------|--------|
| 1 | api | PLAN_feat_api | \`repositories/api/.dwp/plans/PLAN_feat_api\` | backend | pending |
| 2 | web | PLAN_feat_web | \`repositories/web/.dwp/plans/PLAN_feat_web\` | frontend | pending |

## 5. Execution State (Updated During Execution)

| # | Child Plan | Created | Executed | Declared Outputs Present | Key Outputs |
|---|-----------|---------|----------|--------------------------|-------------|
$state_row
| 2 | PLAN_feat_web | [ ] | [ ] | — | — |

### Completed Output References
$refs
EOF
}

# Registry-registered plan paths (the task-3 rule: a recorded plan path, not a
# bare name mention) -> one hub-relative path per line.
registered_plan_paths() {
    grep -oE '[^ `]*\.dwp/plans/PLAN_[A-Za-z0-9_]*' "$MANIFEST" | sort -u
}

# Strict gate — Sequential Runtime-Dependent only (guide §13.10). Mirrors the
# three documented checklist items for the predecessor PLAN_feat_api.
gate_sequential() {
    # 1. Predecessor marked [x] Executed in manifest Execution State.
    awk -F'|' '$0 ~ /PLAN_feat_api/ && $5 ~ /\[x\]/ { found = 1 }
        END { exit found ? 0 : 1 }' "$MANIFEST" || {
        echo "BLOCKED: predecessor not [x] Executed in Execution State" >&2
        return 1
    }
    # 2. "Completed Output References" has the predecessor entry...
    local refs artifact
    refs=$(awk '/^### Completed Output References/,0' "$MANIFEST" \
        | grep -F 'PLAN_feat_api' | grep -F 'Declared artifacts' | head -1)
    if [ -z "$refs" ]; then
        echo "BLOCKED: no Completed Output References entry for predecessor" >&2
        return 1
    fi
    # 3. ...and its declared artifact exists on disk.
    artifact=$(printf '%s\n' "$refs" | grep -oE '`[^`]*`' | tr -d '`' | head -1)
    if [ -z "$artifact" ] || [ ! -f "$HUB/$artifact" ]; then
        echo "BLOCKED: declared predecessor artifact missing on disk: $artifact" >&2
        return 1
    fi
    echo "READY (strict): predecessor executed with declared artifacts on disk"
}

# Lenient gate — Contract-Parallel and Fully Parallel (guide §13.10). Mirrors
# the three documented checklist items; predecessor outputs are NOT required.
gate_lenient() {
    # 1. Design-doc contracts exist on disk (frozen contract + checkpoint).
    local doc
    for doc in DESIGN_CONTRACT.md INTEGRATION_CHECKPOINT.md; do
        local ref
        ref=$(grep -oE "\`[^\`]*$doc\`" "$MANIFEST" | tr -d '`' | head -1)
        if [ -z "$ref" ] || [ ! -f "$PLAN_DIR/$ref" ]; then
            echo "BLOCKED: frozen design doc missing on disk: $ref" >&2
            return 1
        fi
    done
    # 2. Integration checkpoint PROCEED documented.
    if ! grep -qw PROCEED "$PLAN_DIR/analysis_results/INTEGRATION_CHECKPOINT.md"; then
        echo "BLOCKED: no documented PROCEED checkpoint decision" >&2
        return 1
    fi
    # 3. All sibling child DWP folders exist (test -d per registration).
    local path missing=0
    while IFS= read -r path; do
        [ -d "$HUB/$path" ] || { echo "BLOCKED: sibling plan folder missing: $path" >&2; missing=1; }
    done < <(registered_plan_paths)
    [ "$missing" -eq 0 ] || return 1
    echo "READY (lenient): frozen contract + PROCEED checkpoint + siblings present"
}

# Parent completion semantics (execute/orchestrator.md "Recovery and
# completion"): Distributed = created ready plans; Sequential = additionally
# every child executed with registered outputs.
distributed_complete() {
    local path
    while IFS= read -r path; do
        [ -f "$HUB/$path/README.md" ] || {
            echo "INCOMPLETE: child plan not created-ready: $path" >&2; return 1; }
    done < <(registered_plan_paths)
    echo "Distributed complete: all children created and ready"
}

sequential_complete() {
    distributed_complete || return 1
    awk -F'|' '$0 ~ /^\| [0-9]+ \| PLAN_/ && $5 !~ /\[x\]/ { bad = 1 }
        END { exit bad ? 1 : 0 }' "$MANIFEST" || {
        echo "INCOMPLETE: a child is not [x] Executed in Execution State" >&2
        return 1
    }
    echo "Sequential complete: all children executed and registered"
}

# Legacy fallback (guide §13.9): no manifest; the README's Child DWP Plans
# table plus on-disk declared artifacts must establish the SAME readiness
# facts, or the orchestrator BLOCKS. Never migrates the plan.
legacy_gate() {
    local readme="$1"
    [ -f "$MANIFEST" ] && { echo "ERROR: manifest exists — not the legacy path" >&2; return 2; }
    local pending_rows artifact
    pending_rows=$(grep -cE '^\| [0-9]+ \|.*\[ \] (Created|Executed)' "$readme" || true)
    if [ "$pending_rows" -gt 0 ]; then
        echo "BLOCKED: legacy README still shows open child rows" >&2
        return 1
    fi
    while IFS= read -r artifact; do
        [ -f "$HUB/$artifact" ] || {
            echo "BLOCKED: legacy declared artifact missing: $artifact" >&2; return 1; }
    done < <(grep -oE '`[^`]*\.dwp/plans/[^`]*analysis_results/[^`]*`' "$readme" | tr -d '`')
    echo "PROCEED (limitation logged: legacy plan without manifest — equivalent evidence verified)"
}

# ------------------------------------------- strict gate (Sequential)

@test "sequential gate blocks when the predecessor is not executed" {
    build_fixture
    cd "$HUB"
    run gate_sequential
    [ "$status" -eq 1 ]
    printf '%s\n' "$output" | grep -qF 'not [x] Executed'
}

@test "sequential gate passes with executed predecessor, registered outputs and artifact on disk" {
    build_fixture
    write_manifest executed
    printf '# API contract\n' \
        > "$API_PLAN/analysis_results/API_CONTRACT.md"
    cd "$HUB"
    run gate_sequential
    [ "$status" -eq 0 ]
    [[ "$output" =~ "READY (strict)" ]]
}

@test "sequential gate blocks when the predecessor is executed but its declared artifact is missing (evidence before Executed)" {
    build_fixture
    write_manifest executed
    # Execution State says executed + Available, but the declared artifact was
    # never written: the gate must refuse to treat the checkbox as evidence.
    cd "$HUB"
    run gate_sequential
    [ "$status" -eq 1 ]
    [[ "$output" =~ "declared predecessor artifact missing" ]]
}

@test "sequential gate blocks without a Completed Output References entry" {
    build_fixture
    write_manifest executed no_refs
    printf '# API contract\n' \
        > "$API_PLAN/analysis_results/API_CONTRACT.md"
    cd "$HUB"
    run gate_sequential
    [ "$status" -eq 1 ]
    [[ "$output" =~ "no Completed Output References entry" ]]
}

# ------------------------------------------- lenient gate (parallel modes)

@test "contract-parallel passes the lenient gate with no predecessor executed" {
    build_fixture
    cd "$HUB"
    run gate_lenient
    [ "$status" -eq 0 ]
    [[ "$output" =~ "READY (lenient)" ]]
}

@test "contract-parallel blocks when the frozen design contract is missing from disk" {
    build_fixture
    rm "$PLAN_DIR/analysis_results/DESIGN_CONTRACT.md"
    cd "$HUB"
    run gate_lenient
    [ "$status" -eq 1 ]
    [[ "$output" =~ "frozen design doc missing" ]]
}

@test "contract-parallel blocks without a documented PROCEED checkpoint" {
    build_fixture
    printf '# Integration checkpoint\n\nDecision: HOLD\n' \
        > "$PLAN_DIR/analysis_results/INTEGRATION_CHECKPOINT.md"
    cd "$HUB"
    run gate_lenient
    [ "$status" -eq 1 ]
    [[ "$output" =~ "PROCEED" ]]
}

@test "contract-parallel blocks when a sibling child plan folder is missing" {
    build_fixture
    rm -rf "$WEB_PLAN"
    cd "$HUB"
    run gate_lenient
    [ "$status" -eq 1 ]
    [[ "$output" =~ "sibling plan folder missing" ]]
}

# ------------------------------------------- parent completion semantics

@test "distributed completion means created ready plans, not executed children" {
    build_fixture
    cd "$HUB"
    run distributed_complete
    [ "$status" -eq 0 ]
    # The same fixture is NOT sequential-complete: nothing is executed.
    run sequential_complete
    [ "$status" -eq 1 ]
    printf '%s\n' "$output" | grep -qF 'not [x] Executed'
}

@test "sequential completion requires every child executed and registered" {
    build_fixture
    write_manifest executed
    printf '# API contract\n' \
        > "$API_PLAN/analysis_results/API_CONTRACT.md"
    cd "$HUB"
    run sequential_complete
    [ "$status" -eq 1 ]   # child #2 still pending
    printf '%s\n' "$output" | grep -qF 'not [x] Executed'
}

# ------------------------------------------- manifest requirement + legacy fallback

@test "legacy plan without manifest proceeds on sufficient equivalent evidence, logging the limitation" {
    build_fixture
    rm "$MANIFEST"
    cat > "$PLAN_DIR/README.md" <<'EOF'
## Child DWP Plans

| # | Repository | Child Plan | Status | Depends On |
|---|-----------|-----------|--------|-----------|
| 1 | api | PLAN_feat_api | [x] Created / [x] Executed | — |

Output: `repositories/api/.dwp/plans/PLAN_feat_api/analysis_results/API_CONTRACT.md`
EOF
    printf '# API contract\n' > "$API_PLAN/analysis_results/API_CONTRACT.md"
    cd "$HUB"
    run legacy_gate "$PLAN_DIR/README.md"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "limitation logged" ]]
}

@test "legacy plan without manifest blocks when equivalent evidence is insufficient" {
    build_fixture
    rm "$MANIFEST"
    # README claims executed, but the declared artifact never landed on disk.
    cat > "$PLAN_DIR/README.md" <<'EOF'
## Child DWP Plans

| # | Repository | Child Plan | Status | Depends On |
|---|-----------|-----------|--------|-----------|
| 1 | api | PLAN_feat_api | [x] Created / [x] Executed | — |

Output: `repositories/api/.dwp/plans/PLAN_feat_api/analysis_results/API_CONTRACT.md`
EOF
    cd "$HUB"
    run legacy_gate "$PLAN_DIR/README.md"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "BLOCKED" ]]
}

@test "legacy plan with open child rows blocks instead of proceeding on the child's README alone" {
    build_fixture
    rm "$MANIFEST"
    cat > "$PLAN_DIR/README.md" <<'EOF'
## Child DWP Plans

| # | Repository | Child Plan | Status | Depends On |
|---|-----------|-----------|--------|-----------|
| 1 | api | PLAN_feat_api | [x] Created / [ ] Executed | — |
EOF
    cd "$HUB"
    run legacy_gate "$PLAN_DIR/README.md"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "open child rows" ]]
}

# Sentence-level doc assertion that tolerates the source file's own line
# wrapping: normalize to one line, then match the phrase.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}

# ------------------------------------------- static doc contracts

@test "guide defines both mode-aware gates with the no-predecessor-outputs distinction" {
    local guide="$SKILL/guide/orchestrator.md"
    grep -q 'lenient gate' "$guide"
    grep -q 'strict gate' "$guide"
    grep -q 'NOT required' "$guide"
    grep -q 'All predecessors executed' "$guide"
    grep -q 'Declared artifacts exist' "$guide"
    grep -q 'Fully Parallel' "$guide"
}

@test "guide fallback blocks on insufficient legacy evidence and never silently migrates" {
    local guide="$SKILL/guide/orchestrator.md"
    doc_has "$guide" "BLOCK — do not proceed on the child's own README alone"
    doc_has "$guide" "never silently migrate a legacy plan to add a manifest"
}

@test "execute/orchestrator.md keeps evidence-before-Executed and distributed semantics" {
    local exec="$SKILL/execute/orchestrator.md"
    doc_has "$exec" "A nested completed task in JSON is not a completed plan"
    doc_has "$exec" "Distributed parent completion means plans created and ready, not feature implementation complete"
    doc_has "$exec" "block if they cannot establish them"
    doc_has "$exec" "Never silently migrate a legacy plan"
    doc_has "$exec" "Fully Parallel children have no predecessor output dependency"
}

@test "onboarding a skill-less child requires user authorization, never initiative" {
    local guide="$SKILL/guide/orchestrator.md"
    local exec="$SKILL/execute/orchestrator.md"
    doc_has "$guide" "only when the user authorizes"
    doc_has "$exec" "run onboarding only when authorized"
    # The old unconditional-install imperative must be gone.
    run grep -F 'install/confirm DeepWorkPlan there if missing' "$exec"
    [ "$status" -ne 0 ]
}

@test "template Step 1 is mode-dependent and its BLOCKED message forbids inline unblocking" {
    grep -q 'Step 1: Verify Hand-Off Readiness (CRITICAL — mode-dependent)' "$TEMPLATE"
    grep -q 'Sequential Runtime-Dependent.*strict gate — for this mode only' "$TEMPLATE"
    grep -q 'Contract-Parallel or Fully Parallel.*lenient gate' "$TEMPLATE"
    grep -q 'do NOT execute the child inline to "unblock"' "$TEMPLATE"
}
