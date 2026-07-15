#!/usr/bin/env bash
# context.sh — shared context detection for all Dailybot skills.
# Detects the current coding environment and outputs JSON for Dailybot metadata.
# Compatible with: Claude Code, Codex CLI, Cursor, Gemini CLI, OpenClaw, bare shell.
#
# Usage:  bash context.sh
# Output: {"repo":"...","branch":"...","agent_tool":"...","agent_name":"..."}
#
# Per-repo opt-out:
#   If `.dailybot/disabled` exists in the working repo root (or any parent),
#   this script exits silently with code 0 and produces no output. Sub-skills
#   should treat empty output as "skip telemetry for this repo."
#
# Manual fallback (when this script can't run):
#   repo:   git remote get-url origin 2>/dev/null | sed 's|.*/||;s|\.git$||'
#   branch: git branch --show-current 2>/dev/null
#   If git fails, use the current folder name for repo and "unknown" for branch.
#   Assemble metadata JSON manually:
#   {"repo":"<repo>","branch":"<branch>","agent_tool":"<tool>","agent_name":"<name>","model":"<model>"}
#   Model examples: "claude-sonnet-4-6", "o3", "gemini-2.5-pro", "gpt-4o"

set -euo pipefail

# ── Per-repo opt-out check ───────────────────────────────────────────────────
# Walk up from $PWD looking for .dailybot/disabled. If found, exit silently.
check_disabled() {
  local dir="$PWD"
  while [[ "$dir" != "/" && -n "$dir" ]]; do
    if [[ -f "$dir/.dailybot/disabled" ]]; then
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}
if check_disabled; then
  exit 0
fi

# ── Repo name ────────────────────────────────────────────────────────────────
REPO=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
  if [[ -n "$REMOTE" ]]; then
    REPO="${REMOTE##*/}"
    REPO="${REPO%.git}"
  fi
fi
if [[ -z "$REPO" ]]; then
  REPO=$(basename "$PWD")
fi

# ── Branch ───────────────────────────────────────────────────────────────────
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [[ -z "$BRANCH" ]]; then
  BRANCH="unknown"
fi

# ── Agent detection ──────────────────────────────────────────────────────────
# Priority: explicit env var > vendor env vars > parent process basename > unknown.
# We deliberately avoid `ps aux | grep <name>` because it produces false
# positives on any unrelated process whose command line contains the substring.

AGENT_TOOL="unknown"
AGENT_NAME="unknown"

# 1) Explicit override (any agent or wrapper can set this).
if [[ -n "${DAILYBOT_AGENT_TOOL:-}" ]]; then
  AGENT_TOOL="$DAILYBOT_AGENT_TOOL"
  AGENT_NAME="${DAILYBOT_AGENT_NAME:-$AGENT_TOOL}"
fi

# 2) Vendor env vars (set by the harness itself).
if [[ "$AGENT_TOOL" == "unknown" ]]; then
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" || -n "${CLAUDECODE:-}" ]]; then
    AGENT_TOOL="claude-code"; AGENT_NAME="claude-code"
  elif [[ -n "${CODEX_SESSION_ID:-}" || -n "${CODEX_HOME:-}" ]]; then
    AGENT_TOOL="codex-cli"; AGENT_NAME="codex-cli"
  elif [[ -n "${CURSOR_SESSION_ID:-}" || -n "${CURSOR_TRACE_ID:-}" ]]; then
    AGENT_TOOL="cursor"; AGENT_NAME="cursor"
  elif [[ -n "${OPENCLAW_SESSION:-}" ]]; then
    AGENT_TOOL="openclaw"; AGENT_NAME="openclaw"
  elif [[ -n "${GEMINI_SESSION_ID:-}" ]]; then
    AGENT_TOOL="gemini-cli"; AGENT_NAME="gemini-cli"
  elif [[ -n "${WINDSURF_SESSION_ID:-}" ]]; then
    AGENT_TOOL="windsurf"; AGENT_NAME="windsurf"
  fi
fi

# 3) Parent process basename (only when env vars don't pin the agent).
#    Match `comm` (executable basename) — never substring-match across argv.
if [[ "$AGENT_TOOL" == "unknown" ]]; then
  PARENT_COMM=$(ps -o comm= -p "$PPID" 2>/dev/null || true)
  case "$(basename "${PARENT_COMM:-}")" in
    claude|claude-code) AGENT_TOOL="claude-code"; AGENT_NAME="claude-code" ;;
    codex|codex-cli)    AGENT_TOOL="codex-cli";   AGENT_NAME="codex-cli"   ;;
    cursor)             AGENT_TOOL="cursor";      AGENT_NAME="cursor"      ;;
    openclaw)           AGENT_TOOL="openclaw";    AGENT_NAME="openclaw"    ;;
    gemini)             AGENT_TOOL="gemini-cli";  AGENT_NAME="gemini-cli"  ;;
    windsurf)           AGENT_TOOL="windsurf";    AGENT_NAME="windsurf"    ;;
  esac
fi

# 4) CI fallback for unattended runs.
if [[ "$AGENT_TOOL" == "unknown" ]]; then
  if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${CIRCLECI:-}" ]]; then
    AGENT_TOOL="ci"
    AGENT_NAME="ci-agent"
  fi
fi

# ── Output ────────────────────────────────────────────────────────────────────
# Use jq when available (handles all control characters correctly). Fall back
# to python3, then to a hardened bash escaper that covers the characters most
# likely to break manual JSON construction.

emit_json() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn \
      --arg repo "$REPO" \
      --arg branch "$BRANCH" \
      --arg agent_tool "$AGENT_TOOL" \
      --arg agent_name "$AGENT_NAME" \
      '{repo:$repo, branch:$branch, agent_tool:$agent_tool, agent_name:$agent_name}'
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    REPO="$REPO" BRANCH="$BRANCH" AGENT_TOOL="$AGENT_TOOL" AGENT_NAME="$AGENT_NAME" \
      python3 -c 'import json,os; print(json.dumps({"repo":os.environ["REPO"],"branch":os.environ["BRANCH"],"agent_tool":os.environ["AGENT_TOOL"],"agent_name":os.environ["AGENT_NAME"]}))'
    return
  fi
  # Hardened bash fallback: escapes \ " and the most common control chars.
  escape_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    s="${s//$'\b'/\\b}"
    s="${s//$'\f'/\\f}"
    printf '%s' "$s"
  }
  printf '{"repo":"%s","branch":"%s","agent_tool":"%s","agent_name":"%s"}\n' \
    "$(escape_json "$REPO")" \
    "$(escape_json "$BRANCH")" \
    "$(escape_json "$AGENT_TOOL")" \
    "$(escape_json "$AGENT_NAME")"
}

emit_json
