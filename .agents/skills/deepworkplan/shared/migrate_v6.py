#!/usr/bin/env python3
"""v5 -> v6 plan migration: explicit, previewed, one-directional (RFC 9.3).

usage: migrate_v6.py --plan DIR {preview | migrate --authority WHO
                               [--note TEXT] | rollback [--force]
                               | self-test}

A v5 plan is never migrated silently (RFC 9.2): the v6 reader accepts it
read-only forever, and the ONLY thing that turns it into a v6 plan is this
helper, run on purpose. The sequence is preview -> migrate -> (optional)
rollback:

* ``preview`` - integrity check + task mapping + re-evidence list. It
  refuses lossy inputs (unknown task status, a torn manifest/state pair)
  and writes ``migration_v5/PREVIEW.json``, the durable record of what
  migration would do. No v5 byte is touched.
* ``migrate`` - the guarded, resumable sequence, each phase atomic and
  recorded in ``migration_v5/PHASE.json`` so an interruption at ANY point
  is recovered by running it again: backup -> contract synthesis -> the
  manifest swap (the one sanctioned rewrite of a v5 manifest, only after
  the backup exists) -> journal events (a pre_authorization approval
  citing the v5 source digest, one fingerprint-less task_start per
  non-pending task, every v5 gate record imported with its provenance,
  and a migration observation) -> the v6 state projection.
* ``rollback`` - restores the v5 manifest and state byte-identically from
  the verified backup and removes the v6 artifacts. It refuses - until
  ``--force`` - when the journal carries MORE than the migration's own
  events: post-migration v6 work is real history and is not silently
  deleted.

Evidence honesty is the whole design: a v5 gate record that still resolves
is IMPORTED (``imported`` - a matched external source, with provenance),
never observed; a completed task whose records all pass closes its
synthesized criterion on that label, while anything weaker (failed gate,
missing or dangling evidence, an in-progress task) becomes a
RE-EVIDENCE criterion whose bar is ``observed`` - blocked by default until
the gates re-run under v6 execution (D3-5). The reverse direction does
not exist: a v6 plan under the v5 runner is unsupported by contract.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402  (sibling module, same directory)
import ledger  # noqa: E402  (sibling module, same directory)

MIGRATION_NAME = 'migration_v5'
V5_MANIFEST_URLS = tuple(
    'https://deepworkplan.com/schema/plan-manifest/%s.json' % v
    for v in ('v1', 'v2', 'v5'))
STATUSES = ('pending', 'in_progress', 'completed')
CLASSES = ('imported', 're_evidence', 'pending')
PHASES = ('backup', 'contract', 'manifest', 'journal', 'project')


class MigrationError(Exception):
    """Operator-visible refusal; exit code 1."""


# ------------------------------------------------------------------ helpers

def _atomic_write(path, text):
    ledger._atomic_write(path, text)


def _read_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _sha256_file(path):
    return ledger._hash_file(path)


def _slug(text, limit=24):
    slug = ''.join(c if c.isalnum() else '-' for c in text.lower())
    parts = [p for p in slug.split('-') if p]
    return '-'.join(parts)[:limit].strip('-') or 'task'


def _task_id(number, title):
    return 'T-%02d-%s' % (number, _slug(title))


def _criterion_id(number, title):
    return 'AC-t%02d-%s' % (number, _slug(title))


def _resolves(plan_dir, evidence, repo_root):
    if not evidence:
        return False
    candidates = [os.path.join(plan_dir, evidence)]
    if repo_root:
        candidates.append(os.path.join(repo_root, evidence))
    if os.path.isabs(evidence):
        candidates.insert(0, evidence)
    return any(os.path.isfile(c) for c in candidates)


def load_v5(plan_dir):
    """Read and generation-check the v5 pair. Returns (manifest, state)."""
    folder = os.path.basename(os.path.normpath(plan_dir))
    manifest_path = os.path.join(plan_dir, 'manifest.json')
    state_path = os.path.join(plan_dir, 'state.json')
    if not os.path.isfile(manifest_path) or not os.path.isfile(state_path):
        raise MigrationError(
            'migration needs a materialized v5 plan (manifest.json + '
            'state.json) - a plan folder without both is not migratable')
    manifest = _read_json(manifest_path)
    url = manifest.get('schema')
    if url == ledger.MANIFEST_SCHEMA_URL or \
            os.path.isfile(os.path.join(plan_dir, 'contract.json')):
        raise MigrationError(
            '%s is already a v6 plan (v6 manifest or contract.json '
            'present) - migration is one-directional; run rollback first '
            'if this state is unexpected' % folder)
    if url not in V5_MANIFEST_URLS:
        raise MigrationError(
            'manifest.json carries %r - not a v1/v2/v5 plan-manifest '
            'generation; this helper migrates v5 plans only' % url)
    state = _read_json(state_path)
    if manifest.get('name') != folder:
        raise MigrationError(
            'manifest name %r does not match the plan folder %r - a torn '
            'identity is lossy and is not migrated' %
            (manifest.get('name'), folder))
    if state.get('plan') != folder:
        raise MigrationError(
            'state.json plan %r does not match the plan folder %r' %
            (state.get('plan'), folder))
    return manifest, state


# The preview cannot know the real authority, so it anchors its recorded
# contract_id to this placeholder. migrate re-synthesizes under the same
# placeholder and compares: the anchor is a function of the v5 bytes AND
# on-disk evidence resolution only, so a changed world is caught even when
# the manifest/state digest (which covers just the record pair) is intact.
PREVIEW_AUTHORITY = '(set at migrate)'


def source_digest(manifest, state):
    """Hex64 over the canonical v5 pair - the pre-authorization digest."""
    blob = json.dumps({'manifest': manifest, 'state': state},
                      sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(blob).hexdigest()


def analyze(plan_dir, repo_root=None):
    """Integrity check + full mapping of the LIVE v5 pair."""
    manifest, state = load_v5(plan_dir)
    return analyze_pair(manifest, state, plan_dir, repo_root)


def analyze_pair(manifest, state, plan_dir, repo_root=None):
    """Map a v5 manifest/state pair (the live files or the verified backup).

    A resumed migration analyzes the BACKUP pair, not the live folder:
    after the manifest swap the live manifest is the v6 pointer, and the
    mapping must stay anchored to the v5 bytes that were previewed.
    """
    folder = os.path.basename(os.path.normpath(plan_dir))
    updated_at = state.get('updated_at')
    if not isinstance(updated_at, str) or \
            not contract_v6.DATETIME.match(updated_at):
        raise MigrationError(
            'state.json updated_at %r is missing or malformed - it is the '
            'deterministic anchor for the synthesized contract timestamps '
            'and cannot be invented' % updated_at)
    tasks = state.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        raise MigrationError('state.json carries no tasks - nothing to map')
    if isinstance(state.get('task_count'), int) and \
            state['task_count'] != len(tasks):
        raise MigrationError(
            'state.json task_count %s disagrees with %d task records - a '
            'torn state is lossy and is not migrated' %
            (state['task_count'], len(tasks)))
    mapped = []
    numbers = []
    for task in tasks:
        number = task.get('id')
        title = task.get('title')
        status = task.get('status')
        if not isinstance(number, int) or number < 1:
            raise MigrationError(
                'task %r has a non-integer id - unmappable' % number)
        if not isinstance(title, str) or not title.strip():
            raise MigrationError('task %s has no title - unmappable' % number)
        if status not in STATUSES:
            raise MigrationError(
                'task %s carries status %r outside %s - the v5 status '
                'axis is the thing migration maps; an unknown value is '
                'lossy and is not migrated' %
                (number, status, '/'.join(STATUSES)))
        locator = task.get('locator') or {}
        surface = 'README.md'
        if locator.get('kind') == 'file' and \
                isinstance(locator.get('value'), str) and \
                locator['value'].strip():
            surface = locator['value']
        gates = []
        reasons = []
        raw_gates = task.get('gates')
        if raw_gates is None:
            raw_gates = (task.get('outcome') or {}).get('gates') or []
        if not isinstance(raw_gates, list):
            raise MigrationError(
                'task %s gates are not a list - unmappable' % number)
        for i, gate in enumerate(raw_gates, 1):
            command = gate.get('command')
            passes = gate.get('passes')
            exit_code = gate.get('exit_code')
            evidence = gate.get('evidence')
            if not isinstance(command, str) or not command.strip():
                raise MigrationError(
                    'task %s gate %d has no command - unmappable' %
                    (number, i))
            if not isinstance(passes, bool):
                raise MigrationError(
                    'task %s gate %d carries passes=%r - not a boolean; '
                    'unmappable' % (number, i, passes))
            if not isinstance(exit_code, int) or \
                    isinstance(exit_code, bool):
                raise MigrationError(
                    'task %s gate %d carries exit_code=%r - not an '
                    'integer; unmappable' % (number, i, exit_code))
            resolvable = _resolves(plan_dir, evidence, repo_root)
            gates.append({'index': i, 'command': command,
                          'passes': passes, 'exit_code': exit_code,
                          'evidence': evidence, 'resolvable': resolvable})
            if not resolvable:
                reasons.append('gate %d evidence %r does not resolve'
                               % (i, evidence))
            elif not passes:
                reasons.append('gate %d recorded passes=false (exit %d)'
                               % (i, exit_code))
            elif exit_code != 0:
                reasons.append('gate %d claims passes=true with exit %d'
                               % (i, exit_code))
        if status == 'pending':
            klass, accepted = 'pending', ['observed']
        elif status == 'completed' and gates and not reasons:
            klass, accepted = 'imported', ['imported', 'observed']
        else:
            klass, accepted = 're_evidence', ['observed']
            if status == 'in_progress':
                reasons.insert(
                    0, 'v5 recorded the task in_progress - the remaining '
                       'work is gated under v6')
            elif not gates:
                reasons.insert(0, 'no gate records to import')
        mapped.append({
            'number': number, 'title': title, 'status': status,
            'v6_id': _task_id(number, title),
            'criterion': _criterion_id(number, title),
            'class': klass, 'accepted_evidence': accepted,
            'reasons': reasons, 'surface': surface, 'gates': gates})
        numbers.append(number)
    if len(set(numbers)) != len(numbers):
        raise MigrationError('duplicate task numbers - unmappable')
    mapped.sort(key=lambda t: t['number'])
    for previous, task in zip(mapped, mapped[1:]):
        # v5 plans execute in sequential order; the synthesized graph
        # records exactly that (a linear chain is a DAG).
        task.setdefault('prerequisite', previous['v6_id'])
    for task in mapped:
        task.setdefault('prerequisite', None)
    return {
        'plan': folder,
        'manifest': manifest, 'state': state,
        'title': manifest.get('title') or manifest.get('name') or folder,
        'updated_at': updated_at,
        'digest': source_digest(manifest, state),
        'tasks': mapped,
    }


def synthesize_contract(analysis, authority):
    """Build the deterministic v6 contract for the mapped v5 plan.

    Same v5 inputs + same authority -> byte-identical contract -> same
    contract id: an interrupted migration resumes onto the SAME identity.
    The timestamps anchor to the v5 state's last write, never the wall
    clock. Nothing is invented: scope/permissions/envelope are the
    conservative records-only posture, and substantive work after
    migration goes through an amendment (refine, revision chain).
    """
    folder = analysis['plan']
    digest12 = analysis['digest'][:12]
    criteria = []
    for task in analysis['tasks']:
        if task['class'] == 'imported':
            check = ('the imported v5 gate records resolve with exit 0 '
                     '(source digest %s)' % digest12)
        elif task['class'] == 're_evidence':
            check = ('the gates re-run under v6 execution and pass - the '
                     'v5 record did not carry closeable evidence')
        else:
            check = "the task's declared gates pass under v6 execution"
        criteria.append({
            'id': task['criterion'],
            'statement': task['title'],
            'observable_check': check,
            'accepted_evidence': list(task['accepted_evidence'])})
    tasks = []
    for task in analysis['tasks']:
        first_gate = task['gates'][0]['command'] if task['gates'] else None
        tasks.append({
            'id': task['v6_id'],
            'title': task['title'],
            'prerequisites': ([task['prerequisite']]
                              if task['prerequisite'] else []),
            'touched_surface': [task['surface']],
            'gate_intent': [{
                'criterion': task['criterion'],
                'check': (first_gate or 'v5 task record %s (no gate '
                          'recorded)' % task['surface'])[:200]}]})
    return {
        'schema': contract_v6.CONTRACT_SCHEMA_URL,
        'spec_version': '6.0.0',
        'plan': folder,
        'revision': 1,
        'created_at': analysis['updated_at'],
        'title': analysis['title'],
        'outcome': {
            'statement': 'Migrated from v5 plan %s: %s'
                         % (folder, analysis['title']),
            'success_definition': (
                'Every remaining criterion closes on its declared evidence '
                'class; imported v5 evidence stands as provenance, never '
                'as v6 observation.'),
            'out_of_scope': [
                'Re-verification of work completed under the v5 contract '
                '(imported records carry v5 provenance)']},
        'acceptance': {'criteria': criteria},
        'invariants': [],
        'scope': {
            'allowed_paths': ['.dwp/plans/%s/' % folder],
            'forbidden_operations': ['publication', 'force-push',
                                     'history-deletion']},
        'authorization': {
            'mechanism': 'pre_authorization',
            'authority': authority,
            'timestamp': analysis['updated_at'],
            'boundaries': (
                'Migrated from a v5 plan: the v5 records (source digest '
                '%s) are the recorded pre-authorization (D3-2). Scope, '
                'permissions and the resource envelope are records-only '
                'until amended through refine.' % digest12),
            'consent_checkpoints': []},
        'permissions': {
            'granted': [],
            'not_granted': list(contract_v6.CAPABILITIES)},
        'dependencies': [],
        'resource_envelope': {'limits': [{
            'id': 'v5_unmetered', 'limit': 0, 'unit': 'unspecified',
            'enforcement': 'advisory'}]},
        'tasks': tasks,
    }


def build_preview(analysis):
    """The durable preview document (deterministic: no wall clock)."""
    tasks = []
    for task in analysis['tasks']:
        tasks.append({
            'v5_id': task['number'], 'v6_id': task['v6_id'],
            'criterion': task['criterion'], 'title': task['title'],
            'status': task['status'], 'class': task['class'],
            'accepted_evidence': task['accepted_evidence'],
            'reasons': task['reasons'],
            'gates': [{'index': g['index'], 'command': g['command'],
                       'exit_code': g['exit_code'],
                       'passes': g['passes'],
                       'import_as': ('imported' if g['resolvable']
                                     else 'asserted'),
                       'evidence': g['evidence']}
                      for g in task['gates']]})
    return {
        'type': 'dwp-migration-preview',
        'plan': analysis['plan'],
        'source_digest': analysis['digest'],
        'task_mapping': tasks,
        're_evidence_criteria': [t['criterion'] for t in analysis['tasks']
                                 if t['class'] == 're_evidence'],
        'imported_criteria': [t['criterion'] for t in analysis['tasks']
                              if t['class'] == 'imported'],
        'recorded_assumptions': [
            'gate cwd and timeout_seconds are not v5 fields; imported '
            'records carry the repository root and the executor default '
            '(600s), named here rather than invented silently',
            'task_start events for non-pending tasks record NO starting '
            'fingerprint - v5 kept none, so control pairs stay honestly '
            'unavailable on migrated attempts',
        ],
    }


# ----------------------------------------------------------------- commands

def _marker_path(plan_dir):
    return os.path.join(plan_dir, MIGRATION_NAME, 'PHASE.json')


def _load_marker(plan_dir):
    path = _marker_path(plan_dir)
    if not os.path.isfile(path):
        return None
    return _read_json(path)


def _write_marker(plan_dir, marker):
    _atomic_write(_marker_path(plan_dir),
                  json.dumps(marker, sort_keys=True, indent=2) + '\n')


def _find_repo_root(start):
    """The v5 state's evidence pointers are repo-relative; find the root."""
    current = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(current, '.git')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def cmd_preview(plan_dir):
    analysis = analyze(plan_dir, repo_root=_find_repo_root(plan_dir))
    marker = _load_marker(plan_dir)
    if marker and marker.get('rolled_back') is not True and \
            marker.get('completed'):
        raise MigrationError(
            'a migration is in progress or done (phases: %s) - resume it '
            'with migrate, or rollback first' %
            ', '.join(marker.get('completed', [])))
    preview = build_preview(analysis)
    contract = synthesize_contract(analysis, authority=PREVIEW_AUTHORITY)
    errors = contract_v6.contract_errors(contract)
    if errors:
        raise MigrationError(
            'the synthesized contract does not validate: %s - refusing to '
            'preview a plan whose migration could never complete' %
            errors[0])
    preview['contract_id'] = contract_v6.compute_contract_id(contract)
    os.makedirs(os.path.join(plan_dir, MIGRATION_NAME), exist_ok=True)
    _atomic_write(os.path.join(plan_dir, MIGRATION_NAME, 'PREVIEW.json'),
                  json.dumps(preview, sort_keys=True, indent=2) + '\n')
    imported = len(preview['imported_criteria'])
    re_evidence = len(preview['re_evidence_criteria'])
    pending = sum(1 for t in analysis['tasks']
                  if t['class'] == 'pending')
    print('OK: preview for %s (%d tasks: %d imported-closable, '
          '%d re-evidence, %d pending) - contract %s'
          % (analysis['plan'], len(analysis['tasks']), imported,
             re_evidence, pending, preview['contract_id'][:12]))
    print('    re-evidence criteria (blocked by default until the gates '
          're-run under v6): %s'
          % (', '.join(preview['re_evidence_criteria']) or 'none'))
    print('    preview written to %s/PREVIEW.json - migrate with --authority'
          % MIGRATION_NAME)
    return 0


def _phase_backup(plan_dir, marker):
    backup_dir = os.path.join(plan_dir, MIGRATION_NAME, 'backup')
    os.makedirs(backup_dir, exist_ok=True)
    record = {}
    for name in ('manifest.json', 'state.json'):
        src = os.path.join(plan_dir, name)
        dst = os.path.join(backup_dir, name)
        if os.path.isfile(dst):
            if _sha256_file(dst) != _sha256_file(src):
                raise MigrationError(
                    'backup/%s exists but differs from the live v5 file - '
                    'restore it by hand or remove the stale migration '
                    'folder' % name)
        else:
            shutil.copy2(src, dst)
        record[name] = _sha256_file(dst)
    marker['backup_digests'] = record
    _atomic_write(os.path.join(backup_dir, 'BACKUP.json'),
                  json.dumps(record, sort_keys=True, indent=2) + '\n')


def _phase_contract(plan_dir, analysis, authority, marker):
    contract = synthesize_contract(analysis, authority)
    errors = contract_v6.contract_errors(contract)
    if errors:
        raise MigrationError('synthesized contract invalid: %s' % errors[0])
    cid = contract_v6.compute_contract_id(contract)
    chain = os.path.join(plan_dir, 'contracts')
    if os.path.isdir(chain):
        raise MigrationError(
            'a contracts/ revision chain exists - this plan is already '
            'under v6 amendments and is not a migration candidate')
    path = os.path.join(plan_dir, 'contract.json')
    if os.path.isfile(path):
        existing = _read_json(path)
        if existing.get('contract_id') != cid:
            raise MigrationError(
                'contract.json carries %r but this migration synthesizes '
                '%r - never rewrite a stamped contract; rollback first'
                % (existing.get('contract_id'), cid))
    else:
        _atomic_write(path, json.dumps(
            dict(contract, contract_id=cid), sort_keys=True, indent=2)
            + '\n')
    marker['contract_id'] = cid
    marker['authority'] = authority


def _phase_manifest(plan_dir, analysis, cid, marker):
    path = os.path.join(plan_dir, 'manifest.json')
    backup = os.path.join(plan_dir, MIGRATION_NAME, 'backup',
                          'manifest.json')
    if not os.path.isfile(backup):
        raise MigrationError(
            'the v5 manifest backup is missing - the swap never happens '
            'without it')
    current = _read_json(path)
    if current.get('schema') == ledger.MANIFEST_SCHEMA_URL:
        if (current.get('contract') or {}).get('id') != cid:
            raise MigrationError(
                'manifest points at %r, this migration is %r - never '
                'rewrite a pointer; rollback first'
                % ((current.get('contract') or {}).get('id'), cid))
        return  # already swapped (resumed run)
    # RFC 9.3: the ONE sanctioned rewrite of a v5 manifest, backup first.
    _atomic_write(path, json.dumps(
        {'schema': ledger.MANIFEST_SCHEMA_URL, 'plan': analysis['plan'],
         'contract': {'id': cid, 'path': 'contract.json'}},
        sort_keys=True, indent=2) + '\n')


def _phase_journal(plan_dir, analysis, authority, repo_root, note):
    lock = ledger.CooperativeLock(
        plan_dir, identity='%s pid:%d' % (ledger.LEDGER_IDENTITY,
                                          os.getpid()))
    lock.acquire()
    try:
        writer = ledger.Writer(ledger.PlanRecords(plan_dir), lock)
        writer.append(
            'approval',
            {'authority': authority, 'mechanism': 'pre_authorization',
             'plan_digest': analysis['digest']},
            actor={'kind': 'human', 'identity': authority},
            note=note or ('migrated from v5 plan %s (preview + source '
                          'digest %s are the recorded pre-authorization)'
                          % (analysis['plan'], analysis['digest'][:12])),
            idempotent=True)
        actor = {'kind': 'helper', 'identity': 'migrate_v6.py'}
        for task in analysis['tasks']:
            if task['status'] == 'pending':
                continue
            # v5 kept no starting fingerprint: recorded absent, never
            # guessed - control pairs stay honestly unavailable (D2-6).
            writer.append(
                'task_start', {'task': task['v6_id']}, actor=actor,
                note='migrated from v5 task %d (status %s)'
                     % (task['number'], task['status']),
                idempotent=True)
            for gate in task['gates']:
                writer.migrated_gate(
                    task_id=task['v6_id'],
                    criterion=task['criterion'],
                    command=gate['command'],
                    exit_code=gate['exit_code'],
                    evidence_path=(gate['evidence']
                                   if gate['resolvable'] else None),
                    source='v5 %s task %d gate %d (source digest %s)'
                           % (analysis['plan'], task['number'],
                              gate['index'], analysis['digest'][:12]),
                    cwd=repo_root or plan_dir,
                    trust='imported' if gate['resolvable'] else 'asserted')
        imported = sum(1 for t in analysis['tasks'] for g in t['gates']
                       if g['resolvable'])
        writer.append(
            'observation',
            {'statement': 'migrated from v5 plan %s: %d tasks mapped, %d '
                          'gate records imported (source digest %s)'
                          % (analysis['plan'], len(analysis['tasks']),
                             imported, analysis['digest'][:12])},
            actor=actor, trust='imported',
            evidence_path='%s/PREVIEW.json' % MIGRATION_NAME,
            idempotent=True)
        return len(writer.events)
    finally:
        lock.release()


def cmd_migrate(plan_dir, authority, note):
    if not authority:
        raise MigrationError('migrate requires --authority WHO')
    repo_root = _find_repo_root(plan_dir)
    preview_path = os.path.join(plan_dir, MIGRATION_NAME, 'PREVIEW.json')
    if not os.path.isfile(preview_path):
        raise MigrationError(
            'no preview on record - run preview first; migration without '
            'a recorded preview is exactly the silent migration RFC 9.3 '
            'forbids')
    preview = _read_json(preview_path)
    backup = os.path.join(plan_dir, MIGRATION_NAME, 'backup')
    if os.path.isfile(os.path.join(backup, 'state.json')):
        # resumed run (or marker lost mid-way): the live manifest may
        # already be the v6 pointer - anchor the mapping to the verified
        # backup pair, never to post-swap bytes
        analysis = analyze_pair(
            _read_json(os.path.join(backup, 'manifest.json')),
            _read_json(os.path.join(backup, 'state.json')),
            plan_dir, repo_root)
    else:
        analysis = analyze(plan_dir, repo_root=repo_root)
    if preview.get('source_digest') != analysis['digest']:
        raise MigrationError(
            'the v5 records changed since the preview (digest %s -> %s) - '
            'preview again; migrating stale mapping would record the '
            'wrong history'
            % (str(preview.get('source_digest'))[:12],
               analysis['digest'][:12]))
    anchor = contract_v6.compute_contract_id(
        synthesize_contract(analysis, authority=PREVIEW_AUTHORITY))
    if preview.get('contract_id') != anchor:
        raise MigrationError(
            'the v5 world changed since the preview (preview contract %s, '
            'current %s) - evidence resolution differs even though the '
            'record digest matches; preview again (rollback first if a '
            'migration is already in flight)'
            % (str(preview.get('contract_id'))[:12], anchor[:12]))
    marker = _load_marker(plan_dir) or {
        'type': 'dwp-migration-phase', 'source_digest': analysis['digest'],
        'completed': []}
    if marker.get('source_digest') != analysis['digest']:
        raise MigrationError(
            'the phase marker belongs to different v5 records - rollback '
            'or remove the stale migration folder before migrating')
    completed = list(marker.get('completed', []))
    if 'backup' not in completed:
        _phase_backup(plan_dir, marker)
        completed.append('backup')
    if 'contract' not in completed:
        _phase_contract(plan_dir, analysis, authority, marker)
        completed.append('contract')
    if 'manifest' not in completed:
        _phase_manifest(plan_dir, analysis, marker['contract_id'], marker)
        completed.append('manifest')
    marker['completed'] = completed
    _write_marker(plan_dir, marker)
    if 'journal' not in completed:
        marker['journal_events'] = _phase_journal(
            plan_dir, analysis, authority, repo_root, note)
        completed.append('journal')
        marker['completed'] = completed
        _write_marker(plan_dir, marker)
    if 'project' not in completed:
        lock = ledger.CooperativeLock(
            plan_dir, identity='%s pid:%d' % (ledger.LEDGER_IDENTITY,
                                              os.getpid()))
        lock.acquire()
        try:
            writer = ledger.Writer(ledger.PlanRecords(plan_dir), lock)
            writer.project()
        finally:
            lock.release()
        completed.append('project')
        marker['completed'] = completed
        _write_marker(plan_dir, marker)
    re_evidence = [t['criterion'] for t in analysis['tasks']
                   if t['class'] == 're_evidence']
    print('OK: %s migrated to v6 (contract %s, phases %s)'
          % (analysis['plan'], marker['contract_id'][:12],
             '+'.join(completed)))
    print('    re-evidence criteria blocked until their gates re-run '
          'under v6: %s' % (', '.join(re_evidence) or 'none'))
    return 0


def cmd_rollback(plan_dir, force):
    marker = _load_marker(plan_dir)
    if not marker or not marker.get('completed'):
        raise MigrationError(
            'no migration marker - nothing to roll back')
    backup_dir = os.path.join(plan_dir, MIGRATION_NAME, 'backup')
    record = _read_json(os.path.join(backup_dir, 'BACKUP.json'))
    for name, digest in record.items():
        path = os.path.join(backup_dir, name)
        if not os.path.isfile(path) or _sha256_file(path) != digest:
            raise MigrationError(
                'backup/%s is missing or fails its recorded digest - the '
                'v5 bytes cannot be restored verifiably; fix the backup '
                'by hand' % name)
    journal_path = os.path.join(plan_dir, ledger.JOURNAL_NAME)
    if os.path.isfile(journal_path):
        with open(journal_path, encoding='utf-8') as fh:
            live = sum(1 for line in fh if line.strip())
        minted = marker.get('journal_events')
        if isinstance(minted, int) and live > minted:
            message = ('the journal carries %d events, %d more than the '
                       'migration minted - post-migration v6 work is real '
                       'history and is not silently deleted' %
                       (live, live - minted))
            if not force:
                raise MigrationError(
                    message + '; pass --force to discard it deliberately')
            print('WARNING: %s (--force)' % message)
    for name in record:
        shutil.copy2(os.path.join(backup_dir, name),
                     os.path.join(plan_dir, name))
    # state.json was just restored from the backup; contract.json and
    # the journal are v6-only bytes and are removed.
    for artifact in ('contract.json', ledger.JOURNAL_NAME):
        path = os.path.join(plan_dir, artifact)
        if os.path.isfile(path):
            os.remove(path)
    views_dir = os.path.join(plan_dir, 'views')
    if os.path.isdir(views_dir) and not os.listdir(views_dir):
        os.rmdir(views_dir)
    marker['rolled_back'] = True
    _write_marker(plan_dir, marker)
    _atomic_write(os.path.join(plan_dir, MIGRATION_NAME, 'ROLLED_BACK.json'),
                  json.dumps({'restored': sorted(record)},
                             sort_keys=True, indent=2) + '\n')
    print('OK: %s rolled back to v5 (manifest and state restored '
          'byte-identically; contract.json and the journal removed)'
          % marker.get('plan', os.path.basename(os.path.normpath(plan_dir))))
    return 0


# ---------------------------------------------------------------- self-test

def _build_fixture(root):
    """A synthetic v5 plan: clean-completed, re-evidence, pending tasks."""
    plan = os.path.join(root, '.dwp', 'plans', 'PLAN_migration_selftest')
    gates = os.path.join(plan, 'analysis_results', 'gates')
    os.makedirs(gates)
    with open(os.path.join(plan, 'README.md'), 'w') as fh:
        fh.write('# Plan\n\n## Goal\n\nFixture plan.\n')
    for slug in ('1.task_clean.md', '2.task_broken.md', '3.task_pend.md'):
        with open(os.path.join(plan, slug), 'w') as fh:
            fh.write('# %s\n' % slug)
    with open(os.path.join(gates, 'clean.log'), 'w') as fh:
        fh.write('ok\n')
    manifest = {
        'schema': V5_MANIFEST_URLS[2], 'spec_version': '5.0.0',
        'name': 'PLAN_migration_selftest', 'title': 'Migration self-test',
        'created_at': '2026-09-01T09:00:00Z', 'task_count': 3,
        'plan_format': 'full'}
    state = {
        'schema': 'https://deepworkplan.com/schema/plan-state/v5.json',
        'plan': 'PLAN_migration_selftest',
        'updated_at': '2026-09-02T09:00:00Z', 'status': 'in_progress',
        'completed_count': 1, 'task_count': 3, 'format': 'full',
        'materialization': 'ready', 'tasks': [
            {'id': 1, 'title': 'Clean completed task',
             'locator': {'kind': 'file', 'value': '1.task_clean.md'},
             'status': 'completed', 'gates': [
                 {'command': 'pnpm run test:clean', 'passes': True,
                  'exit_code': 0, 'evidence': 'analysis_results/gates/clean.log'}]},
            {'id': 2, 'title': 'Broken evidence task',
             'locator': {'kind': 'file', 'value': '2.task_broken.md'},
             'status': 'completed', 'gates': [
                 {'command': 'pnpm run test:broken', 'passes': True,
                  'exit_code': 0, 'evidence': 'analysis_results/gates/gone.log'}]},
            {'id': 3, 'title': 'Pending task',
             'locator': {'kind': 'file', 'value': '3.task_pend.md'},
             'status': 'pending', 'gates': []}]}
    with open(os.path.join(plan, 'manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    with open(os.path.join(plan, 'state.json'), 'w') as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
    return plan


def self_test():
    """Deterministic probes over a synthetic v5 plan (tmpdir, no network)."""
    results = []

    def check(label, ok, detail=''):
        results.append((label, ok, detail))

    with tempfile.TemporaryDirectory() as root:
        plan = _build_fixture(root)
        # 1. preview classifies and records; nothing is written into the
        #    v5 pair.
        before = (open(os.path.join(plan, 'manifest.json'), 'rb').read(),
                  open(os.path.join(plan, 'state.json'), 'rb').read())
        analysis = analyze(plan, repo_root=root)
        classes = {t['number']: t['class'] for t in analysis['tasks']}
        check('preview maps clean/broken/pending classes',
              classes == {1: 'imported', 2: 're_evidence', 3: 'pending'},
              str(classes))
        check('re-evidence names the dangling pointer',
              any('does not resolve' in r for r in
                  analysis['tasks'][1]['reasons']),
              str(analysis['tasks'][1]['reasons']))
        cmd_preview(plan)
        check('preview leaves the v5 bytes untouched',
              before == (open(os.path.join(plan, 'manifest.json'),
                              'rb').read(),
                         open(os.path.join(plan, 'state.json'),
                              'rb').read()))
        # 1b. evidence that vanishes between preview and migrate must be
        #     refused, not silently re-classified: the source digest
        #     covers only the record pair, so the contract anchor is the
        #     guard that sees resolution change.
        os.remove(os.path.join(plan, 'analysis_results', 'gates',
                               'clean.log'))
        try:
            cmd_migrate(plan, authority='tester', note=None)
            check('a changed world between preview and migrate is refused',
                  False, 'migrate ran')
        except MigrationError as exc:
            check('a changed world between preview and migrate is refused',
                  'the v5 world changed since the preview' in str(exc),
                  str(exc))
        with open(os.path.join(plan, 'analysis_results', 'gates',
                               'clean.log'), 'w') as fh:
            fh.write('ok\n')
        # 2. the synthesized contract validates and is deterministic.
        first = synthesize_contract(analysis, authority='tester')
        second = synthesize_contract(analysis, authority='tester')
        cid1 = contract_v6.compute_contract_id(first)
        check('synthesized contract validates',
              not contract_v6.contract_errors(first))
        check('synthesis is deterministic (same inputs, same id)',
              cid1 == contract_v6.compute_contract_id(second))
        check('authority participates in the contract identity',
              cid1 != contract_v6.compute_contract_id(
                  synthesize_contract(analysis, authority='other')))
        # 3. migrate end to end: phases, events, derived statuses.
        cmd_migrate(plan, authority='tester', note=None)
        marker = _load_marker(plan)
        check('all five phases completed',
              marker['completed'] == list(PHASES), str(marker['completed']))
        check('the v5 manifest became the v6 pointer',
              _read_json(os.path.join(plan, 'manifest.json')) ==
              {'schema': ledger.MANIFEST_SCHEMA_URL,
               'plan': 'PLAN_migration_selftest',
               'contract': {'id': marker['contract_id'],
                            'path': 'contract.json'}})
        events = [json.loads(line) for line in
                  open(os.path.join(plan, ledger.JOURNAL_NAME))]
        types = [e['type'] for e in events]
        check('journal opens with the pre_authorization approval',
              types[0] == 'approval' and
              events[0]['mechanism'] == 'pre_authorization' and
              events[0]['plan_digest'] == analysis['digest'],
              str(types[:3]))
        starts = [e for e in events if e['type'] == 'task_start']
        check('task_start only for non-pending tasks, no fingerprint',
              sorted(e['task'] for e in starts) ==
              ['T-01-clean-completed-task',
               'T-02-broken-evidence-task'] and
              all('fingerprint' not in e for e in starts))
        runs = [e for e in events if e['type'] == 'gate_run']
        check('gate records imported with their labels',
              sorted((e['trust'], e['exit_code']) for e in runs) ==
              [('asserted', 0), ('imported', 0)] and
              all(e['actor']['identity'] == 'migrate_v6.py'
                  for e in runs))
        check('imported events carry the v5 provenance note',
              all(e['note'].startswith('migrated: v5 ')
                  for e in runs if e['trust'] == 'imported'))
        rec = ledger.PlanRecords(plan)
        _events, _torn, _framing = rec.read_journal()
        states1 = ledger.criterion_states(rec.contract, _events,
                                          'T-01-clean-completed-task')
        states2 = ledger.criterion_states(rec.contract, _events,
                                          'T-02-broken-evidence-task')
        check('clean criterion closes via imported',
              states1[0]['satisfied'] and
              states1[0]['trust'] == 'imported')
        check('re-evidence criterion is blocked by default',
              not states2[0]['satisfied'])
        snapshot = _read_json(os.path.join(plan, 'state.json'))
        status = {t['id']: t['status'] for t in snapshot['tasks']}
        check('projection derives completed/in_progress/pending',
              status == {'T-01-clean-completed-task': 'completed',
                         'T-02-broken-evidence-task': 'in_progress',
                         'T-03-pending-task': 'pending'}, str(status))
        # 4. resumability: re-running migrate is a no-op; a mid-state
        #    marker finishes the remaining phases without duplicates.
        cmd_migrate(plan, authority='tester', note=None)
        events_after = [json.loads(line) for line in
                        open(os.path.join(plan, ledger.JOURNAL_NAME))]
        check('re-running migrate mints no duplicate events',
              len(events_after) == len(events))
        # 5. observed can never be minted through the migration opening.
        lock = ledger.CooperativeLock(
            plan, identity='%s pid:%d' % (ledger.LEDGER_IDENTITY,
                                          os.getpid()))
        lock.acquire()
        try:
            writer = ledger.Writer(ledger.PlanRecords(plan), lock)
            try:
                writer.migrated_gate(
                    task_id='T-01-clean-completed-task',
                    criterion='AC-t01-clean-completed-task',
                    command='pnpm run test:clean', exit_code=0,
                    evidence_path='analysis_results/gates/clean.log',
                    source='selftest', trust='observed')
                check('observed refused through the migration opening',
                      False)
            except ledger.LedgerError as exc:
                check('observed refused through the migration opening',
                      'not a migration label' in str(exc))
        finally:
            lock.release()
        # 6. rollback restores the v5 bytes verbatim and removes the v6
        #    artifacts; post-migration work is guarded.
        check('rollback refuses when the journal grew beyond migration',
              _rollback_refuses(plan))
        cmd_rollback(plan, force=True)
        check('rollback restores manifest+state; v6 artifacts removed',
              _read_json(os.path.join(plan, 'manifest.json'))['schema'] in
              V5_MANIFEST_URLS and
              not os.path.isfile(os.path.join(plan, 'contract.json')) and
              not os.path.isfile(os.path.join(plan, ledger.JOURNAL_NAME)))
        check('the restored state is the v5 pair again',
              _read_json(os.path.join(plan, 'state.json'))['plan'] ==
              'PLAN_migration_selftest' and 'tasks' in
              _read_json(os.path.join(plan, 'state.json')))
        # 7. the marker records the rollback.
        marker = _load_marker(plan)
        check('marker records the rollback', marker.get('rolled_back'))
        # 8. lossy inputs are refused with named reasons.
        plan2 = _build_fixture(tempfile.mkdtemp())
        state2 = _read_json(os.path.join(plan2, 'state.json'))
        state2['tasks'][1]['status'] = 'mysterious'
        with open(os.path.join(plan2, 'state.json'), 'w') as fh:
            json.dump(state2, fh, indent=2, sort_keys=True)
        try:
            analyze(plan2)
            check('lossy status refused', False)
        except MigrationError as exc:
            check('lossy status refused', 'mysterious' in str(exc))
        # 9. a v6 plan is refused (one-directional). The rolled-back
        #    fixture is v5 again, so build and migrate a fresh one.
        plan3 = _build_fixture(tempfile.mkdtemp())
        cmd_preview(plan3)
        cmd_migrate(plan3, authority='tester', note=None)
        try:
            load_v5(plan3)
            check('already-v6 refused', False)
        except MigrationError as exc:
            check('already-v6 refused', 'already a v6 plan' in str(exc))
        cmd_rollback(plan3, force=False)
        # 10. no stray lock files were left behind anywhere.
        check('no stray lock files left in the fixtures',
              not any(os.path.exists(os.path.join(p, '.ledger.lock'))
                      for p in (plan, plan2, plan3)))
    ok = all(result[1] for result in results)
    for label, passed, detail in results:
        if not passed:
            print('FAIL %s %s' % (label, detail))
    print('migrate self-test: %s (%d probes)'
          % ('OK' if ok else 'FAILED', len(results)))
    return ok


def _rollback_refuses(plan):
    """True when rollback names the extra history instead of restoring.

    Appends one post-migration observation (a real v6 write) through the
    writer, then expects cmd_rollback to refuse without --force and to
    name what would be lost. The caller rolls back with --force after.
    """
    lock = ledger.CooperativeLock(
        plan, identity='%s pid:%d' % (ledger.LEDGER_IDENTITY, os.getpid()))
    lock.acquire()
    try:
        writer = ledger.Writer(ledger.PlanRecords(plan), lock)
        writer.append('observation', {
            'statement': 'post-migration work happened'},
            actor={'kind': 'agent', 'identity': 'selftest'},
            trust='asserted')
    finally:
        lock.release()
    try:
        cmd_rollback(plan, force=False)
        return False
    except MigrationError as exc:
        return 'not silently deleted' in str(exc)


def main(argv):
    usage = ('usage: migrate_v6.py --plan DIR {preview | migrate '
             '--authority WHO [--note TEXT] | rollback [--force] | '
             'self-test}')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--plan')
    parser.add_argument('command')
    parser.add_argument('--authority')
    parser.add_argument('--note')
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
        return 0 if self_test() else 1
    if not args.plan:
        print(usage)
        return 2
    try:
        plan = ledger.find_plan_dir(args.plan)
        if args.command == 'preview':
            return cmd_preview(plan)
        if args.command == 'migrate':
            return cmd_migrate(plan, args.authority, args.note)
        if args.command == 'rollback':
            return cmd_rollback(plan, args.force)
    except ledger.LedgerError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    except MigrationError as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 1
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
