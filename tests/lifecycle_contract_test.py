"""Behavioral contracts of the installed offline verifier, not prompt replays."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT/'skills/deepworkplan'
SPEC = importlib.util.spec_from_file_location('plan_contract', PACK/'verify/plan_contract.py')
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


class LifecycleContracts(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.plan = Path(self.scratch.name)/'plans/PLAN_lite_fixture'
        shutil.copytree(ROOT/'tests/fixtures/lite-plan/.dwp/plans/PLAN_lite_fixture', self.plan)
        self.state = json.loads((self.plan/'state.json').read_text())
        self.manifest = json.loads((self.plan/'manifest.json').read_text())
        self.readme = (self.plan/'README.md').read_text()

    def persist(self):
        (self.plan/'state.json').write_text(json.dumps(self.state))
        (self.plan/'manifest.json').write_text(json.dumps(self.manifest))
        (self.plan/'README.md').write_text(self.readme)

    def verify(self, expected=True):
        self.persist()
        result = subprocess.run(['bash', str(PACK/'verify/conformance.sh'), '--plan', self.plan.name, str(ROOT)], env={**os.environ, 'DWP_DIR': self.scratch.name}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if expected else 1, result.stdout+result.stderr)
        self.assertNotIn('Traceback', result.stdout+result.stderr)
        return result.stdout

    def complete(self):
        self.state.update(status='completed', completed_count=2)
        for task in self.state['tasks']:
            task.update(status='completed', completed_at='2026-09-11T00:01:00Z', commit='abcdef1', outcome={'worked':'verified'}, gates=[{'command':'true', 'passes':True, 'exit_code':0, 'last_run':'2026-09-11T00:01:00Z', 'evidence':'fixture manual gate verified'}])
        self.readme = self.readme.replace('- [ ]', '- [x]').replace('0/2 completed','2/2 completed')
        (self.plan/'analysis_results/SECURITY_REVIEW.md').write_text('No findings.\n')

    def promote(self):
        import re
        for task in self.state['tasks']:
            ident = task['id']
            filename = f'{ident}.task_'+('final_review' if ident == 2 else 'fixture')+'.md'
            body = re.search(r'(?ms)^## Task '+str(ident)+r'.*?(?=^## |\Z)', self.readme)[0]
            (self.plan/filename).write_text(body)
            task['locator'] = {'kind':'file', 'value':filename}
        self.state['format'] = 'full'
        self.readme = ('# Full fixture\n\n**Standard:** DWP spec 2.4.0\n\n## Goal\n\n'
                       'Keep the fixture contract valid.\n\n## Context\n\nFixture-only plan '
                       "under the skill repo's tests; no product surface.\n\n"
                       'Plan Status: 0/2 completed\n\n'
                       +'\n'.join(f'- [ ] Task {t["id"]}: [{t["title"]}](./{t["locator"]["value"]})' for t in self.state['tasks']))

    def test_ready_and_completed_lite(self):
        self.verify()
        self.complete()
        self.verify()

    def test_markdown_labels_preserve_semantic_fields(self):
        import re
        original = self.readme
        for style in ('**{}:**', '**{}**:', '**{}** ·'):
            self.readme = re.sub(r'^### (Goal|Touched Surface|Acceptance Criteria|Validation)$',
                                 lambda m: style.format(m[1]), original, flags=re.M)
            self.verify()
        self.readme = original.replace('Fixture only.', '**Not applicable — fixture only.**')
        self.verify()
        # Formatting tolerance must never accept an actually empty gate.
        self.readme = self.readme.replace('`true`', '')
        self.verify(False)

    def test_context_required_where_it_matters(self):
        import re
        original = self.readme
        strip_task = re.compile(r'(?ms)^### Context\n+.*?(?=^### )')
        strip_plan = re.compile(r'(?ms)^## Context\n+.*?(?=^## )')
        # A pending task without Context fails, quoting the spec sentence.
        self.readme = strip_task.sub('', original, count=1)
        self.assertIn('start from this section alone', self.verify(False))
        # A completed task is never retroactively failed — its record stays as
        # authored (DWP_SPECIFICATION §6.5 evidence history).
        self.readme = strip_task.sub('', original, count=1)
        self.complete()
        self.verify()
        # The plan-level v2 pair: a README without a Context section fails.
        self.readme = strip_plan.sub('', original)
        self.assertIn('Goal+Context', self.verify(False))

    def test_completed_security_evidence(self):
        self.complete()
        (self.plan/'analysis_results/SECURITY_REVIEW.md').unlink()
        self.assertIn('missing analysis_results/SECURITY_REVIEW.md', self.verify(False))
        (self.plan/'analysis_results/SECURITY_REVIEW.md').write_text('Open critical finding: authorization bypass remains unresolved.\n')
        self.assertIn('unresolved critical', self.verify(False))

    def test_failed_gate_and_later_repair(self):
        self.complete()
        gate = self.state['tasks'][0]['gates'][0]
        gate.update(passes=False, exit_code=1)
        self.assertIn('failing gate', self.verify(False))
        self.state['tasks'][0]['gates'].append(dict(gate, passes=True, exit_code=0))
        self.verify()

    def test_standard_series(self):
        # 2.x is historical (accepted with a marker), 4.x is current; 3.x
        # never existed as a standard and 5.x+ is newer than the checker.
        for spec, fragment, ok in [('4.0.0', 'plan standard: DWP spec 4.0.0', True),
                                   ('2.4.0', '(historical, accepted)', True),
                                   ('3.0.0', 'not a DWP standard', False),
                                   ('5.0.0', 'newer than this checker supports', False)]:
            self.manifest['spec_version'] = spec
            self.assertIn(fragment, self.verify(ok))
        self.manifest['spec_version'] = '2.4.0'

    def test_future_contracts(self):
        self.manifest['spec_version'] = '99.0.0'
        self.assertIn('newer than', self.verify(False))
        self.manifest['spec_version'] = '2.4.0'
        self.state['schema'] = 'https://deepworkplan.com/schema/plan-state/v99.json'
        self.assertIn('unknown state schema', self.verify(False))

    def test_empty_gate_wrong_summary_and_final_order(self):
        original = self.readme
        for bad in [original.replace('`true`',''), original.replace('0/2 completed','2/99 completed'), original.replace('Update fixture','TMP').replace('Final Review','Update fixture').replace('TMP','Final Review')]:
            self.readme = bad
            self.verify(False)

    def test_all_promotion_boundaries(self):
        self.promote()
        self.verify()
        for phase in ('intent','tasks_written','switched'):
            self.state['promotion'] = {'from':'lite','to':'full','phase':phase}
            self.state['materialization'] = 'promoting'
            self.assertIn('/dwp-refine promote', self.verify(False))
        self.state['promotion'] = None
        self.state['materialization'] = 'ready'
        self.verify()

    def test_shape_validator_matches_jsonschema(self):
        from jsonschema import Draft202012Validator
        schema = json.loads((PACK/'spec/schema/plan-state-v2.schema.json').read_text())
        reference = Draft202012Validator(schema)
        cases = [copy.deepcopy(self.state)]
        self.complete(); cases.append(copy.deepcopy(self.state))
        for key, value in [('checkpoint',{'task':'bad'}), ('blocked',{}), ('promotion',{'from':'full','to':'lite','phase':'wrong'}), ('completed_count',True), ('unknown',1)]:
            mutant = copy.deepcopy(self.state); mutant[key] = value; cases.append(mutant)
        for value in [['invalid'], [{}], [{'command':'true','passes':None,'last_run':'now'}]]:
            mutant = copy.deepcopy(self.state); mutant['tasks'][0]['gates'] = value; cases.append(mutant)
        for case in cases:
            self.assertEqual(bool(list(reference.iter_errors(case))), bool(CONTRACT.shape_errors(case, schema, schema)), case)


if __name__ == '__main__':
    unittest.main()
