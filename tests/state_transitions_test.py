"""Behavioral subprocess regressions for the public state writer."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT/'skills/deepworkplan/shared/update-state.py'
FIXTURE = ROOT/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture/state.json'


class Transitions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'state.json'
        self.path.write_bytes(FIXTURE.read_bytes())

    def state(self):
        return json.loads(self.path.read_text())

    def write(self, state):
        self.path.write_text(json.dumps(state))

    def run_writer(self, *args, ok=True):
        before = self.path.read_bytes()
        result = subprocess.run(['python3', str(WRITER), str(self.path), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(self.path.read_bytes(), before)
        return result

    def test_missing_failed_zero_evidence_rejected(self):
        for gate in (None, 'unit|1|failed', 'unit|0|executed=0/0', 'unit|0|', '|0|executed=1'):
            args = ['--task','1','--status','completed']
            if gate is not None:
                args += ['--gate',gate]
            self.run_writer(*args, ok=False)

    def test_unrelated_failure_survives_partial_success(self):
        self.run_writer('--task','1','--status','in_progress','--gate','lint|1|failed')
        self.run_writer('--task','1','--status','completed','--gate','unit|0|executed=2',ok=False)
        self.run_writer('--task','1','--status','completed','--gate','lint|0|fixed','--gate','unit|0|executed=2')
        self.assertEqual(len(self.state()['tasks'][0]['gates']),3)

    def test_structured_gate_handles_pipes_without_execution(self):
        gate = dict(command='cat input | checker',passes=True,exit_code=0,last_run='2026-09-13T00:00:00Z',evidence='executed=1')
        self.run_writer('--task','1','--status','completed','--gate-json',json.dumps(gate))
        self.assertEqual(self.state()['tasks'][0]['gates'][0],gate)

    def test_inconsistent_structured_gate_rejected(self):
        gate = dict(command='unit',passes=True,exit_code=1,last_run='2026-09-13T00:00:00Z',evidence='executed=1')
        self.run_writer('--task','1','--status','completed','--gate-json',json.dumps(gate),ok=False)

    def test_block_and_explicit_repair(self):
        self.run_writer('--task','1','--status','blocked','--block-reason','missing service')
        self.assertEqual(self.state()['status'],'blocked')
        self.run_writer('--task','1','--status','in_progress',ok=False)
        self.run_writer('--task','1','--status','in_progress','--resolve-blocker')
        self.assertIsNone(self.state()['blocked'])
        self.assertEqual(self.state()['status'],'in_progress')

    def test_unrelated_blocker_cannot_be_cleared(self):
        self.run_writer('--task','2','--status','blocked','--block-reason','missing service')
        self.run_writer('--task','1','--status','completed','--resolve-blocker','--gate','unit|0|executed=1',ok=False)

    def test_skipped_never_completes_plan_or_permits_skipping_ahead(self):
        self.run_writer('--task','1','--status','skipped')
        self.run_writer('--task','2','--status','completed','--gate','unit|0|executed=1',ok=False)
        self.run_writer('--task','2','--status','skipped')
        self.assertEqual(self.state()['status'],'in_progress')
        self.assertEqual(self.state()['completed_count'],0)

    def test_malformed_records_are_unchanged(self):
        base = self.state()
        for change in ('identity','count','locator','agent'):
            s = copy.deepcopy(base)
            if change=='identity': s['tasks'][1]['id']=1
            if change=='count': s['completed_count']=1
            if change=='locator': s['tasks'][0]['locator']['value']='#task-2'
            if change=='agent': s['updated_by']='invalid'
            self.write(s)
            self.run_writer('--task','1','--status','in_progress',ok=False)

    def test_stale_snapshot_and_cooperative_lock(self):
        self.run_writer('--task','1','--status','in_progress','--expected-sha256','0'*64,ok=False)
        lock=Path(str(self.path)+'.lock');lock.mkdir()
        self.run_writer('--task','1','--status','in_progress',ok=False)
        lock.rmdir()
        digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.run_writer('--task','1','--status','in_progress','--expected-sha256',digest)

    def test_reopen_requires_explicit_reason(self):
        self.run_writer('--task','1','--status','completed','--gate','unit|0|executed=1')
        self.run_writer('--task','1','--status','pending',ok=False)
        self.run_writer('--task','1','--status','pending','--reopen-reason','approved criterion amendment')

    def test_pending_approval_and_partial_plan_rejected(self):
        for key,value in [('approval','pending'),('materialization','materializing')]:
            self.path.write_bytes(FIXTURE.read_bytes());s=self.state();s[key]=value;self.write(s)
            self.run_writer('--task','1','--status','in_progress',ok=False)


if __name__=='__main__':
    unittest.main()
