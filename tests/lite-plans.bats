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

# --- negative lifecycle probes -------------------------------------------------
# Each builds a throwaway mutant of the committed Lite fixture and asserts the
# conformance checker rejects exactly the unsafe shape, with an actionable line.

mutant_setup() {
  MUT="$(mktemp -d)"
  mkdir -p "$MUT/plans"
  cp -r "$FIXTURE/plans/PLAN_lite_fixture" "$MUT/plans/PLAN_lite_mutant"
  python3 - "$MUT/plans/PLAN_lite_mutant/state.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["plan"]="PLAN_lite_mutant"; json.dump(d,open(p,"w"),indent=2)
PY
  python3 - "$MUT/plans/PLAN_lite_mutant/manifest.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["name"]="PLAN_lite_mutant"; json.dump(d,open(p,"w"),indent=2)
PY
  MUT_DIR="$MUT/plans/PLAN_lite_mutant"
}
mutant_teardown() { [ -n "${MUT:-}" ] && rm -rf "$MUT"; }

state_patch() {
  python3 - "$MUT_DIR/state.json" "$1" <<'PY'
import json,sys
p,expr=sys.argv[1],sys.argv[2]
d=json.load(open(p)); exec(expr); json.dump(d,open(p,"w"),indent=2)
PY
}

run_mutant() { run env DWP_DIR="$MUT" bash "$REPO_ROOT/skills/deepworkplan/verify/conformance.sh" --plan PLAN_lite_mutant "$REPO_ROOT"; }

@test "an interrupted Lite materialization is rejected, not run" {
  mutant_setup
  state_patch 'd["materialization"]="materializing"'
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"materialization is not ready"* ]]
  mutant_teardown
}

@test "an unresolved promotion marker is rejected as a recovery boundary" {
  mutant_setup
  state_patch 'd["promotion"]={"from":"lite","to":"full","phase":"tasks_written"}'
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"unresolved promotion marker"* ]]
  mutant_teardown
}

@test "a duplicated task anchor is rejected" {
  mutant_setup
  printf '\n## Task 1: Duplicate {#task-1}\n' >> "$MUT_DIR/README.md"
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"anchor is missing or duplicated: 1"* ]]
  mutant_teardown
}

@test "a task record with no anchor is rejected" {
  mutant_setup
  python3 - "$MUT_DIR/README.md" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read().replace("{#task-2}","")
open(p,"w").write(s)
PY
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"anchor is missing or duplicated: 2"* ]]
  mutant_teardown
}

@test "a gate-less Lite task is rejected" {
  mutant_setup
  python3 - "$MUT_DIR/README.md" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p).read()
# strip the Validation heading from task 1 only
head,sep,tail=s.partition("## Task 2")
head=head.replace("### Validation","### Notes",1)
open(p,"w").write(head+sep+tail)
PY
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"lacks Validation: 1"* ]]
  mutant_teardown
}

@test "non-contiguous Lite task ids are rejected" {
  mutant_setup
  state_patch 'd["tasks"][1]["id"]=5; d["tasks"][1]["locator"]["value"]="#task-5"'
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"not contiguous"* ]]
  mutant_teardown
}

@test "a false completed_count is rejected" {
  mutant_setup
  state_patch 'd["completed_count"]=2'
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"completed_count disagrees"* ]]
  mutant_teardown
}

@test "state claiming a task the README has not checked is rejected" {
  mutant_setup
  state_patch 'd["tasks"][0]["status"]="completed"; d["completed_count"]=1'
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"disagrees with README: Task 1"* ]]
  mutant_teardown
}

@test "a Lite plan without a Final Review is rejected" {
  mutant_setup
  python3 - "$MUT_DIR/README.md" <<'PY'
import sys
p=sys.argv[1]; open(p,"w").write(open(p).read().replace("Final Review","Wrap Up"))
PY
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"lacks Final Review"* ]]
  mutant_teardown
}

@test "checkboxes inside a fenced example are not progress" {
  mutant_setup
  cat >> "$MUT_DIR/README.md" <<'MD'

```markdown
- [x] Task 1: this is an example, not progress
- [x] Task 2: neither is this
```
MD
  run_mutant
  [ "$status" -eq 0 ]
  [[ "$output" == *"Lite task anchors, records and Final Review are valid"* ]]
  mutant_teardown
}

@test "an unapproved proposal stays structurally valid but is reported" {
  mutant_setup
  state_patch 'd["approval"]="pending"'
  run_mutant
  [ "$status" -eq 0 ]
  [[ "$output" == *"awaiting approval"* ]]
  mutant_teardown
}

@test "an unknown approval value is rejected" {
  mutant_setup
  state_patch 'd["approval"]="yolo"'
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"unknown approval value"* ]]
  mutant_teardown
}

@test "the v2 state schema rejects traversal, absolute and unknown locators" {
  require_jsonschema
  run python3 - "$REPO_ROOT" "$FIXTURE" <<'PY'
import copy, json, sys
from jsonschema import Draft202012Validator
root, fixture = sys.argv[1:]
schema = json.load(open(root + '/skills/deepworkplan/spec/schema/plan-state-v2.schema.json'))
state = json.load(open(fixture + '/plans/PLAN_lite_fixture/state.json'))
v = Draft202012Validator(schema)
assert not list(v.iter_errors(state)), "the shipped fixture must validate"
for bad_value in ('../escape.md', '/etc/passwd', '#task-0', 'task-1', '1.task_x.md/../y'):
    bad = copy.deepcopy(state); bad['tasks'][0]['locator']['value'] = bad_value
    assert list(v.iter_errors(bad)), 'accepted an unsafe locator: ' + bad_value
for bad_kind in ('anchor', 'url', ''):
    bad = copy.deepcopy(state); bad['tasks'][0]['locator']['kind'] = bad_kind
    assert list(v.iter_errors(bad)), 'accepted an unknown locator kind: ' + bad_kind
bad = copy.deepcopy(state); bad['approval'] = 'yolo'
assert list(v.iter_errors(bad)), 'accepted an unknown approval value'
bad = copy.deepcopy(state); bad['cost'] = {'tokens': 1}
assert list(v.iter_errors(bad)), 'v2 state must stay a closed schema'
PY
  [ "$status" -eq 0 ]
}

@test "a promoted v2 Full plan uses file locators and still validates" {
  require_jsonschema
  run python3 - "$REPO_ROOT" "$FIXTURE" <<'PY'
import copy, json, sys
from jsonschema import Draft202012Validator
root, fixture = sys.argv[1:]
schema = json.load(open(root + '/skills/deepworkplan/spec/schema/plan-state-v2.schema.json'))
state = json.load(open(fixture + '/plans/PLAN_lite_fixture/state.json'))
promoted = copy.deepcopy(state)
promoted['format'] = 'full'
for task in promoted['tasks']:
    task['locator'] = {'kind': 'file', 'value': '%d.task_promoted.md' % task['id']}
v = Draft202012Validator(schema)
assert not list(v.iter_errors(promoted)), [e.message for e in v.iter_errors(promoted)]
# A Full plan may not point at an inline anchor and vice versa is caught by the
# conformance checker; the schema guards the locator grammar itself.
bad = copy.deepcopy(promoted); bad['tasks'][0]['locator']['value'] = 'promoted.md'
assert list(v.iter_errors(bad))
PY
  [ "$status" -eq 0 ]
}

@test "an unknown future plan format is refused, not guessed as legacy" {
  require_jsonschema
  run python3 - "$REPO_ROOT" "$FIXTURE" <<'PY'
import copy, json, sys
from jsonschema import Draft202012Validator
root, fixture = sys.argv[1:]
v1 = json.load(open(root + '/skills/deepworkplan/spec/schema/plan-state.schema.json'))
v2 = json.load(open(root + '/skills/deepworkplan/spec/schema/plan-state-v2.schema.json'))
state = json.load(open(fixture + '/plans/PLAN_lite_fixture/state.json'))
future = copy.deepcopy(state)
future['schema'] = 'https://deepworkplan.com/schema/plan-state/v3.json'
# Neither the v1 nor the v2 schema may claim a v3 document.
assert list(Draft202012Validator(v1).iter_errors(future))
assert list(Draft202012Validator(v2).iter_errors(future))
unknown = copy.deepcopy(state); unknown['format'] = 'turbo'
assert list(Draft202012Validator(v2).iter_errors(unknown))
PY
  [ "$status" -eq 0 ]
}

@test "a Lite plan missing its README is reported, not a crashed run" {
  mutant_setup
  rm "$MUT_DIR/README.md"
  run_mutant
  [ "$status" -ne 0 ]
  [[ "$output" == *"has no README.md"* ]]
  # The run must still reach a verdict instead of dying inside the parser.
  [[ "$output" == *"Verdict:"* ]]
  [[ "$output" != *"Traceback"* ]]
  mutant_teardown
}

@test "a healthy Lite plan degrades to advisories when python3 is unavailable" {
  FAKEBIN="$(mktemp -d)/bin"
  mkdir -p "$FAKEBIN"
  for t in bash sh grep sed awk cat ls find basename dirname sort uniq head tail tr wc mktemp rm cp mkdir git readlink stat cut expr; do
    for d in /usr/bin /bin /usr/local/bin; do
      if [ -x "$d/$t" ]; then ln -sf "$d/$t" "$FAKEBIN/$t"; break; fi
    done
  done
  [ -x "$FAKEBIN/grep" ] || skip "could not build a python3-free PATH on this host"
  run env -i PATH="$FAKEBIN" HOME="$HOME" DWP_DIR="$FIXTURE" \
    bash "$REPO_ROOT/skills/deepworkplan/verify/conformance.sh" --plan PLAN_lite_fixture
  # Format dispatch must not depend on python3: a Lite plan may never be
  # misread as a Full plan with zero task files.
  [ "$status" -eq 0 ]
  [[ "$output" == *"python3 unavailable"* ]]
  [[ "$output" != *"mandatory final task missing"* ]]
  rm -rf "$(dirname "$FAKEBIN")"
}
