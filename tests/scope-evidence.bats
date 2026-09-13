#!/usr/bin/env bats

# Scope-and-evidence truth regressions (amendments, invalidation, false
# completion). The python blocks are behavioral oracles: they run the real
# checker and the real writer against sanitized fixtures derived from the
# historical contradiction (a ticked checklist over phases the report called
# structurally impossible). The final test is a contract-presence check and
# is labeled as such — it proves the docs teach the contract, not behavior.

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    WORK="$(mktemp -d)"
}

teardown() { rm -rf "$WORK"; }

@test "honest evidence verifies; a ticked box over admitted non-execution fails" {
  run python3 - "$REPO_ROOT" <<'PY'
import json, pathlib, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'tests'))
from completion_test import ready_plan
pack = pathlib.Path(sys.argv[1])/'skills/deepworkplan'
checker = str(pack/'verify/plan_contract.py')
with tempfile.TemporaryDirectory() as base:
    plan, candidate = ready_plan(base)
    (plan/'state.json').write_text(json.dumps(candidate))
    x = subprocess.run(['python3', checker, str(plan)], capture_output=True, text=True)
    assert x.returncode == 0, x.stdout  # clean control
    lies = ('five runs; fresh agents never entered the flows',
            'the phase did not run in this environment',
            'scenario unexecuted here — structurally impossible',
            'cannot be measured with the frozen harness')
    for lie in lies:
        s = json.loads((plan/'state.json').read_text())
        s['tasks'][0]['gates'][0]['evidence'] = 'executed=1/1; ' + lie
        (plan/'state.json').write_text(json.dumps(s))
        x = subprocess.run(['python3', checker, str(plan)], capture_output=True, text=True)
        assert x.returncode == 1, lie
        assert 'admits the check never ran' in x.stdout, (lie, x.stdout)
        s['tasks'][0]['gates'][0]['evidence'] = 'executed=1/1'
        (plan/'state.json').write_text(json.dumps(s))
        x = subprocess.run(['python3', checker, str(plan)], capture_output=True, text=True)
        assert x.returncode == 0, (lie, x.stdout)  # recovery by honest re-record
print('clean control + 4 injected contradictions, each recoverable')
PY
  [ "$status" -eq 0 ]
}

@test "a completed task whose log still says Status: pending is a mismatch" {
  run python3 - "$REPO_ROOT" <<'PY'
import json, pathlib, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'tests'))
from completion_test import ready_plan
pack = pathlib.Path(sys.argv[1])/'skills/deepworkplan'
checker = str(pack/'verify/plan_contract.py')
for full in (False, True):
    with tempfile.TemporaryDirectory() as base:
        plan, candidate = ready_plan(base, full=full)
        (plan/'state.json').write_text(json.dumps(candidate))
        target = plan/'README.md' if not full else plan/'1.task_update_fixture.md'
        target.write_text(target.read_text().replace('Status: completed.', 'Status: pending.'))
        x = subprocess.run(['python3', checker, str(plan)], capture_output=True, text=True)
        assert x.returncode == 1, ('full' if full else 'lite', x.stdout)
        assert 'still says "Status: pending"' in x.stdout, x.stdout
print('lite + full log/status contradictions detected')
PY
  [ "$status" -eq 0 ]
}

@test "evidence invalidated by refine is not passing evidence until rerun" {
  run python3 - "$REPO_ROOT" <<'PY'
import json, pathlib, subprocess, sys, tempfile
sys.dont_write_bytecode = True
root = pathlib.Path(sys.argv[1])
writer = str(root/'skills/deepworkplan/shared/update-state.py')
state = pathlib.Path(tempfile.mkdtemp())/'state.json'
state.write_bytes((root/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture/state.json').read_bytes())
def run_writer(*args):
    return subprocess.run(['python3', writer, str(state), *args], capture_output=True, text=True)
x = run_writer('--task','1','--status','completed','--gate','check-a|0|executed=1','--gate','check-b|0|executed=2')
assert x.returncode == 0, x.stderr
# refine 3.7 invalidation: reopen task 1, prefix only check-a's evidence.
s = json.loads(state.read_text())
s['tasks'][0]['status'] = 'pending'
s['tasks'][0]['gates'][0]['evidence'] = 'invalidated by refine 2026-09-13: executed=1'
s['status'], s['completed_count'] = 'pending', 0
state.write_text(json.dumps(s))
before = state.read_bytes()
# Re-closing without rerunning the invalidated command must be refused...
x = run_writer('--task','1','--status','completed')
assert x.returncode != 0 and 'invalidated by refine' in (x.stderr + x.stdout), x
assert state.read_bytes() == before
# ...and rerunning only that command closes it while check-b's record survives.
x = run_writer('--task','1','--status','completed','--gate','check-a|0|executed=1 again')
assert x.returncode == 0, x.stderr
s = json.loads(state.read_text())
gates = s['tasks'][0]['gates']
assert any(g['command'] == 'check-b' and g['evidence'] == 'executed=2' for g in gates)
assert gates[-1]['command'] == 'check-a' and gates[-1]['evidence'] == 'executed=1 again'
print('invalidated gate blocks closure until rerun; unrelated passing evidence preserved')
PY
  [ "$status" -eq 0 ]
}

@test "the checker and the writer agree on invalidated reliance" {
  run python3 - "$REPO_ROOT" <<'PY'
import json, pathlib, subprocess, sys, tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(sys.argv[1])/'tests'))
from completion_test import ready_plan
checker = str(pathlib.Path(sys.argv[1])/'skills/deepworkplan/verify/plan_contract.py')
with tempfile.TemporaryDirectory() as base:
    plan, candidate = ready_plan(base)
    candidate['tasks'][0]['gates'][0]['evidence'] = 'invalidated by refine 2026-09-13: executed=1/1'
    (plan/'state.json').write_text(json.dumps(candidate))
    x = subprocess.run(['python3', checker, str(plan)], capture_output=True, text=True)
    assert x.returncode == 1, x.stdout
    assert 'invalidated by refine' in x.stdout, x.stdout
print('completed task relying on invalidated evidence fails read-only verification')
PY
  [ "$status" -eq 0 ]
}

@test "contract presence (labeled): amendment record, five states and no-easier-check" {
  run python3 - "$REPO_ROOT" <<'PY'
import pathlib, sys
pack = pathlib.Path(sys.argv[1])/'skills/deepworkplan'
texts = {
    'refine': (pack/'refine/SKILL.md').read_text(),
    'execute': (pack/'execute/SKILL.md').read_text(),
    'state': (pack/'spec/PLAN_STATE.md').read_text(),
    'spec': (pack/'spec/DWP_SPECIFICATION.md').read_text(),
}
for field in ('Original criterion:', 'Observed:', 'Disposition:', 'Reason:',
              'Authority:', 'Affected tasks:', 'Evidence invalidated:', 'Evidence preserved:'):
    assert field in texts['refine'], field
for state in ('Completed investigation', 'Unexecuted scenario', 'Deferred requirement',
              'Failed gate', 'Achieved product outcome'):
    assert state in texts['state'] and state in texts['spec'], state
assert 'substituting an easier check is not repair' in texts['execute'].lower() or \
       'an easier check is not repair' in texts['execute'].lower()
assert 'amendment' in texts['execute'].lower()
print('amendment record fields, five evidence states and the no-easier-check rule are taught')
PY
  [ "$status" -eq 0 ]
}
