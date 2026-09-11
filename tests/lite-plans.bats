#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  FIXTURE="$REPO_ROOT/tests/fixtures/lite-plan/.dwp"
}

require_jsonschema() {
  python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
}

@test "a ready Lite plan passes the format-aware conformance path" {
  run env DWP_DIR="$FIXTURE" bash "$REPO_ROOT/skills/deepworkplan/verify/conformance.sh" --plan PLAN_lite_fixture "$REPO_ROOT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Lite task anchors, records and Final Review are valid"* ]]
}

@test "Lite v2 schemas accept inline locators and reject an invalid locator" {
  require_jsonschema
  run python3 - "$REPO_ROOT" "$FIXTURE" <<'PY'
import copy, json, sys
from jsonschema import Draft202012Validator
root, fixture = sys.argv[1:]
schema = json.load(open(root + '/skills/deepworkplan/spec/schema/plan-state-v2.schema.json'))
state = json.load(open(fixture + '/plans/PLAN_lite_fixture/state.json'))
assert not list(Draft202012Validator(schema).iter_errors(state))
bad = copy.deepcopy(state); bad['tasks'][0]['locator']['value'] = '../escape.md'
assert list(Draft202012Validator(schema).iter_errors(bad))
PY
  [ "$status" -eq 0 ]
}

@test "create documents boundary options and no-plan protections" {
  run grep -q 'contiguous `trust`/`auto`, `lite` and `full` tokens' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -eq 0 ]
  run grep -q 'conflict is an error' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -eq 0 ]
  run grep -q 'never route it to an' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -eq 0 ]
}

@test "create materializes Lite with the v2 schemas, not a draft" {
  # The Lite-first path must name the concrete v2 schemas it validates against;
  # prose alone let an agent fall through to the v1 Full writer.
  run grep -q 'spec/schema/plan-manifest-v2.schema.json' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -eq 0 ]
  run grep -q 'spec/schema/plan-state-v2.schema.json' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -eq 0 ]
  run grep -q '"kind": "inline", "value": "#task-N"' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -eq 0 ]
  # No shipped reader may still promise a refined draft as the default output.
  run grep -q 'stage the refined draft for review' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -ne 0 ]
  run grep -q 'Creates the \*\*refined draft\*\*' "$REPO_ROOT/skills/deepworkplan/create/SKILL.md"
  [ "$status" -ne 0 ]
}

@test "the generated dwp-create wrapper advertises the Lite-first flow" {
  run grep -q 'single-step refined draft' "$REPO_ROOT/skills/deepworkplan/onboard/command-templates/dwp-create.md"
  [ "$status" -ne 0 ]
  run grep -q 'Lite' "$REPO_ROOT/skills/deepworkplan/onboard/command-templates/dwp-create.md"
  [ "$status" -eq 0 ]
}
