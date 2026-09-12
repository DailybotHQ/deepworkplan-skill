#!/usr/bin/env bash
# Contract tests for hub/child context and root isolation.
#
# execute/orchestrator.md ("Repository and execution boundaries") and
# guide/orchestrator.md §13.5 define the isolation contract this file pins:
#
#   - the hub saves its absolute root before entering a child and returns to
#     the SAVED root (never a literal path such as /workspace);
#   - a hub DWP_DIR override must not leak into a child resolution: resolve in
#     a subshell with `unset DWP_DIR`, or set an explicitly recorded
#     child-specific override;
#   - navigation follows ROOTS REGISTERED IN ORCHESTRATOR_MANIFEST.md —
#     repositories/{repo}/ is a convention, not a hardcoded requirement, and a
#     missing registration is surfaced instead of guessed.
#
# The behavioral tests run the real shared/context.sh inside nested git
# fixtures. They are scripted replays of the documented resolution steps, not
# independent agent replays.
#
# Run with:  bats tests/
# Requires:  bats-core, git, python3

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SKILL="$REPO_ROOT/skills/deepworkplan"
    CONTEXT_SH="$SKILL/shared/context.sh"
    TMPDIR_TEST="$(mktemp -d)"
    HUB="$TMPDIR_TEST/hub"
    CHILD="$HUB/repositories/childrepo"
    OTHER_CHILD="$HUB/workareas/child-x"
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

# ---------------------------------------------------------------- helpers

build_fixture() {
    mkdir -p "$HUB/.dwp/plans/PLAN_parent" "$CHILD" "$OTHER_CHILD"
    git -C "$HUB" init -q
    git -C "$CHILD" init -q
    git -C "$OTHER_CHILD" init -q
    # The manifest registers PLAN_feat_child at a NON-conventional root, so a
    # passing lookup proves navigation follows registration, not the
    # repositories/{repo} convention.
    cat > "$HUB/.dwp/plans/PLAN_parent/ORCHESTRATOR_MANIFEST.md" <<'EOF'
# Orchestrator manifest

## Completed Output References

#### Child #1: PLAN_feat_child (child-x)
- **Declared artifacts:** `workareas/child-x/.dwp/plans/PLAN_feat_child/analysis_results/artifact.txt`
EOF
}

# JSON field from context.sh output. $1=field $2=output line
field() {
    printf '%s\n' "$2" | python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"
}

# The documented manifest-driven child-root lookup: registrations drive
# navigation; anything missing is surfaced, never guessed.
resolve_child_root() {
    local plan="$1" manifest="$HUB/.dwp/plans/PLAN_parent/ORCHESTRATOR_MANIFEST.md"
    local entry path root
    # Registration = a recorded plan path, not a bare header mention.
    entry=$(grep -F "$plan" "$manifest" | grep -F '.dwp/plans/' | head -1)
    if [ -z "$entry" ]; then
        echo "ERROR: $plan is not registered in ORCHESTRATOR_MANIFEST.md — refusing to guess its root" >&2
        return 1
    fi
    path=$(printf '%s\n' "$entry" | grep -oE '[^ \`]*/\.dwp/plans/'"$plan" | head -1)
    root=${path%/.dwp/plans/$plan}
    if [ -z "$root" ] || [ ! -d "$HUB/$root" ]; then
        echo "ERROR: registered root for $plan does not exist under the hub: $root" >&2
        return 1
    fi
    printf '%s\n' "$HUB/$root"
}

# ------------------------------------------------- DWP_DIR isolation (context.sh)

@test "child context resolves the child's own .dwp when no DWP_DIR is set" {
    build_fixture
    cd "$CHILD"
    run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [ "$(field repo_root "$output")" = "$CHILD" ]
    [ "$(field dwp_dir "$output")" = "$CHILD/.dwp" ]
}

@test "a hub DWP_DIR carried into the child leaks into its resolution (the failure the rule prevents)" {
    build_fixture
    cd "$CHILD"
    DWP_DIR="$HUB/.dwp" run bash "$CONTEXT_SH"
    unset DWP_DIR
    [ "$status" -eq 0 ]
    # Naive resolution inherits the hub override — this is exactly why
    # execute/orchestrator.md forbids carrying DWP_DIR into the child.
    [ "$(field dwp_dir "$output")" = "$HUB/.dwp" ]
}

@test "subshell 'unset DWP_DIR' resolves the child's .dwp despite a hub override" {
    build_fixture
    cd "$CHILD"
    export DWP_DIR="$HUB/.dwp"
    run bash -c '( unset DWP_DIR; bash "$1" )' _ "$CONTEXT_SH"
    unset DWP_DIR
    [ "$status" -eq 0 ]
    [ "$(field dwp_dir "$output")" = "$CHILD/.dwp" ]
}

@test "explicit child-specific DWP_DIR override resolves the child's .dwp" {
    build_fixture
    cd "$CHILD"
    DWP_DIR="$CHILD/.dwp" run bash "$CONTEXT_SH"
    [ "$status" -eq 0 ]
    [ "$(field dwp_dir "$output")" = "$CHILD/.dwp" ]
}

# ------------------------------------------------- saved hub root

@test "the saved hub root returns from inside a child; an ad-hoc git-root resolve does not" {
    build_fixture
    cd "$HUB"
    HUB_ROOT="$(git rev-parse --show-toplevel)"
    cd "$CHILD"
    # Resolving the git root while inside the child returns the CHILD — the
    # saved variable is the only correct way back.
    [ "$(git rev-parse --show-toplevel)" = "$CHILD" ]
    cd "$HUB_ROOT"
    [ "$PWD" = "$HUB" ]
}

# ------------------------------------------------- manifest-driven navigation

@test "registered roots drive navigation even at non-conventional locations" {
    build_fixture
    mkdir -p "$OTHER_CHILD/.dwp/plans/PLAN_feat_child"
    cd "$HUB"
    run resolve_child_root PLAN_feat_child
    [ "$status" -eq 0 ]
    [ "$output" = "$OTHER_CHILD" ]
    cd "$output"
    [ -d ".dwp/plans/PLAN_feat_child" ]
}

@test "an unregistered child root is surfaced, not guessed" {
    build_fixture
    cd "$HUB"
    run resolve_child_root PLAN_feat_missing
    [ "$status" -eq 1 ]
    [[ "$output" =~ "not registered" ]]
    # And nothing silently fell back to the repositories/ convention.
    [[ "$output" != *"repositories/childrepo"* ]]
}

# ------------------------------------------------- static doc contracts

@test "no /workspace literal remains anywhere in the hub surface" {
    local f hits=""
    for f in "$SKILL/guide/orchestrator.md" "$SKILL/execute/orchestrator.md" \
             "$SKILL"/examples/ORCHESTRATOR_TASK_TEMPLATE_*.md; do
        hits="$hits$(grep -n '/workspace' "$f" | sed "s|^|$(basename "$f"):|")"
    done
    [ -z "$hits" ]
}

@test "no stale results/ output convention remains in the hub guide" {
    run bash -c "grep -n 'results/' '$SKILL/guide/orchestrator.md' | grep -v analysis_results || true"
    [ -z "$output" ]
}

@test "no unsupported wall-clock percentage claims remain in orchestrator docs" {
    local f
    for f in "$SKILL/guide/orchestrator.md" "$SKILL/execute/orchestrator.md"; do
        run grep -En '~[0-9]+%|[0-9]+% wall|[0-9]+% vs' "$f"
        [ "$status" -ne 0 ]
    done
}

@test "execute/orchestrator.md documents both DWP_DIR isolation patterns" {
    grep -q 'unset DWP_DIR' "$SKILL/execute/orchestrator.md"
    grep -q 'child-specific override' "$SKILL/execute/orchestrator.md"
    grep -q 'Return to the saved hub root' "$SKILL/execute/orchestrator.md"
}
