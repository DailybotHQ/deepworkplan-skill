#!/usr/bin/env bash
set -euo pipefail
# DeepWorkPlan skill pack setup — creates symlinks so the pack and each
# sub-skill are independently discoverable by any agent platform.
#
# Usage:
#   ./setup.sh                 # auto-detect agent platform(s)
#   ./setup.sh --host claude   # explicit: Claude Code
#   ./setup.sh --host cursor   # explicit: Cursor
#   ./setup.sh --host codex    # explicit: OpenAI Codex
#   ./setup.sh --host auto     # detect all installed agents
#
# Bash 3.2-safe (macOS default): avoids all bash-4-only idioms — no
# readarray, no associative arrays, no inline case-conversion expansions.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_DIR="$SCRIPT_DIR/skills/deepworkplan"
PACK_NAME="deepworkplan"

if [ ! -d "$PACK_DIR" ]; then
  echo "Pack directory not found at $PACK_DIR" >&2
  echo "This script must run from the root of the deepworkplan-skill repository." >&2
  exit 1
fi

# ─── Parse flags ──────────────────────────────────────────────
HOST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --host)
      if [ $# -lt 2 ] || [ -z "${2:-}" ]; then
        echo "Missing value for --host" >&2
        exit 1
      fi
      HOST="$2"; shift 2 ;;
    --host=*) HOST="${1#--host=}"; shift ;;
    -h|--help)
      echo "Usage: ./setup.sh [--host claude|cursor|codex|windsurf|copilot|cline|gemini|auto]"
      echo ""
      echo "Creates symlinks for the DeepWorkPlan pack and each sub-skill so your"
      echo "agent discovers them. Run without --host to auto-detect, or specify"
      echo "an agent explicitly."
      exit 0
      ;;
    *) shift ;;
  esac
done

# ─── Agent skill directory map ────────────────────────────────
resolve_skills_dir() {
  local agent="$1"
  case "$agent" in
    claude)   echo "$HOME/.claude/skills" ;;
    cursor)   echo "$HOME/.cursor/skills" ;;
    codex)    echo "$HOME/.codex/skills" ;;
    windsurf) echo "$HOME/.codeium/windsurf/skills" ;;
    copilot)  echo "$HOME/.copilot/skills" ;;
    cline)    echo "$HOME/.cline/skills" ;;
    gemini)   echo "$HOME/.gemini/skills" ;;
    *) echo "" ;;
  esac
}

# ─── Sub-skills to link (verb → deepworkplan-<verb>) ─────────
SKILLS=("create" "execute" "refine" "resume" "status" "onboard")

# ─── Link one agent ──────────────────────────────────────────
link_agent() {
  local agent="$1"
  local skills_dir
  skills_dir="$(resolve_skills_dir "$agent")"
  if [ -z "$skills_dir" ]; then
    echo "Unknown agent: $agent" >&2
    return 1
  fi

  mkdir -p "$skills_dir"

  local linked=()

  # Ensure the pack directory itself is accessible. If the repo was cloned
  # directly into the skills dir, no pack-level symlink is needed. Otherwise,
  # create one pointing at PACK_DIR.
  local pack_target="$skills_dir/$PACK_NAME"
  if [ ! -e "$pack_target" ] && [ "$PACK_DIR" != "$pack_target" ]; then
    ln -snf "$PACK_DIR" "$pack_target"
    echo "  $PACK_NAME -> $PACK_DIR"
  fi

  for skill in "${SKILLS[@]}"; do
    local skill_dir="$PACK_DIR/$skill"
    if [ -f "$skill_dir/SKILL.md" ]; then
      local link_name="deepworkplan-$skill"
      local target="$skills_dir/$link_name"
      if [ -L "$target" ] || [ ! -e "$target" ]; then
        ln -snf "$skill_dir" "$target"
        linked+=("$link_name")
      else
        echo "  skipped $link_name (real file/directory exists)" >&2
      fi
    fi
  done

  if [ ${#linked[@]} -gt 0 ]; then
    echo "  linked: ${linked[*]}"
  fi
}

# ─── Auto-detect installed agents ────────────────────────────
detect_agents() {
  local found=()
  [ -d "$HOME/.claude" ]                   && found+=("claude")
  [ -d "$HOME/.cursor" ]                   && found+=("cursor")
  command -v codex >/dev/null 2>&1         && found+=("codex")
  [ -d "$HOME/.codex" ]                    && found+=("codex")
  [ -d "$HOME/.codeium/windsurf" ]         && found+=("windsurf")
  [ -d "$HOME/.copilot" ]                  && found+=("copilot")
  [ -d "$HOME/.cline" ]                    && found+=("cline")
  [ -d "$HOME/.gemini" ]                   && found+=("gemini")

  # Deduplicate
  if [ ${#found[@]} -gt 0 ]; then
    printf '%s\n' "${found[@]}" | sort -u
  fi
}

# ─── Main ─────────────────────────────────────────────────────
echo "DeepWorkPlan skill pack setup"
echo "Pack directory: $PACK_DIR"
echo ""

if [ -z "$HOST" ] || [ "$HOST" = "auto" ]; then
  agents=()
  while IFS= read -r line; do
    [ -n "$line" ] && agents+=("$line")
  done < <(detect_agents)
  if [ "${#agents[@]}" -eq 0 ]; then
    echo "No known agent platforms detected."
    echo "Install the pack manually by cloning into your agent's skill directory."
    echo "See README.md for paths."
    exit 0
  fi
  for agent in "${agents[@]}"; do
    echo "[$agent]"
    link_agent "$agent"
  done
else
  echo "[$HOST]"
  link_agent "$HOST"
fi

echo ""
echo "Done. Available skills:"
echo "  deepworkplan-create   — create a Deep Work Plan"
echo "  deepworkplan-execute  — execute a plan task-by-task"
echo "  deepworkplan-refine   — refine a draft or modify a final plan"
echo "  deepworkplan-resume   — resume an interrupted plan"
echo "  deepworkplan-status   — report plan status without executing"
echo "  deepworkplan-onboard  — make any repo AI-first"
echo ""
echo "The root 'deepworkplan' skill acts as a router if your agent discovers it."
