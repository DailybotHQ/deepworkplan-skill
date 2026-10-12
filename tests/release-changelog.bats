#!/usr/bin/env bats
# auto-release.yml "Update CHANGELOG.md": a leading `## [Unreleased]` block
# (hand-written release notes such as a `### Learnings` section) is folded
# into the release section the bot generates and removed from the file;
# without the block the step behaves byte-for-byte as before. The real step
# is extracted from the workflow and run against throwaway fixtures.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
WF="$REPO_ROOT/.github/workflows/auto-release.yml"

setup() {
    python3 -c 'import yaml' 2>/dev/null || skip "PyYAML not installed (CI installs it)"
    W="$(cd "$(mktemp -d)" && pwd -P)"
    mkdir -p "$W/run" "$W/tmp"
}

teardown() { rm -rf "${W:-/nonexistent}"; }

# _step <workflow file> — the run text of its "Update CHANGELOG.md" step.
_step() {
    python3 - "$1" <<'PY'
import sys, yaml
for job in yaml.safe_load(open(sys.argv[1]))['jobs'].values():
    for step in job['steps']:
        if step.get('name') == 'Update CHANGELOG.md':
            print(step['run'])
            sys.exit(0)
sys.exit('step not found')
PY
}

# _run <step file> — run it in $W/run with a fixed version, date-free compare.
_run() {
    ( cd "$W/run" && NEW_VERSION=9.9.0 RUNNER_TEMP="$W/tmp" \
        COMMITS=$'feat(skill): one\nfix(docs): two' bash "$1" )
}

_base() {
    cat <<'MD'
# Changelog

Intro paragraph.

MD
}

_old_section() {
    cat <<'MD'
## [9.8.0] — 2026-01-01

### Changes

- older
MD
}

@test "an Unreleased block is folded into the new release section and removed" {
    _step "$WF" > "$W/step.sh"
    { _base; printf '## [Unreleased]\n\n### Learnings\n\n- Gates are hypotheses (6/6 audits).\n- Pins are data.\n\n'; _old_section; } > "$W/run/CHANGELOG.md"
    _run "$W/step.sh"
    ! grep -q 'Unreleased' "$W/run/CHANGELOG.md" || false
    python3 - "$W/run/CHANGELOG.md" "$W/tmp/RELEASE_NOTES.md" <<'PY'
import re, sys
log, notes = open(sys.argv[1]).read(), open(sys.argv[2]).read()
section = re.search(r'(## \[9\.9\.0\][^\n]*\n.*?)(?=## \[9\.8\.0\])', log, re.S).group(1)
body = section.split('\n', 1)[1]
assert body == '\n### Changes\n\n- feat(skill): one\n- fix(docs): two\n\n### Learnings\n\n- Gates are hypotheses (6/6 audits).\n- Pins are data.\n\n\n', repr(body)
assert notes + '\n' == section, (notes, section)   # the insert adds one blank line, as before the fold
assert log.startswith('# Changelog\n\nIntro paragraph.\n\n## [9.9.0]'), log[:80]
assert log.count('## [9.8.0]') == 1 and log.rstrip().endswith('- older')
PY
}

@test "a release without an Unreleased block keeps today's section" {
    _step "$WF" > "$W/step.sh"
    { _base; _old_section; } > "$W/run/CHANGELOG.md"
    _run "$W/step.sh"
    grep -qF '### Changes' "$W/tmp/RELEASE_NOTES.md"
    ! grep -q 'Learnings' "$W/tmp/RELEASE_NOTES.md" || false
    [ -s "$W/run/CHANGELOG.md" ]
}

@test "with no Unreleased block the output is byte-identical to the pre-fold step" {
    git -C "$REPO_ROOT" cat-file -e 782e1e7 2>/dev/null || skip "base revision 782e1e7 not in this clone"
    git -C "$REPO_ROOT" show 782e1e7:.github/workflows/auto-release.yml > "$W/old.yml"
    _step "$W/old.yml" > "$W/old.sh"
    _step "$WF" > "$W/new.sh"
    for variant in old new; do
        rm -rf "$W/run" "$W/tmp" && mkdir -p "$W/run" "$W/tmp"
        { _base; _old_section; } > "$W/run/CHANGELOG.md"
        _run "$W/$variant.sh"
        cp "$W/run/CHANGELOG.md" "$W/$variant.CHANGELOG.md"
        cp "$W/tmp/RELEASE_NOTES.md" "$W/$variant.NOTES.md"
    done
    cmp "$W/old.CHANGELOG.md" "$W/new.CHANGELOG.md"
    cmp "$W/old.NOTES.md" "$W/new.NOTES.md"
}

@test "the fold adds no permission, secret or network call to the workflow" {
    git -C "$REPO_ROOT" cat-file -e 782e1e7 2>/dev/null || skip "base revision 782e1e7 not in this clone"
    python3 - "$WF" <(git -C "$REPO_ROOT" show 782e1e7:.github/workflows/auto-release.yml) <<'PY'
import sys, yaml
new, old = (yaml.safe_load(open(p)) for p in sys.argv[1:3])
assert new.get('permissions') == old.get('permissions')
for job in new['jobs']:
    assert new['jobs'][job].get('permissions') == old['jobs'][job].get('permissions'), job
step = lambda wf: next(s for j in wf['jobs'].values() for s in j['steps'] if s.get('name') == 'Update CHANGELOG.md')
assert step(new).get('env') == step(old).get('env')
run = step(new)['run']
assert 'secrets.' not in run and 'curl' not in run and 'wget' not in run and 'gh ' not in run
PY
}
