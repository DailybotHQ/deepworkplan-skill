#!/usr/bin/env bash
set -euo pipefail

# Sync the shipped skill pack (skills/deepworkplan/) into the dogfood
# location (.agents/skills/deepworkplan/) so this repo eats its own
# cooking.
#
# This is the ONLY supported way to refresh the in-repo deepworkplan
# dogfood copy. auto-release.yml deliberately does NOT overwrite
# `.agents/skills/deepworkplan/` via `npx skills add`, because that would
# pull the last *published tag* while this repo's contributors must dogfood
# the pack at THIS working revision — including changes not yet released.
# Addon skills (`dailybot`, `ai-diff-reviewer`) ARE auto-refreshed on
# release from their own upstreams; deepworkplan is not.
#
# The dogfood copy carries no local adaptations: after this script runs it
# is byte-identical to skills/deepworkplan/, and the check below enforces
# that. The repo's own Dailybot / AI Diff Reviewer wiring lives in
# AGENTS.md and .agents/settings.json, never inside the vendored pack.
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

# Copy file by file through ordinary reads and writes rather than `cp -R`. On
# some overlay/virtiofs mounts `cp` takes a clone/reflink path that can produce
# a right-sized, all-NUL file for a source written moments earlier. The
# checksum check below catches that either way; this avoids it in the first
# place, and keeps the script dependency-free.
while IFS= read -r rel; do
    mkdir -p "$DST/$(dirname "$rel")"
    cat "$SRC/$rel" > "$DST/$rel"
    if [ -x "$SRC/$rel" ]; then
        chmod +x "$DST/$rel"
    fi
done < <(cd "$SRC" && find . -type f | sed 's|^\./||')

src_count="$(find "$SRC" -type f | wc -l | tr -d ' ')"
dst_count="$(find "$DST" -type f | wc -l | tr -d ' ')"

if [ "$src_count" != "$dst_count" ]; then
    echo "ERROR: file count mismatch — source=$src_count  dest=$dst_count" >&2
    exit 1
fi

# A matching file count is not proof the contents copied. On some filesystems a
# copy can produce a right-sized, all-NUL file; verify every byte instead.
# Prefer GNU sha256sum (Linux CI); fall back to shasum -a 256 (default macOS).
if command -v sha256sum >/dev/null 2>&1; then
    src_sums="$(cd "$SRC" && find . -type f -exec sha256sum {} + | sort -k2)"
    dst_sums="$(cd "$DST" && find . -type f -exec sha256sum {} + | sort -k2)"
elif command -v shasum >/dev/null 2>&1; then
    src_sums="$(cd "$SRC" && find . -type f -exec shasum -a 256 {} + | sort -k2)"
    dst_sums="$(cd "$DST" && find . -type f -exec shasum -a 256 {} + | sort -k2)"
else
    echo "ERROR: need sha256sum or shasum to verify the dogfood copy" >&2
    exit 1
fi

if [ "$src_sums" != "$dst_sums" ]; then
    echo "ERROR: content mismatch after copy — these files differ:" >&2
    diff <(printf '%s\n' "$src_sums") <(printf '%s\n' "$dst_sums") >&2 || true
    echo "The dogfood copy is NOT byte-equal to the shipped pack. Re-run; if it" >&2
    echo "persists, copy the listed files individually before committing." >&2
    exit 1
fi

echo "Dogfood refreshed: $dst_count files synced to .agents/skills/deepworkplan/"
echo "Verified: every file is byte-identical to skills/deepworkplan/."

# The lockfile records a content hash of this folder, so refreshing the copy
# without refreshing the hash leaves skills-lock.json lying about what is
# vendored. The helper recomputes ONLY the deepworkplan entry, and refuses to
# write unless it can first reproduce an untouched entry's recorded hash.
if command -v node >/dev/null 2>&1; then
    node "$REPO_ROOT/scripts/update-dogfood-lock.mjs"
else
    echo "WARNING: node not found — skills-lock.json's deepworkplan hash was NOT" >&2
    echo "refreshed and is now stale. Run scripts/update-dogfood-lock.mjs before" >&2
    echo "committing." >&2
fi
