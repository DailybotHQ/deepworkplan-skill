#!/usr/bin/env python3
"""v6 context selection: the per-task context manifest and freshness checks.

RFC section 7: a fresh session receives relevant CURRENT context derived
from the record, with bounded retrieval and measurable overhead. This
module derives that manifest deterministically from the plan's own
records (contract + journal + files under the repository) — it never
loads history upfront, never reads broad or cross-project memory, and
never invents advice: every line is a recorded fact or a pointer to one.

Q6 (the open question this task owns) is answered here and normatively in
``spec/V6_CONTEXT.md`` — which record fields produce which manifest
sections, and the dead-end digest's inclusion window:

  * ``identity``        — contract plan/contract_id/revision + the task id.
  * ``authorization``   — approval events citing the live contract_id
                          (authority, mechanism, ts) and the contract's
                          authorization block VERBATIM (consent
                          checkpoints are carried, never summarized).
  * ``repository_rules``— contract.scope verbatim (allowed_paths,
                          allowed_command_classes, forbidden_operations)
                          plus every declared invariant with its latest
                          recorded status. Mandatory: pruning can never
                          hide the acceptance or authorization boundary.
  * ``acceptance``     — this task's gate_intent criteria with their
                          closure decisions (outcomes.closure): satisfied
                          + mechanism, or the recorded open/blocked reason.
  * ``touched_surface`` — the task's declared surface with per-file
                          content hashes; a missing file or a surface with
                          no evidence mapping widens discovery
                          (``widen_discovery`` true) — a missing impact
                          mapping never justifies a narrow selection.
  * ``evidence``       — in-window, accepted, pointer-valid evidence only.
  * ``next_action``    — the deterministic ladder below.
  * ``dead_ends``      — the U4 digest: failed gates with causes, refused
                          or abandoned strategy changes, and executed
                          experiments whose controls did not discriminate.
                          Each entry is a recorded event with a pointer —
                          never advice, never probabilities. Inclusion
                          window: ALL plan history (archived + live);
                          entries age out only by PROVEN invalidation —
                          a failed gate whose run fingerprint no longer
                          matches the current inputs (the world moved),
                          a non-discriminating control from a superseded
                          contract revision, or an older duplicate refusal
                          of the same (subject, stage). Retention-biased:
                          when invalidation cannot be proven, the entry
                          stays — dropping a dead end risks retrying a
                          known-dead approach.
  * ``freshness``      — ``inputs_fingerprint`` over the contract_id and
                          the touched-surface file hashes; any summary or
                          cached manifest carrying a different fingerprint
                          is stale (``freshness`` command).
  * ``history_triggers`` — history loads ONLY on these declared triggers
                          (v5 read tiers); with no trigger, the manifest
                          alone is the context.

``next_action`` ladder (first match wins, all steps deterministic):
approval missing -> task_start missing -> blocked criteria (needs
authority) -> open controlled criteria (execute the declared control
pair) -> open evidence criteria (produce in-window accepted evidence) ->
all satisfied (complete the task). A task outside the contract is
refused, never guessed.

Cost accounting keeps four quantities distinct (section 7): static
instruction bytes, provider tokens, derived monetary cost and wall-clock
time. Each is reported from its own source; missing data is exposed as
missing, never imputed and never bytes-to-money.

Python 3.9+ stdlib only; imports only its sibling modules; the manifest
is a read-only derivation (no lock, no writes — rendering a manifest
never advances the plan).
"""
import argparse
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402  (sibling module, same directory)
import ledger  # noqa: E402
import outcomes  # noqa: E402
import scheduler  # noqa: E402

MANIFEST_IDENTITY = 'dwp context_manifest.py'
MANDATORY_SECTIONS = ('authorization', 'repository_rules', 'acceptance')
OPTIONAL_SECTIONS = ('history_triggers',)
DEAD_END_CAP = 50


class ContextError(Exception):
    """Operator-visible failure (exit 1)."""


# ---------------------------------------------------------------- inputs

def _hash_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def task_surface(plan_dir, contract, task_id):
    """Per-file content hashes for the task's declared touched surface.

    A directory entry expands to its contained files (sorted, stable); a
    missing entry hashes to None — surfaced, never silently dropped.
    """
    root = _repo_root(plan_dir)
    task = _task_of(contract, task_id)
    files = {}
    for rel in task.get('touched_surface', []):
        path = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if os.path.isdir(path):
            for base, _dirs, names in os.walk(path):
                for name in sorted(names):
                    sub = os.path.relpath(os.path.join(base, name), root)
                    files[sub] = _hash_file(os.path.join(base, name))
        else:
            files[rel] = _hash_file(path)
    return files


def _repo_root(plan_dir):
    up = os.path.dirname(os.path.abspath(plan_dir))
    up = os.path.dirname(up)
    if os.path.basename(up) == '.dwp':
        return os.path.dirname(up)
    return os.path.dirname(os.path.abspath(plan_dir))


def _task_of(contract, task_id):
    for task in contract.get('tasks', []):
        if task.get('id') == task_id:
            return task
    raise ContextError('task %r is not in the contract - the manifest '
                       'never guesses a task the plan did not declare'
                       % task_id)


def inputs_fingerprint(contract_id, files):
    """sha256 over the identity + the touched-surface content hashes."""
    body = {'contract_id': contract_id, 'files': files}
    return hashlib.sha256(json.dumps(body, sort_keys=True,
                                     separators=(',', ':'))
                          .encode('utf-8')).hexdigest()


# ------------------------------------------------------------- dead ends

def _evidence_fingerprints(plan_dir):
    """seq -> run fingerprint from the reuse cache (best effort, honest)."""
    path = os.path.join(plan_dir, 'evidence.jsonl')
    found = {}
    if not os.path.isfile(path):
        return found
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # corrupt sidecar line: skip, never crash reads
            if rec.get('seq'):
                found[rec['seq']] = rec.get('fingerprint')
    return found


def dead_ends(records):
    """The U4 digest: recorded dead approaches, aged out only by proof.

    Retention-biased (module docstring + spec/V6_CONTEXT.md): an entry
    leaves the digest ONLY on a proven record fact - the same run
    fingerprint later passed (the approach stopped failing), a newer
    duplicate refusal exists for the same (subject, stage), or a control
    belongs to a superseded contract revision. A mere surface change
    never silently drops a dead end; the next re-run records the fact.
    """
    events = records.archived_events() + records.read_journal()[0]
    run_fps = _evidence_fingerprints(records.dir)
    passing_fps = set()
    entries = []
    refusal_latest = {}
    for event in events:
        etype = event.get('type')
        seq = event.get('seq', 0)
        if etype == 'gate_run':
            fp = run_fps.get(seq)
            if event.get('exit_code') == 0:
                if fp:
                    passing_fps.add(fp)
                continue
            entries.append({
                'kind': 'failed_gate', 'seq': seq, 'ts': event.get('ts'),
                'task': event.get('task'),
                'criterion': event.get('criterion'),
                'command': event.get('command'),
                'exit_code': event.get('exit_code'),
                'cause': event.get('evidence_path'),
                'run_fingerprint': fp})
        elif etype == 'refusal':
            key = (event.get('subject'), event.get('stage'))
            refusal_latest[key] = {
                'kind': 'refusal', 'seq': seq, 'ts': event.get('ts'),
                'subject': event.get('subject'),
                'stage': event.get('stage'),
                'reason': event.get('reason'),
                'cause': 'journal seq %s' % seq}
        elif etype == 'adaptation' and event.get('decision') == 'refused':
            entries.append({
                'kind': 'refused_adaptation', 'seq': seq,
                'ts': event.get('ts'),
                'subject': '%s adaptation' % event.get('kind'),
                'reason': event.get('reason'),
                'cause': 'journal seq %s' % seq})
        elif etype == 'control_pair' and \
                event.get('verdict') == 'non_discriminating':
            entries.append({
                'kind': 'non_discriminating_control', 'seq': seq,
                'ts': event.get('ts'),
                'criterion': event.get('criterion'),
                'verdict': event.get('verdict'),
                'cause': event.get('evidence_path'),
                'recorded_contract_id': event.get('contract_id')})
    kept = []
    for entry in entries:
        if entry['kind'] == 'failed_gate' and \
                entry.get('run_fingerprint') in passing_fps:
            continue  # the same inputs later passed: not a dead end
        if entry['kind'] == 'non_discriminating_control' and \
                entry.get('recorded_contract_id') != records.contract_id:
            entry['aged_out'] = 'superseded contract revision'
        kept.append(entry)
    kept.extend(refusal_latest.values())
    kept.sort(key=lambda e: e.get('seq', 0))
    return kept[-DEAD_END_CAP:]


# ---------------------------------------------------------------- manifest

def _approvals_of(events, contract_id):
    """Approval events citing the live contract (the running authority)."""
    found = []
    for event in events:
        if event.get('type') == 'approval' and \
                event.get('contract_id') == contract_id:
            found.append({'authority': event.get('authority'),
                          'mechanism': event.get('mechanism'),
                          'ts': event.get('ts'),
                          'seq': event.get('seq')})
    return found


def _valid_evidence(records, events, task_id, states):
    """In-window accepted evidence whose pointer resolves on disk."""
    root = _repo_root(records.dir)
    out = []
    for state in states:
        if not state.get('satisfied'):
            continue
        pointer = state.get('evidence_path')
        candidates = [os.path.join(records.dir, pointer)]
        if not os.path.isabs(pointer):
            candidates.append(os.path.join(root, pointer))
        exists = any(os.path.isfile(c) for c in candidates)
        out.append({'criterion': state.get('criterion'),
                    'seq': state.get('via_seq'),
                    'trust': state.get('trust'),
                    'evidence_path': pointer,
                    'pointer_resolves': exists})
    return out


def _next_action(records, events, task_id, mine):
    """The deterministic ladder - first match wins (module docstring)."""
    if not _approvals_of(events, records.contract_id):
        return {'step': 'approval',
                'action': 'record the materialization-time approval citing '
                          'contract_id %s - task_start is refused without it'
                          % records.contract_id[:12]}
    if ledger.task_start_seq_of(events, task_id) is None:
        return {'step': 'start',
                'action': 'ledger.py --plan <dir> start --task %s - '
                          'captures the starting fingerprint a control '
                          'pair materializes' % task_id}
    blocked = [c for c in mine if c['mechanism'].startswith('blocked')]
    if blocked:
        return {'step': 'authority',
                'action': 'blocked criteria need an authority act '
                          '(amendment) or a changed world, not more '
                          'evidence: %s' % '; '.join(
                              '%s (%s)' % (c['criterion'],
                                           c['mechanism']) for c in blocked)}
    controlled = [c for c in mine if not c['satisfied'] and
                  c.get('control_kind') in outcomes.CONTROL_KINDS]
    if controlled:
        return {'step': 'control',
                'action': 'execute the declared control pair: outcomes.py '
                          '--plan <dir> control --task %s --criterion %s '
                          '--command <cmd> --artifact <path>' %
                          (task_id, controlled[0]['criterion']),
                'criteria': [c['criterion'] for c in controlled]}
    open_evidence = [c for c in mine if not c['satisfied']]
    if open_evidence:
        return {'step': 'evidence',
                'action': 'produce in-window accepted evidence: ledger.py '
                          '--plan <dir> gate --task %s --criterion %s '
                          '--json <command>' %
                          (task_id, open_evidence[0]['criterion']),
                'criteria': [c['criterion'] for c in open_evidence]}
    return {'step': 'complete',
            'action': 'all criteria satisfied on in-window accepted '
                      'evidence: ledger.py --plan <dir> complete --task %s'
                      % task_id}


def manifest(plan_dir, task_id, sections=None):
    """Derive the per-task context manifest (read-only, deterministic).

    ``sections`` may exclude OPTIONAL sections only; the mandatory three
    (authorization, repository_rules, acceptance) are unconditional -
    pruning can never hide an acceptance or authorization boundary. The
    manifest carries no wall clock: ``as_of`` is the last record's
    position and timestamp.
    """
    if sections is not None:
        missing = [s for s in MANDATORY_SECTIONS if s not in sections]
        if missing:
            raise ContextError(
                'the manifest never drops mandatory section(s) %s - '
                'context pruning cannot hide the acceptance or '
                'authorization boundary' % ', '.join(missing))
    records = ledger.PlanRecords(plan_dir)
    contract = records.contract
    task = _task_of(contract, task_id)
    events = records.archived_events() + records.read_journal()[0]
    files = task_surface(plan_dir, contract, task_id)
    closure_all = outcomes.closure(contract, events)
    mine = [c for c in closure_all['criteria']
            if c.get('task') == task_id]
    states = ledger.criterion_states(contract, events, task_id)
    evidenced = [s.get('criterion') for s in states if s.get('satisfied')]
    missing_files = sorted(rel for rel, digest in files.items()
                           if digest is None)
    widen = bool(missing_files) or not evidenced
    reasons = []
    if missing_files:
        reasons.append('touched-surface entries missing on disk: %s'
                       % ', '.join(missing_files))
    if not evidenced:
        reasons.append('no in-window accepted evidence yet - the impact '
                       'of the surface is unmapped')
    doc = {
        'schema': 'https://deepworkplan.com/schema/context-manifest/v6.json',
        'derived_by': MANIFEST_IDENTITY,
        'plan': contract.get('plan'),
        'contract_id': records.contract_id,
        'contract_revision': contract.get('revision'),
        'task': task_id,
        'as_of': {'last_seq': max([e.get('seq', 0) for e in events] or [0]),
                  'event_ts': max([e.get('ts', '') for e in events] or
                                  [''])},
        'authorization': {
            'approvals': _approvals_of(events, records.contract_id),
            'contract_authorization': contract.get('authorization'),
            'permissions': contract.get('permissions')},
        'repository_rules': {
            'scope': contract.get('scope'),
            'invariants': [{'id': inv.get('id'),
                            'statement': inv.get('statement'),
                            **scheduler.invariant_status(
                                contract, events).get(inv.get('id'), {})}
                           for inv in contract.get('invariants', [])],
            'dependencies': contract.get('dependencies')},
        'touched_surface': {'files': files,
                            'widen_discovery': widen,
                            'widen_reasons': reasons},
        'acceptance': mine,
        'evidence': _valid_evidence(records, events, task_id, states),
        'next_action': _next_action(records, events, task_id, mine),
        'dead_ends': dead_ends(records),
        'freshness': {
            'inputs_fingerprint': inputs_fingerprint(
                records.contract_id, files),
            'rule': 'a stored fingerprint different from the current one '
                    'invalidates the summary that carries it'},
    }
    if sections is None or 'history_triggers' in sections:
        doc['history_triggers'] = _history_triggers(contract, events,
                                                    task_id)
    return doc


def _history_triggers(contract, events, task_id):
    """History loads ONLY on these declared triggers (v5 read tiers)."""
    triggers = [{'trigger': 'none', 'loads': 'this manifest alone'}]
    handoff = contract.get('scheduling', {}).get('handoff', {})
    if handoff:
        triggers.append({'trigger': 'handoff (%s)' % '; '.join(
            '%s=%s' % kv for kv in sorted(handoff.items())),
                         'loads': 'state.json + this manifest + the '
                                  'handoff observation'})
    if any(e.get('type') == 'amendment' and task_id in
           (e.get('affected_tasks') or []) for e in events):
        triggers.append({'trigger': 'an amendment affects this task',
                         'loads': 'the amendment event and the revised '
                                  'criterion text'})
    return triggers


# ------------------------------------------------------------- freshness

def freshness(plan_dir, task_id, summary):
    """Compare a stored inputs fingerprint against the current world."""
    if not isinstance(summary, dict) or \
            not summary.get('inputs_fingerprint'):
        raise ContextError('the summary carries no inputs_fingerprint - '
                           'an unattributable summary is stale by '
                           'construction')
    records = ledger.PlanRecords(plan_dir)
    files = task_surface(plan_dir, records.contract, task_id)
    current = inputs_fingerprint(records.contract_id, files)
    stored = summary.get('inputs_fingerprint')
    verdict = 'fresh' if stored == current else 'stale'
    return {'verdict': verdict, 'stored': stored, 'current': current,
            'reason': '' if verdict == 'fresh' else
                      'inputs changed since the summary was derived - the '
                      'summary is invalidated, never silently inherited'}


# ------------------------------------------------------------- accounting

def _span_hours(events):
    stamps = sorted(e.get('ts') for e in events if e.get('ts'))
    if len(stamps) < 2:
        return None
    import calendar
    import time as _time
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    try:
        first = calendar.timegm(_time.strptime(stamps[0], fmt))
        last = calendar.timegm(_time.strptime(stamps[-1], fmt))
    except ValueError:
        return None
    return round((last - first) / 3600.0, 3)


def _latest_sample(events, unit=None, limit_id=None):
    best = None
    for event in events:
        if event.get('type') != 'resource_sample':
            continue
        if unit is not None and event.get('unit') != unit:
            continue
        if limit_id is not None and event.get('limit_id') != limit_id:
            continue
        if best is None or event.get('seq', 0) > best.get('seq', 0):
            best = event
    return best


def accounting(plan_dir, bundle=None):
    """The four quantities, each from its own source, missing as missing.

    Static instruction bytes are MEASURED (the manifest itself plus any
    declared bundle files); provider tokens and monetary cost come only
    from observed meter samples (a host that read the meter - real rates,
    never bytes-to-money); wall-clock time is the recorded event span.
    Nothing is imputed; a missing quantity is null with its reason.
    """
    records = ledger.PlanRecords(plan_dir)
    events = records.archived_events() + records.read_journal()[0]
    instruction_bytes = {'source': 'measured', 'bytes': {}}
    doc = manifest(plan_dir, _only_task(records))
    instruction_bytes['bytes']['manifest_json'] = len(json.dumps(
        doc, sort_keys=True, indent=2).encode('utf-8'))
    for rel in bundle or []:
        instruction_bytes['bytes'][rel] = os.path.getsize(rel) \
            if os.path.isfile(rel) else None
    tokens = _latest_sample(events, unit='tokens')
    spend = _latest_sample(events, limit_id='spend_usd')
    span = _span_hours(events)
    return {
        'instruction_bytes': instruction_bytes,
        'provider_tokens': (
            {'value': tokens.get('value'), 'source': tokens.get('source'),
             'seq': tokens.get('seq')} if tokens else
            {'value': None, 'status': 'missing',
             'reason': 'no observed token meter sample in the records'}),
        'cost_usd': (
            {'value': spend.get('value'), 'source': spend.get('source'),
             'seq': spend.get('seq')} if spend else
            {'value': None, 'status': 'missing',
             'reason': 'no observed spend sample in the records - cost '
                       'comes only from real rates, never from bytes'}),
        'wall_clock_hours': (
            {'value': span, 'source': 'recorded event ts span'} if span
            is not None else
            {'value': None, 'status': 'missing',
             'reason': 'fewer than two timestamped events'}),
        'never': 'bytes are never converted to tokens or money',
    }


def _only_task(records):
    tasks = records.contract.get('tasks', [])
    if not tasks:
        raise ContextError('the contract declares no tasks')
    return tasks[0]['id']


# ---------------------------------------------------------------- render

def render_markdown(doc):
    """Deterministic markdown rendering for a fresh session."""
    lines = ['# Context manifest — %s / %s' % (doc.get('plan'),
                                               doc.get('task')),
             '',
             'Derived from the records at seq %s (%s). No history is '
             'loaded; every line below is a recorded fact or a pointer.'
             % (doc['as_of']['last_seq'], doc['as_of']['event_ts']),
             '']
    auth = doc['authorization']
    lines += ['## Authorization (carried, never summarized)', '']
    for approval in auth['approvals']:
        lines.append('- approval by %s via %s at %s (seq %s)'
                     % (approval['authority'], approval['mechanism'],
                        approval['ts'], approval['seq']))
    for checkpoint in (auth.get('contract_authorization') or {}).get(
            'consent_checkpoints', []):
        lines.append('- consent checkpoint: %s' % checkpoint)
    lines.append('')
    rules = doc['repository_rules']
    lines += ['## Repository rules', '',
              '- forbidden operations: %s'
              % ', '.join((rules['scope'] or {}).get(
                  'forbidden_operations', [])),
              '- allowed command classes: %s'
              % ', '.join((rules['scope'] or {}).get(
                  'allowed_command_classes', []) or []),
              '- invariants:']
    for inv in rules['invariants']:
        lines.append('  - %s — %s (%s)'
                     % (inv.get('id'), inv.get('state'), inv.get(
                         'statement')))
    lines += ['', '## Acceptance', '']
    for crit in doc['acceptance']:
        state = 'satisfied (%s)' % crit['mechanism'] if crit['satisfied'] \
            else crit['mechanism']
        lines.append('- %s: %s' % (crit['criterion'], state))
    lines += ['', '## Next action', '',
              '1. %s' % doc['next_action']['action'], '']
    if doc['dead_ends']:
        lines += ['## Dead ends (recorded — do not retry blindly)', '']
        for entry in doc['dead_ends']:
            note = ' [%s]' % entry['aged_out'] if entry.get('aged_out') \
                else ''
            lines.append('- seq %s %s%s — %s'
                         % (entry['seq'], entry['kind'], note,
                            entry.get('cause') or entry.get('reason')))
    surface = doc['touched_surface']
    lines += ['', '## Touched surface', '']
    for rel, digest in sorted(surface['files'].items()):
        lines.append('- %s: %s' % (rel, digest or 'MISSING ON DISK'))
    if surface['widen_discovery']:
        lines += ['', 'Discovery is WIDENED: %s'
                  % '; '.join(surface['widen_reasons'])]
    lines += ['', 'Freshness fingerprint: `%s`' % doc['freshness'][
        'inputs_fingerprint'], '']
    return '\n'.join(lines)


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
        contract['scope']['allowed_command_classes'] = ['true', 'python3',
                                                        'sh']
        # a gate input OUTSIDE the touched surface: flipping it changes
        # the outcome without changing the run fingerprint
        flag = os.path.join(tmp, 'flag.txt')
        with open(flag, 'w', encoding='utf-8') as fh:
            fh.write('bad')
        contract['tasks'][0]['touched_surface'] = [
            os.path.join(tmp, 'src_file.txt')]
        probe_cmd = ("python3 -c \"import sys; "
                     "sys.exit(0 if open('%s').read()=='ok' else 1)\""
                     % flag)
        cid = contract_v6.compute_contract_id(contract)
        with open(os.path.join(plan, 'contract.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(dict(contract, contract_id=cid), fh)

        # 1. a task outside the contract is refused, never guessed
        try:
            manifest(plan, 'T-missing')
            check('unknown task refused', False)
        except ContextError:
            check('unknown task refused', True)
        # 2. pruning cannot drop a mandatory section
        try:
            manifest(plan, 'T-implement',
                     sections=('authorization', 'repository_rules'))
            check('mandatory-section pruning refused', False)
        except ContextError:
            check('mandatory-section pruning refused', True)
        # 3. before approval the ladder names the approval step
        doc = manifest(plan, 'T-implement')
        check('ladder: approval first without an approval event',
              doc['next_action']['step'] == 'approval',
              doc['next_action']['step'])
        check('as_of is record-derived, never the wall clock',
              doc['as_of']['last_seq'] == 0 and
              doc['as_of']['event_ts'] == '', repr(doc['as_of']))

        # scaffold a real attempt
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('approval',
                      {'authority': 'selftest', 'mechanism':
                       'plan_authorship', 'plan_digest': 'a' * 64},
                      actor={'kind': 'human', 'identity': 'selftest'},
                      idempotent=True)
        writer.start_task('T-implement',
                          actor={'kind': 'agent', 'identity': 'selftest'})
        lock.release()
        doc = manifest(plan, 'T-implement')
        # 4. authorization carried verbatim (authority + checkpoints)
        check('authorization carried verbatim',
              doc['authorization']['approvals'] and
              doc['authorization']['contract_authorization'].get(
                  'consent_checkpoints') ==
              contract['authorization']['consent_checkpoints'])
        # 5. repository rules: forbidden ops + invariant status surface
        check('repository rules carry scope + invariants',
              doc['repository_rules']['scope']['forbidden_operations'] ==
              contract['scope']['forbidden_operations'] and
              doc['repository_rules']['invariants'][0]['state'] ==
              'unevaluated')
        # 6. open controlled criterion -> the control step, widen flagged
        check('ladder: control step for an open controlled criterion',
              doc['next_action']['step'] == 'control' and
              doc['next_action']['criteria'] == ['AC-one'],
              doc['next_action']['step'])
        check('unmapped surface widens discovery',
              doc['touched_surface']['widen_discovery'] is True)

        # 7. a failed gate enters the dead-end digest; the same run
        #    fingerprint later passing retires it
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.run_gate('T-implement', probe_cmd, criterion='AC-one')
        lock.release()
        doc = manifest(plan, 'T-implement')
        ends = [e for e in doc['dead_ends'] if e['kind'] == 'failed_gate']
        check('failed gate recorded in the digest with its cause',
              len(ends) == 1 and ends[0]['exit_code'] == 1 and
              ends[0]['cause'], repr(ends))
        with open(flag, 'w', encoding='utf-8') as fh:
            fh.write('ok')
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        # reuse=False: the flag is OUTSIDE the declared surface, so the
        # fingerprint cannot see the flip - equivalent-input reuse would
        # return the cached fail; the honest path forces the re-run
        writer.run_gate('T-implement', probe_cmd, criterion='AC-one',
                        reuse=False)
        lock.release()
        doc = manifest(plan, 'T-implement')
        ends = [e for e in doc['dead_ends'] if e['kind'] == 'failed_gate']
        check('a later pass on the same fingerprint retires the dead end',
              not ends, repr(doc['dead_ends']))
        # a passing gate is NOT acceptance for a controlled criterion:
        # only a discriminating control pair closes it (task 14 rule) -
        # the manifest must not round a gate pass up to acceptance
        check('a passing gate never closes a controlled criterion',
              doc['next_action']['step'] == 'control' and
              all(e['pointer_resolves'] for e in doc['evidence']),
              doc['next_action']['step'])

        # 8. duplicate refusals collapse to the latest per (subject, stage)
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('refusal', {'subject': 'T-implement',
                                  'stage': 'gate',
                                  'reason': 'first refusal'},
                      actor={'kind': 'helper',
                             'identity': ledger.LEDGER_IDENTITY})
        writer.append('refusal', {'subject': 'T-implement',
                                  'stage': 'gate',
                                  'reason': 'latest refusal'},
                      actor={'kind': 'helper',
                             'identity': ledger.LEDGER_IDENTITY})
        lock.release()
        doc = manifest(plan, 'T-implement')
        refusals = [e for e in doc['dead_ends'] if e['kind'] == 'refusal']
        check('refusals dedup to the latest per subject+stage',
              len(refusals) == 1 and
              refusals[0]['reason'] == 'latest refusal', repr(refusals))

        # 9. a non-discriminating control under a superseded revision is
        #    marked aged_out (records carry the old contract_id)
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        os.makedirs(os.path.join(plan, 'gates'), exist_ok=True)
        with open(os.path.join(plan, 'gates', 'c.log'), 'w',
                  encoding='utf-8') as fh:
            fh.write('old PASS new PASS\n')
        writer.append('control_pair', {
            'criterion': 'AC-one', 'check_artifacts': ['f.txt'],
            'starting_fingerprint': {'revision': 'r1', 'dirty': ''},
            'old_leg': {'available': True, 'outcome': 'PASS',
                        'log': 'gates/c.log'},
            'new_leg': {'outcome': 'PASS', 'log': 'gates/c.log'},
            'verdict': 'non_discriminating', 'trust': 'asserted'},
            actor={'kind': 'agent', 'identity': 'selftest'},
            evidence_path='gates/c.log')
        lock.release()
        rev2 = json.loads(json.dumps(contract))
        rev2['revision'] = 2
        rev2['parent_contract_id'] = cid
        rev2['acceptance']['criteria'][0]['control'] = \
            {'kind': 'exempt', 'rationale': 'prose-only surface'}
        cid2 = contract_v6.compute_contract_id(rev2)
        with open(os.path.join(plan, 'contract.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(dict(rev2, contract_id=cid2), fh)
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('approval',
                      {'authority': 'selftest', 'mechanism':
                       'plan_authorship', 'plan_digest': 'b' * 64},
                      actor={'kind': 'human', 'identity': 'selftest'},
                      idempotent=True)
        lock.release()
        doc = manifest(plan, 'T-implement')
        stale_controls = [e for e in doc['dead_ends']
                          if e['kind'] == 'non_discriminating_control']
        check('superseded control marked aged_out, retention-biased',
              len(stale_controls) == 1 and
              stale_controls[0].get('aged_out') ==
              'superseded contract revision', repr(stale_controls))
        # under the exempt revision the in-window gate pass IS accepted
        # evidence: the ladder advances to complete
        check('exempt criterion advances the ladder to complete',
              doc['next_action']['step'] == 'complete',
              doc['next_action']['step'])

        # 10. freshness: unchanged inputs fresh; a changed input stale
        files = task_surface(plan, rev2, 'T-implement')
        stored = inputs_fingerprint(cid2, files)
        verdict = freshness(plan, 'T-implement',
                            {'inputs_fingerprint': stored})
        check('freshness: unchanged inputs are fresh',
              verdict['verdict'] == 'fresh')
        src = os.path.join(tmp, 'src_file.txt')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write('changed content')
        verdict = freshness(plan, 'T-implement',
                            {'inputs_fingerprint': stored})
        check('freshness: changed inputs invalidate the summary',
              verdict['verdict'] == 'stale')
        try:
            freshness(plan, 'T-implement', {})
            check('unattributable summary refused', False)
        except ContextError:
            check('unattributable summary refused', True)

        # 11. accounting: four quantities, missing as missing
        acct = accounting(plan)
        check('accounting keeps the four quantities distinct',
              set(acct) == {'instruction_bytes', 'provider_tokens',
                            'cost_usd', 'wall_clock_hours', 'never'})
        check('missing meter data is null with its reason, never zero',
              acct['provider_tokens']['value'] is None and
              acct['provider_tokens']['status'] == 'missing' and
              acct['cost_usd']['value'] is None)
        check('instruction bytes are measured, not estimated',
              acct['instruction_bytes']['source'] == 'measured' and
              acct['instruction_bytes']['bytes']['manifest_json'] > 0)
        check('wall clock is the recorded event span',
              isinstance(acct['wall_clock_hours']['value'], (int, float)))

        # 12. determinism: identical records render identical manifests
        doc_a = manifest(plan, 'T-implement')
        doc_b = manifest(plan, 'T-implement')
        check('manifest derivation is deterministic',
              json.dumps(doc_a, sort_keys=True) ==
              json.dumps(doc_b, sort_keys=True))
        md = render_markdown(doc_a)
        check('markdown render carries the boundary sections',
              '## Authorization' in md and '## Repository rules' in md and
              'consent checkpoint' in md and 'MISSING ON DISK' not in md)

        # 13. plan locality: the manifest leaks no host environment
        blob = json.dumps(doc_a)
        check('no host environment leaks into the manifest',
              'PATH' not in blob and 'VIRTUAL_ENV' not in blob and
              os.environ.get('HOME', '') not in blob)
    return (not failures, failures, probes[0])


# --------------------------------------------------------------------- CLI

def main(argv):
    usage = ('usage: context_manifest.py --plan DIR {manifest --task T '
             '[--sections a,b] [--out FILE] [--md] | freshness --task T '
             '--summary FILE | accounting [--bundle P ...] | self-test}')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--plan')
    parser.add_argument('command')
    parser.add_argument('--task')
    parser.add_argument('--sections')
    parser.add_argument('--out')
    parser.add_argument('--md', action='store_true')
    parser.add_argument('--summary')
    parser.add_argument('--bundle', action='append')
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
        if args.command == 'manifest':
            if not args.task:
                print('manifest requires --task')
                return 2
            sections = tuple(s.strip() for s in args.sections.split(',')) \
                if args.sections else None
            doc = manifest(plan, args.task, sections=sections)
            body = render_markdown(doc) if args.md else \
                json.dumps(doc, sort_keys=True, indent=2) + '\n'
            if args.out:
                os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
                with open(args.out, 'w', encoding='utf-8') as fh:
                    fh.write(body)
            print(body)
            return 0
        if args.command == 'freshness':
            if not (args.task and args.summary):
                print('freshness requires --task and --summary')
                return 2
            with open(args.summary, encoding='utf-8') as fh:
                summary = json.load(fh)
            verdict = freshness(plan, args.task, summary)
            print(json.dumps(verdict, sort_keys=True, indent=2))
            return 0 if verdict['verdict'] == 'fresh' else 1
        if args.command == 'accounting':
            acct = accounting(plan, bundle=args.bundle)
            print(json.dumps(acct, sort_keys=True, indent=2))
            return 0
    except ContextError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    except ledger.LedgerError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    except outcomes.OutcomesError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
