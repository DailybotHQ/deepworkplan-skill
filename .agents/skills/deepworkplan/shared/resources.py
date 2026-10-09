#!/usr/bin/env python3
"""v6 resource controls and host capability negotiation (RFC section 8).

The envelope core (commit-plus-pending accounting, observed-only spend,
asserted-degrades-to-advisory) lives in :mod:`scheduler`; the observed-trust
mint for meter samples lives in :mod:`ledger`. This module COMPOSES both and
adds what section 8 still needs:

  * **host capability negotiation** — a closed set of runtime host facts
    (``stop_agent``, ``meter_spend``, ``meter_tokens``,
    ``meter_wall_clock``, ``cancel_children``, ``model_routing``,
    ``subagents``, ``telemetry``). Distinct from the contract's permission
    grants (authority) these are abilities. An unknown key is refused — no
    permission or capability is ever invented. Unstated = False (the
    minimal host, all-advisory, is a supported degraded posture, not an
    error).
  * **counter sources, honestly split** — some counters are JOURNAL-
    observable (wall-clock span, gate retries, dispatch calls: the core
    computes them from records, no host needed); some are HOST-observable
    only (spend, provider tokens: an adapter must read the meter); an
    unknown unit family is advisory with the unit named — a missing
    counter is exposed as missing, never imputed, never free usage.
  * **reserves** — each limit may declare a ``reserve`` (0 <= reserve <=
    limit) held back for verification, retry and resume. The dispatchable
    ceiling is ``limit - reserve``; a refusal fires when
    ``spent + pending + reserve > limit``. The envelope's own accounting is
    untouched — the reserve is applied here, beside it.
  * **exhaustion** — ``record_exhaustion`` persists an incomplete
    checkpoint as a journal observation (``LIMIT: exhausted <id>: ...``)
    and ``dispatch_hold`` derives the stop from the records; recovery is an
    explicit ``LIMIT: recovered`` observation, never a silent resume. An
    exhaustion observation can never satisfy an acceptance criterion — the
    ledger counts only ``gate_run`` events, so exhaustion structurally
    cannot mint completed evidence.
  * **cancellation settlement** — an in-flight reservation (an authorized
    adaptation's declared impact) settles EXACTLY ONCE: ``released``
    (cancelled — the child never consumed the budget) or ``committed``.
    A second settlement with a different disposition is the double-charge
    ambiguity and is refused, not arbitrated. ``pending_after_settlements``
    recomputes pending minus released settlements — derived from records,
    so replays agree by construction, and with zero settlements it equals
    :func:`scheduler.envelope_status` exactly (drift-guarded by tests).
  * **routing posture** — fixed-model by default. Model-tier switching
    requires BOTH an explicit contract grant (the ``model_routing``
    capability) AND the host ability; parallel dispatch requires the
    ``agent_delegation`` grant AND host ``subagents``. Each refusal names
    the missing side. Routing posture is never an efficacy claim.

Python 3.9+ stdlib only; imports only its sibling modules; the only writes
are journal events through the ledger writer.
"""
import argparse
import calendar
import json
import os
import re
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import config as dwp_config  # noqa: E402  (registry + descriptors, spec/CONFIG.md)
import contract_v6  # noqa: E402
import ledger  # noqa: E402
import scheduler  # noqa: E402

RESOURCES_IDENTITY = 'dwp resources.py'
HOST_CAPABILITIES = ('stop_agent', 'meter_spend', 'meter_tokens',
                     'meter_wall_clock', 'cancel_children', 'model_routing',
                     'subagents', 'telemetry')
CAPABILITY_FLOOR = {name: False for name in HOST_CAPABILITIES}
SETTLEMENTS = ('released', 'committed')
EXHAUST_GRAMMAR = re.compile(r'^LIMIT: (exhausted|recovered) '
                             r'([a-z][a-z0-9_]*)(?:: (.*))?$')
RESERVATION_GRAMMAR = re.compile(r'^RESERVATION: (\S+): (released|committed)'
                                 r'(?:: (.*))?$')
# unit family -> (source, host capability when host-sourced). Unknown units
# have no family: advisory with the unit named, never an invented meter.
UNIT_FAMILIES = (
    (('usd', '$', 'cost'), 'host', 'meter_spend'),
    (('token',), 'host', 'meter_tokens'),
    (('hour', 'wall', 'time', ' h'), 'journal', None),
    (('retr', 'attempt'), 'journal', None),  # retr covers retry/retries/retried
    (('call', 'dispatch', 'invocation'), 'journal', None),
)


class ResourcesError(Exception):
    """Operator-visible failure (exit 1)."""


# ------------------------------------------------------- host capabilities

def host_capabilities(declared=None):
    """Merge a host's declared abilities onto the all-False floor.

    Unstated capabilities are False — the minimal host (no model switching,
    no subagents, no telemetry, no stop) is a supported degraded posture.
    An unknown key is refused: no capability is invented.
    """
    caps = dict(CAPABILITY_FLOOR)
    for key, value in (declared or {}).items():
        if key not in HOST_CAPABILITIES:
            raise ResourcesError(
                'unknown host capability %r — the closed set is %s; a '
                'capability is never invented' % (key,
                                                  '/'.join(HOST_CAPABILITIES)))
        caps[key] = bool(value)
    return caps


def _family_of(unit):
    """(source, host capability) for a unit string, or (None, None)."""
    low = ' %s ' % str(unit or '').lower()
    for names, source, cap in UNIT_FAMILIES:
        if any(name in low for name in names):
            return source, cap
    return None, None


def _journal_spent(family_hint, unit, events):
    """Core-observable counters computed from the records."""
    low = str(unit or '').lower()
    if any(n in low for n in ('hour', 'wall', 'time')) or ' h' in low:
        stamps = sorted(e.get('ts') for e in events
                        if isinstance(e, dict) and e.get('ts'))
        if len(stamps) < 2:
            return 0.0
        start = time.strptime(stamps[0][:19], '%Y-%m-%dT%H:%M:%S')
        end = time.strptime(stamps[-1][:19], '%Y-%m-%dT%H:%M:%S')
        return round((calendar.timegm(end) - calendar.timegm(start)) / 3600.0,
                     4)
    runs = [e for e in events if isinstance(e, dict)
            and e.get('type') == 'gate_run']
    if 'retr' in low or 'attempt' in low:
        keys = {(e.get('task'), e.get('criterion')) for e in runs}
        return float(max(0, len(runs) - len(keys)))
    if any(n in low for n in ('call', 'dispatch', 'invocation')):
        return float(sum(1 for e in events if isinstance(e, dict)
                         and e.get('type') == 'selection'))
    return None


# --------------------------------------------------------- envelope report

def envelope_report(contract, events, host_caps=None, extra_impact=None):
    """Per-limit posture with reserves, counter sources and honest modes.

    Composes :func:`scheduler.envelope_status` (spent from observed
    samples, pending from authorized adaptations) and adds the reserve
    ceiling and the capability-aware effective mode. Pure over its inputs.
    """
    caps = host_caps if host_caps is not None else dict(CAPABILITY_FLOOR)
    sched_rows = {row['limit_id']: row
                  for row in scheduler.envelope_status(contract, events,
                                                       extra_impact)}
    rows = []
    refusal = None
    for limit in contract.get('resource_envelope', {}).get('limits', []):
        lid = limit['id']
        sched = sched_rows.get(lid, {})
        value = limit.get('limit')
        reserve = limit.get('reserve') or 0
        source, cap = _family_of(limit.get('unit'))
        spent = None
        mode = None
        if limit.get('enforcement') == 'advisory':
            mode = 'advisory (declared advisory)'
        elif source is None:
            mode = ('advisory (counter family unknown for unit %r — no '
                    'meter is invented)' % limit.get('unit'))
        elif source == 'journal':
            spent = _journal_spent(None, limit.get('unit'), events)
            mode = 'enforced (journal-computed counter)'
        elif not caps.get(cap):
            mode = ('advisory (host cannot meter: no %s capability — '
                    'enforcement parity is never claimed)' % cap)
        elif sched.get('spent') is None:
            mode = ('enforced-pending-only (unmetered spend: a missing '
                    'counter is not free usage)')
        else:
            spent = sched['spent']
            mode = 'enforced (observed meter sample)'
        pending = sched.get('pending', 0.0)
        ceiling = (value - reserve) if isinstance(value, (int, float)) \
            else None
        over = False
        if mode.startswith('enforced') and isinstance(value, (int, float)) \
                and isinstance(ceiling, (int, float)):
            over = ((spent if spent is not None else 0.0) + pending) > \
                ceiling
        row = {'limit_id': lid, 'unit': limit.get('unit'),
               'declared_enforcement': limit.get('enforcement'),
               'effective_mode': mode,
               'counter_source': source,
               'limit': value, 'reserve': reserve, 'dispatch_ceiling': ceiling,
               'spent': spent, 'spent_source': ('journal' if source ==
                                                'journal' else 'host meter'),
               'asserted_latest': sched.get('asserted_latest'),
               'pending': pending, 'over_ceiling': over,
               'host_capability': cap}
        rows.append(row)
        if over and refusal is None:
            refusal = {'rule': 'limit-exhausted',
                       'detail': ('enforced limit %r over its dispatchable '
                                  'ceiling: spent %s + pending %s > %s '
                                  '(limit %s - reserve %s)%s' %
                                  (lid, spent if spent is not None else 0.0,
                                   pending, ceiling, value, reserve,
                                   '' if spent is not None else
                                   ' [unmetered spend: pending-side '
                                   'enforcement only]'))}
    return {'limits': rows, 'refusal': refusal,
            'host_capabilities': caps,
            'unsupported_counters': [r['limit_id'] for r in rows
                                     if r['counter_source'] is None]}


# ------------------------------------------------------------- exhaustion

def _limit_observations(events):
    """Latest LIMIT-grammar observation per limit id."""
    latest = {}
    for event in events:
        if not isinstance(event, dict) or event.get('type') != 'observation':
            continue
        match = EXHAUST_GRAMMAR.match(event.get('statement') or '')
        if match:
            latest[match.group(2)] = {'state': match.group(1),
                                      'detail': match.group(3) or '',
                                      'seq': event.get('seq')}
    return latest


def record_exhaustion(plan_dir, limit_id, detail='', recover=False):
    """Persist the incomplete checkpoint: a LIMIT observation (asserted).

    The journal + snapshot ARE the checkpoint — nothing is completed by
    exhaustion, and the observation type can never satisfy a criterion
    (the ledger counts gate_run events only). The limit must be declared
    in the contract: no counter is invented.
    """
    state = 'recovered' if recover else 'exhausted'
    rec = ledger.PlanRecords(plan_dir)
    known = {limit['id'] for limit in rec.contract.get(
        'resource_envelope', {}).get('limits', [])}
    if limit_id not in known:
        raise ResourcesError(
            'limit %r is not declared in the contract — exhaustion of an '
            'undeclared counter is never recorded' % limit_id)
    lock = ledger.CooperativeLock(plan_dir).acquire()
    try:
        writer = ledger.Writer(rec, lock)
        return writer.append(
            'observation',
            {'statement': 'LIMIT: %s %s%s' % (state, limit_id,
                                              ': %s' % detail if detail
                                              else ''),
             'trust': 'asserted'},
            actor={'kind': 'helper', 'identity': RESOURCES_IDENTITY},
            idempotent=True)
    finally:
        lock.release()


def dispatch_hold(contract, events):
    """The resource hold derived from the records, or None.

    Active while the latest LIMIT observation on an ENFORCED limit says
    exhausted; ``recovered`` clears it. Advisory limits never hold
    dispatch — they are surfaced, not enforced.
    """
    enforced = {limit['id'] for limit in contract.get(
        'resource_envelope', {}).get('limits', [])
        if limit.get('enforcement') == 'enforced'}
    hold = None
    for lid, obs in _limit_observations(events).items():
        if lid in enforced and obs['state'] == 'exhausted':
            if hold is None or (obs.get('seq') or 0) > (hold.get('via_seq')
                                                        or 0):
                hold = {'limit_id': lid, 'reason': obs['detail'],
                        'via_seq': obs.get('seq')}
    return hold


# ------------------------------------------------------ cancellation settle

def _settlements(events):
    """Settlement observations by key: {key: [(disposition, seq)]}."""
    found = {}
    for event in events:
        if not isinstance(event, dict) or event.get('type') != 'observation':
            continue
        match = RESERVATION_GRAMMAR.match(event.get('statement') or '')
        if match:
            found.setdefault(match.group(1), []).append(
                (match.group(2), event.get('seq')))
    return found


def settle_cancellation(plan_dir, key, disposition, detail=''):
    """Settle an in-flight reservation EXACTLY ONCE.

    Identical replay is idempotent (content-keyed dedup); a second
    settlement with a DIFFERENT disposition is the double-charge ambiguity
    and is refused, never arbitrated.
    """
    if disposition not in SETTLEMENTS:
        raise ResourcesError('disposition %r outside %s' %
                             (disposition, '/'.join(SETTLEMENTS)))
    rec = ledger.PlanRecords(plan_dir)
    events = rec.archived_events() + rec.read_journal()[0]
    for prior_disposition, _seq in _settlements(events).get(key, []):
        if prior_disposition != disposition:
            raise ResourcesError(
                'reservation %r already settled as %r — settling again as '
                '%r is the double-charge ambiguity; refuse and investigate'
                % (key, prior_disposition, disposition))
    lock = ledger.CooperativeLock(plan_dir).acquire()
    try:
        writer = ledger.Writer(rec, lock)
        return writer.append(
            'observation',
            {'statement': 'RESERVATION: %s: %s%s' % (key, disposition,
                                                     ': %s' % detail
                                                     if detail else ''),
             'trust': 'asserted'},
            actor={'kind': 'helper', 'identity': RESOURCES_IDENTITY},
            idempotent=True)
    finally:
        lock.release()


def settlement_state(events, key):
    """The settled disposition of a reservation, or None when in flight."""
    seen = _settlements(events).get(key, [])
    if not seen:
        return None
    dispositions = {d for d, _seq in seen}
    if len(dispositions) > 1:
        raise ResourcesError(
            'reservation %r carries conflicting settlements %s — the '
            'accounting is ambiguous until a human reconciles it' %
            (key, sorted(dispositions)))
    return {'disposition': seen[-1][0], 'seq': seen[-1][1]}


def pending_after_settlements(contract, events):
    """Pending impact minus released (cancelled) reservations.

    Mirrors scheduler's pending loop over authorized adaptations exactly
    (every authorized adaptation's positive declared impact, matched by
    unit), then removes reservations settled ``released`` (the cancelled
    child never consumed the budget). With zero settlements the result
    equals :func:`scheduler.envelope_status` pending exactly — the drift
    guard the tests pin.
    """
    limits = contract.get('resource_envelope', {}).get('limits', [])
    pending = {limit['id']: 0.0 for limit in limits}
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
        state = settlement_state(events, 'seq-%s' % event.get('seq'))
        if state and state['disposition'] == 'released':
            continue  # cancelled in flight: never consumed
        for limit in limits:
            if limit.get('unit') == unit:
                pending[limit['id']] += declared
    return pending


# ------------------------------------------- addon-provided abilities (v7)

DETECT_TIMEOUT_S = 10


def _run_detect(command, timeout=DETECT_TIMEOUT_S):
    """Run one descriptor detect command: argv, no shell, read-only, bounded.

    Returns (present, stdout, reason). A missing binary is "not installed",
    never an error.
    """
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return False, '', 'detect command unparsable (%s)' % exc
    import shutil
    resolved = shutil.which(argv[0])
    if resolved is None:
        return False, '', '%s not installed' % argv[0]
    if not os.path.isabs(resolved):
        # a relative PATH entry (".") would let a repository plant the tool
        return False, '', ('%s resolved through a relative PATH entry; '
                           'refused' % argv[0])
    argv[0] = resolved
    try:
        proc = subprocess.run(argv, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=False)
    except FileNotFoundError:
        return False, '', '%s not installed' % argv[0]
    except subprocess.TimeoutExpired:
        return False, '', 'detect timed out after %ss' % timeout
    except OSError as exc:
        return False, '', 'detect failed to start (%s)' % exc
    out = proc.stdout.decode('utf-8', 'replace')
    if proc.returncode != 0:
        return False, out, 'detect exited %d' % proc.returncode
    return True, out, None


def _read_interface(spec, stdout):
    """The integer interface named by ``interface_from``, or None."""
    try:
        if spec.startswith('json:'):
            value = json.loads(stdout).get(spec[5:])
        elif spec.startswith('regex:'):
            match = re.search(spec[6:], stdout)
            value = match.group(1) if match else None
        elif spec.startswith('file-json:'):
            path, field = spec[10:].rsplit('#', 1)
            with open(os.path.expanduser(path), encoding='utf-8') as fh:
                value = json.load(fh).get(field)
        else:
            return None
        if isinstance(value, bool):
            return None
        return int(value)
    except (ValueError, TypeError, AttributeError, OSError, IndexError):
        return None


VERSION_IN_TEXT = re.compile(r'\bv?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)\b')


def _observed_version(det, stdout, repo_root=None):
    """The installed product's version as a tag (vX.Y.Z), or None.

    From a detect command's output, or from the ``version:`` frontmatter of
    a detected SKILL.md path (a vendored skill). Informative only: it feeds
    the registry back-fill and verify's mismatch warning, never a gate.
    """
    text = stdout or ''
    if 'paths' in det:
        base = repo_root or os.getcwd()
        for path in det['paths']:
            full = os.path.expanduser(path) if path.startswith('~/') \
                else os.path.join(base, path)
            if path.endswith('SKILL.md') and os.path.isfile(full):
                with open(full, encoding='utf-8', errors='replace') as fh:
                    head = fh.read(4096)
                match = re.search(r'(?m)^version:\s*["\']?([^"\'\s]+)', head)
                text = match.group(1) if match else ''
                break
    found = VERSION_IN_TEXT.search(text)
    return 'v' + found.group(1) if found else None


def addon_status(key, repo_root=None, addons_dir=None, timeout=DETECT_TIMEOUT_S):
    """Detection verdict for ONE enabled addon (opens its descriptor).

    ``{"descriptor_ok", "detected", "interface", "compatible", "provides",
    "reason"}`` — ``compatible`` is True only when the descriptor is valid,
    detection succeeded and the interface major matches what the
    descriptor pins (or the product publishes none).
    """
    doc, errs = dwp_config.load_descriptor(
        key, addons_dir or dwp_config.ADDONS_DIR)
    verdict = {'descriptor_ok': not errs, 'detected': False,
               'interface': None, 'compatible': False, 'provides': [],
               'reason': None, 'version': None}
    if errs:
        verdict['reason'] = 'invalid descriptor (%s)' % errs[0]
        return verdict
    verdict['provides'] = list(doc.get('provides_abilities', []))
    det = doc['detect']
    stdout = ''
    if 'command' in det:
        present, stdout, reason = _run_detect(det['command'], timeout)
    else:
        base = repo_root or os.getcwd()
        present = any(os.path.isfile(os.path.expanduser(p) if p.startswith('~/')
                                     else os.path.join(base, p))
                      for p in det['paths'])
        reason = None if present else 'none of %s present' % ', '.join(det['paths'])
    verdict['detected'] = present
    if not present:
        verdict['reason'] = reason
        return verdict
    verdict['version'] = _observed_version(det, stdout, repo_root)
    pinned = (doc.get('product') or {}).get('interface')
    if pinned is None:
        verdict['compatible'] = True
        return verdict
    spec = det.get('interface_from')
    found = _read_interface(spec, stdout) if spec else None
    verdict['interface'] = found
    if found is None:
        verdict['reason'] = 'interface unreadable; treated as not available'
    elif found != pinned:
        verdict['reason'] = ('unknown interface major %d (pinned %d); treated '
                             'as not available' % (found, pinned))
    else:
        verdict['compatible'] = True
    return verdict


def effective_abilities(host_caps=None, dwp_root=None, home=None,
                        addons_dir=None, timeout=DETECT_TIMEOUT_S):
    """Host abilities united with what enabled-and-healthy addons provide.

    Computed per call from the host declaration, the registry
    (spec/CONFIG.md) and live detection — never persisted into a plan. An
    addon contributes only when it is enabled AND its descriptor is valid
    AND detection succeeds AND the interface major is compatible; every
    other outcome is exactly one warning and no contribution. No addon file
    is opened for a key the registry does not enable.
    """
    caps = host_capabilities(host_caps)  # closed set; unknown keys refused
    sources = {name: (['host'] if caps.get(name) else []) for name in caps}
    keys = dwp_config.addon_keys(addons_dir or dwp_config.ADDONS_DIR)
    view, warnings = dwp_config.resolve_addons(
        dwp_config.load_files(dwp_root, home), keys)
    enabled = sorted(k for k, v in view.items() if v['enabled'])
    repo_root = os.path.dirname(dwp_root) if dwp_root else None
    addons = {}
    deferred = {}
    for key in enabled:
        verdict = addon_status(key, repo_root, addons_dir, timeout)
        addons[key] = verdict
        if not verdict['detected'] and verdict['descriptor_ok'] and \
                view[key].get('note'):
            # F-05: accepted with a recorded deferral - reported, not warned
            deferred[key] = view[key]['note']
            continue
        if verdict['compatible']:
            for name in verdict['provides']:
                if name not in HOST_CAPABILITIES:  # never invented
                    warnings.append('addon %s: unknown ability %r refused'
                                    % (key, name))
                    continue
                caps[name] = True
                sources[name].append('addon:' + key)
        elif verdict['provides']:
            warnings.append('addon %s: enabled but contributes nothing — %s'
                            % (key, verdict['reason']))
        elif verdict['reason'] and not verdict['descriptor_ok']:
            warnings.append('addon %s: %s' % (key, verdict['reason']))
    return {'abilities': caps, 'sources': sources, 'addons': addons,
            'deferred': deferred, 'warnings': warnings, 'persisted': False}


# ------------------------------------------------------------ routing

def routing_posture(contract, host_caps=None):
    """Fixed-model default; switching needs grant AND host ability."""
    caps = host_caps if host_caps is not None else dict(CAPABILITY_FLOOR)
    granted = set(contract.get('permissions', {}).get('granted', []))
    missing = []
    if 'model_routing' not in granted:
        missing.append('contract grant model_routing')
    if not caps.get('model_routing'):
        missing.append('host capability model_routing')
    model = ('switching_authorized' if not missing else 'fixed_model')
    parallel_missing = []
    if 'agent_delegation' not in granted:
        parallel_missing.append('contract grant agent_delegation')
    if not caps.get('subagents'):
        parallel_missing.append('host capability subagents')
    parallel = ('parallel_authorized' if not parallel_missing
                else 'sequential_only')
    return {'model': {'posture': model, 'missing': missing,
                      'never_an_efficacy_claim': True},
            'parallel': {'posture': parallel, 'missing': parallel_missing}}


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
        events = list(writer.events)
        lock.release()

        # 1-2. capability negotiation: closed set, floor is a posture
        try:
            host_capabilities({'time_travel': True})
            check('unknown host capability refused', False)
        except ResourcesError:
            check('unknown host capability refused', True)
        floor = host_capabilities()
        check('the minimal host is all-False, never an error',
              not any(floor.values()) and len(floor) == len(HOST_CAPABILITIES))
        merged = host_capabilities({'meter_spend': 1})
        check('unstated capabilities default False (no invention)',
              merged['meter_spend'] and not merged['model_routing'])

        # 3-6. counter sources and effective modes
        report = envelope_report(contract, events, floor)
        modes = {row['limit_id']: row['effective_mode']
                 for row in report['limits']}
        check('spend limit on a meterless host is honestly advisory',
              modes['spend_usd'].startswith('advisory (host cannot meter'),
              modes['spend_usd'])
        check('a limit the human declared advisory stays advisory, '
              'whatever the counters say',
              modes['wall_clock_h'] == 'advisory (declared advisory)',
              modes['wall_clock_h'])
        enforced_wall = json.loads(json.dumps(contract))
        enforced_wall['resource_envelope']['limits'][1].update(
            enforcement='enforced')
        report = envelope_report(enforced_wall, events, floor)
        wall = next(row for row in report['limits']
                    if row['limit_id'] == 'wall_clock_h')
        check('wall-clock is journal-computed, no host needed',
              wall['effective_mode'].startswith('enforced (journal') and
              wall['counter_source'] == 'journal',
              wall['effective_mode'])
        check('journal-computed spent derives from the event span',
              isinstance(wall['spent'], float) and wall['spent'] >= 0
              and wall['spent'] < 1.0,
              repr(wall['spent']))
        host = host_capabilities({'meter_spend': True})
        report = envelope_report(contract, events, host)
        spend = next(row for row in report['limits']
                     if row['limit_id'] == 'spend_usd')
        check('metered host without a sample is pending-only, not free',
              spend['effective_mode'].startswith('enforced-pending-only') and
              spend['spent'] is None, spend['effective_mode'])
        # an observed sample flips it to enforced with the meter's value
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        os.makedirs(os.path.join(plan, 'analysis_results'), exist_ok=True)
        with open(os.path.join(plan, 'analysis_results', 'meter.json'),
                  'w', encoding='utf-8') as fh:
            json.dump({'spend_usd': 8.5}, fh)
        writer.append('resource_sample',
                      {'source': 'selftest-meter', 'limit_id': 'spend_usd',
                       'value': 8.5, 'unit': 'USD'},
                      actor={'kind': 'host_adapter',
                             'identity': 'selftest-meter'},
                      trust='observed',
                      evidence_path='analysis_results/meter.json')
        events = list(writer.events)
        lock.release()
        report = envelope_report(contract, events, host)
        spend = next(row for row in report['limits']
                     if row['limit_id'] == 'spend_usd')
        check('observed sample enforces with the metered value',
              spend['effective_mode'].startswith('enforced (observed') and
              spend['spent'] == 8.5, repr(spend['spent']))

        # 7-8. reserves: representation and ceiling
        reserved = json.loads(json.dumps(contract))
        reserved['resource_envelope']['limits'][0]['reserve'] = 3995
        report = envelope_report(reserved, events, host)
        spend = next(row for row in report['limits']
                     if row['limit_id'] == 'spend_usd')
        check('a reserve the spent cannot fit flips the refusal',
              spend['dispatch_ceiling'] == 5 and spend['over_ceiling'] and
              report['refusal']['rule'] == 'limit-exhausted',
              repr(spend['dispatch_ceiling']))
        bad = json.loads(json.dumps(contract))
        bad['resource_envelope']['limits'][0]['reserve'] = 9999
        check('a reserve above the limit is an invalid contract '
              '(runtime-only ceiling: it depends on the sibling limit)',
              any('reserve %s exceeds the limit' % 9999 in e for e in
                  contract_v6.contract_errors(bad)))
        check('a non-numeric reserve is rejected by both halves',
              _schema_rejects_reserve('5'))

        # 9-11. exhaustion: declared-only records, hold, recovery
        try:
            record_exhaustion(plan, 'not_a_limit')
            check('exhaustion of an undeclared limit refused', False)
        except ResourcesError:
            check('exhaustion of an undeclared limit refused', True)
        record_exhaustion(plan, 'spend_usd', 'commit-plus-pending over')
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        events = list(writer.events)
        lock.release()
        hold = dispatch_hold(contract, events)
        check('exhaustion holds dispatch on the enforced limit',
              hold and hold['limit_id'] == 'spend_usd')
        states = ledger.criterion_states(contract, events, 'T-implement')
        check('an exhaustion observation never satisfies a criterion',
              not states[0].get('satisfied'))
        record_exhaustion(plan, 'spend_usd', 'meter back under ceiling',
                          recover=True)
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        events = list(writer.events)
        lock.release()
        check('recovery clears the hold', dispatch_hold(contract, events)
              is None)

        # 12-14. cancellation settlement
        first = settle_cancellation(plan, 'seq-42', 'released',
                                    'child cancelled mid-flight')
        again = settle_cancellation(plan, 'seq-42', 'released',
                                    'child cancelled mid-flight')
        check('identical settlement replay is idempotent',
              first['seq'] == again['seq'],
              'seq %r vs %r' % (first.get('seq'), again.get('seq')))
        try:
            settle_cancellation(plan, 'seq-42', 'committed', 'late report')
            check('conflicting settlement refused (double charge)', False)
        except ResourcesError:
            check('conflicting settlement refused (double charge)', True)
        zero = pending_after_settlements(contract, events)
        sched_pending = {row['limit_id']: row['pending'] for row in
                         scheduler.envelope_status(contract, events)}
        check('zero settlements reproduce scheduler pending exactly',
              zero == sched_pending, '%r vs %r' % (zero, sched_pending))
        # an authorized adaptation with a released settlement stops pending
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        adapt = writer.append(
            'adaptation',
            {'kind': 'retry', 'trigger_observation': 1,
             'evidence_artifact': 'gates/T-implement/001-true.log',
             'hypothesis': 'the gate failed on a missing dependency',
             'action': 'install the dependency and retry the same gate',
             'rationale': 'the failure cause is environmental, not a '
                          'criterion change',
             'authority': 'scheduling.max_retries_per_gate',
             'affected_tasks': ['T-implement'], 'affected_criteria': [],
             'evidence_invalidated': [], 'evidence_preserved': [],
             'resource_impact': {'declared': 2.0, 'unit': 'USD'},
             'decision': 'authorized'},
            actor={'kind': 'agent', 'identity': 'selftest'})
        events = list(writer.events)
        lock.release()
        with_pending = pending_after_settlements(contract, events)
        check('an authorized in-flight adaptation adds its impact',
              with_pending['spend_usd'] == sched_pending['spend_usd'] + 2.0,
              repr(with_pending['spend_usd']))
        settle_cancellation(plan, 'seq-%s' % adapt.get('seq'),
                            'released', 'cancelled before consuming')
        lock = ledger.CooperativeLock(plan).acquire()
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        events = list(writer.events)
        lock.release()
        released = pending_after_settlements(contract, events)
        check('a released settlement subtracts exactly once',
              released['spend_usd'] == sched_pending['spend_usd'],
              repr(released['spend_usd']))

        # 15-17. routing posture: grant AND ability, never invention
        posture = routing_posture(contract, floor)
        check('fixed-model default names both missing sides',
              posture['model']['posture'] == 'fixed_model' and
              len(posture['model']['missing']) == 2)
        grants = json.loads(json.dumps(contract))
        grants['permissions']['granted'].append('model_routing')
        posture = routing_posture(grants, floor)
        check('a grant without host ability stays fixed, reason named',
              posture['model']['posture'] == 'fixed_model' and
              'host capability model_routing' in posture['model']['missing'])
        posture = routing_posture(grants,
                                  host_capabilities({'model_routing': 1}))
        check('grant plus host ability authorizes switching',
              posture['model']['posture'] == 'switching_authorized')
        posture = routing_posture(contract, floor)
        check('parallel dispatch needs delegation grant and subagents',
              posture['parallel']['posture'] == 'sequential_only')

        # 18. unknown unit family: advisory with the unit named
        weird = json.loads(json.dumps(contract))
        weird['resource_envelope']['limits'][0]['unit'] = 'vibes'
        report = envelope_report(weird, events, host)
        row = next(r for r in report['limits'] if r['unit'] == 'vibes')
        check('an unknown counter family is advisory, never invented',
              row['effective_mode'].startswith('advisory (counter family') and
              report['unsupported_counters'] == [row['limit_id']],
              row['effective_mode'])

    # 19. v7 effective abilities: host ∪ enabled-and-healthy addons
    with tempfile.TemporaryDirectory() as tmp:
        addons = os.path.join(tmp, 'addons')
        bindir = os.path.join(tmp, 'bin')
        dwp = os.path.join(tmp, 'repo', '.dwp')
        home = os.path.join(tmp, 'home')
        for d in (bindir, dwp, home):
            os.makedirs(d)
        desc_url = dwp_config.DESCRIPTOR_SCHEMA_URL

        def descriptor(key, command, interface=1, provides=('subagents',)):
            os.makedirs(os.path.join(addons, key))
            with open(os.path.join(addons, key, 'addon.json'), 'w') as fh:
                json.dump({'schema': desc_url, 'key': key,
                           'product': {'repo': 'Example/' + key,
                                       'tag': 'v0.1.0', 'interface': interface},
                           'detect': {'command': command,
                                      'interface_from': 'json:interface'},
                           'provides_abilities': list(provides),
                           'requires_grants': ['agent_delegation'],
                           'transport': 'headless'}, fh)

        def fake(name, body):
            path = os.path.join(bindir, name)
            with open(path, 'w') as fh:
                fh.write('#!/bin/sh\n' + body + '\n')
            os.chmod(path, 0o755)

        fake('fake-ak', 'echo \'{"interface": 1}\'')
        fake('fake-v2', 'echo \'{"interface": 2}\'')
        descriptor('good', 'fake-ak doctor --json',
                   provides=('subagents', 'cancel_children'))
        descriptor('newer', 'fake-v2 doctor --json', provides=('subagents', 'model_routing'))
        descriptor('absent', 'no-such-binary-dwp --version')
        os.makedirs(os.path.join(addons, 'broken'))
        with open(os.path.join(addons, 'broken', 'addon.json'), 'w') as fh:
            fh.write('{not json')
        old_path = os.environ.get('PATH', '')
        os.environ['PATH'] = bindir + os.pathsep + old_path
        try:
            eff = effective_abilities(None, dwp, home, addons)
            check('v7: nothing enabled = the all-False minimal host',
                  not any(eff['abilities'].values()) and not eff['warnings']
                  and eff['persisted'] is False, repr(eff))
            with open(os.path.join(dwp, 'config.json'), 'w') as fh:
                json.dump({'addons': {k: {'enabled': True} for k in
                                      ('good', 'newer', 'absent')}}, fh)
            eff = effective_abilities({'telemetry': True}, dwp, home, addons)
            check('v7: an enabled, detected, compatible addon contributes',
                  eff['abilities']['subagents'] and
                  eff['abilities']['cancel_children'] and
                  eff['sources']['subagents'] == ['addon:good'], repr(eff))
            check('v7: host abilities survive the union',
                  eff['sources']['telemetry'] == ['host'], repr(eff['sources']))
            check('v7: an unknown interface major contributes nothing',
                  not eff['abilities']['model_routing'] and any(
                      'unknown interface major 2' in w for w in eff['warnings']),
                  repr(eff['warnings']))
            check('v7: a missing binary is one warning, never an error',
                  sum('absent' in w for w in eff['warnings']) == 1 and
                  any('not installed' in w for w in eff['warnings']),
                  repr(eff['warnings']))
            check('v7: a disabled addon is never opened (broken JSON unread)',
                  'broken' not in eff['addons'] and
                  not any('broken' in w for w in eff['warnings']))
            with open(os.path.join(dwp, 'config.json'), 'w') as fh:
                json.dump({'addons': {'good': {'enabled': False}}}, fh)
            eff = effective_abilities(None, dwp, home, addons)
            check('v7: disabling the addon removes its abilities',
                  not eff['abilities']['subagents'], repr(eff))
        finally:
            os.environ['PATH'] = old_path
    return (not failures, failures, probes[0])


def _schema_rejects_reserve(value):
    """Both halves reject a malformed reserve: schema and runtime.

    (The reserve <= limit CEILING is runtime-only semantics — it depends
    on the sibling field's value, which draft 2020-12 cannot express —
    the same category as graph integrity: check-schema-contract.py marks
    it runtime_only.)
    """
    contract = contract_v6._selftest_contract()
    contract['resource_envelope']['limits'][0]['reserve'] = value
    runtime_bad = bool(contract_v6.contract_errors(contract))
    schema_path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'spec', 'schema',
        'plan-contract-v6.schema.json')
    try:
        import jsonschema
        schema = json.load(open(schema_path))
        schema_bad = bool(list(jsonschema.Draft202012Validator(
            schema).iter_errors(contract)))
    except ImportError:
        schema_bad = runtime_bad  # dev-only check; runtime half still proven
    return runtime_bad and schema_bad



# --------------------------------------------------------------------- CLI

def main(argv):
    usage = ('usage: resources.py --plan DIR {report [--caps JSON] | routing '
             '[--caps JSON] | abilities [--caps JSON] (add --host-only to '
             'ignore enabled addons) | capabilities [--json JSON] | exhaust --limit '
             'ID [--detail D] | recover --limit ID [--detail D] | settle '
             '--key K --disposition released|committed [--detail D] | hold | '
             'self-test}')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--plan')
    parser.add_argument('command')
    parser.add_argument('--caps', default='{}')
    parser.add_argument('--host-only', action='store_true')
    parser.add_argument('--limit', dest='limit_id')
    parser.add_argument('--key')
    parser.add_argument('--disposition')
    parser.add_argument('--detail', default='')
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print(usage)
        return 2
    if args.command in ('-h', '--help'):
        print(usage)
        return 0
    try:
        if args.command == 'self-test':
            ok, failures, probes = self_test()
            for failure in failures:
                print('FAIL', failure)
            print('self-test: %s (%d probes)' %
                  ('OK' if ok else 'FAILED', probes))
            return 0 if ok else 1
        if args.command == 'capabilities':
            print(json.dumps(host_capabilities(json.loads(args.caps)),
                             sort_keys=True, indent=2))
            return 0
        if not args.plan:
            print(usage)
            return 2
        plan = ledger.find_plan_dir(args.plan)
        host = host_capabilities(json.loads(args.caps))
        effective = effective_abilities(
            host, None if args.host_only else dwp_config.find_dwp_root(plan))
        for line in effective['warnings']:
            print('WARNING: %s' % line, file=sys.stderr)
        caps = effective['abilities']
        rec = ledger.PlanRecords(plan)
        events = rec.archived_events() + rec.read_journal()[0]
        if args.command == 'report':
            print(json.dumps(envelope_report(rec.contract, events, caps),
                             sort_keys=True, indent=2))
            return 0
        if args.command == 'routing':
            posture = routing_posture(rec.contract, caps)
            posture['ability_sources'] = {
                k: v for k, v in effective['sources'].items() if v}
            print(json.dumps(posture, sort_keys=True, indent=2))
            return 0
        if args.command == 'abilities':
            print(json.dumps(effective, sort_keys=True, indent=2))
            return 0
        if args.command == 'hold':
            hold = dispatch_hold(rec.contract, events)
            if hold:
                print('HOLD: limit %s (via seq %s) %s' %
                      (hold['limit_id'], hold.get('via_seq'),
                       hold.get('reason') or ''))
                return 1
            print('OK: no resource hold')
            return 0
        if args.command == 'exhaust':
            if not args.limit_id:
                print(usage)
                return 2
            event = record_exhaustion(plan, args.limit_id, args.detail)
            print('OK: exhaustion recorded at seq %s' % event.get('seq'))
            return 0
        if args.command == 'recover':
            if not args.limit_id:
                print(usage)
                return 2
            event = record_exhaustion(plan, args.limit_id, args.detail,
                                      recover=True)
            print('OK: recovery recorded at seq %s' % event.get('seq'))
            return 0
        if args.command == 'settle':
            if not (args.key and args.disposition):
                print(usage)
                return 2
            event = settle_cancellation(plan, args.key, args.disposition,
                                        args.detail)
            print('OK: settlement recorded at seq %s' % event.get('seq'))
            return 0
    except ResourcesError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    except ledger.LedgerError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
