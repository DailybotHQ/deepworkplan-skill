#!/usr/bin/env bats

@test "v2 preserves v1 task evidence for both representations" {
  run python3 - "$BATS_TEST_DIRNAME/.." <<'PY'
import copy, json, pathlib, sys
from jsonschema import Draft202012Validator
root = pathlib.Path(sys.argv[1])
schema = json.loads((root/'skills/deepworkplan/spec/schema/plan-state-v2.schema.json').read_text())
v = Draft202012Validator(schema)
s = json.loads((root/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture/state.json').read_text())
t = s['tasks'][0]
t.update(status='completed', started_at='2026-09-11T00:00:00Z', completed_at='2026-09-11T00:01:00Z', commit='abcdef1', outcome={'worked':'Fixed behavior', 'tried':['unit regression'], 'failed':[], 'notes':'skills: none'})
t['gates'] = [{'command':'pytest', 'passes':True, 'exit_code':0, 'last_run':'2026-09-11T00:01:00Z', 'evidence':'ran=1/1'}]
s['completed_count'] = 1
assert not list(v.iter_errors(s))
s['format'] = 'full'
for task in s['tasks']:
    task['locator'] = {'kind':'file', 'value':str(task['id'])+'.task_fixture.md'}
assert not list(v.iter_errors(s))
for key, bad in [('gates',['not a gate']), ('commit','not-a-hash'), ('outcome',{'unknown':True})]:
    mutant = copy.deepcopy(s); mutant['tasks'][0][key] = bad
    assert list(v.iter_errors(mutant)), key
for key, bad in [('checkpoint',{'task':'invalid'}), ('blocked',{'unexpected':True}), ('promotion',{'from':'full','to':'lite','phase':'unknown'})]:
    mutant = copy.deepcopy(s); mutant[key] = bad
    assert list(v.iter_errors(mutant)), key
mutant = copy.deepcopy(s)
mutant['tasks'][0]['locator'] = {'kind':'file','value':'#task-1'}
assert list(v.iter_errors(mutant))
PY
  [ "$status" -eq 0 ]
}

@test "v2 rejects missing and mistyped gate evidence fields" {
  run python3 - "$BATS_TEST_DIRNAME/.." <<'PY'
import copy, json, pathlib, sys
from jsonschema import Draft202012Validator
r = pathlib.Path(sys.argv[1]); v = Draft202012Validator(json.loads((r/'skills/deepworkplan/spec/schema/plan-state-v2.schema.json').read_text()))
s = json.loads((r/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture/state.json').read_text())
for gate in [{}, {'command':'pytest','passes':None,'last_run':'2026-09-11'}, {'command':'pytest','passes':True,'last_run':'2026-09-11','extra':1}]:
    s['tasks'][0]['gates'] = [gate]
    assert list(v.iter_errors(s)), gate
PY
  [ "$status" -eq 0 ]
}
