#!/usr/bin/env bash
set -euo pipefail
# Generate SHA256SUMS over the shipped runtime artifact (skills/deepworkplan).
#
# The output is a standard `sha256sum`-format file with paths relative to the
# repository root, so it can be verified with either `sha256sum -c SHA256SUMS`
# or `shasum -a 256 -c SHA256SUMS` from the repo root. The auto-release workflow
# attaches this file to every GitHub Release so users can verify provenance.
#
# Usage:
#   ./scripts/generate-checksums.sh [output-file]   # default: <repo>/SHA256SUMS
#
# Bash 3.2-safe (macOS default): plain arrays only, no associative arrays.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACK_REL="skills/deepworkplan"
OUT="${1:-$REPO_ROOT/SHA256SUMS}"

cd "$REPO_ROOT"

if [ ! -d "$PACK_REL" ]; then
  echo "Pack directory not found: $PACK_REL" >&2
  echo "Run this from the deepworkplan-skill repository." >&2
  exit 1
fi

# Pick whichever checksum tool is available (Linux: sha256sum, macOS: shasum).
if command -v sha256sum >/dev/null 2>&1; then
  HASH_CMD=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  HASH_CMD=(shasum -a 256)
else
  echo "Neither sha256sum nor shasum found on PATH" >&2
  exit 1
fi

# Deterministic output: enumerate files, sort with a stable C locale, hash each.
# Excludes macOS cruft so checksums are reproducible across platforms.
find "$PACK_REL" -type f ! -name '.DS_Store' -print0 \
  | LC_ALL=C sort -z \
  | xargs -0 "${HASH_CMD[@]}" \
  > "$OUT"

echo "Wrote $(wc -l < "$OUT" | tr -d ' ') checksums for ${PACK_REL} to ${OUT}"
