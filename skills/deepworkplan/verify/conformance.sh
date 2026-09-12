#!/usr/bin/env bash
# conformance.sh — automated DeepWorkPlan conformance check (read-only).
#
# Checks that a repository (or agent workspace) is DeepWorkPlan-conformant and
# that its plans are well-formed, per the normative spec in ../spec/. This is
# the mechanical layer of the verify sub-skill: it never edits anything and it
# exits 0 only when every MUST-level check passes.
#
# Usage:
#   conformance.sh [TARGET_DIR]            # repo checks + every plan
#   conformance.sh --repo-only [TARGET_DIR]
#   conformance.sh --plan PLAN_NAME [TARGET_DIR]
#
# Accepts both plan eras: current v2-state plans (Lite or Full) and plans
# authored before them. The plan contract itself lives in plan_contract.py.
#
# Bash 3.2 compatible (macOS default). Requires only git + coreutils; uses
# Python 3.9+ to validate plans; exits 2 (UNVERIFIED) when unavailable.

set -euo pipefail

MODE="all"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAN_FILTER=""
TARGET="."

while [ $# -gt 0 ]; do
  case "$1" in
    --repo-only)
      MODE="repo"
      ;;
    --plan)
      MODE="plan"
      shift
      PLAN_FILTER="${1:-}"
      if [ -z "$PLAN_FILTER" ]; then
        echo "error: --plan requires a plan name" >&2
        exit 2
      fi
      ;;
    --help|-h)
      sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      TARGET="$1"
      ;;
  esac
  shift
done

cd "$TARGET"

# Match shared/context.sh: resolve from the git root (or cwd outside git),
# retaining the documented absolute DWP_DIR override without parsing JSON.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  cd "$(git rev-parse --show-toplevel)"
fi
PLAN_ROOT="${DWP_DIR:-$PWD/.dwp}"
case "$PLAN_ROOT" in
  /*) ;;
  *) echo "error: DWP_DIR must be an absolute path" >&2; exit 2 ;;
esac
if [ -d "$PLAN_ROOT" ]; then
  PLAN_ROOT="$(cd "$PLAN_ROOT" && pwd -P)"
fi

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
UNVERIFIED_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '  [x] %s\n' "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '  [ ] %s\n' "$1"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf '  [~] %s (SHOULD)\n' "$1"
}

# The newest DWP spec this checker implements (DWP_SPECIFICATION.md "Version").
SUPPORTED_SPEC="4.0.0"

# The standard's released series: 2.x is historical (repositories and plans
# onboarded before the 4.x jump stay valid, DWP_SPECIFICATION.md §6.5), 4.x is
# current. There is no 3.x standard — the v3 launch was a product release, not
# a standard bump (the three series are mapped in DWP_SPECIFICATION.md "Status").
standard_series_ok() {  # $1 = declared version; bash 3.2 safe
  case "${1%%.*}" in 2|4) return 0 ;; *) return 1 ;; esac
}

version_le() {
  # $1 <= $2 for dotted numeric versions (bash 3.2 safe; no arrays).
  local a="$1" b="$2" a1 a2 a3 b1 b2 b3
  a1="${a%%.*}"; a="${a#*.}"; a2="${a%%.*}"; a3="${a#*.}"
  b1="${b%%.*}"; b="${b#*.}"; b2="${b%%.*}"; b3="${b#*.}"
  [ "${a1:-0}" -lt "${b1:-0}" ] && return 0
  [ "${a1:-0}" -gt "${b1:-0}" ] && return 1
  [ "${a2:-0}" -lt "${b2:-0}" ] && return 0
  [ "${a2:-0}" -gt "${b2:-0}" ] && return 1
  [ "${a3:-0}" -le "${b3:-0}" ]
}

IS_GIT=0
if git rev-parse --git-dir >/dev/null 2>&1; then
  IS_GIT=1
fi

# ---------------------------------------------------------------- repo checks
check_repo() {
  echo "Repository"

  if [ -f AGENTS.md ] && grep -qiE 'quick commands|## commands' AGENTS.md; then
    pass "AGENTS.md with a Quick Commands block"
  else
    fail "AGENTS.md with a Quick Commands block"
  fi

  if [ -e CLAUDE.md ]; then
    if [ -L CLAUDE.md ] && [ "$(readlink CLAUDE.md)" = "AGENTS.md" ]; then
      pass "CLAUDE.md -> AGENTS.md symlink"
    else
      warn "CLAUDE.md exists but is not a symlink to AGENTS.md"
    fi
  else
    warn "CLAUDE.md missing (Claude Code reads AGENTS.md via this symlink)"
  fi

  local d
  for d in .agents/agents .agents/commands .agents/skills .agents/docs; do
    if [ -d "$d" ]; then
      pass "$d/"
    else
      fail "$d/"
    fi
  done

  if [ -e .claude ]; then
    pass ".claude resolves"
  else
    warn ".claude missing (symlink to .agents)"
  fi

  if [ -e .cursor ]; then
    pass ".cursor resolves"
  else
    warn ".cursor missing (symlink to .agents)"
  fi

  if [ -d docs ]; then
    pass "docs/"
    if [ -f docs/SECURITY.md ]; then
      pass "docs/SECURITY.md"
    else
      warn "docs/SECURITY.md missing (conformance-floor MUST per DOCUMENTATION_STANDARD §3)"
    fi
    check_repo_standard
  else
    warn "docs/ missing (agent workspaces adapt this; repos MUST have it)"
  fi

  check_local_reviewer

  # 2.4.0 removed .dwp/drafts/; only plans/ is required. A leftover drafts/
  # directory is inert and is neither required nor reported.
  if [ -d "$PLAN_ROOT/plans" ]; then
    pass ".dwp/plans"
  else
    fail ".dwp/plans"
  fi

  if [ "$IS_GIT" -eq 1 ]; then
    case "$PLAN_ROOT/" in
      "$PWD/"*)
        if git check-ignore "${PLAN_ROOT#"$PWD"/}" >/dev/null 2>&1; then
          pass ".dwp/ gitignored (or configured plan output directory)"
        else
          fail ".dwp/ gitignored (or configured plan output directory)"
        fi
        ;;
      *) pass "plan output directory outside the repository (DWP_DIR override)" ;;
    esac
  else
    # Agent workspace without git (ARCHETYPES.md §4): the state layer replaces
    # the git log, so every plan must carry it. Enforced per-plan below.
    warn "no git repository — agent-workspace rules apply (PLAN_STATE.md required per plan)"
  fi
}

# Repository standard: provenance line + TESTING_GUIDE §3.4 content.
# A repo onboarded under an earlier standard gets a FINDING (upgrade path); a repo
# that DECLARES 2.3.0+ and lacks the §3.4 content FAILS (DOCUMENTATION_STANDARD §3.5).
check_repo_standard() {
  local declared="" scoped=0
  if [ -f AGENTS.md ]; then
    declared="$(grep -oE 'DWP standard: *[0-9]+\.[0-9]+\.[0-9]+' AGENTS.md 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
  fi
  if [ -f docs/TESTING_GUIDE.md ] && grep -qiE 'scoped|source-to-test|affected consumers|fallback' docs/TESTING_GUIDE.md; then
    scoped=1
  fi
  if [ -n "$declared" ]; then
    if ! version_le "$declared" "$SUPPORTED_SPEC"; then
      fail "AGENTS.md declares DWP standard $declared, newer than this checker supports ($SUPPORTED_SPEC) — upgrade the installed skill"
      return 0
    fi
    if ! standard_series_ok "$declared"; then
      fail "AGENTS.md declares DWP standard $declared, which is not a DWP standard (the series are 2.x historical and 4.x current; there is no 3.x) — correct the provenance line"
      return 0
    fi
    pass "AGENTS.md declares DWP standard $declared"
    if version_le "2.3.0" "$declared"; then
      if [ "$scoped" -eq 1 ]; then
        pass "docs/TESTING_GUIDE.md carries scoped-invocation content (DOCUMENTATION_STANDARD §3.4)"
      else
        fail "docs/TESTING_GUIDE.md lacks the §3.4 content (scoped commands, mapping, fallback) required by the declared standard $declared"
      fi
      return 0
    fi
  fi
  # No declaration, or a pre-2.3.0 declaration: legacy repository → findings, not failures.
  if [ -f docs/TESTING_GUIDE.md ] && [ "$scoped" -eq 0 ]; then
    warn "harness-version finding: docs/TESTING_GUIDE.md has no scoped-invocation/mapping/fallback content (predates DWP 2.3.0) — run the onboard sub-skill in upgrade mode"
  fi
  if [ -z "$declared" ] && [ -f AGENTS.md ]; then
    warn "harness-version finding: AGENTS.md has no 'DWP standard:' provenance line — run the onboard sub-skill in upgrade mode"
  fi
}

# AI Diff Reviewer local review: part of the baseline since DWP standard 2.3.0
# (ADDONS.md §6.5). Vendored skill + an extension file at a recognized path.
# A repository declaring 2.3.0+ without both FAILS; a legacy repository gets a
# harness-version finding. The CI surface (pr-review.yml) is optional — never checked.
check_local_reviewer() {
  local declared="" has_skill=0 has_ext=0 what f
  if [ -f AGENTS.md ]; then
    declared="$(grep -oE 'DWP standard: *[0-9]+\.[0-9]+\.[0-9]+' AGENTS.md 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
  fi
  [ -f .agents/skills/ai-diff-reviewer/SKILL.md ] && has_skill=1
  for f in .review/extension.md .github/ai-diff-reviewer/extension.md .github/ai-pr-reviewer/extension.md; do
    if [ -f "$f" ]; then has_ext=1; break; fi
  done
  if [ "$has_skill" -eq 1 ] && [ "$has_ext" -eq 1 ]; then
    pass "AI Diff Reviewer local review installed (vendored skill + extension file)"
    return 0
  fi
  if [ "$has_skill" -eq 0 ] && [ "$has_ext" -eq 0 ]; then
    what="vendored skill (.agents/skills/ai-diff-reviewer/) and extension file (.review/extension.md) missing"
  elif [ "$has_skill" -eq 0 ]; then
    what="vendored skill missing (.agents/skills/ai-diff-reviewer/)"
  else
    what="extension file missing (.review/extension.md)"
  fi
  if [ -n "$declared" ] && version_le "2.3.0" "$declared" && version_le "$declared" "$SUPPORTED_SPEC"; then
    fail "AI Diff Reviewer local review: $what — required since DWP standard 2.3.0 (ADDONS.md §6.5); run the onboard sub-skill in upgrade mode (a declared exception in AGENTS.md is reported, not excused)"
  else
    warn "harness-version finding: AI Diff Reviewer local review: $what — required since DWP standard 2.3.0 (ADDONS.md §6.5); run the onboard sub-skill in upgrade mode"
  fi
}

# ---------------------------------------------------------------- plan checks
# The structural contract for both plan eras lives in plan_contract.py, so Lite,
# Full and legacy plans are judged by one implementation. It prints one finding
# per line; a leading "~ " marks an advisory (SHOULD), anything else is a
# failure (MUST).
check_plan() {
  local plan_dir="$1" output="" line failures=0 rc=0
  echo ""
  echo "Plan: $(basename "$plan_dir")"
  # Missing tooling proves neither validity nor invalidity. A CI gate must not
  # accept a plan merely because its structural checks could not run.
  if ! command -v python3 >/dev/null 2>&1; then
    warn "plan structure not verified (python3 unavailable) — no structural conformance claim is made for this plan"
    UNVERIFIED_COUNT=$((UNVERIFIED_COUNT + 1))
    return 0
  fi
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    warn "plan structure not verified — Python 3.9+ is required"
    UNVERIFIED_COUNT=$((UNVERIFIED_COUNT + 1))
    return 0
  fi
  output="$(python3 "$SCRIPT_DIR/plan_contract.py" "$plan_dir" "$( [ "$IS_GIT" -eq 1 ] && printf git || printf nogit )" 2>&1)" || rc=$?
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    case "$line" in
      '+ '*) pass "${line#+ }" ;;
      '~ '*) warn "${line#~ }" ;;
      *) fail "$line"; failures=$((failures + 1)) ;;
    esac
  done <<< "$output"
  if [ "$failures" -eq 0 ]; then
    if [ "$rc" -ne 0 ]; then
      fail "plan contract checker exited $rc without naming a finding"
      return 0
    fi
    warn "semantic review required: acceptance satisfaction, affected-test coverage and actual security review"
  fi
}

# -------------------------------------------------------------------- driver
if [ "$MODE" = "repo" ] || [ "$MODE" = "all" ]; then
  check_repo
fi

if [ "$MODE" = "plan" ]; then
  if [ -d "$PLAN_ROOT/plans/$PLAN_FILTER" ]; then
    check_plan "$PLAN_ROOT/plans/$PLAN_FILTER"
  else
    echo "Plan: $PLAN_FILTER"
    fail "plan directory $PLAN_ROOT/plans/$PLAN_FILTER exists"
  fi
elif [ "$MODE" = "all" ] && [ -d "$PLAN_ROOT/plans" ]; then
  for plan_dir in "$PLAN_ROOT"/plans/PLAN_*; do
    [ -d "$plan_dir" ] || continue
    check_plan "$plan_dir"
  done
fi

echo ""
if [ "$FAIL_COUNT" -eq 0 ] && [ "$UNVERIFIED_COUNT" -gt 0 ]; then
  echo "Verdict: UNVERIFIED — $UNVERIFIED_COUNT plan(s) could not be checked ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 2
elif [ "$FAIL_COUNT" -eq 0 ]; then
  echo "Verdict: CONFORMANT ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 0
else
  echo "Verdict: NOT CONFORMANT — $FAIL_COUNT issue(s) ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 1
fi
