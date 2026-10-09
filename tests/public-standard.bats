#!/usr/bin/env bash
# Ecosystem public repository standard (parent amendment A3, S1 + S4 files):
# the community files exist with the sections A3 requires, the README keeps
# the A3 section order, and the repository keeps its public hygiene.
# (S2 — GitHub settings — is checked live by scripts/check-github-settings.sh;
# S3 — hygiene — by scripts/check-public-hygiene.sh and tests/public-hygiene.bats.)
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"

@test "S1 files exist" {
  for f in README.md LICENSE CHANGELOG.md CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md \
           AGENTS.md docs/TESTING_GUIDE.md .gitignore .github/PULL_REQUEST_TEMPLATE.md \
           .github/CODEOWNERS .github/dependabot.yml .github/ISSUE_TEMPLATE/bug_report.yml \
           .github/ISSUE_TEMPLATE/feature_request.yml .github/ISSUE_TEMPLATE/config.yml \
           .github/workflows/ci.yml .github/workflows/auto-release.yml .github/workflows/prerelease.yml; do
    [ -s "$REPO_ROOT/$f" ] || { echo "missing $f"; return 1; }
  done
  [ -L "$REPO_ROOT/CLAUDE.md" ] && [ "$(readlink "$REPO_ROOT/CLAUDE.md")" = "AGENTS.md" ]
}

@test "README follows the A3 section order and ends with the ecosystem footer" {
  python3 - "$REPO_ROOT/README.md" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
heads = [h.strip() for h in re.findall(r'^## (.+)$', text, re.M)]
order = ['What it is', 'Install', 'Quickstart', 'Documentation', 'Security', 'Contributing', 'License']
pos = [heads.index(h) for h in order]
assert pos == sorted(pos), (heads, order)
assert re.search(r'^# .+', text, re.M)
for badge in ('actions/workflows/ci.yml/badge.svg', 'img.shields.io/github/v/release', 'License-MIT'):
    assert badge in text.split('## What it is')[0], badge
assert re.search(r'skills add DailybotHQ/deepworkplan-skill@v\d+\.\d+\.\d+', text), 'no pinned install line'
assert text.rstrip().endswith('Part of the [DeepWorkPlan](https://deepworkplan.com) ecosystem — works on its own.'), 'footer'
PY
}

@test "LICENSE is MIT (SPDX-detectable); the copyright holder is the developer's decision" {
  head -1 "$REPO_ROOT/LICENSE" | grep -qx 'MIT License'
  grep -q 'Permission is hereby granted, free of charge' "$REPO_ROOT/LICENSE"
}

@test "SECURITY.md: supported versions, private reporting, email, response targets, no public issues" {
  f="$REPO_ROOT/SECURITY.md"
  grep -q '^## Supported Versions' "$f"
  grep -qF '| `7.0.0` pre-releases' "$f"
  grep -qF 'https://github.com/DailybotHQ/deepworkplan-skill/security' "$f"
  grep -qF 'security@dailybot.com' "$f"
  grep -qF '**Response targets:**' "$f"
  grep -qi 'never open a public issue' "$f"
}

@test "CODE_OF_CONDUCT is the Contributor Covenant 2.1 with a reachable contact" {
  f="$REPO_ROOT/CODE_OF_CONDUCT.md"
  grep -q '^# Contributor Covenant Code of Conduct' "$f"
  grep -qF 'version 2.1' "$f"
  grep -qE '(conduct|security)@dailybot\.com' "$f"
}

@test "CONTRIBUTING: setup, gate, Conventional Commits, PR flow, no DCO, AGENTS.md" {
  f="$REPO_ROOT/CONTRIBUTING.md"
  grep -q '^## Local development setup' "$f"
  grep -q '^## Commit conventions' "$f"
  grep -q '^## Pull request workflow' "$f"
  grep -qF 'No DCO sign-off is required' "$f"
  grep -qF '[`AGENTS.md`](AGENTS.md)' "$f"
}

@test "issue forms: blank issues off, security routed to SECURITY.md; PR template asks for no secrets/private context" {
  grep -qx 'blank_issues_enabled: false' "$REPO_ROOT/.github/ISSUE_TEMPLATE/config.yml"
  grep -qF 'SECURITY.md' "$REPO_ROOT/.github/ISSUE_TEMPLATE/config.yml"
  [ ! -e "$REPO_ROOT/.github/ISSUE_TEMPLATE/bug_report.md" ]
  grep -qF 'No secrets and no private context' "$REPO_ROOT/.github/PULL_REQUEST_TEMPLATE.md"
}

@test "CODEOWNERS and dependabot (github-actions weekly)" {
  grep -qE '^\* @[A-Za-z0-9-]+' "$REPO_ROOT/.github/CODEOWNERS"
  python3 - "$REPO_ROOT/.github/dependabot.yml" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
ups = {u['package-ecosystem']: u for u in d['updates']}
assert ups['github-actions']['schedule']['interval'] == 'weekly', ups
PY
}

@test ".gitignore keeps plan output, scratch, env files and OS junk out" {
  cd "$REPO_ROOT"
  for p in .dwp/x tmp/x .env .env.production .DS_Store; do
    git check-ignore -q "$p" || { echo "not ignored: $p"; return 1; }
  done
  ! git check-ignore -q .env.example
}

@test "CHANGELOG keeps the Keep a Changelog format; CI runs the hygiene check" {
  grep -qF '[Keep a Changelog]' "$REPO_ROOT/CHANGELOG.md"
  grep -q 'bash scripts/check-public-hygiene.sh' "$REPO_ROOT/.github/workflows/ci.yml"
}
