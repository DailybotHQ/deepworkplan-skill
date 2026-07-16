#!/usr/bin/env bash
set -euo pipefail

# Sync the shipped skill pack (skills/deepworkplan/) into the dogfood
# location (.agents/skills/deepworkplan/) so this repo eats its own
# cooking.
#
# This is the ONLY supported way to refresh the in-repo deepworkplan
# dogfood copy. auto-release.yml deliberately does NOT overwrite
# `.agents/skills/deepworkplan/` via `npx skills add` — that copy is
# repo-adapted for contributors (Dailybot + AI Diff Reviewer addon
# wiring). Addon skills (`dailybot`, `ai-diff-reviewer`) ARE
# auto-refreshed on release; deepworkplan is not.
#
# Run after any intentional change under skills/deepworkplan/ that
# should also land in the contributor dogfood copy. Review the diff
# before committing.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/skills/deepworkplan"
DST="$REPO_ROOT/.agents/skills/deepworkplan"

if [ ! -d "$SRC" ]; then
    echo "ERROR: source pack not found at $SRC" >&2
    exit 1
fi

# Remove stale copy (or lingering symlink from older layout)
if [ -L "$DST" ]; then
    rm "$DST"
elif [ -d "$DST" ]; then
    rm -rf "$DST"
fi

cp -R "$SRC" "$DST"

src_count="$(find "$SRC" -type f | wc -l | tr -d ' ')"
dst_count="$(find "$DST" -type f | wc -l | tr -d ' ')"

if [ "$src_count" != "$dst_count" ]; then
    echo "ERROR: file count mismatch — source=$src_count  dest=$dst_count" >&2
    exit 1
fi

echo "Dogfood refreshed: $dst_count files synced to .agents/skills/deepworkplan/"
