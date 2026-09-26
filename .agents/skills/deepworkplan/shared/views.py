#!/usr/bin/env python3
"""v6 deterministic generated views and the human-edit rule (RFC 4.4).

Generated views are explicit projections of journal + snapshot, written to
``views/<NAME>.md`` files that carry an identity header (view name,
contract_id, source snapshot digest and the snapshot's own updated_at).
Every header value derives from the rendered snapshot — never the wall
clock and never the render's own bookkeeping — so re-rendering unchanged
records is a byte-identical no-op by construction: a render appends its
``view_render`` provenance event ONLY when it actually wrote something.

The human-edit rule: a view file that differs from what render would
produce (its marker proves it was machine-rendered, so a difference means
a human edit) is NEVER silently overwritten. Render reports the divergence
and exits nonzero until the operator picks a reconciliation mode:

  * ``--reconcile human-wins``  — the human edit stays as the view; the
    generated output is written beside it as ``<name>.generated.md``;
  * ``--reconcile generated-wins`` — the generated view is written; the
    human edit is preserved as ``<name>.human.md``.

Both record a ``reconciliation`` event carrying the trigger, the editor
whose change won and the operator-supplied authority (D2-4: authority is
recorded content, not a mechanism label). Direct edits to README.md and
PROGRESS.md remain markdown-wins as in v5; under the journal a
reconciliation regenerates the snapshot and appends the event — the
journal never discards history.

Audit posture (U3/B1, D12): the audit view lists every refusal and
intervention with reasons and proposal pointers — labeled records of
recorded proposals, never aggregated into indices or ratings. A completion
profile (B4) shows, per criterion, the closing mechanism — the evidence
item with its trust label and pointer — or that it is open.

Python 3.9+ stdlib only; imports only its sibling modules.
"""
import argparse
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402
import ledger  # noqa: E402

VIEWS = ('tasks', 'evidence', 'audit', 'completion')
MARKER = '<!-- dwp-view: %s | contract:%s | snapshot:%s | rendered-at:%s -->'


class ViewsError(Exception):
    """Operator-visible failure (exit 1)."""


class DivergenceError(ViewsError):
    """A human-edited generated view refuses silent overwrite (exit 5)."""


# The snapshot is stale when the journal holds STATE events beyond it
# (render provenance never counts — see ledger.PROVENANCE_TYPES).
STATE_TYPES = frozenset(contract_v6.JOURNAL_EVENT_TYPES) - \
    frozenset(ledger.PROVENANCE_TYPES)


def _snapshot(rec, writer):
    """Load state.json, re-projecting when state events outgrew it.

    A snapshot is reused as long as no state-bearing event has landed since
    it was projected (provenance events do not count), so consecutive
    renders of unchanged records share one snapshot and one digest.
    """
    if os.path.isfile(rec.state_path):
        with open(rec.state_path, encoding='utf-8') as fh:
            state = json.load(fh)
        projected = max([p.get('seq', 0) for p in
                         (state.get('positions') or {}).values()] or [0])
        live = max([e.get('seq', 0) for e in writer.events
                    if e.get('type') in STATE_TYPES] or [0])
        if live <= projected:
            return state
    return writer.project()


def render_view(name, events, snapshot, contract, digest):
    """Deterministic Markdown for one view (pure function of its inputs)."""
    lines = []
    if name == 'tasks':
        lines += ['# Task table', '',
                  '| Task | Title | Status | Started at |',
                  '|---|---|---|---|']
        for task in snapshot.get('tasks', []):
            lines.append('| %s | %s | %s | %s |' % (
                task['id'], _md(task.get('title')),
                task.get('status'), task.get('started_seq') or '—'))
        lines += ['', '_Pure projection of the snapshot; statuses are '
                  'derived, never narrated._']
    elif name == 'evidence':
        lines += ['# Evidence index', '',
                  '| Seq | Type | Trust | Subject | Exit | Pointer |',
                  '|---|---|---|---|---|---|']
        for event in events:
            if event.get('type') not in contract_v6.EVIDENCE_TYPES:
                continue
            subject = event.get('criterion') or event.get('limit_id') or ''
            lines.append('| %s | %s | %s | %s | %s | %s |' % (
                event.get('seq'), event.get('type'), event.get('trust', '—'),
                subject, event.get('exit_code', '—'),
                event.get('evidence_path', '—')))
        if len(lines) == 4:
            lines += ['| — | — | — | — | — | — |']
        lines += ['', '_Every evidence item with its trust label; a '
                  'checksum proves byte identity, not the truth of a '
                  'claim._']
    elif name == 'audit':
        lines += ['# Refusals and interventions', '']
        refusals = [e for e in events if e.get('type') == 'refusal']
        interventions = [e for e in events
                         if e.get('type') == 'intervention']
        lines += ['## Refusals (%d)' % len(refusals), '']
        for event in refusals:
            lines += ['- seq %s — %s at %s: %s' % (
                event.get('seq'), event.get('subject'),
                event.get('stage'), event.get('reason'))]
        if not refusals:
            lines += ['_No refusals recorded — this records that nothing '
                      'was proposed, not that nothing would have been '
                      'refused._']
        lines += ['', '## Interventions (%d)' % len(interventions), '']
        for event in interventions:
            lines += ['- seq %s — %s: %s — question: %s' % (
                event.get('seq'), event.get('category'),
                event.get('description'), event.get('question'))]
        if not interventions:
            lines += ['_No interventions recorded._']
    elif name == 'completion':
        lines += ['# Completion profile', '',
                  '| Task | Criterion | Satisfied | Mechanism | Pointer |',
                  '|---|---|---|---|---|']
        for task in snapshot.get('tasks', []):
            for crit in task.get('criteria', []):
                if crit.get('satisfied'):
                    mech = 'evidence (seq %s, trust %s)' % (
                        crit.get('via_seq'), crit.get('trust'))
                    pointer = crit.get('evidence_path') or '—'
                else:
                    mech = 'open'
                    pointer = '—'
                lines.append('| %s | %s | %s | %s | %s |' % (
                    task['id'], crit.get('criterion'),
                    'yes' if crit.get('satisfied') else 'no', mech, pointer))
        lines += ['', '_Per criterion: the closing mechanism — the '
                  'evidence item with its trust label — never a bare '
                  'claim (A4). Reconciled-authority closures are v6.0 '
                  'amendments until lifecycle wiring renders them '
                  'here._']
    else:
        raise ViewsError('unknown view %r' % name)
    return '\n'.join(lines) + '\n'


def render(plan_dir, names, out_dir=None, reconcile=None, authority=None,
           force=False):
    """Render views; enforce the human-edit rule; record view_render."""
    rec = ledger.PlanRecords(plan_dir)
    lock = ledger.CooperativeLock(plan_dir).acquire(force=force)
    try:
        writer = ledger.Writer(rec, lock)
        snapshot = _snapshot(rec, writer)
        digest = rec.snapshot_digest()
        if not digest:
            raise ViewsError('projection produced no snapshot to anchor a '
                             'view marker to')
        ts = snapshot.get('updated_at') or ''
        out_dir = out_dir or os.path.join(plan_dir, 'views')
        os.makedirs(out_dir, exist_ok=True)
        written = []
        digests = {}
        for name in names:
            body = render_view(name, writer.events, snapshot,
                               rec.contract, digest)
            header = MARKER % (name, rec.contract_id[:16], digest[:16], ts)
            content = header + '\n\n' + body
            digests[name] = hashlib.sha256(
                content.encode('utf-8')).hexdigest()
            target = os.path.join(out_dir, name + '.md')
            existing = None
            if os.path.isfile(target):
                with open(target, encoding='utf-8') as fh:
                    existing = fh.read()
                if existing == content:
                    continue  # unchanged records: an idempotent no-op
            if existing is not None and (
                    existing.startswith('<!-- dwp-view:') or
                    not _machine_written(writer.events, name, existing)):
                # N3: a file that differs from render output is treated
                # as human-edited whether or not its marker survived —
                # marker-less edits are divergence, never silent
                # overwrites. _machine_written consults the per-view
                # digests the last render recorded.
                if reconcile is None:
                    raise DivergenceError(
                        '%s was human-edited after its last render; '
                        'refusing to overwrite silently — pass '
                        '--reconcile human-wins or generated-wins '
                        '(with --authority)' % target)
                if authority is None:
                    raise ViewsError('reconciliation requires --authority '
                                     '(recorded content, D2-4)')
                if reconcile == 'human-wins':
                    with open(target[:-3] + '.generated.md', 'w',
                              encoding='utf-8') as fh:
                        fh.write(content)
                    outcome = 'human edit kept; generated output beside it'
                    written.append('%s (reconciled: %s)' %
                                   (name, reconcile))
                else:
                    with open(target[:-3] + '.human.md', 'w',
                              encoding='utf-8') as fh:
                        fh.write(existing)
                    with open(target, 'w', encoding='utf-8') as fh:
                        fh.write(content)
                    outcome = 'generated view written; human edit preserved'
                    written.append('%s (reconciled: %s)' %
                                   (name, reconcile))
                _record_reconciliation(writer, name, authority, outcome)
                continue
            with open(target, 'w', encoding='utf-8') as fh:
                fh.write(content)
            written.append(name)
        if written:
            # provenance is recorded ONLY for a render that wrote — a
            # re-render of unchanged records appends nothing (and never
            # feeds back into the snapshot; see ledger.PROVENANCE_TYPES)
            writer.append('view_render',
                          {'view': '+'.join(w.split(' ')[0] for w in written),
                           'snapshot_digest': digest,
                           'digests': {n: digests[n] for n in
                                       [w.split(' ')[0] for w in written]}},
                          actor={'kind': 'helper',
                                 'identity': ledger.LEDGER_IDENTITY})
        return written
    finally:
        lock.release()


def _machine_written(events, name, existing):
    """N3: prove a marker-less view file is machine output.

    The last view_render event records a per-view digest of exactly what
    render wrote. A file whose bytes match that digest is machine
    output; anything else (or no recorded digest at all) is treated as
    a human edit.
    """
    recorded = None
    for event in events:
        if event.get('type') == 'view_render' and \
                isinstance(event.get('digests'), dict):
            if name in event['digests']:
                recorded = event['digests'][name]
    if recorded is None:
        return False
    return hashlib.sha256(existing.encode('utf-8')).hexdigest() == recorded


def _record_reconciliation(writer, name, authority, outcome):
    """Record reconciliation once per unchanged state (idempotent)."""
    for event in reversed(writer.events):
        if event.get('type') != 'reconciliation':
            continue
        if event.get('editor') == 'human edit of views/%s.md' % name and \
                event.get('authority') == authority and \
                event.get('note') == outcome:
            return  # already recorded for this exact state
        break
    writer.append('reconciliation',
                  {'trigger': 'generated-view divergence',
                   'editor': 'human edit of views/%s.md' % name,
                   'authority': authority},
                  actor={'kind': 'human', 'identity': authority},
                  note=outcome)


def _md(text):
    return str(text or '').replace('|', '\\|').replace('\n', ' ')


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
        # observed evidence comes from the executor, never an append
        writer.run_gate('T-implement', 'true', criterion='AC-one')
        writer.project()
        lock.release()
        # 1. render is deterministic across two runs
        r1 = render(plan, ['tasks', 'audit'])
        with open(os.path.join(plan, 'views', 'tasks.md'),
                  encoding='utf-8') as fh:
            body1 = fh.read()
        r2 = render(plan, ['tasks', 'audit'])
        with open(os.path.join(plan, 'views', 'tasks.md'),
                  encoding='utf-8') as fh:
            body2 = fh.read()
        check('re-render of unchanged records is byte-identical',
              body1 == body2)
        check('re-render of unchanged records writes nothing (idempotent)',
              r2 == [], 'second render returned %r' % (r2,))
        rec0 = ledger.PlanRecords(plan)
        renders0 = [e for e in rec0.read_journal()[0]
                    if e.get('type') == 'view_render']
        check('one provenance event for the batch that wrote',
              len(renders0) == 1)
        # 2. human edit refuses silent overwrite
        target = os.path.join(plan, 'views', 'tasks.md')
        with open(target, 'a', encoding='utf-8') as fh:
            fh.write('\nHUMAN NOTE\n')
        try:
            render(plan, ['tasks'])
            check('human edit must refuse overwrite', False)
        except DivergenceError:
            check('human edit refuses overwrite', True)
        # 3. reconciliation modes preserve both copies + record the event
        render(plan, ['tasks'], reconcile='generated-wins',
               authority='selftest operator')
        check('human copy preserved',
              os.path.isfile(target[:-3] + '.human.md'))
        rec = ledger.PlanRecords(plan)
        events, _torn, _framing = rec.read_journal()
        reconciliations = [e for e in events
                           if e.get('type') == 'reconciliation']
        check('reconciliation recorded with authority',
              len(reconciliations) == 1 and
              reconciliations[0].get('authority') == 'selftest operator')
        # 4. a view rendered before new state events is stale: refresh
        #    refuses until reconciled (nothing silently overwrites a
        #    marker-carrying file), then reconciles with recorded authority
        try:
            render(plan, ['audit'])
            check('stale render must refuse refresh', False)
        except DivergenceError:
            check('stale render refuses silent refresh', True)
        render(plan, ['audit'], reconcile='generated-wins',
               authority='selftest operator')
        with open(os.path.join(plan, 'views', 'audit.md'),
                  encoding='utf-8') as fh:
            audit = fh.read()
        check('audit states the empty-refusal meaning',
              'nothing was proposed' in audit)
    return (not failures, failures, probes[0])


# --------------------------------------------------------------------- CLI

def main(argv):
    usage = ('usage: views.py --plan DIR {render|self-test} '
             '[--view tasks,evidence,audit,completion|--all] [--out DIR] '
             '[--reconcile human-wins|generated-wins] [--authority WHO] '
             '[--force]')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--plan')
    parser.add_argument('command')
    parser.add_argument('--view')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--out')
    parser.add_argument('--reconcile',
                        choices=['human-wins', 'generated-wins'])
    parser.add_argument('--authority')
    parser.add_argument('--force', action='store_true')
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
    if args.command != 'render':
        print(usage)
        return 2
    if args.all:
        names = list(VIEWS)
    elif args.view:
        names = [n.strip() for n in args.view.split(',') if n.strip()]
    else:
        names = ['tasks', 'evidence', 'audit']
    for name in names:
        if name not in VIEWS:
            print('unknown view %r (choose from %s)' % (name, ', '.join(VIEWS)))
            return 2
    try:
        rendered = render(ledger.find_plan_dir(args.plan), names,
                          out_dir=args.out, reconcile=args.reconcile,
                          authority=args.authority, force=args.force)
        if rendered:
            print('OK: rendered %s' % ', '.join(rendered))
        else:
            print('OK: no view changed — records unchanged, nothing written')
        return 0
    except DivergenceError as exc:
        print('DIVERGENCE: %s' % exc, file=sys.stderr)
        return 5
    except ViewsError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    except ledger.LedgerError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
