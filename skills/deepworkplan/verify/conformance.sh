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
# Bash 3.2 compatible (macOS default). Requires only git + coreutils; uses
# python3 for JSON validation when available, degrades gracefully when not.

set -euo pipefail

MODE="all"
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

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

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

json_valid() {
  # $1 = file. Returns 0 when the file parses as JSON (or python3 is absent,
  # in which case we only check non-emptiness — degrade, don't block).
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$1" >/dev/null 2>&1
  else
    [ -s "$1" ]
  fi
}

json_int() {
  # $1 = file, $2 = dotted key path (one level only needed here).
  # Prints the integer value, or nothing on failure.
  if command -v python3 >/dev/null 2>&1; then
    python3 -c '
import json, sys
try:
    v = json.load(open(sys.argv[1]))[sys.argv[2]]
    print(int(v))
except Exception:
    pass
' "$1" "$2" 2>/dev/null
  fi
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

  if [ -d docs ]; then
    pass "docs/"
  else
    warn "docs/ missing (agent workspaces adapt this; repos MUST have it)"
  fi

  if [ -d .dwp/plans ] && [ -d .dwp/drafts ]; then
    pass ".dwp/plans + .dwp/drafts"
  else
    fail ".dwp/plans + .dwp/drafts"
  fi

  if [ "$IS_GIT" -eq 1 ]; then
    if git check-ignore .dwp >/dev/null 2>&1; then
      pass ".dwp/ gitignored"
    else
      fail ".dwp/ gitignored"
    fi
  else
    # Agent workspace without git (ARCHETYPES.md §4): the state layer replaces
    # the git log, so every plan must carry it. Enforced per-plan below.
    warn "no git repository — agent-workspace rules apply (PLAN_STATE.md required per plan)"
  fi
}

# ---------------------------------------------------------------- plan checks
check_plan() {
  # $1 = plan directory
  local plan_dir="$1"
  local plan_name
  plan_name="$(basename "$plan_dir")"
  echo ""
  echo "Plan: $plan_name"

  local f
  for f in README.md PROMPTS.md PROGRESS.md; do
    if [ -f "$plan_dir/$f" ]; then
      pass "$f"
    else
      fail "$f"
    fi
  done

  if [ -d "$plan_dir/analysis_results" ]; then
    pass "analysis_results/"
  else
    fail "analysis_results/"
  fi

  local task_count=0
  for f in "$plan_dir"/[0-9]*.task_*.md; do
    [ -f "$f" ] || continue
    task_count=$((task_count + 1))
  done
  if [ "$task_count" -ge 3 ]; then
    pass "task files present ($task_count)"
  else
    fail "task files present ($task_count; need >= 1 user task + 2 mandatory final tasks)"
  fi

  if ls "$plan_dir"/[0-9]*.task_skills_agents_discovery.md >/dev/null 2>&1; then
    pass "mandatory task: skills & agents discovery"
  else
    fail "mandatory task: skills & agents discovery"
  fi
  if ls "$plan_dir"/[0-9]*.task_executive_report.md >/dev/null 2>&1; then
    pass "mandatory task: executive report"
  else
    fail "mandatory task: executive report"
  fi

  if [ -f "$plan_dir/README.md" ]; then
    if grep -qE 'Plan Status: *[0-9]+/[0-9]+' "$plan_dir/README.md"; then
      pass "README has a Plan Status count"
    else
      fail "README has a Plan Status count"
    fi
  fi

  # Validation gates: every task file must declare a Validation section.
  local gateless=0
  for f in "$plan_dir"/[0-9]*.task_*.md; do
    [ -f "$f" ] || continue
    if ! grep -qiE '^#+ .*validation' "$f"; then
      gateless=$((gateless + 1))
    fi
  done
  if [ "$gateless" -eq 0 ]; then
    pass "every task declares a Validation section"
  else
    fail "every task declares a Validation section ($gateless missing)"
  fi

  # State layer (PLAN_STATE.md): optional in a git repo, REQUIRED without git.
  if [ -f "$plan_dir/state.json" ]; then
    if json_valid "$plan_dir/state.json"; then
      pass "state.json parses"
      check_state_desync "$plan_dir"
    else
      fail "state.json parses"
    fi
    if [ -f "$plan_dir/manifest.json" ] && json_valid "$plan_dir/manifest.json"; then
      pass "manifest.json parses"
    else
      fail "manifest.json present and parses (required alongside state.json)"
    fi
  else
    if [ "$IS_GIT" -eq 1 ]; then
      warn "no state layer (state.json) — RECOMMENDED for new plans"
    else
      fail "state.json (REQUIRED in a workspace without git, PLAN_STATE.md §2.1)"
    fi
  fi
}

check_state_desync() {
  # Markdown wins: compare README [x] count against state.json completed_count.
  local plan_dir="$1"
  local md_done state_done
  md_done="$(grep -cE '^\s*- \[x\]' "$plan_dir/README.md" 2>/dev/null || true)"
  state_done="$(json_int "$plan_dir/state.json" completed_count)"
  if [ -z "$state_done" ]; then
    warn "state.json desync check skipped (python3 unavailable or field missing)"
    return 0
  fi
  if [ "$md_done" -eq "$state_done" ]; then
    pass "state.json in sync with README ($state_done completed)"
  else
    fail "state.json desync: README shows $md_done completed, state.json says $state_done (markdown wins — regenerate state.json, PLAN_STATE.md §5)"
  fi
}

# -------------------------------------------------------------------- driver
if [ "$MODE" = "repo" ] || [ "$MODE" = "all" ]; then
  check_repo
fi

if [ "$MODE" = "plan" ]; then
  if [ -d ".dwp/plans/$PLAN_FILTER" ]; then
    check_plan ".dwp/plans/$PLAN_FILTER"
  else
    echo "Plan: $PLAN_FILTER"
    fail "plan directory .dwp/plans/$PLAN_FILTER exists"
  fi
elif [ "$MODE" = "all" ] && [ -d .dwp/plans ]; then
  for plan_dir in .dwp/plans/PLAN_*; do
    [ -d "$plan_dir" ] || continue
    check_plan "$plan_dir"
  done
fi

echo ""
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "Verdict: CONFORMANT ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 0
else
  echo "Verdict: NOT CONFORMANT — $FAIL_COUNT issue(s) ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 1
fi
