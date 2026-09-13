#!/usr/bin/env bats
# Contract tests for the CI workflow's own guarantees.
#
# A workflow that runs a suite without its dependencies goes GREEN having
# verified nothing, and a selection that matches no tests does the same. Both
# look like success. This suite pins the guards against them, and derives what
# it can from the repository rather than from a second copy of the workflow.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    CI="$REPO_ROOT/.github/workflows/ci.yml"
    SK="$REPO_ROOT/skills/deepworkplan"
    [ -f "$CI" ]
}

@test "the bats job installs every dependency its tests import" {
    # Derive the requirement from the tests themselves: any module they import
    # under a skip guard must be installed by the job that runs them.
    local needed=""
    grep -rhoE "import ([a-z_]+)' 2>/dev/null \|\| skip" "$REPO_ROOT"/tests/*.bats \
        | sed -E "s/import ([a-z_]+)'.*/\1/" | sort -u > /tmp/needed.txt || true
    [ -s /tmp/needed.txt ]
    while IFS= read -r mod; do
        grep -qE "pip install .*$mod" "$CI" || needed="$needed $mod"
    done < /tmp/needed.txt
    if [ -n "$needed" ]; then
        echo "tests skip without these, and CI does not install them:$needed"
        echo "A skipped required case is a silent gap, not a pass."
        return 1
    fi
}

@test "the bats job refuses an empty selection and undeclared skips" {
    # Bats exits 0 for a plan of zero. The job must read the TAP plan.
    grep -qF '1\.\.\\([0-9]*\)' "$CI" || grep -q 'TAP plan' "$CI"
    grep -q "the suite did not run" "$CI"
    # And it must fail on any skip but the one documented environment case.
    grep -q "an undeclared skip occurred" "$CI"
    grep -qF "auto-detect can't reach the 'no agents' branch" "$CI"
    # That allowance must still correspond to a real skip in the suite, or the
    # exception is stale and hiding something.
    grep -rqF "auto-detect can't reach the 'no agents' branch" "$REPO_ROOT"/tests/*.bats
}

@test "the installer smoke asserts every sub-skill setup.sh actually links" {
    # The oracle is setup.sh, not a hardcoded list in two places.
    # setup.sh declares the list once, in its SKILLS array. Read it from there
    # so this assertion cannot drift from the installer it describes. A failure
    # to derive it is a defect in this test, never a reason to skip: a skipped
    # case is the silent gap this whole suite exists to prevent.
    local expected
    expected="$(sed -n 's/^SKILLS=(\(.*\))$/\1/p' "$REPO_ROOT/setup.sh" | tr -d '"' | tr ' ' '\n' | grep -c . >/dev/null; \
        sed -n 's/^SKILLS=(\(.*\))$/\1/p' "$REPO_ROOT/setup.sh" | tr -d '"')"
    if [ -z "$expected" ]; then
        echo "could not read the SKILLS array from setup.sh — fix this derivation"
        return 1
    fi
    [ "$(printf '%s\n' $expected | wc -l | tr -d ' ')" -eq 9 ]
    for v in $expected; do
        grep -qE "for v in [^;]*\b$v\b" "$CI" || {
            echo "setup.sh links deepworkplan-$v but the CI smoke never checks it"
            return 1
        }
    done
    # And the prose count must match the real one.
    if grep -qi "six sub-skill" "$CI"; then
        echo "the installer smoke still claims six sub-skills"; return 1
    fi
}

@test "the documented Python floor is actually exercised, stdlib-only" {
    grep -q "python-floor:" "$CI"
    grep -qE "python-version: '3\.9'" "$CI"
    # The job must prove the stdlib path is the one under test.
    grep -q "this job must prove the stdlib-only path" "$CI"
    # It must run a helper, not merely compile it.
    grep -q "conformance.sh --plan PLAN_lite_fixture" "$CI"
    # Every shipped Python helper must be covered by it.
    local missing=""
    while IFS= read -r helper; do
        rel="${helper#"$REPO_ROOT/"}"
        grep -qF "$rel" "$CI" || missing="$missing $rel"
    done < <(find "$SK" -name '*.py' -not -path '*__pycache__*' | sort)
    if [ -n "$missing" ]; then
        echo "shipped helper(s) not compiled on the documented floor:$missing"
        return 1
    fi
    # The floor the workflow tests must equal the floor the docs claim.
    grep -q "Python 3.9+" "$REPO_ROOT/docs/TESTING_GUIDE.md"
}

@test "CI lints every shell script the repository ships or gates numbers with" {
    local missing=""
    while IFS= read -r script; do
        rel="${script#"$REPO_ROOT/"}"
        case "$rel" in
            skills/*|scripts/*|setup.sh|tests/efficiency/*) ;;
            *) continue ;;
        esac
        # Either named outright, or covered by a glob the job runs.
        grep -qF "$rel" "$CI" && continue
        dir="$(dirname "$rel")"
        grep -qF "shellcheck $dir/*.sh" "$CI" && continue
        missing="$missing $rel"
    done < <(find "$REPO_ROOT" -name '*.sh' -not -path '*/.git/*' -not -path '*/.agents/*' | sort)
    if [ -n "$missing" ]; then
        echo "shell script(s) never linted by CI:$missing"; return 1
    fi
}

@test "CI needs no secret, no credential and no network-only runtime dependency" {
    # The reliability guarantees must reproduce from the repository alone.
    if grep -nE 'secrets\.[A-Z_]+' "$CI"; then
        echo "ci.yml references a repository secret — the deterministic gate must not need one"
        return 1
    fi
    # No AI-reviewer workflow is shipped by this repository (docs/SECURITY.md).
    [ ! -f "$REPO_ROOT/.github/workflows/pr-review.yml" ]
    # And nothing in CI may depend on the gitignored plan directory.
    if grep -nE '\.dwp/' "$CI"; then
        echo "ci.yml reads the gitignored plan directory"; return 1
    fi
}

@test "the workflow reference documents the two silent-green failure modes" {
    local doc="$REPO_ROOT/.github/docs/WORKFLOWS.md"
    flat="$(tr '\n' ' ' < "$doc" | tr -s ' ')"
    echo "$flat" | grep -qF -- "A green job is not automatically a verified one."
    echo "$flat" | grep -qF -- "green having verified none of them"
    echo "$flat" | grep -qF -- "all nine"
    echo "$flat" | grep -qF -- "python-floor"
}
