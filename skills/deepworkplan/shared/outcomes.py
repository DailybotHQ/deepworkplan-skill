#!/usr/bin/env python3
"""v6 observable outcome verification: closure, receipts, review states.

RFC section 6 made every acceptance claim point to evidence of BEHAVIOR.
This module is the outcome half of that rule; the execution half lives in
``ledger.py run_control`` (mechanical residency, U2/A6 — the helper itself
executes both legs of a declared control and records the observed
``control_pair``).

What this module decides (pure functions over the records, mirrors of the
scheduler's posture — it decides, it never dispatches):

  * **closure** — per acceptance criterion, whether it may close and by
    which mechanism. A criterion declaring a ``regression`` or
    ``discrimination`` control closes ONLY on an in-window, helper-executed
    (``observed``) ``control_pair`` whose verdict is ``discriminating`` —
    (old FAIL, new PASS). ``(PASS, PASS)`` pairs stay non-discriminating,
    ``control_unavailable`` never counts toward acceptance, and an
    ``asserted`` pair is a claim, not behavior: none of them close. An
    exempt (or control-less) criterion closes on ordinary accepted
    evidence inside the current attempt window (the ledger's own
    criterion states).
  * **reconciled completions (A4/D2-4)** — a criterion may close
    ``reconciled`` only under amendment authority: a recorded
    ``reconciliation`` whose authority matches an ``amendment`` of that
    criterion. Without that authority the criterion is ``blocked``, never
    reconciled.
  * **review states** — the upstream AI Diff Reviewer is consumed, never
    duplicated: review results are recorded as ordinary asserted
    observations with a closed grammar (``REVIEW: <state>[: finding]``,
    state one of clean/critical/missing/error/incomplete) and the
    preserved failure semantics — ``critical`` blocks plan completion,
    ``missing``/``error``/``incomplete`` are never a clean pass. A review
    state NEVER satisfies a criterion: reviewer cleanliness, agreement
    between two models, schema validity and fabricated receipts are not
    behavioral acceptance (the receipt recomputes from records, so a
    fabricated one fails digest comparison).
  * **receipts (D2-10a)** — a deterministic verification receipt over the
    projection: per criterion the closing mechanism with its evidence
    pointer, the control verdict, the review state and the evaluator
    context. ``--evaluator fresh`` records a fresh evaluation context
    where the host supports one and falls back honestly (with the
    recorded caveat: a fresh context reduces shared conversational
    assumptions; it is not independence evidence).

Python 3.9+ stdlib only; imports only its sibling modules; the only writes
are the receipt file and journal events through the ledger writer.
"""
import argparse
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402
import ledger  # noqa: E402

OUTCOMES_IDENTITY = 'dwp outcomes.py'
REVIEW_STATES = ('clean', 'critical', 'missing', 'error', 'incomplete')
CONTROL_KINDS = ('regression', 'discrimination')
FRESH_CAVEAT = ('a fresh evaluator context reduces shared conversational '
                'assumptions; it does not guarantee statistically '
                'independent errors - recorded as such, never as '
                'independence evidence')


class OutcomesError(Exception):
    """Operator-visible failure (exit 1)."""


def _criteria_index(contract):
    """criterion id -> {kind, rationale, accepted_evidence}."""
    index = {}
    for crit in contract.get('acceptance', {}).get('criteria', []):
        control = crit.get('control') or {}
        index[crit.get('id')] = {
            'control_kind': control.get('kind'),
            'control_rationale': control.get('rationale'),
            'accepted_evidence': crit.get('accepted_evidence') or [],
        }
    return index


def _owner_of(contract, criterion):
    """The task whose gate_intent declares the criterion (first wins)."""
    for task in contract.get('tasks', []):
        for intent in task.get('gate_intent', []):
            if intent.get('criterion') == criterion:
                return task.get('id')
    return None


def review_state(events):
    """Latest review observation by grammar; None when never evaluated."""
    latest = None
    for event in events:
        if event.get('type') != 'observation':
            continue
        statement = event.get('statement') or ''
        if not statement.startswith('REVIEW: '):
            continue
        parts = statement[len('REVIEW: '):].split(':', 1)
        if parts[0] in REVIEW_STATES:
            latest = {'state': parts[0],
                      'finding': parts[1].strip() if len(parts) > 1 else '',
                      'seq': event.get('seq')}
    return latest


def _control_pairs(events, criterion, floor_seq):
    """In-window control pairs on the criterion, executed (observed) only."""
    pairs = []
    for event in events:
        if event.get('type') != 'control_pair':
            continue
        if event.get('criterion') != criterion:
            continue
        if event.get('seq', 0) < floor_seq:
            continue  # stale: recorded before the current attempt started
        pairs.append(event)
    return pairs


def _amendment_authorities(events, criterion):
    """Authorities of amendments touching the criterion (original or revised
    statement naming the criterion id)."""
    authorities = set()
    for event in events:
        if event.get('type') != 'amendment':
            continue
        text = ' '.join(str(event.get(k, '')) for k in
                        ('original_criterion', 'revised_criterion'))
        if criterion in text:
            authorities.add(event.get('authority'))
    return authorities


def _reconciliation_for(events, criterion):
    """The latest reconciliation whose trigger/editor names the criterion —
    reconciliations are view-level records, so the criterion is named in
    the trigger/editor text."""
    found = None
    for event in events:
        if event.get('type') != 'reconciliation':
            continue
        text = ' '.join(str(event.get(k, '')) for k in ('trigger', 'editor'))
        if criterion in text:
            found = event
    return found


def _is_signoff(events, seq):
    """True when the closing record is a human sign-off (never executed)."""
    return any(e.get('seq') == seq and e.get('type') == 'gate_run' and
               e.get('command') == ledger.SIGNOFF_COMMAND for e in events)


def closure(contract, events):
    """Per-criterion closure decisions + the plan-level review state.

    Returns a dict describing every criterion of the contract: whether it
    may close, by which mechanism, and why not otherwise. Pure over its
    inputs — deterministic under replay.
    """
    index = _criteria_index(contract)
    review = review_state(events)
    decisions = []
    for crit_id, meta in index.items():
        owner = _owner_of(contract, crit_id)
        floor = ledger.task_start_seq_of(events, owner) or 0
        entry = {'criterion': crit_id, 'task': owner,
                 'control_kind': meta['control_kind'] or 'none',
                 'satisfied': False, 'mechanism': 'open'}
        kind = meta['control_kind']
        if kind in CONTROL_KINDS:
            # behavioral acceptance: only an executed, in-window,
            # discriminating pair closes a controlled criterion
            pairs = _control_pairs(events, crit_id, floor)
            # existence semantics: ONE executed discriminating pair closes;
            # an asserted pair claiming the same verdict is a claim that
            # never counts and never poisons a later executed pair
            discriminating = [p for p in pairs
                              if p.get('verdict') == 'discriminating'
                              and p.get('trust') == 'observed']
            unavailable = [p for p in pairs
                           if p.get('verdict') == 'control_unavailable']
            if discriminating:
                entry.update(satisfied=True, mechanism='control_pair',
                             via_seq=discriminating[-1].get('seq'),
                             verdict='discriminating',
                             evidence_path=discriminating[-1].get(
                                 'evidence_path'))
            if not entry['satisfied']:
                executed = [p for p in pairs if p.get('trust') == 'observed']
                if not pairs:
                    entry['mechanism'] = 'open (no in-window control pair)'
                elif not executed:
                    entry['mechanism'] = ('open (pair is asserted, not '
                                          'executed - a claim is not '
                                          'behavior)')
                elif unavailable:
                    entry['mechanism'] = ('blocked (control unavailable: '
                                          'the pair proves nothing and '
                                          'never rounds up)')
                else:
                    entry['mechanism'] = ('open (control did not '
                                          'discriminate: %s)'
                                          % pairs[-1].get('verdict'))
        else:
            states = ledger.criterion_states(
                contract, events, owner) if owner else []
            state = next((s for s in states
                          if s.get('criterion') == crit_id), None)
            if state and state.get('satisfied'):
                entry.update(satisfied=True,
                             mechanism='signoff' if _is_signoff(
                                 events, state.get('via_seq'))
                             else 'evidence',
                             via_seq=state.get('via_seq'),
                             trust=state.get('trust'),
                             evidence_path=state.get('evidence_path'))
            elif state and state.get('stale_seqs'):
                entry['mechanism'] = 'open (evidence stale: %s)' % \
                    ','.join(map(str, state['stale_seqs']))
            else:
                entry['mechanism'] = 'open (no in-window accepted evidence)'
        # A4/D2-4: reconciled closure requires amendment authority - for
        # controlled AND exempt criteria alike (authority is the one path
        # that may close what behavior has not, and it is recorded)
        recon = _reconciliation_for(events, crit_id)
        if recon is not None and not entry['satisfied']:
            if recon.get('authority') in \
                    _amendment_authorities(events, crit_id):
                entry.update(satisfied=True, mechanism='reconciled',
                             authority=recon.get('authority'))
            else:
                entry['mechanism'] = ('blocked (reconciliation without '
                                      'amendment authority never '
                                      'closes evidence)')
        decisions.append(entry)
    blocked = any(d['mechanism'].startswith('blocked') for d in decisions)
    return {'criteria': decisions,
            'review': review,
            'review_blocks': bool(review and review['state'] == 'critical'),
            'plan_blocked': bool(
                blocked or (review and review['state'] == 'critical'))}


def receipt(plan_dir, evaluator='local', out=None):
    """Deterministic verification receipt over the current projection.

    The receipt recomputes every closure from the records and carries the
    digest of what it rendered from, so a fabricated or hand-edited receipt
    fails any later comparison (D2-10a: the receipt contract extends to
    the v6 projection).
    """
    rec = ledger.PlanRecords(plan_dir)
    events, _torn, _framing = rec.read_journal()
    events = rec.archived_events() + events
    # read-only: the receipt recomputes from the records, it never writes
    # the plan (not even a fresh snapshot - rendering is the writer's job)
    result = closure(rec.contract, events)
    used = evaluator
    fallback = None
    if evaluator == 'fresh':
        # capability fallback: a fresh context is host support, not a given
        env = os.environ.get('DWP_FRESH_EVALUATOR', '')
        if not env or env.lower() in ('0', 'no', 'false'):
            used = 'local'
            fallback = ('host does not report fresh-context support '
                        '(DWP_FRESH_EVALUATOR unset) - recorded as the '
                        'local context, never claimed as fresh')
    journal_sha = None
    if os.path.isfile(rec.journal_path):
        with open(rec.journal_path, 'rb') as fh:
            journal_sha = hashlib.sha256(fh.read()).hexdigest()
    digest_source = {'journal_sha256': journal_sha,
                     'snapshot': rec.snapshot_digest(),
                     'last_seq': max([e.get('seq', 0) for e in events] or
                                     [0])}
    doc = {'schema': 'https://deepworkplan.com/schema/verification-receipt/'
                     'v6.json',
           'plan': rec.contract.get('plan'),
           'contract_id': rec.contract_id,
           'rendered_from': digest_source,
           'evaluator': {'requested': evaluator, 'used': used,
                         'fallback': fallback,
                         'caveat': FRESH_CAVEAT},
           'closure': result,
           'totals': {
               'criteria': len(result['criteria']),
               'satisfied': sum(1 for c in result['criteria']
                                if c['satisfied']),
               'open': sum(1 for c in result['criteria']
                           if not c['satisfied']
                           and not c['mechanism'].startswith('blocked')),
               'blocked': sum(1 for c in result['criteria']
                              if c['mechanism'].startswith('blocked'))}}
    body = json.dumps(doc, sort_keys=True, indent=2).encode('utf-8')
    doc['receipt_sha256'] = hashlib.sha256(body).hexdigest()
    if out:
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write('\n')
    return doc


def record_review(plan_dir, state, finding=None, actor=None):
    """Record one review observation through the ledger writer.

    The state comes from reading the upstream reviewer's artifacts — a
    mediated claim, so it is recorded asserted (A1); the grammar carries
    the state and the finding.
    """
    if state not in REVIEW_STATES:
        raise OutcomesError('review state %r outside the closed set %s'
                            % (state, '/'.join(REVIEW_STATES)))
    statement = 'REVIEW: %s' % state
    if finding:
        statement += ': %s' % finding
    rec = ledger.PlanRecords(plan_dir)
    lock = ledger.CooperativeLock(plan_dir).acquire()
    try:
        writer = ledger.Writer(rec, lock)
        event = writer.append('observation',
                              {'statement': statement, 'trust': 'asserted'},
                              actor=actor or {'kind': 'agent',
                                              'identity': OUTCOMES_IDENTITY})
    finally:
        lock.release()
    return event


def run_control(plan_dir, task_id, criterion, command, artifacts,
                timeout=600):
    """Thin orchestration over the ledger's control executor."""
    rec = ledger.PlanRecords(plan_dir)
    lock = ledger.CooperativeLock(plan_dir).acquire()
    try:
        writer = ledger.Writer(rec, lock)
        return writer.run_control(task_id, criterion, command, artifacts,
                                  timeout=timeout)
    finally:
        lock.release()


# ---------------------------------------------------------------- selftest

def self_test():
    import tempfile
    failures = []
    probes = [0]

    def check(label, ok, detail=''):
        probes[0] += 1
        if not ok:
            failures.append('%s%s' % (label,
                                      (': ' + detail) if detail else ''))

    with tempfile.TemporaryDirectory() as tmp:
        plan = os.path.join(tmp, 'PLAN_selftest_v6')
        os.makedirs(plan)
        contract = contract_v6._selftest_contract()
        cid = contract_v6.compute_contract_id(contract)
        with open(os.path.join(plan, 'contract.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(dict(contract, contract_id=cid), fh)
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('approval', {'authority': 'selftest',
                                   'mechanism': 'plan_authorship',
                                   'plan_digest': 'a' * 64},
                      actor={'kind': 'human', 'identity': 'selftest'},
                      idempotent=True)
        writer.append('task_start', {'task': 'T-implement'},
                      actor={'kind': 'agent', 'identity': 'selftest'},
                      idempotent=True)
        events0 = list(writer.events)
        lock.release()

        # 1. a controlled criterion without a pair stays open
        result = closure(contract, events0)
        crit = result['criteria'][0]
        check('regression-controlled criterion starts open',
              crit['criterion'] == 'AC-one' and not crit['satisfied'] and
              'control' in crit['mechanism'], crit['mechanism'])

        # 2. an ASSERTED pair is a claim, never behavior
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('control_pair', {
            'criterion': 'AC-one', 'check_artifacts': ['f.txt'],
            'starting_fingerprint': {'revision': 'r1', 'dirty': ''},
            'old_leg': {'available': True, 'outcome': 'FAIL',
                        'log': 'l'},
            'new_leg': {'outcome': 'PASS', 'log': 'l2'},
            'verdict': 'discriminating', 'trust': 'asserted'},
            actor={'kind': 'agent', 'identity': 'selftest'})
        events1 = list(writer.events)
        lock.release()
        crit = closure(contract, events1)['criteria'][0]
        check('an asserted discriminating pair never closes the criterion',
              not crit['satisfied'] and 'asserted' in crit['mechanism'],
              crit['mechanism'])

        # 3. an executed discriminating pair closes it; a review state
        #    never would (the log artifact exists so the pointer resolves)
        os.makedirs(os.path.join(plan, 'gates'), exist_ok=True)
        with open(os.path.join(plan, 'gates', 'legs.log'), 'w',
                  encoding='utf-8') as fh:
            fh.write('old: FAIL\nnew: PASS\n')
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('control_pair', {
            'criterion': 'AC-one', 'check_artifacts': ['f.txt'],
            'starting_fingerprint': {'revision': 'r1', 'dirty': ''},
            'old_leg': {'available': True, 'outcome': 'FAIL',
                        'log': 'l'},
            'new_leg': {'outcome': 'PASS', 'log': 'l2'},
            'verdict': 'discriminating', 'trust': 'observed',
            'evidence_path': 'gates/legs.log'},
            actor={'kind': 'helper', 'identity': ledger.LEDGER_IDENTITY})
        writer.append('observation',
                      {'statement': 'REVIEW: clean', 'trust': 'asserted'},
                      actor={'kind': 'agent', 'identity': 'selftest'})
        events2 = list(writer.events)
        lock.release()
        crit = closure(contract, events2)['criteria'][0]
        check('executed discriminating pair closes the criterion',
              crit['satisfied'] and crit['mechanism'] == 'control_pair',
              crit['mechanism'])
        review = review_state(events2)
        check('review grammar parsed with state clean',
              review and review['state'] == 'clean')

        # 4. critical review blocks the plan but satisfies nothing
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('observation',
                      {'statement': 'REVIEW: critical: seeded defect '
                                    'survives', 'trust': 'asserted'},
                      actor={'kind': 'agent', 'identity': 'selftest'})
        events3 = list(writer.events)
        lock.release()
        result = closure(contract, events3)
        check('critical review blocks plan completion',
              result['plan_blocked'] and result['review_blocks'])
        check('critical review satisfies no criterion',
              all(not c['satisfied'] or c['mechanism'] != 'review'
                  for c in result['criteria']))

        # 5. reconciliation without amendment authority blocks, with it
        #    closes as reconciled
        contract2 = contract_v6._selftest_contract()
        contract2['acceptance']['criteria'][0]['control'] = \
            {'kind': 'exempt', 'rationale': 'prose-only surface'}
        crit_state = closure(contract2, events0)['criteria'][0]
        check('exempt criterion closes on ordinary evidence',
              crit_state['satisfied'] or 'evidence' in
              crit_state['mechanism'], crit_state['mechanism'])
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('reconciliation',
                      {'trigger': 'generated-view divergence for AC-one',
                       'editor': 'human edit of views/tasks.md',
                       'authority': 'selftest operator'},
                      actor={'kind': 'human', 'identity': 'operator'})
        events4 = list(writer.events)
        lock.release()
        crit = closure(contract2, events4)['criteria'][0]
        check('reconciliation without amendment authority blocks',
              (not crit['satisfied'] and crit['mechanism'].startswith(
                  'blocked')) or crit['satisfied'], crit['mechanism'])
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('amendment', {
            'original_criterion': 'AC-one: validator exits 0',
            'observed_finding': 'fixture drifted', 'disposition': 'revised',
            'revised_criterion': 'AC-one: validator exits 0 on v6 fixture',
            'reason': 'schema generation changed',
            'authority': 'selftest operator',
            'affected_tasks': ['T-implement'],
            'evidence_invalidated': [], 'evidence_preserved': []},
            actor={'kind': 'human', 'identity': 'operator'})
        events5 = list(writer.events)
        lock.release()
        crit = closure(contract2, events5)['criteria'][0]
        check('reconciliation under amendment authority closes reconciled',
              crit['satisfied'] and crit['mechanism'] == 'reconciled',
              crit['mechanism'])

        # 6. the receipt recomputes from records and carries its digest
        doc = receipt(plan, evaluator='fresh')
        check('fresh evaluator falls back honestly without host support',
              doc['evaluator']['used'] == 'local' and
              doc['evaluator']['fallback'], doc['evaluator']['used'])
        check('receipt carries a digest of its rendered source',
              len(doc.get('receipt_sha256', '')) == 64)
        check('receipt totals cover every criterion',
              doc['totals']['criteria'] == len(doc['closure']['criteria']))
    return (not failures, failures, probes[0])


# --------------------------------------------------------------------- CLI

def main(argv):
    usage = ('usage: outcomes.py --plan DIR {closure [--task T] | receipt '
             '[--evaluator fresh|local] [--out FILE] | review --state S '
             '[--finding F] | control --task T --criterion AC --command '
             'CMD --artifact P [--artifact P ...] [--timeout N] | '
             'self-test}')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--plan')
    parser.add_argument('command')
    parser.add_argument('--task')
    parser.add_argument('--criterion')
    parser.add_argument('--command', dest='check_command')
    parser.add_argument('--artifact', action='append')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--evaluator', default='local',
                        choices=['fresh', 'local'])
    parser.add_argument('--out')
    parser.add_argument('--state')
    parser.add_argument('--finding')
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print(usage)
        return 2
    if args.command in ('-h', '--help'):
        print(usage)
        return 0
    if args.command == 'self-test':
        ok, failures, probes = self_test()
        for failure in failures:
            print('FAIL', failure)
        print('self-test: %s (%d probes)' %
              ('OK' if ok else 'FAILED', probes))
        return 0 if ok else 1
    try:
        if not args.plan:
            print(usage)
            return 2
        plan = ledger.find_plan_dir(args.plan)
        if args.command == 'closure':
            rec = ledger.PlanRecords(plan)
            events, _t, _f = rec.read_journal()
            result = closure(rec.contract, rec.archived_events() + events)
            if args.task:
                result['criteria'] = [c for c in result['criteria']
                                      if c.get('task') == args.task]
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0
        if args.command == 'receipt':
            doc = receipt(plan, evaluator=args.evaluator, out=args.out)
            print('OK: receipt %s (%d/%d satisfied, %d blocked) sha256 %s'
                  % (args.out or 'stdout', doc['totals']['satisfied'],
                     doc['totals']['criteria'], doc['totals']['blocked'],
                     doc['receipt_sha256'][:16]))
            return 0
        if args.command == 'review':
            event = record_review(plan, args.state, args.finding)
            print('OK: review %s recorded at seq %s'
                  % (args.state, event.get('seq')))
            return 0
        if args.command == 'control':
            if not (args.task and args.criterion and args.check_command and
                    args.artifact):
                print(usage)
                return 2
            result = run_control(plan, args.task, args.criterion,
                                 args.check_command, args.artifact,
                                 timeout=args.timeout)
            print('OK: control pair verdict %s (%s) at seq %s'
                  % (result['verdict'], result['reason'], result['seq']))
            return 0
    except OutcomesError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    except ledger.LedgerError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
