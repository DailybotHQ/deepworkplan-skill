#!/usr/bin/env bats
# Contract tests for honest instruction accounting.
#
# Round-1's counter-finding was not only that flows read too much: it was that
# the ONLY published number — the per-flow entry bundle — could be read as the
# cost of a whole run. It is not. A run pays the entry bundle at t0 and then
# whatever its triggers fire; the two must be measured and published
# separately, and the second must never be hidden by relabelling an inevitable
# read as "conditional".
#
# The contract under test:
#   - tests/efficiency/paths.tsv declares named end-to-end read paths, each an
#     ordered list of phases with the literal trigger that loads them;
#   - every file it names exists AND is declared in the entry flow's own
#     "Shared resources" section, so a path can never drift from the read
#     contract it models (broken/missing-reference detection);
#   - a path's entry phase is exactly that flow's compulsory read set, so
#     entry and end-to-end numbers stay internally consistent;
#   - files read at more than one moment are disclosed, never double-counted;
#   - the script publishes its exclusions and states plainly that entry bytes
#     do not cap a run;
#   - create's tiering is a real path change (a Lite creation reads no guide
#     file) and the Full path still pays for what it loads — the anti-gaming
#     assertion;
#   - the guard cost this plan added is disclosed rather than hidden.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    PACK="$REPO_ROOT/skills/deepworkplan"
    PATHS="$REPO_ROOT/tests/efficiency/paths.tsv"
    MEASURE="$REPO_ROOT/tests/efficiency/measure-instruction-load.sh"
}

# --- the manifest itself -----------------------------------------------------

@test "paths.tsv declares the six named end-to-end paths" {
    [ -f "$PATHS" ]
    local ids
    ids="$(rows | cut -f1 | sort -u)"
    for want in create-lite create-full execute-final-review \
                resume-assessment resume-execution conditional-escalation; do
        printf '%s\n' "$ids" | grep -qx "$want" || {
            echo "missing path: $want"; echo "$ids"; return 1
        }
    done
    [ "$(printf '%s\n' "$ids" | wc -l | tr -d ' ')" -eq 6 ]
}

@test "every manifest row has four tab-separated fields and a nonempty trigger" {
    local bad
    bad="$(rows | awk -F'\t' 'NF != 4 || $2 == "" || $3 == "" || $4 == "" {print NR": "$0}')"
    if [ -n "$bad" ]; then echo "malformed rows:"; printf '%s\n' "$bad"; return 1; fi
    # A nonempty manifest is the point: zero rows must never read as success.
    [ "$(rows | wc -l | tr -d ' ')" -ge 20 ]
}

@test "every file a path names exists in the pack" {
    local missing=""
    while IFS= read -r rel; do
        [ -f "$PACK/$rel" ] || missing="$missing $rel"
    done < <(rows | cut -f4 | sort -u)
    if [ -n "$missing" ]; then echo "paths.tsv names missing files:$missing"; return 1; fi
}

@test "every file a path names is declared in that flow's Shared resources" {
    # Drift guard: the manifest models the read contract, so it may only name
    # files the contract itself links. A companion that disappears from a
    # flow's tiers, or one the manifest invents, fails here.
    local offenders=""
    while IFS=$'\t' read -r pid _ph _tr rel; do
        local flow flows found section
        flow="$(entry_flow "$pid")"
        # The router is the implicit entry read of every path. A path that
        # loads another flow's contract (resume -> execute at Step 5) is
        # governed by that flow's tiers from then on, so its section counts
        # as a declaration site too.
        [ "$rel" = "SKILL.md" ] && continue
        flows="$flow $(governing_flows "$pid")"
        found=0
        for f in $flows; do
            [ "$rel" = "$f/SKILL.md" ] && { found=1; break; }
            section="$(sed -n '/^## Shared resources/,/^## [A-Z]/p' "$PACK/$f/SKILL.md")"
            declared "$section" "$rel" && { found=1; break; }
        done
        [ "$found" -eq 1 ] || offenders="$offenders
  $pid: $rel not linked in the Shared resources of:$flows"
    done < <(rows | awk -F'\t' '!seen[$1 FS $4]++')
    if [ -n "$offenders" ]; then echo "undeclared path files:$offenders"; return 1; fi
}

# --- internal consistency of the two measurements ----------------------------

@test "the script publishes paths, repeats, triggers, exclusions and the non-cap rule" {
    run bash "$MEASURE" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    printf '%s' "$output" | grep -qF "## End-to-end instruction paths"
    printf '%s' "$output" | grep -qF "## Repeated reads (disclosed, not counted twice)"
    printf '%s' "$output" | grep -qF "## Phase triggers"
    printf '%s' "$output" | grep -qF "## Exclusions"
    printf '%s' "$output" | grep -qF "## What this measurement is not"
    printf '%s' "$output" | grep -qF "Not a cap on a run."
    printf '%s' "$output" | grep -qF "neither bounds the total context"
}

@test "each path's entry column equals that flow's compulsory read set" {
    run bash "$MEASURE" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    local pid flow bundle entry
    for pid in create-lite create-full execute-final-review \
               resume-assessment resume-execution conditional-escalation; do
        flow="$(entry_flow "$pid")"
        bundle="$(printf '%s' "$output" | awk -v f="$flow" '$1 == f && $3 == "bytes" {print $2}')"
        entry="$(printf '%s' "$output" | awk -v p="$pid" '$1 == p && NF == 6 {print $2}')"
        [ -n "$bundle" ] && [ -n "$entry" ]
        if [ "$bundle" -ne "$entry" ]; then
            echo "$pid: entry column $entry != $flow bundle $bundle"; return 1
        fi
    done
}

@test "path totals are at least their entry bundle and never double-count" {
    run bash "$MEASURE" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    local line pid entry total files sum
    while IFS= read -r line; do
        set -- $line
        pid="$1"; entry="$2"; total="$3"; files="$5"
        [ "$total" -ge "$entry" ] || { echo "$pid: total $total < entry $entry"; return 1; }
        # Unique-file accounting: the reported file count must equal the number
        # of distinct files the manifest names for that path, and the reported
        # byte total must equal the sum of those distinct files' sizes — a
        # repeated read may not inflate either.
        [ "$files" -eq "$(rows | awk -F'\t' -v p="$pid" '$1 == p && !s[$4]++' | wc -l | tr -d ' ')" ]
        sum=0
        while IFS= read -r rel; do
            sum=$(( sum + $(wc -c < "$PACK/$rel" | tr -d ' ') ))
        done < <(rows | awk -F'\t' -v p="$pid" '$1 == p && !s[$4]++ {print $4}')
        [ "$sum" -eq "$total" ] || { echo "$pid: sum $sum != reported $total"; return 1; }
    done < <(printf '%s' "$output" | awk 'NF == 6 && $2 ~ /^[0-9]+$/ && $4 ~ /x$/')
}

@test "a repeated read is disclosed for every file a path loads at two moments" {
    run bash "$MEASURE" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    local repeats
    repeats="$(rows | awk -F'\t' '{n[$1 FS $4]++} END {for (k in n) if (n[k] > 1) {split(k, a, FS); print a[1]"\t"a[2]}}')"
    [ -n "$repeats" ]   # the manifest must actually exercise this case
    while IFS=$'\t' read -r pid rel; do
        printf '%s' "$output" | grep -qE "^$pid +$rel +[0-9]+ moments" || {
            echo "undisclosed repeated read: $pid $rel"; return 1
        }
    done < <(printf '%s\n' "$repeats")
}

@test "a broken path reference fails the measurement instead of counting zero" {
    # Injected-failure control for the reference check above.
    local work
    work="$(mktemp -d)"
    cp -R "$PACK" "$work/pack-tmp" && mkdir -p "$work/skills" && mv "$work/pack-tmp" "$work/skills/deepworkplan"
    mkdir -p "$work/tests/efficiency"
    cp "$MEASURE" "$PATHS" "$work/tests/efficiency/"
    printf 'injected\tentry\tinjected control\tguide/NO_SUCH_FILE.md\n' >> "$work/tests/efficiency/paths.tsv"
    run bash "$work/tests/efficiency/measure-instruction-load.sh" "$work"
    rm -rf "$work"
    [ "$status" -ne 0 ]
    printf '%s' "$output" | grep -qF "does not exist"
}

# --- create's tiering: a real path change, not a relabel ---------------------

@test "create declares the three tiers with literal only-when triggers" {
    local cr section cond offenders
    cr="$PACK/create/SKILL.md"
    doc_has "$cr" "## Shared resources (read at their moment, not upfront)"
    doc_has "$cr" "**Essential now (before composing anything):**"
    doc_has "$cr" "**Conditional — read only when the trigger fires:**"
    doc_has "$cr" "**Never by default:**"
    section="$(sed -n '/^## Shared resources/,/^## Parameter Reference/p' "$cr")"
    cond="$(printf '%s' "$section" | sed -n '/^- \*\*Conditional/,/^- \*\*Never/p' | sed '$d')"
    [ -n "$cond" ]
    offenders="$(printf '%s' "$cond" | awk '
        /^- /{next}
        /^  - /{if (b != "" && b !~ /only +when/) print b; b = $0; next}
        {gsub(/ +/, " "); b = b " " $0}
        END{if (b != "" && b !~ /only +when/) print b}')"
    if [ -n "$offenders" ]; then echo "conditional entries without a trigger:"; printf '%s\n' "$offenders"; return 1; fi
    # The never tier must stay link-free or its files silently become compulsory.
    local never
    never="$(printf '%s' "$section" | sed -n '/^- \*\*Never by default/,$p')"
    [ -n "$never" ]
    printf '%s' "$never" | grep -qF 'not defensively, not "to be safe"'
    if printf '%s' "$never" | grep -q ']('; then
        echo "never-by-default tier contains a link:"; printf '%s\n' "$never" | grep ']('; return 1
    fi
}

@test "a Lite creation reads no guide file at all" {
    run bash "$MEASURE" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    # The entry bundle names its files; none may come from guide/.
    local files
    files="$(printf '%s' "$output" | awk '$1 == "create" && $3 == "bytes"')"
    if printf '%s' "$files" | grep -q 'guide/'; then
        echo "create entry bundle still loads a guide file: $files"; return 1
    fi
    # The pre-tiering bundle was 103,400 B (router + create + CREATE_PLAN +
    # PROMPTS_TEMPLATE + authoring + adaptation + dwp-paths). The bound leaves
    # headroom for prose growth but trips if a guide companion returns.
    local bytes
    bytes="$(printf '%s' "$output" | awk '$1 == "create" && $3 == "bytes" {print $2}')"
    [ -n "$bytes" ]
    [ "$bytes" -le 75000 ]
}

@test "the Full path still pays for the companions it loads" {
    # Anti-gaming: relabelling authoring.md and structure.md as conditional is
    # only honest because the path that needs them is measured and reports the
    # higher number. If create-full ever stopped counting them, this fails.
    run bash "$MEASURE" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    local lite full
    lite="$(printf '%s' "$output" | awk '$1 == "create-lite" && NF == 6 {print $3}')"
    full="$(printf '%s' "$output" | awk '$1 == "create-full" && NF == 6 {print $3}')"
    [ -n "$lite" ] && [ -n "$full" ]
    [ "$full" -gt "$lite" ]
    rows | awk -F'\t' '$1 == "create-full" {print $4}' | grep -qx 'guide/authoring.md'
    rows | awk -F'\t' '$1 == "create-full" {print $4}' | grep -qx 'guide/structure.md'
}

@test "an always-firing trigger is counted on the paths it fires on" {
    # The Final Review companions load on every create, so both create paths
    # must count them even though they sit in the conditional tier.
    local pid
    for pid in create-lite create-full; do
        rows | awk -F'\t' -v p="$pid" '$1 == p {print $4}' | grep -qx 'create/addon-augmentations.md' || {
            echo "$pid does not count the Final Review addon companion"; return 1
        }
        rows | awk -F'\t' -v p="$pid" '$1 == p {print $4}' | grep -qx 'guide/execution.md' || {
            echo "$pid does not count guide/execution.md"; return 1
        }
    done
    # And the contract says so in words, so a future editor cannot "optimize"
    # the number by pretending the trigger is rare.
    doc_has "$PACK/create/SKILL.md" "this trigger always fires, so the end-to-end path measurement counts it"
}

@test "the execute Final Review names the reviewer file it loads" {
    # A companion the flow loads but never names is a dangling reference: the
    # manifest cannot model it and a reader cannot find it.
    doc_has "$PACK/execute/SKILL.md" "](../addons/ai-diff-reviewer/SKILL.md)"
    [ -f "$PACK/addons/ai-diff-reviewer/SKILL.md" ]
}

# --- the guard cost this plan added -----------------------------------------

@test "the reliability guard cost is disclosed, not hidden" {
    local rec="$REPO_ROOT/docs/evaluations/v5-reliability.md"
    [ -f "$rec" ]
    doc_has "$rec" "## Instruction accounting"
    doc_has "$rec" "Guard cost"
    # The record must state the baseline it measures against and refuse the
    # two claims this plan forbids.
    doc_has "$rec" "6bf7830"
    doc_has "$rec" "Not a cap on a run."
}

@test "the testing registry maps this surface to its commands" {
    doc_has "$REPO_ROOT/docs/TESTING_GUIDE.md" "tests/context-accounting.bats"
    doc_has "$REPO_ROOT/docs/TESTING_GUIDE.md" "tests/efficiency/paths.tsv"
}

# --- helpers -----------------------------------------------------------------

rows() {
    grep -v '^#' "$PATHS" | grep -v '^[[:space:]]*$'
}

# Flows whose read contract the path itself loads after its entry flow.
governing_flows() {
    rows | awk -F'\t' -v p="$1" '$1 == p && $4 ~ /\/SKILL\.md$/ {sub("/SKILL.md", "", $4); print $4}' | sort -u
}

entry_flow() {
    case "$1" in
        create-*) echo create ;;
        resume-*) echo resume ;;
        *) echo execute ;;
    esac
}

# True when the Shared resources section links $2 — either at its full pack
# path (after stripping ../ and ./) or by bare filename when the link carries
# no directory component at all.
declared() {
    local section="$1" rel="$2" target norm
    while IFS= read -r target; do
        norm="$target"
        while case "$norm" in ../*|./*) true ;; *) false ;; esac; do
            norm="${norm#../}"; norm="${norm#./}"
        done
        [ "$norm" = "$rel" ] && return 0
        case "$target" in
            */*) ;;
            *) [ "$target" = "${rel##*/}" ] && return 0 ;;
        esac
    done < <(printf '%s' "$section" | grep -o '](\([^)]*\)\.md)' | sed 's/^](//; s/)$//')
    return 1
}

# Sentence-level assertion that tolerates the source file's own line wrapping.
doc_has() {
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
