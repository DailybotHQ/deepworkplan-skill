#!/usr/bin/env bats
# Schema-line publication guards (DWP standard 5.0.0, schema v5 URLs).
#
# The v5 schema URLs are generation snapshots of the v2 shape — no property
# added, renamed, or re-typed. Three invariants keep that line honest:
#   1. URL<->file sync: every deepworkplan.com/schema/... URL referenced in
#      the pack maps to a shipped file in spec/schema/ under the pinned
#      naming convention (v1 unsuffixed, vN>=2 suffixed), and every shipped
#      schema file's $id follows the same convention. This is the guard that
#      would have caught the website gap on the skill side of the boundary.
#   2. Fixtures: v2-era and v5-era manifest/state pairs each validate under
#      their own schema file (jsonschema when installed, like
#      tests/schema-contract.bats); the v5 files are exact generation
#      snapshots of v2 ($id/schema-const/description excepted); and
#      plan_contract.py pairs eras (v5 state with a v2 manifest is a torn
#      write, and vice versa).
#   3. Version agreement: the four spec docs' Version fields agree with each
#      other and with both checkers' SUPPORTED_SPEC, and the create/onboard
#      writers emit the v5 URLs + spec_version 5.0.0.
#
# scripts/check-schema-contract.py (dev infra) is deliberately NOT extended to
# the v5 line: its fixtures declare <= 2.4.0, so staying at (2, 4, 0) is
# harmless; the runtime contract (plan_contract.py) is what carries v5.

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    PACK="$REPO_ROOT/skills/deepworkplan"
    TMPDIR_TEST="$(mktemp -d)"
}
teardown() { rm -rf "$TMPDIR_TEST"; }

@test "every schema URL referenced in the pack maps to a shipped schema file" {
    urls="$(grep -rhoE 'https://deepworkplan\.com/schema/plan-(manifest|state)/v[0-9]+\.json' "$PACK" | sort -u)"
    [ -n "$urls" ]
    # v1/v2/v5 for both labels = six URLs, all published lines.
    [ "$(echo "$urls" | wc -l | tr -d ' ')" -eq 6 ]
    while IFS= read -r url; do
        label="${url#*schema/plan-}"; label="${label%%/*}"
        v="${url##*/v}"; v="${v%.json}"
        if [ "$v" = "1" ]; then file="plan-$label.schema.json"; else file="plan-$label-v$v.schema.json"; fi
        [ -s "$PACK/spec/schema/$file" ] || { echo "URL $url has no shipped file spec/schema/$file"; exit 1; }
    done <<< "$urls"
}

@test "every shipped schema file's \$id follows the URL/naming convention and pins its own const" {
    for f in "$PACK"/spec/schema/plan-manifest*.schema.json "$PACK"/spec/schema/plan-state*.schema.json; do
        base="$(basename "$f")"
        url="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("$id",""))' "$f")"
        [ -n "$url" ] || { echo "$base has no \$id"; exit 1; }
        label="${url#*schema/plan-}"; label="${label%%/*}"
        v="${url##*/v}"; v="${v%.json}"
        case "$base" in
            plan-$label.schema.json) [ "$v" = "1" ] || { echo "$base names v$v in \$id $url"; exit 1; } ;;
            plan-$label-v$v.schema.json) : ;;
            *) echo "$base does not match its \$id $url"; exit 1 ;;
        esac
        # the closed schema const must equal the file's own \$id
        const="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["properties"]["schema"].get("const",""))' "$f")"
        [ "$const" = "$url" ] || { echo "$base schema const $const != \$id $url"; exit 1; }
    done
}

@test "the v5 schemas are exact generation snapshots of the v2 shape" {
    python3 - "$PACK/spec/schema" <<'PY'
import copy, json, sys
base = sys.argv[1]
for label in ('manifest', 'state'):
    v2 = json.load(open(f'{base}/plan-{label}-v2.schema.json'))
    v5 = json.load(open(f'{base}/plan-{label}-v5.schema.json'))
    desc = v5.pop('description', None)
    assert desc and 'generation snapshot of the v2 shape' in desc.lower(), 'v5 description must state the snapshot honestly'
    assert 'remain valid' in desc.lower(), 'v5 description must say v2 plans remain valid'
    n5 = copy.deepcopy(v5)
    n5['$id'] = v2['$id']
    n5['properties']['schema'] = v2['properties']['schema']
    assert n5 == v2, f'plan-{label}-v5 diverges from the v2 shape beyond $id/const/description'
PY
}

@test "v2-era and v5-era fixtures validate under their own schemas (jsonschema)" {
    python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
    python3 - "$PACK/spec/schema" <<'PY'
import json, sys, jsonschema
base = sys.argv[1]
manifest = {
    "schema": "https://deepworkplan.com/schema/plan-manifest/v2.json",
    "spec_version": "4.0.0", "name": "PLAN_schema_fixture", "archetype": "individual",
    "rigor": "standard", "created_at": "2026-09-01T09:00:00Z",
    "task_count": 2, "plan_format": "full",
}
state = {
    "schema": "https://deepworkplan.com/schema/plan-state/v2.json",
    "plan": "PLAN_schema_fixture", "updated_at": "2026-09-01T09:00:00Z",
    "status": "pending", "completed_count": 0, "task_count": 2,
    "format": "full", "materialization": "ready",
    "tasks": [{"id": 1, "locator": {"kind": "inline", "value": "#task-1"},
               "title": "one", "status": "pending", "gates": []}],
}
for era in ('v2', 'v5'):
    ver = '4.0.0' if era == 'v2' else '5.0.0'
    m = dict(manifest, schema=manifest['schema'].replace('v2.json', f'{era}.json'), spec_version=ver)
    s = dict(state, schema=state['schema'].replace('v2.json', f'{era}.json'))
    for label, doc in (('manifest', m), ('state', s)):
        schema = json.load(open(f'{base}/plan-{label}-{era}.schema.json'))
        jsonschema.Draft202012Validator(schema).validate(doc)  # raises when invalid
    # negative probe: the schema const actually pins the era — a v2 document
    # must be rejected by the v5 schema and vice versa
    other = 'v5' if era == 'v2' else 'v2'
    wrong = dict(manifest, schema=manifest['schema'].replace('v2.json', f'{other}.json'))
    schema = json.load(open(f'{base}/plan-manifest-{era}.schema.json'))
    try:
        jsonschema.Draft202012Validator(schema).validate(wrong)
        raise AssertionError(f'{era} manifest schema accepted a {other} URL')
    except jsonschema.ValidationError:
        pass
PY
}

@test "plan_contract.py pairs schema eras and accepts the full published line" {
    folder="$TMPDIR_TEST/PLAN_schema_fixture"
    mkdir -p "$folder"
    m5='{"schema":"https://deepworkplan.com/schema/plan-manifest/v5.json","spec_version":"5.0.0","name":"PLAN_schema_fixture","archetype":"individual","rigor":"standard","created_at":"2026-09-01T09:00:00Z","task_count":2,"plan_format":"full"}'
    s5='{"schema":"https://deepworkplan.com/schema/plan-state/v5.json","plan":"PLAN_schema_fixture","updated_at":"2026-09-01T09:00:00Z","status":"pending","completed_count":0,"task_count":2,"format":"full","materialization":"ready","tasks":[{"id":1,"locator":{"kind":"inline","value":"#task-1"},"title":"one","status":"pending","gates":[]}]}'
    m2='{"schema":"https://deepworkplan.com/schema/plan-manifest/v2.json","spec_version":"4.0.0","name":"PLAN_schema_fixture","archetype":"individual","rigor":"standard","created_at":"2026-09-01T09:00:00Z","task_count":2,"plan_format":"full"}'
    echo "$m5" > "$folder/manifest.json"; echo "$s5" > "$folder/state.json"
    # v5 state + v2 manifest = torn write, fails with the era-pairing message
    echo "$m2" > "$folder/manifest.json"
    run python3 "$PACK/verify/plan_contract.py" "$folder"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q 'v5 state requires its v5 creation manifest'
    # a URL outside the published line is unknown, not silently accepted
    python3 - "$folder" <<'PY'
import json, sys
p = sys.argv[1] + '/state.json'
d = json.load(open(p)); d['schema'] = 'https://deepworkplan.com/schema/plan-state/v4.json'
json.dump(d, open(p, 'w'))
PY
    run python3 "$PACK/verify/plan_contract.py" "$folder"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q 'unknown state schema URL'
}

@test "the four spec docs and both checkers agree on 5.0.0, and writers emit the v5 line" {
    for doc in DWP_SPECIFICATION PLAN_STATE DOCUMENTATION_STANDARD; do
        grep -q '^| \*\*Version\*\* | 5\.0\.0 |$' "$PACK/spec/$doc.md" || { echo "$doc.md Version != 5.0.0"; exit 1; }
    done
    grep -q '^| Version | 5\.0\.0 |$' "$PACK/spec/LITE_PLANS.md" || { echo "LITE_PLANS.md Version != 5.0.0"; exit 1; }
    grep -q "^SUPPORTED_SPEC = '5.0.0'$" "$PACK/verify/plan_contract.py"
    grep -q '^SUPPORTED_SPEC="5.0.0"$' "$PACK/verify/conformance.sh"
    # writers: new plans declare the v5 URLs and spec_version 5.0.0
    grep -q 'plan-manifest/v5\.json' "$PACK/create/SKILL.md"
    grep -q 'plan-state/v5\.json' "$PACK/create/SKILL.md"
    grep -q '\*\*"5\.0\.0"\*\*' "$PACK/create/SKILL.md"
    grep -q 'DWP spec 5\.0\.0' "$PACK/create/SKILL.md"
    grep -q 'DWP standard: 5\.0\.0' "$PACK/onboard/SKILL.md"
}
