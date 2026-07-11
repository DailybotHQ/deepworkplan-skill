#!/usr/bin/env bash
# Refresh the committed dogfood copy at .agents/skills/deepworkplan using the
# same consumer install path as npx skills (skills-lock.json). Commit the
# updated tree after refreshing.
#
# Usage:
#   ./scripts/refresh-dogfood-skill.sh          # restore from lockfile
#   ./scripts/refresh-dogfood-skill.sh --update # pull latest from GitHub
#
# Bash 3.2-safe.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCKFILE="$REPO_ROOT/skills-lock.json"

cd "$REPO_ROOT"

if [ ! -f "$LOCKFILE" ]; then
  echo "skills-lock.json not found — run: npx skills add DailybotHQ/deepworkplan-skill -y -p -s deepworkplan" >&2
  exit 1
fi

MODE="install"
if [ "${1:-}" = "--update" ]; then
  MODE="update"
fi

if [ "$MODE" = "update" ]; then
  npx skills update deepworkplan -y -p
else
  npx skills experimental_install
fi

if [ ! -f ".agents/skills/deepworkplan/SKILL.md" ]; then
  echo "Install failed: .agents/skills/deepworkplan/SKILL.md missing" >&2
  exit 1
fi

VERSION="$(grep -E '^version:' .agents/skills/deepworkplan/SKILL.md | head -1 | sed 's/version: *//;s/"//g')"
echo "OK: deepworkplan $VERSION at .agents/skills/deepworkplan"
echo "Commit .agents/skills/deepworkplan/ (and skills-lock.json if it changed) when ready."
