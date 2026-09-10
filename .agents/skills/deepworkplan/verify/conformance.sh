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
# Accepts both plan lifecycle shapes: the 2.3.0 single Final Review and the
# pre-2.3.0 three-final-task ending (DWP_SPECIFICATION.md §6.5).
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

json_str() {
  # $1 = file, $2 = top-level key. Prints the string value, or nothing.
  if command -v python3 >/dev/null 2>&1; then
    python3 -c '
import json, sys
try:
    v = json.load(open(sys.argv[1]))[sys.argv[2]]
    print(str(v))
except Exception:
    pass
' "$1" "$2" 2>/dev/null
  fi
}

# The newest DWP spec this checker implements (DWP_SPECIFICATION.md "Version").
SUPPORTED_SPEC="2.3.0"

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

  if [ -d "$PLAN_ROOT/plans" ] && [ -d "$PLAN_ROOT/drafts" ]; then
    pass ".dwp/plans + .dwp/drafts"
  else
    fail ".dwp/plans + .dwp/drafts"
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
# Two accepted lifecycle shapes (DWP_SPECIFICATION.md §6, §6.5):
#   new    — one mandatory final task, {N}.task_final_review*.md, last;
#   legacy — {N-2}.task_security_review.md, {N-1}.task_skills_agents_discovery.md,
#            {N}.task_executive_report.md (plans authored before 2.3.0).
# A declared migration (README "**Standard:** ... (migrated from ...)") may also
# keep an already-completed security_review as N-1 followed by the final review.
# Mixed, missing, duplicate or misordered final tasks FAIL. A plan declaring a
# standard newer than this checker FAILS with an upgrade message.
plan_standard() {
  # Prints the standard the plan executes: README declaration wins, then the
  # manifest's spec_version, else "" (legacy by definition, PLAN_STATE.md §6.1).
  local plan_dir="$1" v=""
  if [ -f "$plan_dir/README.md" ]; then
    v="$(grep -oE 'Standard:\*\* *DWP spec *[0-9]+\.[0-9]+\.[0-9]+' "$plan_dir/README.md" 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
  fi
  if [ -z "$v" ] && [ -f "$plan_dir/manifest.json" ]; then
    v="$(json_str "$plan_dir/manifest.json" spec_version)"
  fi
  printf '%s' "$v"
}

task_id_of() {
  # $1 = task file path → its numeric id.
  local b
  b="$(basename "$1")"
  printf '%s' "${b%%.*}"
}

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

  # Partial materialization (DWP_SPECIFICATION §3): the README skeleton is written
  # early with `Plan Status: materializing`; a plan still carrying it was never
  # finished. Report the intended shape from manifest.json and stop checking.
  if [ -f "$plan_dir/README.md" ] && grep -qE 'Plan Status: *materializing' "$plan_dir/README.md"; then
    local intended="" present
    if [ -f "$plan_dir/manifest.json" ]; then intended="$(json_str "$plan_dir/manifest.json" task_count)"; fi
    present="$(find "$plan_dir" -maxdepth 1 -name '[0-9]*.task_*.md' 2>/dev/null | wc -l | tr -d ' ')"
    fail "partial materialization: README says 'Plan Status: materializing' (manifest declares ${intended:-?} tasks, $present task files present) — complete or discard it with create/refine; never execute it"
    return 0
  fi
  if [ ! -f "$plan_dir/manifest.json" ]; then
    local std_for_manifest
    std_for_manifest="$(plan_standard "$plan_dir")"
    if [ -n "$std_for_manifest" ] && version_le "2.3.0" "$std_for_manifest"; then
      warn "harness-version finding: manifest.json missing (plans authored under 2.3.0 write it first, PLAN_STATE.md §2)"
    fi
  fi

  if [ -d "$plan_dir/analysis_results" ]; then
    pass "analysis_results/"
  else
    fail "analysis_results/"
  fi

  # ---- task inventory: count, numeric ids, uniqueness, contiguity -------------
  local task_count=0 max_id=0 id ids="" dup=0 nonnum=0
  for f in "$plan_dir"/[0-9]*.task_*.md; do
    [ -f "$f" ] || continue
    task_count=$((task_count + 1))
    id="$(task_id_of "$f")"
    case "$id" in
      ''|*[!0-9]*) nonnum=$((nonnum + 1)); continue ;;
    esac
    case " $ids " in
      *" $id "*) dup=$((dup + 1)) ;;
    esac
    ids="$ids $id"
    if [ "$id" -gt "$max_id" ]; then max_id="$id"; fi
  done
  if [ "$nonnum" -gt 0 ]; then
    fail "task ids are numeric ($nonnum file(s) with a non-numeric prefix)"
  fi
  if [ "$dup" -gt 0 ]; then
    fail "task ids are unique ($dup duplicate id(s))"
  else
    pass "task ids are unique"
  fi
  local gap=0 k=1
  while [ "$k" -le "$max_id" ]; do
    case " $ids " in
      *" $k "*) ;;
      *) gap=$((gap + 1)) ;;
    esac
    k=$((k + 1))
  done
  if [ "$gap" -eq 0 ] && [ "$max_id" -eq "$task_count" ] && [ "$dup" -eq 0 ] && [ "$nonnum" -eq 0 ]; then
    pass "task ids are contiguous 1..$max_id (numeric order)"
  else
    fail "task ids are contiguous 1..N ($gap missing id(s); $task_count files, highest id $max_id)"
  fi

  # ---- lifecycle shape ----------------------------------------------------------
  local declared shape="" fr_id="" fr_count=0 sr_id="" sd_id="" er_id="" migrated=0
  declared="$(plan_standard "$plan_dir")"
  if [ -f "$plan_dir/README.md" ] && grep -qE '\*\*Standard:\*\*.*\(migrated from' "$plan_dir/README.md"; then migrated=1; fi
  for f in "$plan_dir"/[0-9]*.task_final_review*.md; do
    [ -f "$f" ] || continue
    fr_count=$((fr_count + 1)); fr_id="$(task_id_of "$f")"
  done
  for f in "$plan_dir"/[0-9]*.task_security_review.md; do [ -f "$f" ] && sr_id="$(task_id_of "$f")"; done
  for f in "$plan_dir"/[0-9]*.task_skills_agents_discovery.md; do [ -f "$f" ] && sd_id="$(task_id_of "$f")"; done
  for f in "$plan_dir"/[0-9]*.task_executive_report.md; do [ -f "$f" ] && er_id="$(task_id_of "$f")"; done

  if [ -n "$declared" ] && ! version_le "$declared" "$SUPPORTED_SPEC"; then
    fail "plan declares DWP spec $declared, newer than this checker supports ($SUPPORTED_SPEC) — upgrade the installed skill before executing it"
  elif [ -n "$declared" ]; then
    pass "plan standard: DWP spec $declared$( [ "$migrated" -eq 1 ] && printf ' (declared migration)')"
  else
    warn "plan standard undeclared (no README Standard line, no manifest) — treated as legacy"
  fi

  if [ "$fr_count" -gt 1 ]; then
    fail "exactly one Final Review task ($fr_count found)"
  elif [ "$fr_count" -eq 1 ] && [ -n "$sd_id$er_id" ]; then
    fail "mixed lifecycle: a Final Review task coexists with legacy skills_agents_discovery/executive_report tasks — pick one shape (DWP_SPECIFICATION §6.5)"
  elif [ "$fr_count" -eq 1 ]; then
    shape="new"
    if [ "$fr_id" = "$max_id" ]; then
      pass "mandatory final task: Final Review is task $max_id (last)"
    else
      fail "mandatory final task: Final Review must be the last task (found id $fr_id, highest id $max_id)"
    fi
    if [ -n "$sr_id" ]; then
      if [ "$migrated" -eq 1 ] && [ "$sr_id" -eq $((max_id - 1)) ] && grep -qE "^[[:space:]]*- \[x\].*(${sr_id}\.task_security_review|[Tt]ask[[:space:]]+${sr_id}\b)" "$plan_dir/README.md" 2>/dev/null; then
        pass "migrated plan keeps its completed Security Review as task $sr_id before the Final Review"
      else
        fail "mixed lifecycle: security_review task alongside a Final Review is valid only for a declared migration with the security review already completed (refine migrate, step 3)"
      fi
    fi
    if [ "$task_count" -ge 2 ]; then
      pass "task files present ($task_count)"
    else
      fail "task files present ($task_count; need >= 1 user task + the Final Review)"
    fi
    if [ -n "$declared" ] && version_le "$declared" "2.2.0"; then
      warn "plan uses the 2.3.0 shape but declares $declared — add the README declared-migration line (PLAN_STATE §6.1)"
    fi
  elif [ -n "$sr_id" ] || [ -n "$sd_id" ] || [ -n "$er_id" ]; then
    shape="legacy"
    if [ -n "$declared" ] && version_le "2.3.0" "$declared" && [ "$migrated" -eq 0 ]; then
      fail "plan declares DWP spec $declared but carries the pre-2.3.0 three-final-task shape — a declared new plan must end with a single Final Review"
    fi
    if [ -n "$sr_id" ] && [ "$sr_id" -eq $((max_id - 2)) ]; then
      pass "mandatory task: security review"
    else
      fail "mandatory task: security review (legacy shape: must be task N-2$( [ -n "$sr_id" ] && printf ', found %s' "$sr_id" ))"
    fi
    if [ -n "$sd_id" ] && [ "$sd_id" -eq $((max_id - 1)) ]; then
      pass "mandatory task: skills & agents discovery"
    else
      fail "mandatory task: skills & agents discovery (legacy shape: must be task N-1$( [ -n "$sd_id" ] && printf ', found %s' "$sd_id" ))"
    fi
    if [ -n "$er_id" ] && [ "$er_id" -eq "$max_id" ]; then
      pass "mandatory task: executive report"
    else
      fail "mandatory task: executive report (legacy shape: must be task N$( [ -n "$er_id" ] && printf ', found %s' "$er_id" ))"
    fi
    if [ "$task_count" -ge 4 ]; then
      pass "task files present ($task_count)"
    else
      fail "task files present ($task_count; legacy shape needs >= 1 user task + 3 mandatory final tasks)"
    fi
  else
    fail "mandatory final task missing — accepted shapes: {N}.task_final_review.md last (DWP 2.3.0+), or {N-2}.task_security_review.md + {N-1}.task_skills_agents_discovery.md + {N}.task_executive_report.md (pre-2.3.0)"
  fi

  # Objective structure of the Final Review (filename alone proves nothing).
  if [ "$shape" = "new" ]; then
    local frf missing=""
    for frf in "$plan_dir"/[0-9]*.task_final_review*.md; do
      [ -f "$frf" ] || continue
      grep -qi 'security' "$frf" || missing="$missing security-pass"
      grep -qiE 'final-state|full (validation|suite|gate)|complete applicable' "$frf" || missing="$missing final-state-validation"
      grep -qiE 'skills' "$frf" || missing="$missing skills-reconciliation"
    done
    if [ -z "$missing" ]; then
      pass "Final Review names its three parts (security pass, final-state validation, skills reconciliation)"
    else
      fail "Final Review file does not mention:$missing (DWP_SPECIFICATION §6.1) — the filename alone does not prove coverage"
    fi
  fi

  # Completed-plan security artifact (DWP_SPECIFICATION §6.1 / verify/SKILL.md):
  # when every task is [x] / Plan Status N/N, SECURITY_REVIEW.md must exist and
  # must not leave an unresolved critical finding.
  if [ -f "$plan_dir/README.md" ]; then
    local status_line done_n total_n unchecked=0 completed_plan=0
    status_line="$(grep -E 'Plan Status: *[0-9]+/[0-9]+' "$plan_dir/README.md" 2>/dev/null | head -1 || true)"
    if [ -n "$status_line" ]; then
      done_n="$(printf '%s' "$status_line" | sed -E 's/.*Plan Status: *([0-9]+)\/([0-9]+).*/\1/')"
      total_n="$(printf '%s' "$status_line" | sed -E 's/.*Plan Status: *([0-9]+)\/([0-9]+).*/\2/')"
      if [ -n "$done_n" ] && [ -n "$total_n" ] && [ "$done_n" = "$total_n" ] && [ "$total_n" -gt 0 ]; then
        completed_plan=1
      fi
    fi
    unchecked="$(grep -cE '^\s*- \[ \]' "$plan_dir/README.md" 2>/dev/null || true)"
    if [ "${unchecked:-0}" -ne 0 ] || ! grep -qE '^\s*- \[x\]' "$plan_dir/README.md" 2>/dev/null; then
      completed_plan=0
    fi
    if [ "$completed_plan" -eq 1 ]; then
      if [ -f "$plan_dir/analysis_results/SECURITY_REVIEW.md" ]; then
        pass "completed plan has analysis_results/SECURITY_REVIEW.md"
        local sr="$plan_dir/analysis_results/SECURITY_REVIEW.md"
        if grep -qiE 'open critical finding|critical finding remains|unresolved critical finding:' "$sr" \
          || (grep -qiE 'unresolved critical' "$sr" && ! grep -qiE 'no unresolved critical|without (an )?unresolved critical|0 unresolved critical|zero unresolved critical' "$sr"); then
          fail "completed plan SECURITY_REVIEW.md still reports an unresolved critical finding (DWP_SPECIFICATION §6.1) — fix or record explicit acceptance"
        elif grep -qiE '(^|[|[:space:]])critical([|[:space:]]|$)|🚨[[:space:]]*critical' "$sr" \
          && ! grep -qiE 'no unresolved critical|0 critical|zero critical|explicitly accepted|accepted by the (user|developer)|criticals?: *0|no findings' "$sr"; then
          fail "completed plan SECURITY_REVIEW.md mentions critical findings without a clear resolution/acceptance (DWP_SPECIFICATION §6.1)"
        else
          pass "completed plan SECURITY_REVIEW.md has no unresolved critical finding"
        fi
      else
        fail "completed plan missing analysis_results/SECURITY_REVIEW.md (DWP_SPECIFICATION §6.1 / verify/SKILL.md) — Final Review must write it even when clean"
      fi
    fi
  fi

  # ---- README ↔ files ↔ state correspondence -----------------------------------
  if [ -f "$plan_dir/README.md" ]; then
    if grep -qE 'Plan Status: *[0-9]+/[0-9]+' "$plan_dir/README.md"; then
      pass "README has a Plan Status count"
    else
      fail "README has a Plan Status count"
    fi
    local unreferenced=0 broken=0 link
    for f in "$plan_dir"/[0-9]*.task_*.md; do
      [ -f "$f" ] || continue
      grep -qF "$(basename "$f")" "$plan_dir/README.md" || unreferenced=$((unreferenced + 1))
    done
    while IFS= read -r link; do
      [ -n "$link" ] || continue
      [ -f "$plan_dir/$link" ] || broken=$((broken + 1))
    done < <(grep -oE '\]\(\./[0-9]+\.task_[A-Za-z0-9_]+\.md\)' "$plan_dir/README.md" 2>/dev/null | sed 's/](\.\///; s/)$//' | sort -u)
    local linked
    linked="$(grep -cE '\]\(\./[0-9]+\.task_[A-Za-z0-9_]+\.md\)' "$plan_dir/README.md" 2>/dev/null || true)"
    if [ "${linked:-0}" -eq 0 ]; then
      warn "README task list carries no task-file links (finding — pre-2.3.0 READMEs may list tasks without links; correspondence not checked)"
    elif [ "$unreferenced" -eq 0 ] && [ "$broken" -eq 0 ]; then
      pass "README task list matches the task files"
    else
      fail "README task list matches the task files ($unreferenced file(s) not referenced, $broken README link(s) broken)"
    fi
  fi

  # Dependency references: "Task K" mentioned in a Read Before Starting section must exist.
  local badref=0 ref
  for f in "$plan_dir"/[0-9]*.task_*.md; do
    [ -f "$f" ] || continue
    while IFS= read -r ref; do
      [ -n "$ref" ] || continue
      case " $ids " in
        *" $ref "*) ;;
        *) badref=$((badref + 1)) ;;
      esac
    done < <(sed -n '/^## [0-9.]* *Read Before Starting/,/^## /p' "$f" 2>/dev/null | grep -oE '[Tt]ask [0-9]+' | grep -oE '[0-9]+' | sort -u)
  done
  if [ "$badref" -eq 0 ]; then
    pass "Read Before Starting references resolve to existing tasks"
  else
    warn "Read Before Starting references $badref task number(s) that do not exist (finding — check renumbering)"
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

  # 2.3.0 findings (never failures — semantic content is reviewed by the agent):
  if [ "$shape" = "new" ]; then
    local nots=0
    for f in "$plan_dir"/[0-9]*.task_*.md; do
      [ -f "$f" ] || continue
      case "$(basename "$f")" in *task_final_review*) continue ;; esac
      grep -qiE '^#+ .*touched surface|^\*\*touched surface' "$f" || nots=$((nots + 1))
    done
    if [ "$nots" -eq 0 ]; then
      pass "every task carries a Touched Surface section"
    else
      warn "$nots task(s) without a Touched Surface section (finding — required for behavior-changing tasks, DWP_SPECIFICATION §5.0.2; docs/research tasks may state not applicable)"
    fi
    if [ -f "$plan_dir/analysis_results/SKILLS_CANDIDATES.md" ]; then
      pass "analysis_results/SKILLS_CANDIDATES.md present"
    else
      warn "analysis_results/SKILLS_CANDIDATES.md missing (finding — acceptable until the first candidate exists; task logs may record 'none')"
    fi
  fi

  # State layer (PLAN_STATE.md): optional in a git repo, REQUIRED without git.
  if [ -f "$plan_dir/state.json" ]; then
    if json_valid "$plan_dir/state.json"; then
      pass "state.json parses"
      check_state_desync "$plan_dir"
      check_state_tasks "$plan_dir" "$task_count"
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
    pass "state.json completed_count matches README ($state_done completed)"
  else
    fail "state.json desync: README shows $md_done completed, state.json says $state_done (markdown wins — regenerate state.json, PLAN_STATE.md §5)"
  fi
}

check_state_tasks() {
  # state.json task entries must correspond 1:1 to the task files on disk.
  local plan_dir="$1" task_count="$2" state_count
  state_count="$(json_int "$plan_dir/state.json" task_count)"
  [ -n "$state_count" ] || return 0
  if [ "$state_count" -eq "$task_count" ]; then
    pass "state.json task_count matches the task files ($task_count)"
  else
    fail "state.json task_count ($state_count) differs from the task files on disk ($task_count) — regenerate state.json (PLAN_STATE.md §5)"
  fi
  if command -v python3 >/dev/null 2>&1; then
    local problems
    problems="$(python3 - "$plan_dir" <<'PYEOF'
import json, os, re, sys
from collections import Counter

d = sys.argv[1]
state = json.load(open(os.path.join(d, "state.json")))
tasks = state.get("tasks", [])
files = {f for f in os.listdir(d) if re.match(r"^\d+\.task_.*\.md$", f)}
if not isinstance(tasks, list) or any(not isinstance(t, dict) for t in tasks):
    print("state.json tasks must be an array of task objects")
    sys.exit(0)
listed = [t.get("file") for t in tasks]
if any(not isinstance(f, str) for f in listed):
    print("state.json task entries require a file name")
    sys.exit(0)
if len(tasks) != len(files) or set(listed) != files:
    print("state.json task entries do not match the task files one-to-one")
if any(n > 1 for n in Counter(listed).values()):
    print("state.json has duplicate task entries")
ids = [t.get("id") for t in tasks]
if any(type(i) is not int for i in ids):
    print("state.json task ids must be integers")
elif len(set(ids)) != len(ids):
    print("state.json has duplicate task ids")
for task in tasks:
    match = re.match(r"^(\d+)\.task_", task["file"])
    if match and task.get("id") != int(match[1]):
        print("state.json task id disagrees with file: " + task["file"])

# Read only task checkboxes outside fenced examples. Accept either Task N
# labels or direct task-file links; other checklist items are not plan tasks.
readme = open(os.path.join(d, "README.md")).read()
checks = {}
fence = None
for line in readme.splitlines():
    marker = re.match(r"^\s*(`{3,}|~{3,})", line)
    if marker:
        token = marker[1][0]
        fence = None if fence == token else (fence or token)
        continue
    if fence:
        continue
    box = re.match(r"^\s*- \[([ xX])\]\s*(.*)", line)
    if not box:
        continue
    task = re.search(r"\b[Tt]ask\s+(\d+)\b|(?:^|\[)(\d+)\.task_", box[2])
    if task:
        ident = int(task[1] or task[2])
        if ident in checks:
            print("README has duplicate task checkbox: " + str(ident))
        checks[ident] = box[1].lower() == "x"
if set(checks) != set(range(1, len(files) + 1)):
    print("README task checkboxes do not match the task ids on disk")
for task in tasks:
    ident = task.get("id")
    status = task.get("status")
    if status not in ("pending", "in_progress", "completed", "blocked", "skipped"):
        print("state.json invalid task status: " + task["file"])
    if type(ident) is int and ident in checks:
        if (status == "completed") != checks[ident]:
            print("state.json task status disagrees with README: Task " + str(ident))
done = sum(t.get("status") == "completed" for t in tasks)
if state.get("completed_count") != done:
    print("state.json completed_count disagrees with task statuses")
summary = re.search(r"Plan Status: *([0-9]+)/([0-9]+)", readme)
if summary and (int(summary[1]), int(summary[2])) != (sum(checks.values()), len(files)):
    print("README Plan Status count disagrees with task checkboxes/files")
PYEOF
)"
    if [ -z "$problems" ]; then
      pass "state.json task entries and statuses match README and task files"
    else
      while IFS= read -r problem; do
        fail "$problem (markdown wins — regenerate state.json when stale)"
      done <<< "$problems"
    fi
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
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "Verdict: CONFORMANT ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 0
else
  echo "Verdict: NOT CONFORMANT — $FAIL_COUNT issue(s) ($PASS_COUNT passed, $WARN_COUNT advisory)"
  exit 1
fi
