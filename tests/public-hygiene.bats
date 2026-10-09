#!/usr/bin/env bash
# scripts/check-public-hygiene.sh (ecosystem amendment A3, S3): the real
# script against throwaway git repositories with planted content, plus the
# live repository (which must be clean).
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
CHECK="$REPO_ROOT/scripts/check-public-hygiene.sh"

setup() {
  R="$(cd "$(mktemp -d)" && pwd -P)"
  git -C "$R" init -q
}
teardown() { rm -rf "$R"; }

_plant() { # _plant <path> <content>
  mkdir -p "$R/$(dirname "$1")"
  printf '%s\n' "$2" > "$R/$1"
  git -C "$R" add "$1"
}

@test "the live repository is clean" {
  run bash "$CHECK" "$REPO_ROOT"
  [ "$status" -eq 0 ]
  [[ "$output" == "OK: public hygiene"* ]] || return 1
}

@test "a clean repository passes; public role aliases are allowed" {
  _plant README.md 'Report to security@dailybot.com or support@dailybot.com; bot ops@dailybot.com.'
  run bash "$CHECK" "$R"
  [ "$status" -eq 0 ]
}

@test "personal paths, private org, repo and tooling names, private addresses fail" {
  _plant a.md "see /Users/$(printf jdoe)/projects/x"
  _plant b.md "$(printf 'DailyBot-%s' Inc)/secret-repo"
  _plant c.md "clone $(printf 'dailybot-%s' core) first"
  _plant d.md "run $(printf 'db%s' dev) up"
  _plant e.md "mail $(printf 'jane%sdailybot.com' @)"
  run bash "$CHECK" "$R"
  [ "$status" -eq 1 ]
  for label in personal-path private-org private-repo internal-tooling private-email; do
    [[ "$output" == *"[$label]"* ]] || { echo "missing $label"; return 1; }
  done
}

@test "a real-looking secret fails even when its file is allowlisted; values are never printed" {
  key="AKIA$(printf 'ABCDEFGHIJKLMNOP')"
  _plant config.py "AWS = '$key'"
  printf 'config.py  needs it\n' > "$R/.public-hygiene-allow"; git -C "$R" add .public-hygiene-allow
  run bash "$CHECK" "$R"
  [ "$status" -eq 1 ]
  [[ "$output" == *"[aws-key]"* ]] || return 1
  [[ "$output" != *"$key"* ]] || return 1
}

@test "an obviously fake fixture passes only when allowlisted with a reason" {
  _plant tests/fixture.txt "fake_token = '$(printf 'ghp_%s' 0123456789abcdefghijABCDEFGHIJ012345)' # planted test value"
  run bash "$CHECK" "$R"
  [ "$status" -eq 1 ]
  printf 'tests/fixture.txt  planted secret-shaped fixture for scanner tests\n' > "$R/.public-hygiene-allow"
  git -C "$R" add .public-hygiene-allow
  run bash "$CHECK" "$R"
  [ "$status" -eq 0 ]
}

@test "vendored skill copies under .agents/skills/ are out of scope; untracked files are not scanned" {
  _plant .agents/skills/upstream/SKILL.md "upstream text naming $(printf 'dailybot-%s' core)"
  printf 'see /Users/%s/x\n' jdoe > "$R/untracked.md"
  run bash "$CHECK" "$R"
  [ "$status" -eq 0 ]
}

@test "a non-repository root is a usage error, not a pass" {
  run bash "$CHECK" "$(mktemp -d)"
  [ "$status" -eq 2 ]
}
