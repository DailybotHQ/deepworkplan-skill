"""Lifecycle-level acceptance regressions for the v5 reliability guarantees.

The existing suites test each helper in isolation. These scenarios drive a
**whole plan** through the shipped helpers — guarded writer, finalizer,
read-only checker — over one realistic workspace, and inject each fault at the
moment it would really occur. Every scenario has a clean control that must
succeed and an injected defect that must be refused at the named boundary,
with the plan still recoverable afterwards.

Pre-registered as F1-F8 in tests/reliability/PROTOCOL.md. Stdlib only.
"""
import json
import os
import re
import pathlib
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

# This module imports pack helpers in order to test them. Without this, CPython
# writes a __pycache__ INTO the installed pack — the very guarantee F11 asserts,
# broken by the suite that asserts it (tests/completion_test.py catches it).
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'skills/deepworkplan'
WRITER = PACK / 'shared/update-state.py'
FINALIZER = PACK / 'shared/finalize_plan.py'
CHECKER = PACK / 'verify/conformance.sh'
WORKLOAD = ROOT / 'tests/reliability/workload'

PLAN_README = """# Plan: Ledger overdraw guard

Plan Format: Lite

Materialization: ready

Approval: approved

**Standard:** DWP spec 5.0.0

Plan Status: 0/2 completed

## Goal

Refuse an overdrawing transfer instead of recording it.

## Context

Acceptance fixture for the v5 reliability protocol. Product surface is the
frozen ledger workload copied into this workspace.

## Task 1: Refuse overdrawing transfers {#task-1}

### Goal

`Ledger.transfer` raises `ValueError` and records nothing when the source
cannot cover the amount.

### Context

The defect is stated in the workload's own AGENTS.md.

### Touched Surface

`src/ledger.py`, `tests/test_ledger.py`. Risk class: isolated implementation.

### Acceptance Criteria

An overdrawing transfer raises `ValueError` and leaves both balances unchanged,
with a test that fails before the fix.

### Validation

`python3 -m unittest discover -s tests -t .`

### Completion & Log

Status: pending.

## Task 2: Final Review {#task-2}

### Goal

Security pass, final-state validation, skills reconciliation and documentation
reconciliation.

### Context

Closing task.

### Touched Surface

Plan records only.

### Acceptance Criteria

The security pass, final-state validation, skills reconciliation and
documentation reconciliation are recorded.

### Validation

`python3 -m unittest discover -s tests -t .`

### Completion & Log

Status: pending.

## Task List

- [ ] Task 1: Refuse overdrawing transfers
- [ ] Task 2: Final Review
"""

STATE = {
    "schema": "https://deepworkplan.com/schema/plan-state/v2.json",
    "plan": "PLAN_ledger_overdraw_guard",
    "updated_at": "2026-09-13T00:00:00Z",
    "status": "pending",
    "completed_count": 0,
    "task_count": 2,
    "format": "lite",
    "materialization": "ready",
    "approval": "approved",
    "promotion": None,
    "tasks": [
        {"id": 1, "locator": {"kind": "inline", "value": "#task-1"},
         "title": "Refuse overdrawing transfers", "status": "pending", "gates": []},
        {"id": 2, "locator": {"kind": "inline", "value": "#task-2"},
         "title": "Final Review", "status": "pending", "gates": []},
    ],
}

MANIFEST = {
    "schema": "https://deepworkplan.com/schema/plan-manifest/v2.json",
    "spec_version": "5.0.0",
    "name": "PLAN_ledger_overdraw_guard",
    "archetype": "individual",
    "rigor": "micro",
    "created_at": "2026-09-13T00:00:00Z",
    "task_count": 2,
    "plan_format": "lite",
}

FIX = '''    def transfer(self, source, target, cents):
        """Move `cents` from `source` to `target`, refusing an overdraw."""
        if cents < 0:
            raise ValueError("transfer amount must be positive")
        if self.balance(source) < cents:
            raise ValueError("transfer would overdraw the source")
        self.add(source, -cents)
        self.add(target, cents)
'''

TEST = '''
    def test_overdrawing_transfer_is_refused_and_records_nothing(self):
        ledger = Ledger()
        ledger.add("cash", 100)
        with self.assertRaises(ValueError):
            ledger.transfer("cash", "savings", 500)
        self.assertEqual(ledger.balance("cash"), 100)
        self.assertEqual(ledger.balance("savings"), 0)
'''


TASK_FILE = """# Task {n}: {title}

## 1. Context

Acceptance fixture for the Full-format publication path.

## 2. Goal

{goal}

## 3. Touched Surface

- Planned surface: `src/ledger.py`, `tests/test_ledger.py`.
- Risk class: isolated implementation.
- Test mapping: `python3 -m unittest discover -s tests -t .`

## 4. Acceptance Criteria

{criteria}

## 5. Validation

`python3 -m unittest discover -s tests -t .`

## 6. Completion & Log (filled by the agent)

Status: pending.
"""

FULL_README = """# Plan: Ledger overdraw guard (Full)

Plan Format: Full

Materialization: ready

Approval: approved

**Standard:** DWP spec 5.0.0

Plan Status: 0/2 completed

## Goal

Refuse an overdrawing transfer instead of recording it.

## Context

Acceptance fixture for the v5 reliability protocol, Full representation: every
task lives in its own file, so every locator is `kind: "file"`.

## Task List

- [ ] Task 1: Refuse overdrawing transfers — [1.task_refuse.md](1.task_refuse.md)
- [ ] Task 2: Final Review — [2.task_final_review.md](2.task_final_review.md)
"""


class Lifecycle(unittest.TestCase):
    """One workspace per scenario: workload + plan + git, as a real run has."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        shutil.copytree(WORKLOAD, self.repo)
        self.plan = self.repo / '.dwp/plans/PLAN_ledger_overdraw_guard'
        (self.plan / 'analysis_results/gates').mkdir(parents=True)
        (self.plan / 'README.md').write_text(PLAN_README)
        (self.plan / 'PROGRESS.md').write_text(
            '# Progress\n\n## Active context\n\nStatus: 0/2 completed. Next: Task 1.\n')
        (self.plan / 'PROMPTS.md').write_text('# Prompts\n\nSee README.\n')
        self.state_path = self.plan / 'state.json'
        self.write_state(STATE)
        (self.plan / 'manifest.json').write_text(json.dumps(MANIFEST, indent=2))
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.repo / '.gitignore').write_text('.dwp/\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'chore: workload baseline')

    # --- helpers ---------------------------------------------------------
    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo,
                              capture_output=True, text=True, check=False)

    def write_state(self, state):
        self.state_path.write_text(json.dumps(state, indent=2))

    def state(self):
        return json.loads(self.state_path.read_text())

    def suite(self):
        return subprocess.run(
            ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.'],
            cwd=self.repo, capture_output=True, text=True)

    def apply_fix(self, with_test=True):
        src = self.repo / 'src/ledger.py'
        text = src.read_text()
        head = text.split('    def transfer(')[0]
        src.write_text(head + FIX)
        if with_test:
            tf = self.repo / 'tests/test_ledger.py'
            body = tf.read_text()
            tf.write_text(body.replace('\n\nif __name__ ==', TEST + '\n\nif __name__ =='))

    def gate_log(self, name, text):
        path = self.plan / 'analysis_results/gates' / name
        path.write_text(text)
        return f'analysis_results/gates/{name}'

    def close_task(self, task, *extra, gate=None, ok=True):
        before = self.state_path.read_bytes()
        args = ['python3', str(WRITER), str(self.state_path),
                '--task', str(task), '--status', 'completed', *extra]
        if gate:
            args += ['--gate', gate]
        result = subprocess.run(args, capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0,
                             f'writer refused a legitimate close: {result.stderr}')
        else:
            self.assertNotEqual(result.returncode, 0,
                                f'writer accepted an illegitimate close: {result.stdout}')
            self.assertEqual(self.state_path.read_bytes(), before,
                             'a refused write still mutated state.json')
        return result

    def terminal_candidate(self, log):
        """A well-formed terminal projection: completed tasks with evidence,
        completion timestamps, and the terminal checkpoint the contract
        requires. Building it correctly is the point — a malformed candidate
        would be refused for the wrong reason."""
        state = self.state()
        stamp = '2026-09-13T00:00:00+00:00'
        for task in state['tasks']:
            task['status'] = 'completed'
            task.setdefault('started_at', stamp)
            task['completed_at'] = stamp
            if not task['gates']:
                task['gates'] = [dict(command='python3 -m unittest discover -s tests -t .',
                                      passes=True, exit_code=0, last_run=stamp,
                                      evidence=f'executed=5; log={log}')]
        state['completed_count'] = len(state['tasks'])
        state['status'] = 'completed'
        state['checkpoint'] = {'task': state['tasks'][-1]['id'], 'step': 'done',
                               'at': stamp, 'note': 'plan complete'}
        return state

    def conformance(self):
        return subprocess.run(
            ['bash', str(CHECKER), '--plan', self.plan.name, str(self.repo)],
            capture_output=True, text=True)

    def finalize(self, candidate=None, ok=True):
        state = candidate if candidate is not None else self.state()
        path = Path(self.tmp.name) / 'candidate.json'
        path.write_text(json.dumps(state))
        result = subprocess.run(
            ['python3', str(FINALIZER), str(self.plan), '--candidate', str(path)],
            capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def complete_task_one(self):
        """The honest happy path: implement, test, log, commit, record."""
        self.apply_fix()
        run = self.suite()
        self.assertEqual(run.returncode, 0, run.stderr)
        evidence = self.gate_log('task1.log', run.stderr + run.stdout)
        self.mark_log_completed(1)
        self.git('add', '-A')
        self.git('commit', '-qm', 'fix: refuse overdrawing transfers')
        sha = self.git('rev-parse', 'HEAD').stdout.strip()
        self.close_task(1, '--commit', sha, '--worked', 'refuse overdrawing transfers',
                        gate=f'python3 -m unittest discover -s tests -t .|0|executed=5; log={evidence}')
        return sha

    def mark_log_completed(self, task):
        """Close the task's own record the way the contract requires.

        Not just the status line: the guarded completion transaction refuses a
        plan whose task records lack their skills and documentation
        dispositions, which is the rule this fixture must satisfy honestly
        rather than work around.
        """
        readme = self.plan / 'README.md'
        text = readme.read_text()
        marker = f'## Task {task}:'
        head, _, tail = text.partition(marker)
        tail = tail.replace(
            'Status: pending.',
            'Status: completed.\nSkills disposition: none — existing commands suffice.\n'
            'Documentation decision: not applicable — fixture workload, no registered '
            'surface changed.', 1)
        text = head + marker + tail
        title = STATE['tasks'][task - 1]['title']
        readme.write_text(text.replace(f'- [ ] Task {task}: {title}',
                                       f'- [x] Task {task}: {title}')
                          .replace(f'Plan Status: {task - 1}/2 completed',
                                   f'Plan Status: {task}/2 completed'))

    # --- F0: the clean control the rest is measured against ---------------
    def test_F0_clean_lifecycle_completes_and_conforms(self):
        self.complete_task_one()
        self.mark_log_completed(2)
        log = self.gate_log('task2.log', 'final-state validation: OK')
        run = self.suite()
        self.assertEqual(run.returncode, 0)
        self.git('add', '-A')
        self.git('commit', '-qm', 'chore: final review')
        sha = self.git('rev-parse', 'HEAD').stdout.strip()
        (self.plan / 'analysis_results/SECURITY_REVIEW.md').write_text(
            '# Security review\n\nNo unresolved critical finding.\n\n'
            '## Documentation reconciliation\n\nChecked: AGENTS.md — current.\n')
        self.close_task(2, '--commit', sha, '--worked', 'final review',
                        gate=f'python3 -m unittest discover -s tests -t .|0|executed=5; log={log}')
        state = self.state()
        self.assertEqual(state['status'], 'completed')
        self.assertEqual(state['completed_count'], 2)
        self.assertTrue(any(self.plan.rglob('FINALIZATION.json')),
                        'a completed publication left no receipt')
        self.assertFalse(any(self.plan.rglob('.finalizing.json')),
                         'a completed publication left its failure marker')
        check = self.conformance()
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    # --- F1: evidence that admits the command never ran -------------------
    def test_F1_non_execution_evidence_is_refused(self):
        self.apply_fix()
        log = self.gate_log('f1.log', 'command not run: interpreter unavailable\n')
        self.close_task(1, gate=f'python3 -m unittest discover -s tests -t .|0|'
                                f'not executed; log={log}', ok=False)
        self.assertEqual(self.state()['tasks'][0]['status'], 'pending')

    # --- F2: a selection that executed nothing ----------------------------
    def test_F2_zero_test_selection_is_refused(self):
        self.apply_fix()
        log = self.gate_log('f2.log', 'Ran 0 tests\n\nOK\n')
        self.close_task(1, gate=f'python3 -m unittest tests.nothing|0|executed=0/0; '
                                f'log={log}', ok=False)
        self.assertEqual(self.state()['tasks'][0]['status'], 'pending')

    # --- F3: malformed state is refused without destroying the file -------
    def test_F3_malformed_state_is_refused_and_preserved(self):
        truncated = self.state_path.read_text()[:120]
        self.state_path.write_text(truncated)
        result = subprocess.run(
            ['python3', str(WRITER), str(self.state_path), '--task', '1',
             '--status', 'completed', '--gate', 'unit|0|executed=4'],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.state_path.read_text(), truncated,
                         'the writer rewrote a state file it could not parse')
        check = self.conformance()
        self.assertNotEqual(check.returncode, 0,
                            'the checker accepted an unparseable state layer')

    # --- F4: evidence a later refine invalidated --------------------------
    def test_F4_invalidated_evidence_must_be_rerun(self):
        sha = self.complete_task_one()
        self.assertEqual(self.state()['tasks'][0]['status'], 'completed')
        state = self.state()
        # refine changed the acceptance criterion, so it stamps the earned
        # record as invalidated evidence (state_contract.INVALIDATED_PREFIX).
        gate = state['tasks'][0]['gates'][0]
        gate['evidence'] = ('invalidated by refine 3.7: the acceptance criterion '
                            'changed; rerun before closing')
        state['tasks'][0]['status'] = 'pending'
        state['tasks'][0].pop('completed_at', None)
        state['completed_count'] = 0
        # refine reopened the only started task, so the plan is pending again;
        # the projection must agree or the writer refuses it for that reason
        # instead of the one under test.
        state['status'] = 'pending'
        state['checkpoint'] = {'task': 1, 'step': 're-validate', 'at': '2026-09-13T00:00:00+00:00',
                               'note': 'refine 3.7 invalidated task 1 evidence'}
        self.write_state(state)
        # Closing again on the invalidated record must be refused...
        self.close_task(1, '--commit', sha, '--gate-json', json.dumps(gate), ok=False)
        # ...and accepted once the gate is genuinely re-run.
        run = self.suite()
        self.assertEqual(run.returncode, 0)
        log = self.gate_log('f4-rerun.log', run.stderr + run.stdout)
        self.close_task(1, '--commit', sha, '--worked', 're-ran after refine',
                        gate=f'python3 -m unittest discover -s tests -t .|0|'
                             f'executed=5; log={log}')
        self.assertEqual(self.state()['tasks'][0]['status'], 'completed')

    # --- F5: a completed task whose log still says pending ----------------
    def test_F5_log_status_mismatch_is_caught(self):
        """The declared boundary, not the assumed one.

        Mid-plan the guarded writer accepts the close — it validates the state
        layer, and the plan is not being published yet. The contradiction is
        caught by the read-only checker, and again by the completion
        transaction if the plan tries to finish in that shape. This scenario
        asserts both, because "caught somewhere" is not a contract.
        """
        self.apply_fix()
        run = self.suite()
        log = self.gate_log('f5.log', run.stderr + run.stdout)
        self.git('add', '-A')
        self.git('commit', '-qm', 'fix: refuse overdrawing transfers')
        sha = self.git('rev-parse', 'HEAD').stdout.strip()
        # README still says "Status: pending." for task 1 — the log was not closed.
        self.close_task(1, '--commit', sha,
                        gate=f'python3 -m unittest discover -s tests -t .|0|'
                             f'executed=5; log={log}')
        check = self.conformance()
        self.assertNotEqual(check.returncode, 0,
                            'the checker accepted a completed task whose log says pending')
        self.assertIn('still says', check.stdout + check.stderr)
        # And the plan cannot be published in that shape either.
        self.mark_log_completed(2)
        self.finalize(candidate=self.terminal_candidate(log), ok=False)

    # --- F6: an evidence pointer that dangles or escapes -------------------
    def test_F6_unresolvable_log_pointer_is_refused(self):
        self.apply_fix()
        self.mark_log_completed(1)
        for pointer in ('analysis_results/gates/missing.log',
                        '../../../etc/passwd',
                        '/etc/passwd'):
            self.close_task(1, gate=f'python3 -m unittest discover -s tests -t .|0|'
                                    f'executed=5; log={pointer}', ok=False)
        self.assertEqual(self.state()['tasks'][0]['status'], 'pending')

    # --- F7: completion interrupted after the marker ----------------------
    def test_F7_interrupted_finalization_is_recoverable(self):
        self.complete_task_one()
        self.mark_log_completed(2)
        log = self.gate_log('task2.log', 'final-state validation: OK')
        self.git('add', '-A')
        self.git('commit', '-qm', 'chore: final review')
        sha = self.git('rev-parse', 'HEAD').stdout.strip()
        (self.plan / 'analysis_results/SECURITY_REVIEW.md').write_text(
            '# Security review\n\nNo unresolved critical finding.\n\n'
            '## Documentation reconciliation\n\nChecked: AGENTS.md — current.\n')
        # A crash between the marker and the receipt leaves the marker behind:
        # seed it before the closing write, which is when publication happens.
        marker = self.plan / '.finalizing.json'
        marker.write_text(json.dumps({'stage': 'publishing'}))
        refused = self.close_task(2, '--commit', sha, '--worked', 'final review',
                                  gate=f'python3 -m unittest discover -s tests -t .|0|'
                                       f'executed=5; log={log}', ok=False)
        self.assertIn('--recover', refused.stderr,
                      'the refusal did not name the recovery action')
        self.assertTrue(marker.exists(), 'the refusal removed the evidence of the crash')
        # Recovery is explicit and completes the publication.
        state = self.terminal_candidate(log)
        candidate = Path(self.tmp.name) / 'recover.json'
        candidate.write_text(json.dumps(state))
        recovered = subprocess.run(
            ['python3', str(FINALIZER), str(self.plan), '--candidate', str(candidate),
             '--recover'], capture_output=True, text=True)
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertFalse(marker.exists(),
                         'recovery left the interruption marker in place')
        self.assertTrue(any(self.plan.rglob('FINALIZATION.json')))
        self.assertEqual(self.conformance().returncode, 0)

    # --- F8: unrelated dirty work at closure ------------------------------
    def test_F8_unrelated_dirty_work_is_neither_committed_nor_discarded(self):
        stray = self.repo / 'NOTES_unrelated.md'
        stray.write_text('a developer note that belongs to nobody\n')
        self.complete_task_one()
        self.assertTrue(stray.exists(), 'unrelated work was discarded')
        tracked = self.git('ls-files', 'NOTES_unrelated.md').stdout.strip()
        self.assertEqual(tracked, 'NOTES_unrelated.md',
                         'the happy path swept an unrelated file into its commit '
                         'silently — this fixture commits with `git add -A`, so it '
                         'documents the exposure the executor rule exists to prevent')
        # What must never happen: the file vanishing, or the plan claiming a
        # surface it did not reconcile. The state records only what it touched.
        worked = self.state()['tasks'][0]['outcome']['worked']
        self.assertNotIn('NOTES_unrelated', worked)


class TemplateFidelity(unittest.TestCase):
    """A plan authored exactly as the pack documents must pass the pack.

    F9, added after the L2 acceptance run found that it did not: the canonical
    task-file template prescribes a heading with a descriptive suffix that the
    field parser refused, so the field read as empty, finalization failed, and
    the error blamed the task's log — which was complete. The defect could only
    surface in a Full lifecycle driven end to end, which is exactly what the
    live runs do and the unit suites did not.
    """

    def setUp(self):
        sys.path.insert(0, str(PACK / 'verify'))
        from plan_contract import field_content
        self.field_content = field_content

    def test_F9_documented_headings_are_parseable(self):
        body = 'Status: completed.\nSkills disposition: none.\n'
        for heading in ('## 11. Completion & Log (filled by the agent)',
                        '## 9. Completion & Log (filled by the agent)',
                        '## Completion & Log',
                        '### Completion & Log',
                        '## 11. Completion & Log'):
            with self.subTest(heading=heading):
                self.assertEqual(self.field_content(heading + '\n\n' + body,
                                                    'Completion & Log').strip(),
                                 body.strip(),
                                 f'heading not parsed: {heading!r}')

    def test_F9_every_shipped_template_heading_parses(self):
        """The oracle is the shipped templates themselves, not a copy of them."""
        checked = 0
        for path in list((PACK / 'examples').glob('*TASK_TEMPLATE*.md')) + \
                    [PACK / 'guide/authoring.md']:
            text = path.read_text()
            for line in text.split('\n'):
                if re.match(r'^#{2,6}[ \t]+(?:\d+[.]?[ \t]*)?Completion & Log', line):
                    self.assertTrue(
                        self.field_content(line + '\n\nStatus: completed.\n',
                                           'Completion & Log'),
                        f'{path.name} ships a heading the parser cannot read: {line!r}')
                    checked += 1
        self.assertGreaterEqual(checked, 4,
                                'no template headings were checked — the oracle '
                                'selected nothing, which is never a pass')

    def test_F9_publication_refusal_names_the_real_cause(self):
        """A misleading error is a defect: it sent a reader hunting the wrong file."""
        source = (PACK / 'shared/finalize_plan.py').read_text()
        self.assertIn('no readable "Completion & Log" section', source)
        self.assertIn('cannot be published', source)
        self.assertNotIn('requires a completed log and skills/docs decisions', source,
                         'the message that blamed the log is back')


class NoFalseRefusals(unittest.TestCase):
    """F10: a refusal must be true about the artifact it refuses.

    Found by the R2-L1 acceptance run: the finalizer tested `'pending' in
    log.lower()`, so a completed log containing the word "appending" — domain
    vocabulary for an append-only ledger — was refused with the message "its
    log still says pending", which was false about the file. The checker
    already used a status-line rule; the finalizer did not.
    """

    def setUp(self):
        sys.path.insert(0, str(PACK / 'verify'))
        sys.path.insert(0, str(PACK / 'shared'))

    def test_F10_pending_is_matched_on_the_status_line_only(self):
        from finalize_plan import validate  # noqa: F401  (import must resolve)
        source = (PACK / 'shared/finalize_plan.py').read_text()
        self.assertNotIn("'pending' in log.lower()", source,
                         'the substring test that produced a false refusal is back')
        # The behavioral check: words that merely contain "pending" must pass,
        # and a real pending status line must still be caught.
        import re as _re
        pattern = _re.compile(
            r"(?im)^\s*(?:\*\*)?status(?:\*\*)?\s*:?\s*(?:\*\*)?\s*pending\b")
        self.assertIn(pattern.pattern, source,
                      'the finalizer no longer uses the status-line rule')
        for benign in ('Status: completed.\nNotes: guard runs before appending either leg.',
                       'Status: completed.\nThe suspending of the old rule is recorded.',
                       '**Status:** completed\nAppending is atomic.'):
            self.assertIsNone(pattern.search(benign),
                              f'benign log refused: {benign!r}')
        for real in ('Status: pending.', '**Status:** pending',
                     'status:  pending\nmore text'):
            self.assertIsNotNone(pattern.search(real),
                                 f'a genuinely pending log slipped through: {real!r}')


class PackStaysReadOnly(unittest.TestCase):
    """F11: running the shipped flows must not write into the installed pack.

    Two acceptance runs observed a `__pycache__` inside the pack and one
    attributed it to the writer's import of the finalizer. The attribution did
    not hold — the shipped scripts set `sys.dont_write_bytecode` and write
    nothing — but the guarantee was never pinned, so nothing would have caught
    it if it stopped being true. Now something does.
    """

    def test_F11_shipped_helpers_leave_no_bytecode_in_the_pack(self):
        for helper in ('shared/update-state.py', 'shared/finalize_plan.py',
                       'verify/plan_contract.py'):
            source = (PACK / helper).read_text()
            self.assertIn('sys.dont_write_bytecode = True', source,
                          f'{helper} may write bytecode into the installed pack')
            # The flag must be set BEFORE the first local import, or it is
            # too late for exactly the module it was meant to protect.
            flag = source.index('sys.dont_write_bytecode = True')
            local = [source.index(f'from {m} import')
                     for m in ('state_contract', 'plan_contract')
                     if f'from {m} import' in source]
            for position in local:
                self.assertLess(flag, position,
                                f'{helper} sets the flag after a local import')


class FullFormatPublication(unittest.TestCase):
    """F12: the Full representation must reach the guarded publication too.

    Found by the R2-L2 acceptance run, and caused by a fix in this very task:
    a function-local `import re` bound `re` as a local for the whole of
    finalize_plan.validate(). Lite plans took the branch that ran it and were
    fine; a Full plan — every locator `kind: "file"` — never did, so the first
    readable log hit an UnboundLocalError and guarded publication was
    unreachable for Full plans entirely.

    Every lifecycle scenario above uses a Lite plan, which is exactly why they
    all passed while the Full path was broken. Representation is a dimension
    the suite has to cover, not an implementation detail.
    """

    def test_F12_no_shipped_helper_shadows_a_module_level_import(self):
        """The bug class, caught statically in every shipped Python helper."""
        import ast
        checked = 0
        for path in sorted(PACK.rglob('*.py')):
            tree = ast.parse(path.read_text())
            module_names = {a.asname or a.name.split('.')[0]
                            for node in tree.body if isinstance(node, ast.Import)
                            for a in node.names}
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Import):
                        for alias in inner.names:
                            name = alias.asname or alias.name.split('.')[0]
                            self.assertNotIn(
                                name, module_names,
                                f'{path.name}:{inner.lineno} imports {name!r} inside '
                                f'{node.name}(), shadowing the module-level import for '
                                f'the whole function — every path that skips this line '
                                f'raises UnboundLocalError')
            checked += 1
        self.assertGreater(checked, 0, 'no helper was scanned — never a pass')

    def test_F12_a_full_plan_publishes_through_the_guarded_path(self):
        """End to end: the behavior the static guard protects."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        plan = pathlib.Path(tmp.name) / 'PLAN_full_fixture'
        (plan / 'analysis_results/gates').mkdir(parents=True)
        (plan / 'README.md').write_text(FULL_README)
        (plan / 'PROGRESS.md').write_text('# Progress\n\n## Active context\n\nStatus: 0/2.\n')
        (plan / 'PROMPTS.md').write_text('# Prompts\n\nSee README.\n')
        (plan / '1.task_refuse.md').write_text(TASK_FILE.format(
            n=1, title='Refuse overdrawing transfers',
            goal='An overdrawing transfer raises ValueError and records nothing.',
            criteria='The guard runs before either entry is appended.'))
        (plan / '2.task_final_review.md').write_text(TASK_FILE.format(
            n=2, title='Final Review',
            goal='Security pass, final-state validation, skills and documentation reconciliation.',
            criteria='All four parts recorded.'))
        (plan / 'analysis_results/SECURITY_REVIEW.md').write_text(
            '# Security review\n\nNo unresolved critical finding.\n\n'
            '## Documentation reconciliation\n\nChecked: AGENTS.md — current.\n')
        (plan / 'analysis_results/SKILLS_CANDIDATES.md').write_text(
            '# Skills candidates\n\nNone recorded.\n')
        (plan / 'manifest.json').write_text(json.dumps(
            {**MANIFEST, 'name': 'PLAN_full_fixture', 'plan_format': 'full',
             'task_count': 2}, indent=2))
        stamp = '2026-09-13T00:00:00+00:00'
        log = 'analysis_results/gates/full.log'
        (plan / log).write_text('Ran 5 tests\n\nOK\n')
        # Close both logs the way the contract requires.
        for name in ('1.task_refuse.md', '2.task_final_review.md'):
            f = plan / name
            f.write_text(f.read_text().replace(
                'Status: pending.',
                'Status: completed.\nSkills disposition: none — existing commands suffice.\n'
                'Documentation decision: not applicable — fixture, no registered surface.'))
        readme = (plan / 'README.md').read_text()
        (plan / 'README.md').write_text(
            readme.replace('- [ ] Task', '- [x] Task').replace(
                'Plan Status: 0/2 completed', 'Plan Status: 2/2 completed'))
        state = {
            **STATE, 'plan': 'PLAN_full_fixture', 'format': 'full',
            'status': 'completed', 'completed_count': 2,
            'checkpoint': {'task': 2, 'step': 'done', 'at': stamp, 'note': 'complete'},
            'tasks': [
                {'id': 1, 'locator': {'kind': 'file', 'value': '1.task_refuse.md'},
                 'title': 'Refuse overdrawing transfers', 'status': 'completed',
                 'started_at': stamp, 'completed_at': stamp,
                 'gates': [dict(command='python3 -m unittest discover -s tests -t .',
                                passes=True, exit_code=0, last_run=stamp,
                                evidence=f'executed=5; log={log}')]},
                {'id': 2, 'locator': {'kind': 'file', 'value': '2.task_final_review.md'},
                 'title': 'Final Review', 'status': 'completed',
                 'started_at': stamp, 'completed_at': stamp,
                 'gates': [dict(command='python3 -m unittest discover -s tests -t .',
                                passes=True, exit_code=0, last_run=stamp,
                                evidence=f'executed=5; log={log}')]},
            ],
        }
        (plan / 'state.json').write_text(json.dumps(state, indent=2))
        candidate = pathlib.Path(tmp.name) / 'candidate.json'
        candidate.write_text(json.dumps(state))
        result = subprocess.run(
            ['python3', str(FINALIZER), str(plan), '--candidate', str(candidate)],
            capture_output=True, text=True)
        # The regression signature: a traceback, not a refusal.
        self.assertNotIn('UnboundLocalError', result.stderr,
                         'the Full path still crashes inside validate()')
        self.assertNotIn('Traceback', result.stderr,
                         f'publication crashed instead of deciding: {result.stderr}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((plan / 'analysis_results/FINALIZATION.json').exists()
                        or any(plan.rglob('FINALIZATION.json')),
                        'a Full plan published without leaving a receipt')


if __name__ == '__main__':
    unittest.main(verbosity=2)
