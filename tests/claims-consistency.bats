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
    tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"
}
