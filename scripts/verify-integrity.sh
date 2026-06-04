#!/usr/bin/env bash
set -euo pipefail
# Verify the shipped skill pack against a published SHA256SUMS file.
#
# This is the "verify before you run" path: before trusting (or running
# `setup.sh` on) a copy of this skill, confirm every shipped file matches the
# checksums published with the release.
#
# Usage:
#   ./scripts/verify-integrity.sh [SHA256SUMS-file]   # default: <repo>/SHA256SUMS
#
# Workflow for a downloaded copy:
#   1. Download SHA256SUMS from the GitHub Release for the version you installed.
#   2. Place it at the repo root (or pass its path as the argument).
#   3. Run this script; a non-zero exit means a file does not match.
#
# Bash 3.2-safe.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUMS="${1:-$REPO_ROOT/SHA256SUMS}"

cd "$REPO_ROOT"

if [ ! -f "$SUMS" ]; then
  echo "Checksum file not found: $SUMS" >&2
  echo "Generate one with scripts/generate-checksums.sh, or download SHA256SUMS" >&2
  echo "from the matching GitHub Release: https://github.com/DailybotHQ/deepworkplan-skill/releases" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "$SUMS"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 -c "$SUMS"
else
  echo "Neither sha256sum nor shasum found on PATH" >&2
  exit 1
fi

echo "Integrity OK — the skill pack matches ${SUMS}"
