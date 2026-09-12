#!/usr/bin/env bash
# Contract tests for the DWP standard version alignment (task 15):
# new stamps say 4.0.0 going forward; 2.x stays accepted as historical (no
# existing plan is rewritten); there is no 3.x standard (the v3 launch was a
# product release); schema URLs stay v2. Three version series are documented
# so a reader never confuses package version, standard and schema URL.
#
# Run with:  bats tests/
# Requires:  bats-core, git, python3

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    FIXTURE="$REPO_ROOT/tests/fixtures/lite-plan/.dwp"
}

@test "the checker implements the 4.x standard with the 2.x/4.x series rule" {
    grep -q "SUPPORTED_SPEC = '4.0.0'" "$SK/verify/plan_contract.py"
    grep -q 'SUPPORTED_SPEC="4.0.0"' "$SK/verify/conformance.sh"
    grep -q 'SPEC_SERIES = (2, 4)' "$SK/verify/plan_contract.py"
    grep -q 'standard_series_ok' "$SK/verify/conformance.sh"
    # Both eras reject a non-series version with the same teaching.
    grep -q 'which is not a DWP standard' "$SK/verify/plan_contract.py"
    [ "$(grep -c 'which is not a DWP standard' "$SK/verify/plan_contract.py")" -ge 2 ]
}

@test "new stamps say 4.0.0 — onboard, create and the spec documents" {
    grep -q 'DWP standard: 4.0.0 (onboarded' "$SK/onboard/SKILL.md"
    grep -q '"4.0.0"' "$SK/create/SKILL.md"
    grep -q '| Standard | DWP spec 4.0.0 |' "$SK/create/SKILL.md"
    grep -q '| \*\*Version\*\* | 4.0.0 |' "$SK/spec/DWP_SPECIFICATION.md"
    grep -q '| \*\*Version\*\* | 4.0.0 |' "$SK/spec/PLAN_STATE.md"
    grep -q '| Version | 4.0.0 |' "$SK/spec/LITE_PLANS.md"
    grep -q 'DWP standard: 4.0.0 (onboarded' "$SK/spec/DOCUMENTATION_STANDARD.md"
    # No stale 2.4.0-as-current stamp survives in the shipped pack; only
    # historical prose ("removed in 2.4.0", "under 2.4.0") remains.
    run grep -rn 'DWP spec 2\.4\.0' "$SK"
    [ "$status" -ne 0 ]
    run grep -rn 'DWP standard: 2\.4\.0' "$SK"
    [ "$status" -ne 0 ]
    run grep -rn '"2\.4\.0"' "$SK/create/SKILL.md"
    [ "$status" -ne 0 ]
}

@test "behavioral: a plan declaring 3.0.0 fails, 4.0.0 and 2.4.0 pass" {
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
    for spec in 4.0.0 2.4.0 3.0.0 5.0.0; do
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
        elif [ "$spec" = 5.0.0 ]; then
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
    for spec in 3.0.0 5.0.0 4.0.0 2.4.0; do
        printf '# AGENTS\n\nDWP standard: %s (onboarded 2026-09-12; skill 4.0.3)\n' "$spec" > "$WORK/AGENTS.md"
        run bash "$SK/verify/conformance.sh" --repo-only "$WORK"
        case "$spec" in
            3.0.0) [[ "$output" == *"not a DWP standard"* ]] ;;
            5.0.0) [[ "$output" == *"newer than this checker supports"* ]] ;;
            *) [[ "$output" == *"AGENTS.md declares DWP standard $spec"* ]]
               [[ "$output" != *"not a DWP standard"* ]] ;;
        esac
    done
    rm -rf "$WORK"
}

@test "schema URLs stay v2 — a schema-shape series, not the standard's version" {
    run bash -c "grep -rn 'schema/plan-\(state\|manifest\)/v[3-9]' '$SK'"
    [ "$status" -ne 0 ]
    grep -q 'plan-manifest/v2.json' "$SK/create/SKILL.md"
    grep -q 'plan-state/v2.json' "$SK/create/SKILL.md"
    grep -q 'https://deepworkplan.com/schema/plan-state/v2.json' "$SK/spec/schema/plan-state-v2.schema.json"
}

@test "the three version series are mapped wherever versions are explained" {
    tr '\n' ' ' < "$SK/spec/DWP_SPECIFICATION.md" | tr -s ' ' | grep -qF 'Three version series coexist on purpose'
    tr '\n' ' ' < "$SK/spec/PLAN_STATE.md" | tr -s ' ' | grep -qF 'there is no 3.x standard'
    tr '\n' ' ' < "$SK/spec/DOCUMENTATION_STANDARD.md" | tr -s ' ' | grep -qF 'never compared against this line'
    tr '\n' ' ' < "$SK/spec/DWP_SPECIFICATION.md" | tr -s ' ' | grep -qF 'changes no requirement from 2.4.0'
}
