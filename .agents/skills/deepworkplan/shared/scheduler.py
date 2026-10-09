#!/usr/bin/env python3
"""v6 authorization core: scheduler proposals against a deterministic core.

Implements RFC section 5 (draft-4) for v6 new plans. The split is
absolute:

  * **The scheduler is a model.** It proposes — "select task T-x next",
    "adapt: retry this gate / split this task / reorder". Proposals are
    cheap, and no proposal is trusted.
  * **This module is the deterministic core.** :func:`authorize` is a pure
    function of ``(contract, events, proposal)`` — no wall clock, no
    random, no filesystem, no network. It accepts or refuses with a named
    rule, and the refusal reasons are stable strings a test can pin.

What authorize refuses (each rule names itself in the reason):

  * a proposal whose type is outside ``PROPOSAL_TYPES`` (closed set);
  * an invalid contract (cycles, dropped requirements, closed-object
    violations — caught by :mod:`contract_v6` before scheduling logic);
  * an invalid journal record (tampered or corrupt records stop dispatch);
  * any proposal before an ``approval`` event cites the live contract;
  * a **failed, stale or never-evaluated boundary invariant** — invariant
    breaches are stops, never scheduling inputs (D3-6). Evaluations ride
    ordinary ``observation`` events with the closed grammar
    ``INV-<id>: pass`` / ``INV-<id>: fail: <reason>`` and are fresh only
    at or after the plan's reference position (the latest ``task_start``,
    else the ``approval``);
  * an enforced envelope limit that commit-plus-pending would exceed
    (A5): spent is the latest **observed** sample per limit (asserted
    samples are advisory), pending is the declared impact of every
    authorized adaptation still affecting incomplete work, plus the
    proposal's own declared impact;
  * ``select`` for an unknown, already-complete task, a task with
    incomplete prerequisites (a prerequisite whose criteria are only
    stale-satisfied is not complete — deferral disguised as completion is
    refused here), or a task whose ``touched_surface`` overlaps a task
    currently in progress (A8: intra-plan parallelism on overlapping
    surfaces is serialized; independent in-scope work stays selectable);
  * ``adapt`` outside the closed section-3.3 enumeration, beyond the
    contract-declared caps, a **blind retry** (a retry whose trigger
    observation does not postdate the last attempt on the same
    criterion), or a retry past ``max_retries_per_gate``.

Bounded adaptation is structural: the caps default finite (never
unlimited), a contract can declare tighter or looser bounds in its
optional ``scheduling`` block, and loops terminate because every path that
could repeat forever hits a cap or the blind-retry rule.

Starvation (A11): :func:`ready` ranks eligible tasks oldest-first on the
**journal clock** (waiting is measured in events since the task became
eligible, never wall time). A task waiting at or beyond
``scheduling.starvation_threshold_events`` (default 50) carries a
``priority_boost`` with the ``aging`` payload that the ``selection``
event shape requires — recorded by the caller through the ledger, never
fabricated here.

Child plans (U5/A8/D3-8): intra-repo parallelism runs as **sibling
plans**, each a single-writer contract+journal scoped to declared file
ownership. This module authorizes exactly one record; it never sees, and
never writes, a sibling's paths. The overlap rule above is the in-plan
half of that boundary.

This module is READ-ONLY. It never writes a journal event, never takes
the ledger lock, and never executes anything: recording an authorized
proposal (``adaptation`` / ``selection`` events) is the writer's job, and
a refusal to record is the caller's decision. Python 3.9+ stdlib only.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402  (sibling module, same directory)
import ledger  # noqa: E402  (sibling module; pure semantics are shared)

SCHEDULER_IDENTITY = 'dwp-scheduler/6.0'

#: The closed set of proposals the core understands (RFC section 5).
PROPOSAL_TYPES = ('select', 'adapt')

#: Finite defaults for the optional contract ``scheduling`` block. A cap
#: is NEVER unlimited by default; a contract declares tighter or looser.
DEFAULT_STARVATION_THRESHOLD_EVENTS = 50
DEFAULT_MAX_ADAPTATIONS_PER_TASK = 3
DEFAULT_MAX_RETRIES_PER_GATE = 2

SELECT_FIELDS = {'type', 'task'}
ADAPT_FIELDS = {'type', 'kind', 'trigger_observation', 'evidence_artifact',
                'hypothesis', 'action', 'rationale', 'affected_tasks',
                'affected_criteria', 'authority', 'evidence_invalidated',
                'evidence_preserved', 'resource_impact'}

EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_REFUSE = 10


class SchedulerError(Exception):
    """Operator-visible failure; exit 1."""


class ContractInvalidRefusal(SchedulerError):
    """The plan's contract fails validation at load time.

    The pure ``authorize`` names this refusal ``contract-invalid``, but a
    contract that does not validate never finishes loading — so the CLI
    converts the load failure into the same named refusal decision (exit
    10) instead of an opaque exit-1 error. The rule-name contract holds
    on every surface (U3/B1).
    """


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


# ------------------------------------------------------------- policies

def scheduling_policy(contract):
    """Effective caps/threshold: contract declarations over finite
    defaults. The result is a plain dict a test can pin."""
    sched = contract.get('scheduling') or {}
    return {
        'starvation_threshold_events': sched.get(
            'starvation_threshold_events',
            DEFAULT_STARVATION_THRESHOLD_EVENTS),
        'max_adaptations_per_task': sched.get(
            'max_adaptations_per_task', DEFAULT_MAX_ADAPTATIONS_PER_TASK),
        'max_retries_per_gate': sched.get(
            'max_retries_per_gate', DEFAULT_MAX_RETRIES_PER_GATE),
    }


def _refusal(rule, detail):
    return {'decision': 'refuse', 'rule': rule, 'reason': detail}


# ------------------------------------------------------------ the record

def reference_position(events):
    """The position fresh invariant evaluations must reach (D3-6): the
    latest task_start, else the approval — the points where boundaries
    are re-verified before more work is dispatched."""
    start = None
    approval = None
    for event in events:
        if not isinstance(event, dict):
            continue
        etype = event.get('type')
        seq = event.get('seq') or 0
        if etype == 'task_start' and (start is None or seq > start):
            start = seq
        elif etype == 'approval' and (approval is None or seq > approval):
            approval = seq
    if start is not None:
        return start
    return approval or 0


def invariant_status(contract, events):
    """Per declared invariant: the latest grammar-matching observation.

    Grammar (closed): ``INV-<id>: pass`` or ``INV-<id>: fail: <reason>``
    as the statement of an ``observation`` event. Statements that do not
    match the grammar for a declared invariant are ordinary observations
    and are ignored here. Returns {id: {'state', 'seq', 'detail'}} where
    state is pass/fail/stale/unevaluated.
    """
    prefix = {inv['id']: inv['id'] + ': '
              for inv in contract.get('invariants', [])}
    latest = {}
    for event in events:
        if not isinstance(event, dict) or event.get('type') != 'observation':
            continue
        statement = event.get('statement')
        if not isinstance(statement, str):
            continue
        for iid, head in prefix.items():
            if not statement.startswith(head):
                continue
            verdict = statement[len(head):]
            if verdict == 'pass':
                outcome = 'pass'
            elif verdict == 'fail' or verdict.startswith('fail:'):
                outcome = 'fail'
            else:
                continue  # not an invariant evaluation
            seq = event.get('seq') or 0
            if iid not in latest or seq >= latest[iid]['seq']:
                latest[iid] = {'state': outcome, 'seq': seq,
                               'detail': statement}
    reference = reference_position(events)
    status = {}
    for iid in prefix:
        found = latest.get(iid)
        if found is None:
            status[iid] = {'state': 'unevaluated', 'seq': None}
        elif found['seq'] < reference:
            status[iid] = {'state': 'stale', 'seq': found['seq']}
        else:
            status[iid] = found
    return status


def invariant_refusal(contract, events):
    """The stop-refusal for boundary invariants, or None when all are
    fresh passes. Unevaluated and stale are stops exactly like failures:
    the core will not dispatch on unverified boundaries, and it never
    fabricates an evaluation to proceed (D3-6)."""
    for iid, found in invariant_status(contract, events).items():
        if found['state'] == 'fail':
            return _refusal(
                'invariant-failed',
                'invariant %s failed (observation at seq %s): invariant '
                'breaches are stops, never scheduling inputs — repair and '
                're-evaluate before proposing more work (D3-6)'
                % (iid, found['seq']))
        if found['state'] == 'stale':
            return _refusal(
                'invariant-stale',
                'invariant %s was last evaluated at seq %s, before the '
                'current reference position %d — re-evaluate at or after '
                'the position before proposing more work (D3-6)'
                % (iid, found['seq'], reference_position(events)))
        if found['state'] == 'unevaluated':
            return _refusal(
                'invariant-unevaluated',
                'invariant %s is declared but never evaluated — a declared '
                'boundary is verified before dispatch, never assumed '
                '(D3-6): record an observation "%s: pass" first'
                % (iid, iid))
    return None


# -------------------------------------------------------------- envelope

def envelope_status(contract, events, extra_impact=None):
    """Commit-plus-pending accounting per limit (A5).

    spent   = the latest **observed** resource_sample per limit id
              (asserted samples are advisory-only for enforced limits);
    pending = the declared impact of every authorized adaptation still
              affecting incomplete work, plus ``extra_impact`` (the
              proposal under evaluation, {declared, unit}).
    """
    limits = contract.get('resource_envelope', {}).get('limits', [])
    known = {limit['id']: limit for limit in limits}
    samples = {}
    advisory = {}
    for event in events:
        if not isinstance(event, dict) or \
                event.get('type') != 'resource_sample':
            continue
        lid = event.get('limit_id')
        if lid not in known:
            continue
        seq = event.get('seq') or 0
        slot = samples if event.get('trust') == 'observed' else advisory
        if lid not in slot or seq >= slot[lid]['seq']:
            slot[lid] = {'value': event.get('value'), 'seq': seq}

    def incomplete_affects(event):
        for tid in event.get('affected_tasks') or []:
            if not ledger.task_complete(contract, events, tid):
                return True
        return False

    pending = {lid: 0.0 for lid in known}
    for event in events:
        if not isinstance(event, dict) or \
                event.get('type') != 'adaptation' or \
                event.get('decision') != 'authorized':
            continue
        impact = event.get('resource_impact') or {}
        declared = impact.get('declared')
        unit = impact.get('unit')
        if not isinstance(declared, (int, float)) or declared <= 0:
            continue
        for lid, limit in known.items():
            if limit.get('unit') == unit:
                pending[lid] += declared
    # the proposal under evaluation commits too (A5 commit-plus-pending)
    impact = extra_impact or {}
    if isinstance(impact.get('declared'), (int, float)) and \
            impact['declared'] > 0:
        for lid, limit in known.items():
            if limit.get('unit') == impact.get('unit'):
                pending[lid] += impact['declared']

    rows = []
    for limit in limits:
        lid = limit['id']
        spent = samples.get(lid, {}).get('value')
        rows.append({
            'limit_id': lid,
            'unit': limit.get('unit'),
            'enforcement': limit.get('enforcement'),
            'limit': limit.get('limit'),
            'spent': spent,
            'asserted_latest': advisory.get(lid, {}).get('value'),
            'pending': pending.get(lid, 0.0),
            'metered': spent is not None,
        })
    return rows


def envelope_refusal(contract, events, extra_impact=None):
    """The refusal for an enforced limit that commit-plus-pending would
    exceed, or None. An unmetered enforced limit enforces the pending
    side only — missing data is exposed as missing, never imputed (and
    recorded ``metered: false`` by :func:`envelope_status`)."""
    for row in envelope_status(contract, events, extra_impact):
        if row['enforcement'] != 'enforced':
            continue
        spent = row['spent'] if row['spent'] is not None else 0.0
        total = spent + row['pending']
        if total > row['limit']:
            return _refusal(
                'envelope-exceeded',
                'enforced limit %r would be exceeded: %s + %s pending > '
                '%s %s (A5 commit-plus-pending)%s' % (
                    row['limit_id'], spent, row['pending'], row['limit'],
                    row['unit'],
                    '' if row['metered'] else
                    ' [limit unmetered: no observed sample on record]'))
    return None


# ------------------------------------------------------------ authorize

def _adapt_event(contract, events, proposal):
    """The journal event the writer would append for an accepted adapt
    proposal — authorize checks exactly this object, so what was checked
    is what gets recorded (no drift between the two)."""
    event = {key: proposal[key] for key in proposal if key != 'type'}
    event.update({
        'schema': contract_v6.journal_url_for(contract),
        'type': 'adaptation',
        'seq': _last_seq(events) + 1,
        'ts': _last_ts(events) or '1970-01-01T00:00:00Z',
        'plan': contract['plan'],
        'contract_id': contract.get('contract_id') or
        contract_v6.compute_contract_id(contract),
        'actor': {'kind': 'agent', 'identity': SCHEDULER_IDENTITY},
        'decision': 'authorized',
    })
    return event


def _last_seq(events):
    return max([e.get('seq', 0) for e in events
                if isinstance(e, dict)] or [0])


def _last_ts(events):
    return max([e.get('ts') for e in events
                if isinstance(e, dict) and e.get('ts')] or [None])


def _task(contract, task_id):
    for task in contract.get('tasks', []):
        if task.get('id') == task_id:
            return task
    return None


def _authorized_adaptations(events):
    return [event for event in events
            if isinstance(event, dict) and
            event.get('type') == 'adaptation' and
            event.get('decision') == 'authorized']


def authorize(contract, events, proposal):
    """Pure accept/refuse for one scheduler proposal.

    Returns ``{'decision': 'accept', ...}`` — for ``select`` the chosen
    task plus the checks that passed; for ``adapt`` the ready-to-append
    journal event — or ``{'decision': 'refuse', 'rule', 'reason'}`` with
    a stable rule name. Never raises for a well-formed call, never reads
    anything but its arguments.
    """
    if not isinstance(proposal, dict):
        return _refusal('proposal-shape', 'a proposal is a JSON object')
    ptype = proposal.get('type')
    if ptype not in PROPOSAL_TYPES:
        return _refusal(
            'proposal-type',
            'unknown proposal type %r — the closed set is %s '
            '(RFC section 5)' % (ptype, '/'.join(PROPOSAL_TYPES)))

    errors = contract_v6.contract_errors(contract)
    if errors:
        return _refusal(
            'contract-invalid',
            'the contract does not validate, so nothing schedules: %s'
            % errors[0])
    live_id = contract.get('contract_id') or \
        contract_v6.compute_contract_id(contract)
    errors = contract_v6.journal_errors(list(events), contract=contract) \
        if events else []
    if errors:
        return _refusal(
            'record-invalid',
            'the journal record does not validate, so nothing schedules '
            '(tampered or corrupt records stop dispatch): %s' % errors[0])

    approved = any(isinstance(event, dict) and event.get('type') == 'approval'
                   and event.get('contract_id') == live_id
                   for event in events)
    if not approved:
        return _refusal(
            'approval-missing',
            'no approval event cites the live contract_id %s — '
            'materialization approval precedes every proposal (D3-7/D2-3)'
            % live_id[:12])

    stop = invariant_refusal(contract, events)
    if stop is not None:
        return stop

    extra_impact = proposal.get('resource_impact') \
        if ptype == 'adapt' else None
    stop = envelope_refusal(contract, events, extra_impact)
    if stop is not None:
        return stop

    if ptype == 'select':
        return _authorize_select(contract, events, proposal)
    return _authorize_adapt(contract, events, proposal, live_id)


def _authorize_select(contract, events, proposal):
    unknown = set(proposal) - SELECT_FIELDS
    if unknown:
        return _refusal(
            'proposal-shape',
            'select takes %s, found extra field(s) %s' %
            (sorted(SELECT_FIELDS), sorted(unknown)))
    task_id = proposal.get('task')
    task = _task(contract, task_id)
    if task is None:
        return _refusal(
            'unknown-task', 'task %r is not in the contract' % task_id)
    if ledger.task_complete(contract, events, task_id):
        return _refusal(
            'task-complete',
            'task %s is already complete — completed work never re-selects; '
            'new work on the same surface is a new task or a revision'
            % task_id)
    for prereq in task.get('prerequisites', []):
        if not ledger.task_complete(contract, events, prereq):
            return _refusal(
                'prerequisite-open',
                'prerequisite %s of %s is not complete (a prerequisite '
                'whose criteria carry only stale evidence is not '
                'complete — deferral disguised as completion is refused '
                'here)' % (prereq, task_id))
    # A8/D3-8: single writer per surface. Overlapping in-progress work is
    # serialized; independent in-scope work remains selectable.
    surface = set(task.get('touched_surface') or [])
    for other in contract.get('tasks', []):
        other_id = other.get('id')
        if other_id == task_id:
            continue
        started = ledger.task_start_seq_of(events, other_id)
        if started is None or \
                ledger.task_complete(contract, events, other_id):
            continue
        overlap = surface & set(other.get('touched_surface') or [])
        if overlap:
            return _refusal(
                'surface-serialization',
                'touched-surface overlap with in-progress %s (%s): '
                'intra-plan parallelism on overlapping surfaces is '
                'serialized (A8); independent in-scope work stays '
                'selectable' % (other_id, ', '.join(sorted(overlap))))
    return {
        'decision': 'accept', 'type': 'select', 'task': task_id,
        'checks': ['contract', 'approval', 'invariants', 'envelope',
                   'prerequisites', 'surface-serialization'],
    }


def _authorize_adapt(contract, events, proposal, live_id):
    unknown = set(proposal) - ADAPT_FIELDS
    if unknown:
        return _refusal(
            'proposal-shape',
            'adapt takes the adaptation shape, found extra field(s) %s — '
            'criterion content never rides a proposal (discarded '
            'requirements are refused)' % sorted(unknown))
    event = _adapt_event(contract, events, proposal)
    errors = contract_v6.journal_event_errors(event, contract)
    if errors:
        return _refusal(
            'adaptation-shape',
            'the proposal is not a valid adaptation event: %s '
            '(closed section-3.3 enumeration; an adaptation never carries '
            'criterion content — weakening acceptance is an amendment '
            'with recorded authority)' % errors[0])

    policy = scheduling_policy(contract)
    affected = set(proposal.get('affected_tasks') or [])
    counts = {}
    for prior in _authorized_adaptations(events):
        shared = affected & set(prior.get('affected_tasks') or [])
        for tid in shared:
            counts[tid] = counts.get(tid, 0) + 1
    for tid in sorted(affected):
        if counts.get(tid, 0) >= policy['max_adaptations_per_task']:
            return _refusal(
                'adaptation-cap',
                'task %s already carries %d authorized adaptation(s); the '
                'contract-declared cap is %d (bounded adaptation — loops '
                'terminate)' % (tid, counts[tid],
                                policy['max_adaptations_per_task']))

    if proposal.get('kind') == 'retry':
        criteria = set(proposal.get('affected_criteria') or [])
        retries = 0
        for prior in _authorized_adaptations(events):
            if prior.get('kind') == 'retry' and \
                    criteria & set(prior.get('affected_criteria') or []):
                retries += 1
        if retries >= policy['max_retries_per_gate']:
            return _refusal(
                'retry-cap',
                '%d authorized retry adaptation(s) already touch these '
                'criteria; max_retries_per_gate is %d' %
                (retries, policy['max_retries_per_gate']))
        last_attempt = max(
            [e.get('seq', 0) for e in events
             if isinstance(e, dict) and e.get('type') == 'gate_run' and
             e.get('criterion') in criteria] or [0])
        trigger = proposal.get('trigger_observation') or 0
        if last_attempt and trigger <= last_attempt:
            return _refusal(
                'blind-retry',
                'the trigger observation (seq %d) does not postdate the '
                'last attempt on these criteria (seq %d) — a retry needs a '
                'new observation explaining what changed; no-progress '
                'retries are refused' % (trigger, last_attempt))

    return {
        'decision': 'accept', 'type': 'adapt',
        'checks': ['contract', 'approval', 'invariants', 'envelope',
                   'adaptation-shape', 'caps', 'blind-retry'],
        'event': event,
    }


# ------------------------------------------------------------- readiness

def ready(contract, events):
    """Eligible tasks ranked oldest-first on the journal clock (A11).

    waiting_since_seq is the seq of the event that made the task
    eligible: the highest criterion-satisfaction seq among its
    prerequisites (or the approval seq when there are none). waiting is
    the number of journal events since — never wall time, so aging is
    deterministic under replay.
    """
    policy = scheduling_policy(contract)
    last = _last_seq(events)
    approval_seq = max(
        [e.get('seq', 0) for e in events
         if isinstance(e, dict) and e.get('type') == 'approval'] or [0])
    candidates = []
    for order, task in enumerate(contract.get('tasks', [])):
        task_id = task.get('id')
        if ledger.task_complete(contract, events, task_id):
            continue
        blocked = False
        since = approval_seq or 1
        for prereq in task.get('prerequisites', []):
            states = ledger.criterion_states(contract, events, prereq)
            if not all(state.get('satisfied') for state in states):
                blocked = True
                break
            for state in states:
                since = max(since, state.get('via_seq') or 0)
        if blocked:
            continue
        waiting = last - since
        entry = {
            'task': task_id,
            'waiting_since_seq': since,
            'waiting_events': waiting,
            'rank': 0,
            'priority_boost': waiting >=
            policy['starvation_threshold_events'],
            'aging': None,
        }
        if entry['priority_boost']:
            entry['aging'] = {
                'waiting_since_seq': since,
                'threshold': str(policy['starvation_threshold_events']),
            }
        candidates.append((waiting, order, entry))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    ranked = []
    for position, (_, _, entry) in enumerate(candidates, 1):
        entry['rank'] = position
        ranked.append(entry)
    return ranked


def boost_events(contract, events):
    """The ``selection`` payloads the caller should record for starved
    tasks, in rank order (A11). The scheduler never appends: these go
    through the ledger writer, which validates the closed shape."""
    return [{'task': entry['task'], 'priority_boost': True,
             'aging': entry['aging']}
            for entry in ready(contract, events)
            if entry['priority_boost']]


# ---------------------------------------------------------------- selftest

def _selftest_plan(tmp):
    """A real v6 plan built through the real writer: the scheduler's
    self-test exercises the integration, not a hand-built mock."""
    contract = {
        'schema': contract_v6.CONTRACT_SCHEMA_URL,
        'spec_version': '6.0.0',
        'plan': 'PLAN_scheduler_selftest',
        'revision': 1,
        'created_at': '2026-09-26T00:00:00Z',
        'title': 'scheduler self-test',
        'outcome': {
            'statement': 'authorize() decides deterministically.',
            'success_definition': 'Every probe pins a named rule.',
            'out_of_scope': ['live dispatch (Task 17 wiring)']},
        'acceptance': {'criteria': [
            {'id': 'AC-implement', 'statement': 'The module ships',
             'observable_check': 'import succeeds',
             'accepted_evidence': ['observed']},
            {'id': 'AC-verify', 'statement': 'The module is verified',
             'observable_check': 'self-test OK',
             'accepted_evidence': ['observed']},
            {'id': 'AC-document', 'statement': 'The module is documented',
             'observable_check': 'AGENT_PROTOCOL names every rule',
             'accepted_evidence': ['observed', 'asserted']},
        ]},
        'invariants': [
            {'id': 'INV-no-network',
             'statement': 'The core never makes a network call.'}],
        'scope': {'allowed_paths': ['src/'], 'allowed_command_classes':
                  ['test', 'true'], 'forbidden_operations': ['network']},
        'authorization': {
            'mechanism': 'plan_authorship', 'authority': 'self-test',
            'timestamp': '2026-09-26T00:00:00Z',
            'boundaries': 'in-memory scenario only',
            'consent_checkpoints': []},
        'permissions': {'granted': ['fs_write_plan_scope'],
                        'not_granted': ['network_access',
                                        'agent_delegation']},
        'dependencies': [],
        'resource_envelope': {'limits': [
            {'id': 'spend_usd', 'limit': 100, 'unit': 'USD',
             'enforcement': 'enforced',
             'metering_source': 'selftest: declared samples'},
        ]},
        'scheduling': {'starvation_threshold_events': 3,
                       'max_adaptations_per_task': 1,
                       'max_retries_per_gate': 1},
        'tasks': [
            {'id': 'T-implement', 'title': 'Implement',
             'prerequisites': [], 'touched_surface': ['src/runner.py'],
             'gate_intent': [{'criterion': 'AC-implement',
                              'check': 'compile'}]},
            {'id': 'T-verify', 'title': 'Verify',
             'prerequisites': ['T-implement'],
             'touched_surface': ['test/runner.bats'],
             'gate_intent': [{'criterion': 'AC-verify',
                              'check': 'bats'}]},
            {'id': 'T-document', 'title': 'Document',
             'prerequisites': [], 'touched_surface': ['docs/runner.md'],
             'gate_intent': [{'criterion': 'AC-document',
                              'check': 'read'}]},
            {'id': 'T-overlap', 'title': 'Touches the same doc file',
             'prerequisites': [], 'touched_surface': ['docs/runner.md'],
             'gate_intent': [{'criterion': 'AC-document',
                              'check': 'read'}]},
        ],
    }
    cid = contract_v6.compute_contract_id(contract)
    plan_dir = os.path.join(tmp, 'PLAN_scheduler_selftest')
    os.makedirs(plan_dir)
    with open(os.path.join(plan_dir, 'contract.json'), 'w',
              encoding='utf-8') as handle:
        json.dump(dict(contract, contract_id=cid), handle)
    records = ledger.PlanRecords(plan_dir)
    lock = ledger.CooperativeLock(plan_dir, identity=SCHEDULER_IDENTITY)
    lock.acquire()
    try:
        writer = ledger.Writer(records, lock)
        helper = {'kind': 'helper', 'identity': SCHEDULER_IDENTITY}
        writer.append('approval', {
            'authority': 'self-test', 'mechanism': 'plan_authorship',
            'plan_digest': cid}, actor=helper, idempotent=True)
        # A1: an invariant evaluation is an agent-mediated observation —
        # recorded asserted, never observed (the grammar INV-<id>: pass is
        # trust-agnostic; the label names who mediated the claim)
        writer.append('observation', {
            'statement': 'INV-no-network: pass'}, actor=helper,
            trust='asserted')
        writer.append('task_start', {'task': 'T-implement'},
                      actor=helper, idempotent=True)
        # D3-6: boundaries are re-verified at or after task-start; the
        # scenario follows the discipline the core enforces.
        writer.append('observation', {
            'statement': 'INV-no-network: pass'}, actor=helper,
            trust='asserted')
        # B1/M5: observed gate evidence exists only through the executor,
        # bound to the task's declared criterion inside the started task
        writer.run_gate('T-implement', 'true', criterion='AC-implement')
        return records, writer
    finally:
        lock.release()


def self_test():
    """In-memory probes over a real writer-built record."""
    import tempfile
    failures = []
    probes = [0]

    def synthetic(contract, seq, etype, **payload):
        """A well-formed journal event appended by hand in a probe."""
        event = dict(payload)
        event.update({
            'schema': contract_v6.JOURNAL_SCHEMA_URL, 'type': etype,
            'seq': seq, 'ts': '2026-09-26T00:00:0%dZ' % (seq % 10),
            'plan': contract['plan'],
            'contract_id': contract['contract_id'],
            'actor': {'kind': 'helper', 'identity': SCHEDULER_IDENTITY},
        })
        return event

    def check(label, ok, detail=''):
        probes[0] += 1
        if not ok:
            failures.append('%s%s' % (label, (': ' + detail)
                                      if detail else ''))

    with tempfile.TemporaryDirectory() as tmp:
        records, writer = _selftest_plan(tmp)
        contract = records.contract
        events = writer.events

        # 1. determinism: identical inputs, identical decision
        proposal = {'type': 'select', 'task': 'T-verify'}
        first = json.dumps(authorize(contract, events, proposal),
                           sort_keys=True)
        second = json.dumps(authorize(contract, events, proposal),
                            sort_keys=True)
        check('authorize is deterministic', first == second)

        # 2. prerequisite ordering: T-verify selectable once T-implement
        #    carries in-window accepted evidence
        decision = authorize(contract, events, proposal)
        check('select after completion', decision['decision'] == 'accept',
              json.dumps(decision))

        # 3. unknown task and proposal types are refused by name
        check('unknown task refused',
              authorize(contract, events,
                        {'type': 'select', 'task': 'T-nope'})['rule'] ==
              'unknown-task')
        check('unknown type refused',
              authorize(contract, events, {'type': 'teleport'})['rule'] ==
              'proposal-type')

        # 4. invariants: a fail is a stop, and stale/unevaluated too
        failed = list(events)
        failed.append(synthetic(contract, 99, 'observation',
                                statement='INV-no-network: fail: probe '
                                          'called out', trust='asserted'))
        check('failed invariant stops',
              authorize(contract, failed, proposal)['rule'] ==
              'invariant-failed')
        mystery = {key: value for key, value in contract.items()
                   if key != 'contract_id'}
        mystery['invariants'] = [{'id': 'INV-mystery', 'statement': 'x'}]
        mystery_id = contract_v6.compute_contract_id(mystery)
        mystery = dict(mystery, contract_id=mystery_id)
        mystery_events = [dict(event, contract_id=mystery_id)
                          for event in events]
        check('unevaluated invariant stops',
              authorize(mystery, mystery_events,
                        proposal)['rule'] == 'invariant-unevaluated')

        # 5. approval boundary
        check('no approval, no dispatch',
              authorize(contract, [e for e in events
                                   if e.get('type') != 'approval'],
                        proposal)['rule'] == 'approval-missing')

        # 6. envelope: commit-plus-pending, observed spend only
        spent = list(events)
        spent.append(dict(
            synthetic(contract, 98, 'resource_sample',
                      source='selftest-meter', limit_id='spend_usd',
                      value=99.5, unit='USD', trust='observed',
                      evidence_path='analysis_results/meter.json'),
            actor={'kind': 'host_adapter', 'identity': 'selftest-meter'}))
        over = {'type': 'adapt', 'kind': 'change_strategy',
                'trigger_observation': 2, 'evidence_artifact': 'a.md',
                'hypothesis': 'a different tactic converges',
                'action': 'switch tactics on T-implement',
                'rationale': 'the first tactic plateaued',
                'authority': 'recorded observation',
                'affected_tasks': ['T-implement'],
                'affected_criteria': [],
                'evidence_invalidated': [], 'evidence_preserved': [],
                'resource_impact': {'declared': 5, 'unit': 'USD'}}
        check('commit-plus-pending refused',
              authorize(contract, spent, over)['rule'] == 'envelope-exceeded')

        # 7. caps and blind retries (spend far from the cap so the CAP is
        #    the rule under test, not the envelope)
        spent2 = list(events)
        spent2.append(dict(
            synthetic(contract, 98, 'resource_sample',
                      source='selftest-meter', limit_id='spend_usd',
                      value=90.0, unit='USD', trust='observed',
                      evidence_path='analysis_results/meter.json'),
            actor={'kind': 'host_adapter', 'identity': 'selftest-meter'}))
        ok_adapt = dict(over, resource_impact={'declared': 0.5,
                                               'unit': 'USD'})
        decision = authorize(contract, spent2, ok_adapt)
        check('adapt within envelope accepted',
              decision['decision'] == 'accept', json.dumps(decision))
        twice = spent2 + [decision['event']] if 'event' in decision \
            else spent2
        check('adaptation cap enforced',
              authorize(contract, twice, ok_adapt)['rule'] ==
              'adaptation-cap')
        blind = {'type': 'adapt', 'kind': 'retry', 'trigger_observation': 1,
                 'evidence_artifact': 'b.md', 'hypothesis': 'try again',
                 'action': 'retry the gate', 'rationale': 'flake',
                 'authority': 'hunch', 'affected_tasks': ['T-implement'],
                 'affected_criteria': ['AC-implement'],
                 'evidence_invalidated': [], 'evidence_preserved': [],
                 'resource_impact': {'declared': 0, 'unit': 'USD'}}
        check('blind retry refused',
              authorize(contract, spent, blind)['rule'] == 'blind-retry')

        # 8. starvation aging on the journal clock
        ranked = ready(contract, events)
        check('ready excludes complete tasks',
              all(entry['task'] != 'T-implement' for entry in ranked),
              json.dumps(ranked))
        aged = ready(contract, spent)
        starved = [entry for entry in aged if entry['priority_boost']]
        check('starvation fires at the declared threshold',
              bool(starved) and starved[0]['aging']['threshold'] == '3',
              json.dumps(aged))
        boosts = boost_events(contract, spent)
        check('boost payloads match the selection shape',
              bool(boosts) and boosts[0]['aging']['waiting_since_seq'] >= 1)

        # 9. surface serialization: an overlapping in-progress task blocks
        #    select, non-overlapping does not (the task lives in the base
        #    contract; a contract edit would be a new revision needing
        #    fresh approval, which is a different rule)
        started = list(events)
        started.append(synthetic(contract, 97, 'task_start',
                                 task='T-overlap'))
        started.append(synthetic(contract, 100, 'observation',
                                 statement='INV-no-network: pass',
                                 trust='asserted'))
        check('overlapping surface serialized',
              authorize(contract, started,
                        {'type': 'select', 'task': 'T-document'})['rule'] ==
              'surface-serialization')
        check('independent surface selectable',
              authorize(contract, started,
                        {'type': 'select',
                         'task': 'T-verify'})['decision'] == 'accept')

    return (not failures, failures, probes[0])


# ---------------------------------------------------------------------- CLI

def _load_plan(plan_path):
    plan_dir = ledger.find_plan_dir(plan_path)
    try:
        records = ledger.PlanRecords(plan_dir)
    except ledger.LedgerError as exc:
        raise ContractInvalidRefusal(str(exc))
    events, torn, _framing = records.read_journal()
    if torn is not None:
        raise SchedulerError(
            'journal has a torn tail at byte %d (%s) — open the writer '
            'once to repair it before asking the core to decide'
            % torn)
    # B3: plan history is archived + live — approvals and evidence windows
    # survive rolls, so the core reads both, exactly like the writer
    return records.contract, records.archived_events() + events


def _read_proposal(value, path):
    if value is not None:
        text = value
    elif path is not None:
        if path == '-':
            text = sys.stdin.read()
        else:
            with open(path, encoding='utf-8') as handle:
                text = handle.read()
    else:
        raise SchedulerError('pass a proposal with --json or --file')
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchedulerError('proposal does not parse as JSON: %s' % exc)


def main(argv):
    usage = ('usage: scheduler.py authorize PLAN (--json PROPOSAL | '
             '--file FILE) | ready PLAN | boosts PLAN | self-test')
    if not argv or argv[0] in ('-h', '--help'):
        print(usage)
        return 0 if argv else EXIT_USAGE
    command, rest = argv[0], argv[1:]
    if command == 'self-test':
        ok, failures, probes = self_test()
        for failure in failures:
            print('FAIL', failure)
        print('self-test: %s (%d probes)' %
              ('OK' if ok else 'FAILED', probes))
        return 0 if ok else EXIT_ERROR
    if command in ('authorize', 'ready', 'boosts'):
        if not rest:
            print(usage)
            return EXIT_USAGE
        contract, events = _load_plan(rest[0])
        if command == 'authorize':
            proposal, path = None, None
            i = 1
            while i < len(rest):
                if rest[i] == '--json' and i + 1 < len(rest):
                    proposal = rest[i + 1]
                    i += 2
                elif rest[i] == '--file' and i + 1 < len(rest):
                    path = rest[i + 1]
                    i += 2
                else:
                    print(usage)
                    return EXIT_USAGE
            decision = authorize(contract, events,
                                 _read_proposal(proposal, path))
            print(json.dumps(decision, sort_keys=True, indent=2))
            return 0 if decision['decision'] == 'accept' else EXIT_REFUSE
        if command == 'ready':
            print(json.dumps(ready(contract, events), sort_keys=True,
                             indent=2))
            return 0
        print(json.dumps(boost_events(contract, events), sort_keys=True,
                         indent=2))
        return 0
    print(usage)
    return EXIT_USAGE


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except ContractInvalidRefusal as exc:
        print(json.dumps(
            {'decision': 'refuse', 'rule': 'contract-invalid',
             'reason': 'the contract does not validate, so nothing '
                       'schedules: %s' % exc}, sort_keys=True, indent=2))
        sys.exit(EXIT_REFUSE)
    except (SchedulerError, ledger.LedgerError) as exc:
        print('error: %s' % exc, file=sys.stderr)
        sys.exit(EXIT_ERROR)
