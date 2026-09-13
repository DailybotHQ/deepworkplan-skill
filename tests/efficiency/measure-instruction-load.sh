#!/usr/bin/env bash
# Reproducible static measurement of the skill's instruction surface.
# Prints per-file bytes of the installed pack and the *compulsory read set* per flow
# (router + sub-skill + every file the sub-skill's "Shared resources" section links).
# Bytes are filesystem bytes; "/4" is a labeled estimate, never a token measurement.
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
ROOT="$(cd "$ROOT" && pwd)"
PACK="$ROOT/skills/deepworkplan"
[ -d "$PACK" ] || { echo "no pack at $PACK" >&2; exit 1; }

REVISION="export (record source revision separately)"
if [ "$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null || true)" = "$ROOT" ]; then
  REVISION="$(git -C "$ROOT" rev-parse --short HEAD)"
fi
echo "# Instruction load — $REVISION"
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

PATHS="$(dirname "$0")/paths.tsv"
if [ -f "$PATHS" ]; then
  SIZES="$(mktemp)"; trap 'rm -f "$SIZES"' EXIT
  # One size row per unique file named in the manifest. A missing file is a
  # hard error: a broken reference must never silently measure as zero bytes.
  awk -F'\t' '!/^#/ && NF >= 4 && !seen[$4]++ {print $4}' "$PATHS" | while IFS= read -r rel; do
    if [ ! -f "$PACK/$rel" ]; then
      echo "paths.tsv names a file that does not exist: $rel" >&2; exit 1
    fi
    printf '%s\t%s\n' "$rel" "$(wc -c < "$PACK/$rel" | tr -d ' ')"
  done > "$SIZES"
  [ -s "$SIZES" ] || { echo "no measurable rows in $PATHS" >&2; exit 1; }

  echo
  awk -F'\t' '
    FNR == NR { if (NF >= 2) sz[$1] = $2; next }
    /^#/ || NF < 4 { next }
    {
      p = $1; ph = $2; tr = $3; f = $4
      if (!(p in seenp)) { seenp[p] = 1; porder[++np] = p }
      key = p SUBSEP f
      if (!(key in seenf)) {
        seenf[key] = 1; ubytes[p] += sz[f]; ufiles[p]++
      }
      moments[key]++
      mnames[key] = mnames[key] (mnames[key] == "" ? "" : ", ") ph
      if (moments[key] == 2) { rorder[p] = rorder[p] (rorder[p] == "" ? "" : SUBSEP) f }
      phk = p SUBSEP ph
      if (!(phk in seenph)) {
        seenph[phk] = 1; nph[p]++
        trig[p] = trig[p] (trig[p] == "" ? "" : "\n") p "\t" ph "\t" tr
      }
      if (ph == "entry" && !((p SUBSEP f) in seene)) { seene[p SUBSEP f] = 1; ebytes[p] += sz[f] }
      total_rows++
    }
    END {
      print "## End-to-end instruction paths (unique pack files per named path)"
      print ""
      print "A path is the entry bundle plus the companions its named triggers load."
      print "Each unique file counts ONCE per path; files read at more than one moment"
      print "are disclosed below, never double-counted. Declared in tests/efficiency/paths.tsv."
      print ""
      printf "%-24s %9s %9s %8s %7s %7s\n", "path", "entry B", "path B", "vs entry", "files", "phases"
      for (i = 1; i <= np; i++) {
        p = porder[i]
        ratio = (ebytes[p] > 0) ? ubytes[p] / ebytes[p] : 0
        printf "%-24s %9d %9d %7.2fx %7d %7d\n", p, ebytes[p], ubytes[p], ratio, ufiles[p], nph[p]
      }
      print ""
      print "## Repeated reads (disclosed, not counted twice)"
      print ""
      any = 0
      for (i = 1; i <= np; i++) {
        p = porder[i]
        if (rorder[p] == "") continue
        n = split(rorder[p], rf, SUBSEP)
        for (j = 1; j <= n; j++) {
          k = p SUBSEP rf[j]
          printf "%-24s %-34s %d moments (%s)  %d B\n", p, rf[j], moments[k], mnames[k], sz[rf[j]]
          any = 1
        }
      }
      if (!any) print "(none declared)"
      print ""
      print "## Phase triggers"
      print ""
      for (i = 1; i <= np; i++) {
        n = split(trig[porder[i]], tl, "\n")
        for (j = 1; j <= n; j++) {
          split(tl[j], c, "\t")
          printf "%-24s %-18s %s\n", c[1], c[2], c[3]
        }
      }
    }
  ' "$SIZES" "$PATHS"

  cat <<'DISCLOSURE'

## Exclusions (what these numbers deliberately leave out)

Pack instruction files only. Every path above excludes: the repository's own
files the agent also reads (AGENTS.md, docs/TESTING_GUIDE.md, source under
review, existing plan folders), tool and command output, the plan files the
flow writes and re-reads, re-reads after a context compaction or handoff, the
agent's own output, and anything a host injects (system prompt, hooks, memory).

## What this measurement is not

- **Not tokens.** These are filesystem bytes. The `/4` column is a labeled
  estimate of tokens, never a measurement. No monetary or billing figure
  follows from any number here.
- **Not a cap on a run.** The entry bundle is what a flow loads at t0 and the
  path total is what its named triggers add — neither bounds the total context
  a real session consumes, which is dominated by the excluded material above.
  An entry-bundle reduction is a smaller starting read, not a proven saving in
  a live session.
- **Not a behavioral claim.** A declared read contract is what the pack
  instructs. Whether a given model obeys it is live evidence, recorded per
  harness in docs/COMPATIBILITY.md, not something this script can show.
DISCLOSURE
fi
