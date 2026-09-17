#!/usr/bin/env bats
# Packaging integrity: only `skills/deepworkplan/` reaches a user's disk.
#
# Every test here runs against an EXPORTED copy of the pack in a scratch
# directory, with no `tests/`, `scripts/`, contributor docs or repository
# checkout anywhere near it — because that is the shape a downstream user
# actually installs. A helper that quietly reaches back into this repository
# works perfectly here and fails for everyone else.
#
# Run with:  bats tests/
# Requires:  bats-core, python3

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    EXPORT="$(mktemp -d)"
    cp -R "$REPO_ROOT/skills/deepworkplan" "$EXPORT/pack"
    find "$EXPORT/pack" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    PACK="$EXPORT/pack"
    WORK="$(mktemp -d)"
}

teardown() {
    rm -rf "$EXPORT" "$WORK" "${FAKEBIN:-}"
}

fixture_plan() {
    cp -R "$REPO_ROOT/tests/fixtures/lite-plan/.dwp" "$WORK/.dwp"
    echo "$WORK/.dwp/plans/PLAN_lite_fixture"
}

@test "the exported pack contains no contributor file" {
    # The ship boundary, checked from the export rather than from prose.
    local strays=""
    for forbidden in tests scripts .github docs CONTRIBUTING.md AGENTS.md; do
        [ -e "$PACK/$forbidden" ] && strays="$strays $forbidden"
    done
    if [ -n "$strays" ]; then
        echo "contributor surface shipped inside the pack:$strays"; return 1
    fi
    # And nothing in the runtime may reference those paths as if they were present.
    local escaped
    escaped="$(grep -rnoE '(^|[^A-Za-z0-9_/-])(tests|scripts)/[A-Za-z0-9_./-]+' \
        "$PACK" --include=*.py --include=*.sh || true)"
    # Prose may legitimately name a TARGET repository's tests/ or scripts/;
    # executable code may not.
    if [ -n "$escaped" ]; then
        echo "runtime code references a contributor path:"; printf '%s\n' "$escaped"; return 1
    fi
}

@test "the read-only checker runs from an export with nothing else present" {
    local plan; plan="$(fixture_plan)"
    [ -d "$plan" ]
    run bash "$PACK/verify/conformance.sh" --plan PLAN_lite_fixture "$WORK"
    echo "$output"
    [ "$status" -eq 0 ]
    [[ "$output" == *"CONFORMANT"* ]]
}

@test "onboarding and verification resolve their working-principles resource from an export" {
    run python3 - "$PACK" <<'PY'
from pathlib import Path
import re
import sys

pack = Path(sys.argv[1]).resolve()
for flow in ('onboard', 'verify'):
    entry = pack / flow / 'SKILL.md'
    links = re.findall(r'\]\(([^)]+working-principles\.md)\)', entry.read_text())
    assert links, f'{flow} cannot discover its working-principles resource'
    for link in links:
        target = (entry.parent / link).resolve()
        assert pack in target.parents, f'{flow} resource escapes the installed pack'
        assert target.is_file() and target.stat().st_size, f'{flow} resource missing'
PY
    echo "$output"
    [ "$status" -eq 0 ]
}

@test "the contributor agent entry point stays within budget and its local document links resolve" {
    run python3 - "$REPO_ROOT" <<'PY'
from pathlib import Path
import re
import sys

repo = Path(sys.argv[1])
text = (repo / 'AGENTS.md').read_text()
assert 150 <= len(text.splitlines()) <= 500, 'AGENTS.md exceeds its lean-index budget'
text = re.sub(r'```.*?```', '', text, flags=re.S)
for link in re.findall(r'\]\(([^)]+)\)', text):
    if '://' in link or link.startswith('#'):
        continue
    target = repo / link.split('#')[0]
    assert target.exists(), f'Broken AGENTS.md link: {link}'
PY
    echo "$output"
    [ "$status" -eq 0 ]
}

@test "the guarded writer and the completion transaction run from an export" {
    local plan; plan="$(fixture_plan)"
    run python3 "$PACK/shared/update-state.py" "$plan/state.json" \
        --task 1 --status in_progress
    echo "$output"
    [ "$status" -eq 0 ]
    # And the finalizer refuses an unearned publication rather than crashing on
    # a missing contributor file.
    run python3 "$PACK/shared/finalize_plan.py" "$plan" --candidate "$plan/state.json"
    echo "$output"
    [ "$status" -ne 0 ]
    [[ "$output" != *"Traceback"* ]]
    [[ "$output" == *"NOT COMPLETED"* ]]
}

@test "a missing interpreter degrades honestly instead of passing" {
    # The claim in docs/TESTING_GUIDE.md: without a capable interpreter the
    # checker exits non-zero with UNVERIFIED — it never reports a result it did
    # not verify.
    local plan; plan="$(fixture_plan)"
    FAKEBIN="$(mktemp -d)"
    local tool path
    for tool in bash sed awk grep find ls cat tr head tail sort wc dirname \
                basename mktemp rm cp mv git date printf test; do
        path="$(command -v "$tool" 2>/dev/null)" && ln -sf "$path" "$FAKEBIN/$tool"
    done
    [ -x "$FAKEBIN/grep" ] || skip "could not build a python3-free PATH on this host"
    run env PATH="$FAKEBIN" bash "$PACK/verify/conformance.sh" --plan PLAN_lite_fixture "$WORK"
    echo "$output"
    [ "$status" -ne 0 ]
    [[ "$output" == *"UNVERIFIED"* ]]
    [[ "$output" != *"CONFORMANT"* ]]
}

@test "the exported runtime makes no network call" {
    # Static: no runtime helper names a network client or a URL scheme it would
    # fetch. Documentation links are prose and live in .md files.
    local hits
    # Word-boundary, command-position matches only: "in sync with" and
    # "completed_count" must not read as a netcat invocation.
    hits="$(grep -rnE '(^|[^A-Za-z0-9_.])(urllib|httpx|socket\.(socket|create_connection)|curl|wget|netcat)($|[^A-Za-z0-9_])' \
        "$PACK" --include=*.py --include=*.sh || true)"
    hits="$hits$(grep -rnE '^[[:space:]]*(import|from)[[:space:]]+(requests|urllib|http\.client|socket)\b' \
        "$PACK" --include=*.py || true)"
    if [ -n "$hits" ]; then
        echo "runtime code reaches the network:"; printf '%s\n' "$hits"; return 1
    fi
}

@test "published schema snapshots are unchanged and still validate their fixtures" {
    # The schemas are a public contract: a plan written against v1 or v2 must
    # keep validating. Compare the exported copies against the committed ones
    # byte for byte, then run the repo's own schema regression.
    local schema
    for schema in "$PACK"/spec/schema/*.json; do
        [ -f "$schema" ] || continue
        diff -q "$schema" "$REPO_ROOT/skills/deepworkplan/spec/schema/$(basename "$schema")"
    done
    run python3 "$REPO_ROOT/scripts/check-schema-contract.py"
    echo "$output"
    [ "$status" -eq 0 ]
}

@test "the dogfood mirror is byte-identical to the shipped pack" {
    run diff -rq --exclude=__pycache__ \
        "$REPO_ROOT/skills/deepworkplan" "$REPO_ROOT/.agents/skills/deepworkplan"
    echo "$output"
    [ "$status" -eq 0 ]
    # And the lock records the mirror it actually has.
    [ -f "$REPO_ROOT/skills-lock.json" ]
    grep -q 'deepworkplan' "$REPO_ROOT/skills-lock.json"
}

@test "every evidence file published with the pack is sanitized" {
    # tests/reliability/evidence/ ships in the repository (not the pack) and is
    # read by reviewers. An absolute path there leaks a machine layout.
    local leaked
    leaked="$(grep -rlE '/(app|home|Users|root)/' "$REPO_ROOT/tests/reliability/evidence/" || true)"
    if [ -n "$leaked" ]; then
        echo "evidence file(s) contain absolute paths:"; printf '%s\n' "$leaked"; return 1
    fi
    # And each one must record which round it belongs to and its real tree state,
    # so a PASS cannot be read as stronger than the conditions it ran under.
    local f
    for f in "$REPO_ROOT"/tests/reliability/evidence/*.json; do
        python3 - "$f" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for key in ("run_id", "verdict", "round", "tree_state", "oracles"):
    assert d.get(key) is not None, f"{sys.argv[1]}: missing {key}"
assert d["verdict"] in ("PASS", "FAIL"), d["verdict"]
PY
    done
}
