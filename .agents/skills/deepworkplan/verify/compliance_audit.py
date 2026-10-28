#!/usr/bin/env python3
"""Compliance audit of finished v6/v7 plans; read-only, standard library only.

Conformance (`conformance.sh`) asks whether a plan is well-formed. This audit
asks whether the work followed the rules the pack already ships, so the next
roadmap does not re-propose mechanisms that exist but are unused (ADR 0006,
R17/R11). It reads a plan's own records - `contract.json`, `journal.ndjson`,
`state.json`, `analysis_results/` - and never writes, repairs or runs
anything.

Per plan it reports:
  * criteria closed on a declared evidence class, and criteria closed outside it;
  * whether a Final Review task completed;
  * declared controls and their latest control-pair verdicts, including
    dirty-start `control_unavailable` voids (D3-3);
  * `§5.1.4 control missing` observations the ledger recorded at completion;
  * whether the human request is kept verbatim (`analysis_results/HUMAN_NOTE.md`);
  * re-anchoring: reported as unmeasured, because execution leaves no record
    of it (the honest answer until a record exists).

Usage:
  compliance_audit.py PLAN_DIR [PLAN_DIR ...] [--json]
  compliance_audit.py --plans-dir DWP_PLANS_DIR [--json]

Exit 0 when the audit ran (findings are data, not failures); 2 on usage
errors, or when a plan was unreadable (reported as skipped; the other plans
are still audited).
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, 'shared'))
import ledger  # noqa: E402  (read-side helpers only: PlanRecords, snapshot)

RECORD_SCHEMAS = ('plan-manifest/v6.json', 'plan-manifest/v7.json')
_FINAL_REVIEW = re.compile(r'final[-_ ]?review', re.IGNORECASE)


def _read_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _has_human_note(plan_dir):
    """A verbatim request kept anywhere under analysis_results/."""
    root = os.path.join(plan_dir, 'analysis_results')
    for _dir, _subdirs, files in os.walk(root):
        if any(f.startswith(('HUMAN_NOTE', 'HUMAN_REQUEST')) and
               f.endswith('.md') for f in files):
            return True
    return False


def generation(plan_dir):
    """'v6' / 'v7' for a record-layer plan, else None (never judged here)."""
    manifest = os.path.join(plan_dir, 'manifest.json')
    if not os.path.isfile(manifest):
        return None
    try:
        schema = _read_json(manifest).get('schema', '')
    except (OSError, ValueError):
        return None
    for suffix in RECORD_SCHEMAS:
        if schema.endswith(suffix):
            return suffix.split('/')[-1][:2]
    return None


def audit_plan(plan_dir):
    """One plan's compliance record (a plain dict, JSON-serializable)."""
    plan_dir = os.path.abspath(plan_dir)
    name = os.path.basename(plan_dir.rstrip('/'))
    gen = generation(plan_dir)
    if gen is None:
        return {'plan': name, 'generation': None,
                'skipped': 'not a v6/v7 record-layer plan'}
    # The same read side the verifier uses: the live contract (highest
    # revision under contracts/) and a snapshot derived from the journal,
    # computed without the lock and without writing.
    records = ledger.PlanRecords(plan_dir)
    contract = records.contract
    events, _torn, _framing = records.read_journal()
    events = records.archived_events() + events
    snapshot = ledger.read_only_snapshot(records)
    statuses = {t.get('id'): t.get('status')
                for t in snapshot.get('tasks', [])}
    criteria = contract.get('acceptance', {}).get('criteria', [])
    owner = {}
    for task in contract.get('tasks', []):
        for intent in task.get('gate_intent', []):
            owner[intent.get('criterion')] = task.get('id')

    # "Closed" is decided exactly as the ledger decides it at completion
    # (ledger.criterion_states: in-window gate runs, amendment-invalidated
    # evidence excluded). A criterion with an in-window passing gate run
    # whose trust label the criterion does not accept is "outside".
    invalid_before = ledger.invalidated_before(events)
    accepted_by = {c.get('id'): set(c.get('accepted_evidence') or [])
                   for c in criteria}
    satisfied, outside = set(), set()
    for task in contract.get('tasks', []):
        tid = task.get('id')
        try:
            states = ledger.criterion_states(contract, events, tid)
        except ledger.LedgerError:
            continue
        start = ledger.task_start_seq_of(events, tid)
        for state in states:
            cid = state.get('criterion')
            if state.get('satisfied'):
                satisfied.add(cid)
                continue
            if start is None:
                continue
            for e in events:
                if e.get('type') == 'gate_run' and \
                        e.get('criterion') == cid and \
                        e.get('task') == tid and \
                        e.get('exit_code') == 0 and \
                        e.get('seq', 0) >= start and \
                        e.get('seq', 0) >= invalid_before.get(cid, 0) and \
                        e.get('trust') not in accepted_by.get(cid, set()):
                    outside.add(cid)
    closed_ok = [c.get('id') for c in criteria if c.get('id') in satisfied]
    closed_outside = [c.get('id') for c in criteria
                      if c.get('id') in outside and
                      c.get('id') not in satisfied]
    unclosed = [c.get('id') for c in criteria
                if c.get('id') not in satisfied and
                c.get('id') not in outside]

    # The Final Review is named, not flagged, in a contract: match the
    # task id or title ("T-final-review", "Final Review"), not any "final".
    final_tasks = [t.get('id') for t in contract.get('tasks', [])
                   if _FINAL_REVIEW.search('%s %s' % (t.get('id') or '',
                                                     t.get('title') or ''))]
    final_review = 'completed' if any(
        statuses.get(t) == 'completed' for t in final_tasks) else (
        'missing' if not final_tasks else 'not completed')

    controlled = [c.get('id') for c in criteria
                  if (c.get('control') or {}).get('kind') in
                  ('regression', 'discrimination')]
    verdicts = {}
    dirty_voids = 0
    for event in events:
        if event.get('type') != 'control_pair':
            continue
        verdicts[event.get('criterion')] = event.get('verdict')
        if event.get('verdict') == 'control_unavailable' and \
                (event.get('starting_fingerprint') or {}).get('dirty'):
            dirty_voids += 1
    undecided = [c.get('id') for c in criteria
                 if not c.get('control') and
                 'observed' in (c.get('accepted_evidence') or [])]
    missing_obs = sum(1 for e in events if e.get('type') == 'observation' and
                      'control missing' in (e.get('statement') or ''))

    return {
        'plan': name,
        'generation': gen,
        'tasks_completed': sum(1 for s in statuses.values() if s == 'completed'),
        'tasks_total': len(contract.get('tasks', [])),
        'criteria_closed_on_declared_class': closed_ok,
        'criteria_closed_outside_declared_class': closed_outside,
        'criteria_unclosed': unclosed,
        'final_review': final_review,
        'controls_declared': controlled,
        'control_verdicts': {c: verdicts.get(c, 'no pair recorded')
                             for c in controlled},
        'dirty_start_control_voids': dirty_voids,
        'criteria_without_control_decision': undecided,
        'section_5_1_4_observations': missing_obs,
        'verbatim_request': _has_human_note(plan_dir),
        're_anchoring': 'unmeasured: execution leaves no record of it',
    }


def _markdown(records):
    lines = ['| Plan | Gen | Tasks | Criteria on class | Outside class | '
             'Final Review | Controls (verdicts) | Dirty voids | '
             'No control decision | §5.1.4 obs. | Verbatim request |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in records:
        if r.get('skipped'):
            lines.append('| %s | — | skipped: %s |  |  |  |  |  |  |  |  |'
                         % (r['plan'], r['skipped']))
            continue
        controls = ', '.join('%s=%s' % kv for kv in
                             r['control_verdicts'].items()) or 'none'
        lines.append('| %s | %s | %d/%d | %d | %d | %s | %s | %d | %d | %d | %s |' % (
            r['plan'], r['generation'], r['tasks_completed'], r['tasks_total'],
            len(r['criteria_closed_on_declared_class']),
            len(r['criteria_closed_outside_declared_class']),
            r['final_review'], controls, r['dirty_start_control_voids'],
            len(r['criteria_without_control_decision']),
            r['section_5_1_4_observations'],
            'yes' if r['verbatim_request'] else 'no'))
    lines.append('')
    lines.append('Re-anchoring: unmeasured for every plan - execution leaves no '
                 'record of it.')
    return '\n'.join(lines)


def main(argv):
    as_json = '--json' in argv
    args = [a for a in argv if a != '--json']
    plans = []
    if args[:1] == ['--plans-dir']:
        if len(args) != 2 or not os.path.isdir(args[1]):
            print(__doc__)
            return 2
        root = args[1]
        plans = [os.path.join(root, d) for d in sorted(os.listdir(root))
                 if os.path.isdir(os.path.join(root, d))]
    else:
        plans = args
    if not plans or any(a in ('-h', '--help') for a in plans):
        print(__doc__)
        return 0 if plans else 2
    records = []
    unreadable = 0
    for plan in plans:
        if not os.path.isdir(plan):
            sys.stderr.write('not a plan directory: %s\n' % plan)
            return 2
        try:
            records.append(audit_plan(plan))
        except (OSError, ValueError, ledger.LedgerError) as exc:
            # one unreadable plan never hides the others' results
            sys.stderr.write('cannot read %s: %s\n' % (plan, exc))
            records.append({'plan': os.path.basename(plan.rstrip('/')),
                            'generation': None,
                            'skipped': 'unreadable: %s' % exc})
            unreadable += 1
    if as_json:
        print(json.dumps({'schema': 'dwp-compliance-audit/1',
                          'plans': records}, indent=1, ensure_ascii=False))
    else:
        print(_markdown(records))
    return 2 if unreadable else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
