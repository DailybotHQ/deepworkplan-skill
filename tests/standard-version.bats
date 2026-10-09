#!/usr/bin/env bash
# Contract tests for current v6 provenance and retained v5 base documents.
# Older standard series remain accepted for existing plans; there is no 3.x
# standard. Schema URLs are generation-specific and remain independent of
# the pack version.
#
# Run with:  bats tests/
# Requires:  bats-core, git, python3

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    FIXTURE="$REPO_ROOT/tests/fixtures/lite-plan/.dwp"
}

@test "repository provenance accepts v6 while the v5 plan checker stays generation-bound" {
    grep -q "SUPPORTED_SPEC = '5.0.0'" "$SK/verify/plan_contract.py"
    grep -q 'SUPPORTED_SPEC="6.0.0"' "$SK/verify/conformance.sh"
    grep -q 'SPEC_SERIES = (2, 4, 5)' "$SK/verify/plan_contract.py"
    grep -q 'standard_series_ok' "$SK/verify/conformance.sh"
    # Both eras reject a non-series version with the same teaching.
    grep -q 'which is not a DWP standard' "$SK/verify/plan_contract.py"
    [ "$(grep -c 'which is not a DWP standard' "$SK/verify/plan_contract.py")" -ge 2 ]
}

@test "new provenance says 6.0.0 while retained v5 documents keep their version" {
    grep -q 'DWP standard: 6.0.0 (onboarded' "$SK/onboard/SKILL.md"
    grep -q '"5.0.0"' "$SK/create/SKILL.md"
    grep -q '| Standard | DWP spec 5.0.0 |' "$SK/create/SKILL.md"
    grep -q '| \*\*Version\*\* | 5.0.0 |' "$SK/spec/DWP_SPECIFICATION.md"
    grep -q '| \*\*Version\*\* | 5.0.0 |' "$SK/spec/PLAN_STATE.md"
    grep -q '| Version | 5.0.0 |' "$SK/spec/LITE_PLANS.md"
    grep -q 'DWP standard: 6.0.0 (onboarded' "$SK/spec/DOCUMENTATION_STANDARD.md"
    # No stale 4.0.0/2.4.0-as-current stamp survives in the shipped pack;
    # only historical prose ("plans created under 4.0.0", "removed in 2.4.0")
    # remains.
    run grep -rn 'DWP spec 4\.0\.0' "$SK"
    [ "$status" -ne 0 ]
    run grep -rn 'DWP standard: 4\.0\.0' "$SK"
    [ "$status" -ne 0 ]
    run grep -rn '"4\.0\.0"' "$SK/create/SKILL.md"
    [ "$status" -ne 0 ]
    run grep -rn 'DWP spec 2\.4\.0' "$SK"
    [ "$status" -ne 0 ]
    run grep -rn 'DWP standard: 2\.4\.0' "$SK"
    [ "$status" -ne 0 ]
    run grep -rn '"2\.4\.0"' "$SK/create/SKILL.md"
    [ "$status" -ne 0 ]
}

@test "behavioral: a plan declaring 3.0.0 fails; 5.0.0, 4.0.0 and 2.4.0 pass" {
    WORK="$(mktemp -d)"
    mkdir -p "$WORK/plans"
    cp -r "$FIXTURE/plans/PLAN_lite_fixture" "$WORK/plans/PLAN_series_check"
    python3 - "$WORK/plans/PLAN_series_check" <<'PY'
import json, sys
base = sys.argv[1]
for name, key in (('state.json', 'plan'), ('manifest.json', 'name')):
    path = f'{base}/{name}'
    doc = json.load(open(path))
    doc[key] = 'PLAN_series_check'
    json.dump(doc, open(path, 'w'), indent=2)
PY
    for spec in 5.0.0 4.0.0 2.4.0 3.0.0 9.9.9; do
        python3 - "$WORK/plans/PLAN_series_check/manifest.json" "$spec" <<'PY'
import json, sys
path, spec = sys.argv[1:]
doc = json.load(open(path))
doc['spec_version'] = spec
json.dump(doc, open(path, 'w'), indent=2)
PY
        run env DWP_DIR="$WORK" bash "$SK/verify/conformance.sh" --plan PLAN_series_check "$REPO_ROOT"
        if [ "$spec" = 3.0.0 ]; then
            [ "$status" -ne 0 ]
            [[ "$output" == *"not a DWP standard"* ]]
        elif [ "$spec" = 9.9.9 ]; then
            [ "$status" -ne 0 ]
            [[ "$output" == *"newer than this checker supports"* ]]
        else
            [ "$status" -eq 0 ]
            [[ "$output" == *"plan standard: DWP spec $spec"* ]]
        fi
    done
    rm -rf "$WORK"
}

@test "behavioral: an AGENTS.md declaring a non-series standard fails repo conformance" {
    WORK="$(mktemp -d)"
    ( cd "$WORK" && git init -q . && mkdir -p .dwp/plans docs && printf '.dwp/\n' > .gitignore )
    printf 'scoped mapping fallback\n' > "$WORK/docs/TESTING_GUIDE.md"
    for spec in 3.0.0 9.9.9 5.0.0 4.0.0 2.4.0; do
        printf '# AGENTS\n\nDWP standard: %s (onboarded 2026-09-12; skill 5.1.0)\n' "$spec" > "$WORK/AGENTS.md"
        run bash "$SK/verify/conformance.sh" --repo-only "$WORK"
        case "$spec" in
            3.0.0) [[ "$output" == *"not a DWP standard"* ]] ;;
            9.9.9) [[ "$output" == *"newer than this checker supports"* ]] ;;
            *) [[ "$output" == *"AGENTS.md declares DWP standard $spec"* ]]
               [[ "$output" != *"not a DWP standard"* ]] ;;
        esac
    done
    rm -rf "$WORK"
}

@test "schema URLs are the v1/v2/v5 line plus the deliberate v6 line and its v7 contract generation" {
    # No v3/v4 schema URL may ever appear. plan-state stays on the published
    # v1/v2/v5 line forever — the v6 projection schema is plan-snapshot/v6,
    # never a plan-state/v6. Every other family adds exactly the deliberate
    # v6 candidate generation of the DWP v6 campaign (manifest = the A12
    # pointer, snapshot = the projection, contract, journal-event,
    # context-manifest), each pinned below and mapped to a shipped file by
    # tests/schema-publication.bats.
    # The 7.0.0 line adds exactly the v7 contract generation
    # (spec/V7_CONTRACT.md): plan-contract/v7, journal-event/v7 and
    # plan-manifest/v7. There is no snapshot or context-manifest v7 — v7
    # plans project into plan-snapshot/v6.
    run bash -c "grep -rn 'schema/plan-state/v[3-46-9]\|schema/plan-\(manifest\|contract\)/v[3-48-9]\|schema/plan-snapshot/v[3-47-9]\|schema/journal-event/v[3-48-9]\|schema/context-manifest/v[3-47-9]' '$SK'"
    [ "$status" -ne 0 ]
    grep -q 'plan-manifest/v5.json' "$SK/create/SKILL.md"
    grep -q 'plan-state/v5.json' "$SK/create/SKILL.md"
    grep -q 'https://deepworkplan.com/schema/plan-state/v2.json' "$SK/spec/schema/plan-state-v2.schema.json"
    grep -q 'https://deepworkplan.com/schema/plan-state/v5.json' "$SK/spec/schema/plan-state-v5.schema.json"
    # The v6 candidate line is pinned exactly: five families, five files.
    for pair in \
        'plan-manifest/v6.json plan-manifest-v6.schema.json' \
        'plan-snapshot/v6.json plan-snapshot-v6.schema.json' \
        'plan-contract/v6.json plan-contract-v6.schema.json' \
        'journal-event/v6.json journal-event-v6.schema.json' \
        'context-manifest/v6.json context-manifest-v6.schema.json' \
        'plan-manifest/v7.json plan-manifest-v7.schema.json' \
        'plan-contract/v7.json plan-contract-v7.schema.json' \
        'journal-event/v7.json journal-event-v7.schema.json'; do
        set -- $pair
        [ -s "$SK/spec/schema/$2" ]
        grep -q "https://deepworkplan.com/schema/$1" "$SK/spec/schema/$2"
    done
    # Historical URLs stay valid forever: the v2 files are untouched and the
    # v5 description states the generation-snapshot relationship.
    grep -q 'Generation snapshot of the v2 shape' "$SK/spec/schema/plan-state-v5.schema.json"
    grep -q 'Generation snapshot of the v2 shape' "$SK/spec/schema/plan-manifest-v5.schema.json"
}

@test "the three version series are mapped wherever versions are explained" {
    tr '\n' ' ' < "$SK/spec/DWP_SPECIFICATION.md" | tr -s ' ' | grep -qF 'Three version series coexist on purpose'
    tr '\n' ' ' < "$SK/spec/PLAN_STATE.md" | tr -s ' ' | grep -qF 'there is no 3.x standard'
    tr '\n' ' ' < "$SK/spec/DOCUMENTATION_STANDARD.md" | tr -s ' ' | grep -qF 'never compared against this line'
    # The 4.0.0 alignment move is recorded as precedent for the 5.0.0 one.
    tr '\n' ' ' < "$SK/spec/DWP_SPECIFICATION.md" | tr -s ' ' | grep -qF 'without changing any requirement from 2.4.0'
    # The anti-lockstep rule: the standard never chases the skill's version.
    tr '\n' ' ' < "$SK/spec/DWP_SPECIFICATION.md" | tr -s ' ' | grep -qF 'Anti-lockstep rule'
}
