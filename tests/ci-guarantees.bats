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

# ------------------------------------------------ pre-release channel (v7)

# _step <workflow> <step name> — print the `run:` script of one step.
_step() {
    python3 - "$1" "$2" <<'PY'
import sys, yaml
wf = yaml.safe_load(open(sys.argv[1]))
for job in wf['jobs'].values():
    for step in job['steps']:
        if step.get('name') == sys.argv[2]:
            print(step['run'])
            sys.exit(0)
sys.exit('step not found: ' + sys.argv[2])
PY
}

# _repo <version> <tags...> — a throwaway repo whose router carries <version>.
_repo() {
    local version="$1"; shift
    R="$(cd "$(mktemp -d)" && pwd -P)"
    git -C "$R" init -q
    mkdir -p "$R/skills/deepworkplan"
    printf -- '---\nname: deepworkplan\nversion: "%s"\n---\n' "$version" > "$R/skills/deepworkplan/SKILL.md"
    git -C "$R" add -A
    git -C "$R" -c user.email=t@t -c user.name=t commit -qm "chore: base"
    for t in "$@"; do git -C "$R" tag "$t"; done
    git -C "$R" -c user.email=t@t -c user.name=t commit -q --allow-empty -m "feat(skill)!: something new"
}

_decide() { # _decide <head message> — run auto-release's decision step in $R
    _step "$REPO_ROOT/.github/workflows/auto-release.yml" "Determine bump level + new version" > "$R/decide.sh"
    ( cd "$R" && GITHUB_OUTPUT="$R/out" HEAD_MSG="$1" bash "$R/decide.sh" >/dev/null )
    cat "$R/out"
}

@test "stable releases ignore pre-release tags when finding the last release" {
    _repo 6.1.0 v6.1.0 v7.0.0-beta.1
    out="$(_decide 'feat(skill)!: something new')"
    printf '%s\n' "$out" | grep -qx 'last_tag=v6.1.0'
    printf '%s\n' "$out" | grep -qx 'new_version=7.0.0'
    rm -rf "$R"
}

@test "a pre-release in flight blocks stable releases unless the merge says [graduate]" {
    _repo 7.0.0-beta.1 v6.1.0 v7.0.0-beta.1
    out="$(_decide 'fix(docs): typo')"
    printf '%s\n' "$out" | grep -qx 'skip=true'
    ! printf '%s\n' "$out" | grep -q '^new_version='
    rm -f "$R/out"
    out="$(_decide 'Merge: release 7.0.0 [graduate]')"
    printf '%s\n' "$out" | grep -qx 'new_version=7.0.0'
    printf '%s\n' "$out" | grep -qx 'bump=graduate'
    rm -rf "$R"
}

@test "prerelease.yml validates the version, refuses an existing tag, never publishes latest" {
    WF="$REPO_ROOT/.github/workflows/prerelease.yml"
    grep -q '^  workflow_dispatch:' "$WF"
    ! grep -qE '^  (push|pull_request|schedule):' "$WF"
    grep -q -- '--prerelease --latest=false' "$WF"
    grep -qF 'files: SHA256SUMS' "$REPO_ROOT/.github/workflows/auto-release.yml"
    grep -q 'gh release create "$TAG" SHA256SUMS' "$WF"
    grep -q 'bash scripts/generate-checksums.sh' "$WF"
    grep -q 'npx --yes skills add "DailybotHQ/deepworkplan-skill@${TAG}"' "$WF"
    _repo 6.1.0 v6.1.0 v7.0.0-beta.1
    _step "$WF" "Validate the requested version" > "$R/validate.sh"
    for bad in 7.0.0 7.0.0-beta v7.0.0-beta.1 '7.0.0-beta.1; touch pwned' 7.0.0-nightly.1; do
        ( cd "$R" && GITHUB_OUTPUT="$R/vout" REQUESTED="$bad" bash "$R/validate.sh" >/dev/null 2>&1 ) && { echo "accepted $bad"; return 1; }
    done
    [ ! -e "$R/pwned" ]
    # an existing pre-release tag is never moved
    ( cd "$R" && GITHUB_OUTPUT="$R/vout" REQUESTED=7.0.0-beta.1 bash "$R/validate.sh" >/dev/null 2>&1 ) && { echo "moved an existing tag"; return 1; }
    ( cd "$R" && GITHUB_OUTPUT="$R/vout" REQUESTED=7.0.0-beta.2 bash "$R/validate.sh" >/dev/null )
    grep -qx 'tag=v7.0.0-beta.2' "$R/vout"
    grep -qx 'last_stable=v6.1.0' "$R/vout"
    rm -rf "$R"
}

@test "the stable channel never offers a pre-release; the docs state the release order" {
    tr '\n' ' ' < "$SK/upgrade/SKILL.md" | tr -s ' ' | grep -qF 'ignore pre-release tags (`vX.Y.Z-beta.N`, `-rc.N`, `-alpha.N`) unless the developer explicitly asks for the pre-release channel'
    grep -q '^## 4. prerelease.yml' "$REPO_ROOT/.github/docs/WORKFLOWS.md"
    grep -qF 'Merge the work to `main` with `[skip release]`' "$REPO_ROOT/.github/docs/WORKFLOWS.md"
    grep -q '^## 4.0.1 Pre-releases (manual)' "$REPO_ROOT/PUBLISHING.md"
}
