#!/usr/bin/env bash
# Reproducible static measurement of the skill's instruction surface.
# Prints per-file bytes of the installed pack and the *compulsory read set* per flow
# (router + sub-skill + every file the sub-skill's "Shared resources" section links).
# Bytes are filesystem bytes; "/4" is a labeled estimate, never a token measurement.
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
PACK="$ROOT/skills/deepworkplan"
[ -d "$PACK" ] || { echo "no pack at $PACK" >&2; exit 1; }

echo "# Instruction load — $(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo no-git)"
echo
echo "## Installed Markdown (bytes)"
( cd "$PACK" && find . -name '*.md' -type f -print0 | xargs -0 wc -c | grep -v ' total$' | sort -rn | head -12 | sed 's/^ *//; s| \./| |' | awk '{printf "%-52s %8s\n",$2,$1}' )
echo "total: $(find "$PACK" -name '*.md' -type f -print0 | xargs -0 cat | wc -c)"
echo
echo "## Compulsory read set per flow (router + SKILL.md + linked shared resources)"
for flow in create execute resume refine onboard status verify; do
  f="$PACK/$flow/SKILL.md"; [ -f "$f" ] || continue
  total=$(( $(wc -c < "$PACK/SKILL.md") + $(wc -c < "$f") ))
  files="SKILL.md $flow/SKILL.md"
  # links of the form [`x`](../path) or (path) inside the Shared resources section
  while IFS= read -r ref; do
    p="$PACK/$flow/$ref"; p="$(cd "$(dirname "$p")" 2>/dev/null && pwd)/$(basename "$p")" || continue
    [ -f "$p" ] || continue
    case "$p" in *.md) total=$(( total + $(wc -c < "$p") )); files="$files ${p#"$PACK"/}";; esac
  done < <(sed -n '/^## Shared resources/,/^## /p' "$f" | awk '
      /^- /{cond = ($0 ~ /[Cc]onditional/)}      # a new bullet: conditional if its first line says so
      !cond {print}' | grep -o '](\.\./[^)]*\.md)' | sed 's/](\(.*\))/\1/' | sort -u)
  printf "%-8s %8d bytes  (~%d est. tokens)  <- %s\n" "$flow" "$total" $(( total / 4 )) "$files"
done
