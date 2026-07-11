#!/usr/bin/env bash
set -euo pipefail

# Sync the shipped skill pack (skills/deepworkplan/) into the dogfood
# location (.agents/skills/deepworkplan/) so this repo eats its own
# cooking. Run after any change to files under skills/deepworkplan/.

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
