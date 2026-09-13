#!/usr/bin/env bats
# Contract tests for claims that must stay true as the pack changes.
#
# Prose drifts silently. Every assertion here derives its expectation from the
# filesystem (count the sub-skills, list the helpers, read the standard) rather
# than from a second copy of the same sentence, so a claim cannot stay green by
# being wrong in two places at once.
#
# What it pins:
#   - the sub-skill count quoted in contributor docs equals the number that
#     actually ships;
#   - the helper inventory quoted in TRUST.md and the contributor docs equals
#     the helpers that actually ship;
#   - every shipped spec document's methodology footer states the current
#     standard, not a superseded one;
#   - the documentation-closure policy is stated once and consistently: the
#     task that touches a registered surface updates its docs, and the Final
#     Review sweeps what is left — no instruction licenses deferring;
#   - absolutes that outran the mechanism are gone and do not return
#     (guaranteed output parity, the ~90/~10 and 99% ratios);
#   - the published claim table exists and labels contract-presence evidence
#     as such.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
}

@test "the quoted sub-skill count equals the number of sub-skills that ship" {
    local actual
    # A sub-skill is a directory under the pack root with its own SKILL.md,
    # excluding the shared/spec/guide/examples areas and the addons tree.
    actual="$(find "$SK" -mindepth 2 -maxdepth 2 -name SKILL.md \
        -not -path "$SK/addons/*" | wc -l | tr -d ' ')"
    [ "$actual" -eq 9 ]
    local word="nine"
    for f in "$REPO_ROOT/AGENTS.md" "$REPO_ROOT/CONTRIBUTING.md" \
             "$REPO_ROOT/PUBLISHING.md" "$REPO_ROOT/docs/OPENCLAW.md" \
             "$REPO_ROOT/docs/DESIGN.md"; do
        if grep -qiE '\b(six|seven|eight) sub-skill' "$f"; then
            echo "stale sub-skill count in $f (the pack ships $actual):"
            grep -niE '\b(six|seven|eight) sub-skill' "$f"
            return 1
        fi
    done
    grep -q "router + $word sub-skills" "$REPO_ROOT/AGENTS.md"
}

@test "the quoted helper inventory names every helper that ships" {
    local helpers
    helpers="$(cd "$SK" && find . -name '*.py' -o -name '*.sh' | sed 's|^\./||' | sort)"
    [ -n "$helpers" ]
    # TRUST.md is the install-time promise a user reads before running anything:
    # every executable the pack ships must be named there.
    local missing=""
    while IFS= read -r h; do
        grep -qF "$(basename "$h")" "$SK/TRUST.md" || missing="$missing $h"
    done <<< "$helpers"
    if [ -n "$missing" ]; then
        echo "TRUST.md does not name shipped helper(s):$missing"; return 1
    fi
    # And the contributor scope list must not still describe a Bash-only pack.
    grep -qF "state_contract.py" "$REPO_ROOT/AGENTS.md"
    grep -qF "finalize_plan.py" "$REPO_ROOT/AGENTS.md"
    grep -qF "state_contract.py" "$REPO_ROOT/CONTRIBUTING.md"
}

@test "every shipped spec footer states the current standard" {
    local standard offenders
    standard="$(grep -m1 -oE '^SUPPORTED_SPEC = .[0-9]+\.[0-9]+\.[0-9]+' \
        "$SK/verify/plan_contract.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    [ -n "$standard" ]
    offenders="$(grep -rn 'Part of the DeepWorkPlan methodology v' "$SK" \
        | grep -v "methodology v$standard," || true)"
    if [ -n "$offenders" ]; then
        echo "spec footer(s) not at the current standard ($standard):"
        printf '%s\n' "$offenders"
        return 1
    fi
    # The check is only meaningful if footers exist at all.
    [ "$(grep -rl 'Part of the DeepWorkPlan methodology v' "$SK" | wc -l | tr -d ' ')" -ge 8 ]
}

@test "documentation closure is one policy: current in the task, swept at the end" {
    # The normative rule.
    doc_has "$SK/spec/DWP_SPECIFICATION.md" "is **not** deferred to a final catch-up task"
    doc_has "$SK/guide/authoring.md" "is a reconciliation miss, not a follow-up"
    # The execution loop must agree with it rather than license deferral.
    doc_has "$SK/execute/SKILL.md" "does **block this task's closure**"
    doc_has "$SK/execute/SKILL.md" "never as a silent carry-forward"
    # The exact wording that contradicted §6.6 must not return.
    if doc_has "$SK/execute/SKILL.md" "they are recorded and swept by the Final"; then
        echo "the deferral licence is back in execute/SKILL.md"
        grep -n "recorded and swept" "$SK/execute/SKILL.md"
        return 1
    fi
    # Both halves keep the true part: a doc fix does not invalidate a passing gate.
    doc_has "$SK/execute/SKILL.md" "invalidate a passing code gate"
}

@test "retired absolutes and unsupported ratios do not come back" {
    local offenders
    offenders="$(grep -rnE '~?9[05]% (identical|common|baseline)|~10% repo-specific|99% case' \
        "$SK" "$REPO_ROOT/docs" "$REPO_ROOT/README.md" "$REPO_ROOT/AGENTS.md" 2>/dev/null || true)"
    if [ -n "$offenders" ]; then
        echo "unsupported ratio claim(s) returned:"; printf '%s\n' "$offenders"; return 1
    fi
    # Parity of inputs is the claim; equality of model output is not.
    if grep -q "parity is guaranteed" "$REPO_ROOT/AGENTS.md"; then
        echo "AGENTS.md again guarantees local/CI parity"; return 1
    fi
    doc_has "$REPO_ROOT/AGENTS.md" "input parity is the claim"
    # The adaptation guidance keeps the provenance without the false precision.
    doc_has "$SK/shared/adaptation.md" "not a measured constant"
}

@test "the published claim table labels each kind of evidence" {
    local rec="$REPO_ROOT/docs/evaluations/v5-reliability.md"
    doc_has "$rec" "## Claims, mechanisms and evidence"
    doc_has "$rec" "**Contract presence**"
    doc_has "$rec" "it is *never* evidence that a model obeys it"
    doc_has "$rec" "### Claims deliberately not made"
    doc_has "$rec" "No claim that a plan cannot fail."
    # Every row must carry a limitation column entry — an unbounded claim is
    # the defect this table exists to prevent.
    local rows bad
    rows="$(awk '/^\| Claim \| Mechanism/{t=1; next} t && /^\|---/{next} t && /^\|/{print} t && !/^\|/{t=0}' "$rec")"
    [ "$(printf '%s\n' "$rows" | wc -l | tr -d ' ')" -ge 8 ]
    bad="$(printf '%s\n' "$rows" | awk -F'|' 'NF < 7 || $6 ~ /^ *$/ {print}')"
    if [ -n "$bad" ]; then echo "claim row without a limitation:"; printf '%s\n' "$bad"; return 1; fi
}

@test "the testing registry registers this suite" {
    doc_has "$REPO_ROOT/docs/TESTING_GUIDE.md" "tests/claims-consistency.bats"
}

doc_has() {
    sed 's/^[[:space:]]*>[[:space:]]\{0,1\}//' "$1" | tr '\n' ' ' | tr -s ' ' | grep -qF -- "$2"
}

@test "the Lite anatomy teaches a field label the checker actually parses" {
    # Found by the L1 acceptance run: the sketch showed bare `**Goal**` in
    # prose, the agent wrote `**Goal.**`, and the checker reported one "lacks
    # Goal" issue per task for zero content reasons. The sketch now states the
    # accepted forms and says why they are load-bearing.
    local cr="$SK/create/SKILL.md"
    doc_has "$cr" "The label form is load-bearing, not styling."
    doc_has "$cr" 'Write each field label as `**Goal:**` or `**Goal**` — those two, exactly.'
    doc_has "$cr" "makes the field invisible to it"
    # And the claim must stay true: those two forms are what the parser accepts.
    grep -q "label_pattern" "$SK/verify/plan_contract.py"
    grep -qF "r'\\*\\*(?:'+label+r')\\s*:?\\*\\*" "$SK/verify/plan_contract.py"
}

@test "a missing testing registry has a documented resolution, not a dead read" {
    # Found by the L1 acceptance run: create declares the target's
    # docs/TESTING_GUIDE.md compulsory, but the workspace had none while
    # AGENTS.md documented both a full and a scoped command — a case the
    # procedure did not cover.
    local cr="$SK/create/SKILL.md"
    doc_has "$cr" "When the target has no \`docs/TESTING_GUIDE.md\`"
    doc_has "$cr" "the gate is derived from the real commands found there"
    doc_has "$cr" "never a reason to invent a command the repository does not have"
}

@test "the trust promise admits the one place the pack is written to" {
    # Found by the L2 acceptance run: importing a pack helper leaves a
    # __pycache__ inside the installed pack, which the install-time promise
    # said never happens. The claim is narrowed to the truth rather than the
    # observation being ignored.
    doc_has "$SK/TRUST.md" "one honest exception that is CPython's behavior rather than ours"
    doc_has "$SK/TRUST.md" "safe to delete"
    # The shipped helpers must actually set the flag the promise cites.
    for helper in shared/update-state.py shared/finalize_plan.py; do
        grep -q "sys.dont_write_bytecode = True" "$SK/$helper" || {
            echo "$helper does not set dont_write_bytecode"; return 1
        }
    done
}

@test "the label rule covers Full task files, not only Lite records" {
    # Found by the R2-L2 acceptance run: the "labels are load-bearing" callout
    # existed only on the Lite path, while plan_contract.py parses Full task
    # files identically. An agent authoring a Full plan had to read the checker
    # to learn the accepted forms.
    doc_has "$SK/guide/authoring.md" "Section headings and field labels are load-bearing, not styling."
    doc_has "$SK/guide/authoring.md" "applies to **Full task files exactly as it does to Lite inline records**"
    doc_has "$SK/guide/authoring.md" "makes the field invisible to the checker"
}

@test "create does not present an execute-time helper as a create-time step" {
    # Found by the R2-L2 acceptance run: Step 4.5 told create to "include
    # verified plan publication from shared/finalize_plan.py", but at create
    # time there is no candidate and no completed log for it to validate.
    doc_has "$SK/create/SKILL.md" "is an **execute-time** helper"
    doc_has "$SK/create/SKILL.md" "do not try to run it here"
    doc_has "$SK/create/SKILL.md" "What create owes is the Final Review **task text**"
    # And the checker invocation must not be given in a form no flow can run.
    doc_has "$SK/create/SKILL.md" "written relative to this file, not to any flow's working directory"
}

@test "a Full plan records its Format Decision" {
    # Found by the R2-L2 acceptance run: the Format Decision record was
    # specified only in the Lite anatomy, so an explicit full preference that
    # overrode the rubric left no audit trail.
    doc_has "$SK/create/SKILL.md" "the **Format Decision** record — the observed signals and why this plan is Full"
    doc_has "$SK/create/SKILL.md" "overrode the rubric, so the choice is auditable"
}

@test "the Lite anatomy is valid markdown and DWP_DIR is described correctly" {
    # Both found by the R2-L1 acceptance run. The anatomy block collapsed three
    # '##' headings onto one line — copied literally it is not markdown and
    # defeats the checker's own Goal/Context detection. And Step 4.5 called
    # DWP_DIR "the actual plan root", while every other pack file defines it as
    # the .dwp directory that CONTAINS plans/; following it literally points
    # the checker at a tree with no plans/ in it.
    local cr="$SK/create/SKILL.md"
    if grep -qE '^## [0-9]+\. [A-Za-z ]+ +## [0-9]+\.' "$cr"; then
        echo "the anatomy block again collapses headings onto one line:"
        grep -nE '^## [0-9]+\. [A-Za-z ]+ +## [0-9]+\.' "$cr"
        return 1
    fi
    if grep -q "DWP_DIR pointing to the actual plan root" "$cr"; then
        echo "Step 4.5 again misdescribes DWP_DIR"; return 1
    fi
    doc_has "$cr" "the \`.dwp\` directory that contains \`plans/\`** — not at the plan folder itself"
    # The claim must agree with the definition the shared reference gives.
    doc_has "$SK/shared/dwp-paths.md" "DWP_DIR"
}

@test "the guide teaches how to address a cited section" {
    # Found by the R3-L2 acceptance run: both create and execute cite
    # "guide/execution.md §6.1", but that file's heading is `## 6.1.` — the
    # index requires top-level sections in its map, so a subsection sits at the
    # same level as its parent. An agent extracting `### 6.1` reads EMPTY and
    # exits ZERO: a silent no-read, the worst failure mode for a tiered path.
    doc_has "$SK/guide/GUIDE.md" "Addressing a section: by its number, not by a heading level."
    doc_has "$SK/guide/GUIDE.md" "would match nothing, exit **zero**, and read **empty**"
    doc_has "$SK/guide/GUIDE.md" "comes back empty, that is a defect to report"
    # And the citation gate must be real: every cited §N.M has to resolve.
    grep -q "cited section does not exist" "$REPO_ROOT/scripts/check-guide-migration.py"
}

@test "the citation gate actually catches a broken section reference" {
    # Injected-failure control: a gate that never fails proves nothing.
    local work
    work="$(mktemp -d)"
    cp -R "$SK" "$work/deepworkplan"
    printf '\nSee `../guide/execution.md` §99.99 for details.\n' >> "$work/deepworkplan/create/SKILL.md"
    run python3 "$REPO_ROOT/scripts/check-guide-migration.py" --pack "$work/deepworkplan"
    rm -rf "$work"
    [ "$status" -ne 0 ]
    [[ "$output" == *"cited section does not exist"* ]]
}

@test "closing the last task documents the terminal checkpoint it requires" {
    # Found by the R3-L2 acceptance run: the `--checkpoint-step done` literal
    # lived only in spec/PLAN_STATE.md §4.4, which the execute tier does not
    # load for a normal close. An agent reading the refusal as "the transaction
    # cannot run" hand-closes and leaves no receipt — exactly the failure this
    # evaluation's round 2 produced (oracle A6).
    doc_has "$SK/execute/SKILL.md" "Closing the LAST task additionally requires \`--checkpoint-step done\`"
    doc_has "$SK/execute/SKILL.md" "correctable input error, not a broken transaction"
    doc_has "$SK/execute/SKILL.md" "Never read it as permission to close the plan by hand"
    # And the rule must be where the spec says it is.
    doc_has "$SK/spec/PLAN_STATE.md" "The terminal checkpoint is the one fixed value."
    grep -q 'completed state requires terminal checkpoint' "$SK/shared/state_contract.py"
    grep -q '"step": "done"' "$SK/shared/state_contract.py"
}

@test "create does not generate a checklist step execute forbids" {
    # Found by the R3-L2 acceptance run: the generated Final Review checklist
    # hard-coded a commit, while execute forbids manufacturing a cosmetic one
    # for a review whose whole output is gitignored. The executing agent was
    # forced to choose which contract to disobey.
    doc_has "$SK/create/SKILL.md" "a **review-only** outcome is a legitimate close"
    doc_has "$SK/create/SKILL.md" "Do not emit a checklist line that hard-codes a commit"
    doc_has "$SK/execute/SKILL.md" "A review-only Final Review may close with no commit."
    doc_has "$SK/execute/SKILL.md" "Never manufacture an empty or cosmetic commit"
}
