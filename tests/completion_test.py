"""Independent plan-fixture oracles for terminal publication and crash recovery."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT/'skills/deepworkplan'
sys.path.insert(0,str(PACK/'shared'))
from finalize_plan import publish


def ready_plan(base, full=False):
    plan=Path(base)/'PLAN_lite_fixture'
    shutil.copytree(ROOT/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture',plan)
    candidate=json.loads((plan/'state.json').read_text())
    stamp='2026-09-13T00:00:00Z'
    for t in candidate['tasks']:
        t.update(status='completed',completed_at=stamp,gates=[dict(command='fixture-oracle',passes=True,exit_code=0,last_run=stamp,evidence='executed=1/1')])
    candidate.update(status='completed',completed_count=2,blocked=None,checkpoint=dict(task=2,step='done',at=stamp,note='Complete'))
    readme=(plan/'README.md').read_text().replace('[ ]','[x]').replace('0/2','2/2')
    log='\n### Completion & Log\n\nStatus: completed.\nSkills disposition: none.\nDocumentation decision: fixture updated.\n'
    readme=readme.replace('`true`','`true`\n'+log)
    if full:
        candidate['format']='full'
        manifest=json.loads((plan/'manifest.json').read_text());manifest['plan_format']='full'
        (plan/'manifest.json').write_text(json.dumps(manifest))
        for t in candidate['tasks']:
            filename=f'{t["id"]}.task_'+('final_review' if t['id']==2 else 'update_fixture')+'.md'
            t['locator']={'kind':'file','value':filename}
            body=readme.split(f'## Task {t["id"]}:',1)[1].split('\n## ',1)[0]
            (plan/filename).write_text('# Task '+str(t['id'])+':'+body)
            readme=readme.replace(f'- [x] Task {t["id"]}:',f'- [x] Task {t["id"]}: [{filename}]({filename})')
        readme=readme.replace('Plan Format: Lite','Plan Format: Full')
    (plan/'README.md').write_text(readme)
    (plan/'analysis_results/SECURITY_REVIEW.md').write_text('# Security review\n\nNo unresolved critical findings.\n\nDocumentation reconciliation: current.\n')
    (plan/'analysis_results/SKILLS_CANDIDATES.md').write_text('# Skills candidates\n\nNone.\n')
    return plan,candidate


class Completion(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.plan,self.candidate=ready_plan(self.tmp.name)

    def checker(self):
        return subprocess.run(['python3',str(PACK/'verify/plan_contract.py'),str(self.plan)],capture_output=True,text=True)

    def test_lite_publish_and_idempotent_receipt(self):
        publish(self.plan,self.candidate)
        first=(self.plan/'state.json').read_bytes()
        receipt=(self.plan/'analysis_results/FINALIZATION.json').read_bytes()
        publish(self.plan,self.candidate)
        self.assertEqual(first,(self.plan/'state.json').read_bytes())
        self.assertEqual(receipt,(self.plan/'analysis_results/FINALIZATION.json').read_bytes())
        self.assertEqual(self.checker().returncode,0)

    def test_full_uses_same_contract(self):
        with tempfile.TemporaryDirectory() as d:
            plan,candidate=ready_plan(d,full=True)
            publish(plan,candidate)
            self.assertEqual(json.loads((plan/'state.json').read_text())['status'],'completed')

    def test_invalid_candidate_failed_gate_and_terminal_blocker(self):
        original=(self.plan/'state.json').read_bytes()
        for defect in ('missing','failed','blocker','checkpoint'):
            c=copy.deepcopy(self.candidate)
            if defect=='missing': c['tasks'][1]['gates']=[]
            if defect=='failed': c['tasks'][1]['gates'][0].update(passes=False,exit_code=1)
            if defect=='blocker': c['blocked']=dict(task=1,reason='unresolved',since='2026-09-13T00:00:00Z')
            if defect=='checkpoint': c['checkpoint']['step']='start'
            with self.assertRaises(ValueError):publish(self.plan,c)
            self.assertEqual(original,(self.plan/'state.json').read_bytes())

    def test_interruption_before_state_publish_and_recovery(self):
        original=(self.plan/'state.json').read_bytes()
        def fault(phase):
            if phase=='before_publish':raise RuntimeError('simulated interruption')
        with self.assertRaises(RuntimeError):publish(self.plan,self.candidate,fault=fault)
        self.assertEqual(original,(self.plan/'state.json').read_bytes())
        self.assertNotEqual(self.checker().returncode,0)
        publish(self.plan,self.candidate,recover=True)
        self.assertEqual(self.checker().returncode,0)

    def test_interruption_after_publish_preserves_state_and_recovers(self):
        def fault(phase):
            if phase=='after_publish':raise RuntimeError('simulated interruption')
        with self.assertRaises(RuntimeError):publish(self.plan,self.candidate,fault=fault)
        self.assertEqual(json.loads((self.plan/'state.json').read_text()),self.candidate)
        with self.assertRaises(ValueError):publish(self.plan,self.candidate)
        publish(self.plan,self.candidate,recover=True)
        self.assertEqual(self.checker().returncode,0)

    def test_changed_artifacts_do_not_get_success_receipt(self):
        def fault(phase):
            if phase=='after_publish':
                f=self.plan/'README.md';f.write_text(f.read_text().replace('[x] Task 1','[ ] Task 1'))
        with self.assertRaises(ValueError):publish(self.plan,self.candidate,fault=fault)
        self.assertTrue((self.plan/'.finalizing.json').exists())
        self.assertFalse((self.plan/'analysis_results/FINALIZATION.json').exists())
        self.assertNotEqual(self.checker().returncode,0)

    def test_no_acceptance_log_no_closure(self):
        f=self.plan/'README.md';f.write_text(f.read_text().replace('Skills disposition:','Other disposition:'))
        with self.assertRaises(ValueError):publish(self.plan,self.candidate)

    def test_read_only_checker_leaves_no_artifacts(self):
        publish(self.plan,self.candidate)
        def snapshot():return {str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in self.plan.rglob('*') if f.is_file()}
        before=snapshot();self.assertEqual(self.checker().returncode,0);self.assertEqual(before,snapshot())
        self.assertFalse(list(PACK.rglob('__pycache__')))

    def test_cli_uses_candidate_without_running_its_commands(self):
        c=Path(self.tmp.name)/'candidate.json';c.write_text(json.dumps(self.candidate))
        x=subprocess.run(['python3',str(PACK/'shared/finalize_plan.py'),str(self.plan),'--candidate',str(c)],capture_output=True,text=True)
        self.assertEqual(x.returncode,0,x.stderr)


if __name__=='__main__':unittest.main()
