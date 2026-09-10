#!/usr/bin/env bats
# Tests for scripts/check-guide-migration.py (dev-only guide split validator).

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    CHECK="$REPO_ROOT/scripts/check-guide-migration.py"
    TMPDIR_TEST="$(mktemp -d)"
}
teardown() { rm -rf "$TMPDIR_TEST"; }

@test "the shipped guide passes links, section map and pointer checks" {
    run python3 "$CHECK" --pack "$REPO_ROOT/skills/deepworkplan"
    [ "$status" -eq 0 ]
}

@test "GUIDE.md routing index stays small (under 8 KB)" {
    [ "$(wc -c < "$REPO_ROOT/skills/deepworkplan/guide/GUIDE.md")" -lt 8192 ]
}

@test "a broken guide link is detected" {
    cp -r "$REPO_ROOT/skills/deepworkplan" "$TMPDIR_TEST/pack"
    echo '[bad](../guide/does-not-exist.md)' >> "$TMPDIR_TEST/pack/create/SKILL.md"
    run python3 "$CHECK" --pack "$TMPDIR_TEST/pack"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'broken link'
}

@test "a section missing from the GUIDE.md map is detected" {
    cp -r "$REPO_ROOT/skills/deepworkplan" "$TMPDIR_TEST/pack"
    printf '\n## 99. Orphan Section\n\ntext\n' >> "$TMPDIR_TEST/pack/guide/structure.md"
    run python3 "$CHECK" --pack "$TMPDIR_TEST/pack"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'not in GUIDE.md map'
}

@test "a lost line is detected against a baseline" {
    cp -r "$REPO_ROOT/skills/deepworkplan" "$TMPDIR_TEST/pack"
    printf 'A unique baseline line that no guide file contains.\n' > "$TMPDIR_TEST/baseline.md"
    run python3 "$CHECK" --pack "$TMPDIR_TEST/pack" --baseline "$TMPDIR_TEST/baseline.md"
    [ "$status" -ne 0 ]
    echo "$output" | grep -q 'line lost'
}
