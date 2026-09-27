#!/usr/bin/env python3
"""v6 execution ledger: the append-only journal writer and snapshot projector.

Implements RFC section 4 (draft-4) for v6 new plans:

  * ``journal.ndjson`` — append-only event log, one closed object per line,
    validated by :mod:`contract_v6`. Events are never edited or deleted.
  * ``state.json`` — the deterministic snapshot projection: task statuses,
    criterion satisfaction, per-type journal positions, resource totals.
    Rebuilt only by this module, atomically (temp + rename + fsync); it is
    the recovery root, never the memory.

Write discipline (section 4.3, D2-1/D2-9c): a cooperative ``.ledger.lock``
directory serializes writers; a session whose journal grew behind its back
(an editor bypassing the writer) is refused at write time by the byte
position check — the collision is reported loudly on stderr and exits
nonzero, because a second append from the colliding session would itself
violate single-writer. A torn final line (crash mid-append) is repaired on
the next open-for-write: the incomplete tail is truncated and an explicit
``journal_repair`` event records the byte offset and cause.

Trust discipline (section 4.5, A1): the ``gate`` subcommand is the only
producer of ``observed`` records — the helper itself executes the command
with declared cwd, environment, timeout, and captured outputs. Everything
appended through ``append`` is written as the caller declares, and
``observed`` on a mediating (``agent``) actor is refused by
:mod:`contract_v6`; use ``asserted`` and name the mediation.

Evidence identity: run results are cached under a content fingerprint
(sha256 over the hashed inputs the check declared — task surface files,
command, cwd, env subset, toolchain, selection). ``reuse`` returns the
prior result only on an exact fingerprint match; a changed input is a new
fingerprint and can never reuse a stale result.

Stale evidence (D2-9b): a criterion only counts evidence recorded at or
after the task's ``task_start`` journal position, with a trust label the
criterion accepts. Boundary invariants are likewise evaluated at or after
task-start (D3-6); the projector refuses to count earlier items as
satisfying.

Durability (A10): ``export`` copies journal + snapshot + the full contract
chain to an operator-named destination with verified digests. ``roll``
archives the journal beside the plan (nothing is ever deleted;
snapshot-cited positions become archive-addressable, D2-8) and is OFF by
default — the default posture is export, not roll.

Python 3.9+ stdlib only. Never executes gates except via the explicit
``gate`` subcommand. Never edits or deletes journal events.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402  (sibling module, same directory)

LEDGER_IDENTITY = 'dwp-ledger/6.0'
LOCK_DIRNAME = '.ledger.lock'
LOCK_STALE_SECONDS = 900
# RFC 9.1: the v6 snapshot is a NEW schema-URL generation, never a mutation
# of the v5 shapes. The plan-state label is the frozen v1/v2/v5 shape series
# (a generation snapshot of the v2 shape); the v6 snapshot therefore
# publishes under its own label, beside plan-contract/v6 and
# journal-event/v6, and is described by spec/schema/plan-snapshot-v6.schema.json.
STATE_SCHEMA_URL = 'https://deepworkplan.com/schema/plan-snapshot/v6.json'

# RFC 9.1 again, for the plan identity: the v6 manifest is its own new
# generation (the v1/v2/v5 manifest shapes are frozen), and it carries the
# A12 contract pointer that makes a plan's v6-ness discoverable even when
# materialization crashed between the manifest and the contract.
MANIFEST_SCHEMA_URL = 'https://deepworkplan.com/schema/plan-manifest/v6.json'

# Journal types that are render provenance, not plan state: they never
# advance the projected snapshot (a view's own bookkeeping must not change
# the state the view is anchored to).
PROVENANCE_TYPES = ('view_render',)
JOURNAL_NAME = 'journal.ndjson'
EVIDENCE_NAME = 'evidence.jsonl'
GATES_DIRNAME = 'gates'


class LedgerError(Exception):
    """Operator-visible failure; exit code 1."""


class CollisionError(LedgerError):
    """The journal grew behind this writer's back (D2-9c). Exit 2."""


class ApprovalMissing(LedgerError):
    """task_start refused: no approval event cites the live contract. Exit 3."""


class CompletionRefused(LedgerError):
    """Completion refused on missing in-window accepted evidence. Exit 4."""


# ---------------------------------------------------------------- plan load

def _sibling_module():
    return contract_v6


def find_plan_dir(path):
    """Accept a plan directory, a state.json path, or a journal path."""
    path = os.path.abspath(path)
    if os.path.isdir(path):
        return path
    parent = os.path.dirname(path)
    if os.path.isfile(path) and os.path.basename(parent).startswith('PLAN_'):
        return parent
    raise LedgerError('no plan directory found at %r' % path)


def plan_markdown_digest(plan_dir):
    """Deterministic digest of the plan markdown the authority approves.

    Every ``*.md`` file directly in the plan folder (README, PROGRESS, the
    task files), sorted by name, concatenated, sha256. A plan with no
    markdown has nothing to approve — materialization refuses rather than
    approving a folder of records alone.
    """
    names = sorted(name for name in os.listdir(plan_dir)
                   if name.endswith('.md') and os.path.isfile(
                       os.path.join(plan_dir, name)))
    if not names:
        raise LedgerError(
            'no plan markdown (*.md) in %s — the materialization-time '
            'approval digests the plan the authority approved; a folder '
            'with no markdown is not approvable' % plan_dir)
    digest = hashlib.sha256()
    for name in names:
        with open(os.path.join(plan_dir, name), 'rb') as fh:
            digest.update(fh.read())
    return digest.hexdigest()


def _atomic_write(path, text):
    """Write text to path via temp + rename + fsync (write discipline)."""
    hold = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=hold, prefix='.tmp-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def materialize_plan(plan_dir, contract_file, authority='developer',
                     mechanism='plan_authorship', note=None):
    """Materialize a v6 plan: manifest -> contract -> approval (A12).

    One guarded, resumable sequence. The order is normative (RFC 3.1/A12,
    ``spec/V6_LIFECYCLE.md``): the manifest carries the contract pointer so
    a crash between manifest and contract still leaves the plan's v6-ness
    discoverable; the contract lands stamped with its content-addressed
    identity; the materialization-time ``approval`` journal event — citing
    the live ``contract_id`` and the digest of the plan markdown — is the
    first journal event and the only thing that opens the task-start gate.

    Every step is idempotent and resume-safe: an interrupted materialization
    is completed by running it again with the same inputs. What is never
    allowed: rewriting a contract that differs (that is a revision — the
    refine amendment path), or touching a manifest of another generation
    (a v1/v2/v5 manifest belongs to its recorded lifecycle, RFC 9.2).
    """
    if mechanism not in contract_v6.MECHANISMS:
        raise LedgerError(
            'mechanism %r outside %s (D3-2: exactly two exist)'
            % (mechanism, ' and '.join(contract_v6.MECHANISMS)))
    with open(contract_file, encoding='utf-8') as fh:
        contract = json.load(fh)
    contract.pop('contract_id', None)
    errors = contract_v6.contract_errors(contract)
    if errors:
        raise LedgerError('contract invalid: %s' % errors[0])
    folder = os.path.basename(os.path.normpath(plan_dir))
    if contract.get('plan') != folder:
        raise LedgerError(
            'contract plan %r does not match the plan folder %r — the '
            'manifest asserts the folder identity; materializing a '
            'mismatched contract would record the wrong plan'
            % (contract.get('plan'), folder))
    cid = contract_v6.compute_contract_id(contract)
    digest = plan_markdown_digest(plan_dir)

    # -- 1. manifest: the contract pointer (written first, A12) ----------
    manifest_path = os.path.join(plan_dir, 'manifest.json')
    manifest = {'schema': MANIFEST_SCHEMA_URL, 'plan': contract['plan'],
                'contract': {'id': cid, 'path': 'contract.json'}}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding='utf-8') as fh:
            existing = json.load(fh)
        if existing.get('schema') != MANIFEST_SCHEMA_URL:
            raise LedgerError(
                'manifest.json is %r — a different generation. v1/v2/v5 '
                'manifests belong to their recorded lifecycle and are '
                'never rewritten (RFC 9.2)' % existing.get('schema'))
        if (existing.get('contract') or {}).get('id') != cid:
            raise LedgerError(
                'manifest contract pointer %r does not match this '
                'contract %r — never rewrite a pointer; amend through '
                'refine (the revision chain)' %
                ((existing.get('contract') or {}).get('id'), cid))
    else:
        _atomic_write(manifest_path, json.dumps(
            manifest, sort_keys=True, indent=2) + '\n')

    # -- 2. contract: stamped, atomic, never rewritten -------------------
    chain = os.path.join(plan_dir, 'contracts')
    if os.path.isdir(chain):
        raise LedgerError(
            'a contracts/ revision chain exists — the contract is owned '
            'by amendments from here on; materialization never rewrites it')
    contract_path = os.path.join(plan_dir, 'contract.json')
    if os.path.exists(contract_path):
        with open(contract_path, encoding='utf-8') as fh:
            stamped = json.load(fh)
        if stamped.get('contract_id') != cid:
            raise LedgerError(
                'contract.json already carries %r; this contract is %r — a '
                'materialization never rewrites a contract, that is a '
                'revision (refine amendment path)' %
                (stamped.get('contract_id'), cid))
    else:
        _atomic_write(contract_path, json.dumps(
            dict(contract, contract_id=cid), sort_keys=True, indent=2) + '\n')

    # -- 3. approval: the materialization-time journal event -------------
    lock = CooperativeLock(plan_dir, identity='%s pid:%d' %
                           (LEDGER_IDENTITY, os.getpid()))
    lock.acquire()
    try:
        writer = Writer(PlanRecords(plan_dir), lock)
        for event in writer.events:
            if event.get('type') == 'approval' and \
                    event.get('contract_id') == cid:
                return {'plan': contract['plan'], 'contract_id': cid,
                        'approval_seq': event.get('seq'),
                        'digest': digest, 'resumed': True}
        payload = {'authority': authority, 'mechanism': mechanism,
                   'plan_digest': digest}
        event = writer.append(
            'approval', payload,
            actor={'kind': 'human', 'identity': authority},
            note=note, idempotent=True)
        return {'plan': contract['plan'], 'contract_id': cid,
                'approval_seq': event.get('seq'), 'digest': digest,
                'resumed': False}
    finally:
        lock.release()


class PlanRecords:
    """Read-side view of one v6 plan's records (contract, journal, state)."""

    def __init__(self, plan_dir):
        self.dir = plan_dir
        self.journal_path = os.path.join(plan_dir, JOURNAL_NAME)
        self.state_path = os.path.join(plan_dir, 'state.json')
        self.evidence_path = os.path.join(plan_dir, EVIDENCE_NAME)
        self.gates_dir = os.path.join(plan_dir, GATES_DIRNAME)
        self.contract = self._load_contract()
        if self.contract.get('schema') != contract_v6.CONTRACT_SCHEMA_URL:
            raise LedgerError(
                'the v6 ledger serves v6 contracts only; older plans keep '
                'their recorded tooling (RFC 9.1): found %r' %
                self.contract.get('schema'))
        errors = contract_v6.contract_errors(self.contract)
        if errors:
            raise LedgerError('contract invalid: %s' % errors[0])

    def _load_contract(self):
        """Live contract = highest revision under contracts/, else contract.json."""
        chain_dir = os.path.join(self.dir, 'contracts')
        best = None
        if os.path.isdir(chain_dir):
            for name in sorted(os.listdir(chain_dir)):
                if not name.endswith('.json'):
                    continue
                doc = self._read_json(os.path.join(chain_dir, name))
                rev = doc.get('revision', 0)
                if not isinstance(rev, int):
                    continue
                if best is None or rev > best.get('revision', 0):
                    best = doc
        if best is not None:
            return best
        single = os.path.join(self.dir, 'contract.json')
        if os.path.isfile(single):
            return self._read_json(single)
        raise LedgerError('no contract.json and no contracts/ chain in %s'
                          % self.dir)

    @staticmethod
    def _read_json(path):
        # A corrupted persisted artifact must refuse by name — the journal
        # stays untouched and the operator learns which file to restore.
        # A raw JSONDecodeError stack dump hides both.
        try:
            with open(path, encoding='utf-8') as fh:
                return json.load(fh)
        except ValueError as exc:
            raise LedgerError(
                '%s is corrupt (not valid JSON: %s) — no write was made; '
                'restore the contract or roll back before continuing'
                % (os.path.basename(path), exc))

    @property
    def contract_id(self):
        stamped = self.contract.get('contract_id')
        return stamped or contract_v6.compute_contract_id(self.contract)

    def read_journal(self):
        """Return (events, torn, framing) for the LIVE journal.

        torn is (byte_offset, cause) or None: a final line that does not
        parse or undecodable bytes — a torn tail from a crash mid-append
        (section 4.3), truncated at the line start on the next open.
        framing is True when the final line parsed as a complete event
        but the file lacks its trailing newline: the event is complete
        and durable — only the framing byte was lost — so the writer
        restores the newline instead of deleting it (B2).
        """
        if not os.path.exists(self.journal_path):
            return [], None, False
        with open(self.journal_path, 'rb') as fh:
            raw = fh.read()
        events = []
        offset = 0
        torn = None
        framing = False
        for line in raw.split(b'\n'):
            if not line.strip():
                offset += len(line) + 1
                continue
            try:
                text = line.decode('utf-8')
            except UnicodeDecodeError:
                torn = (offset, 'undecodable bytes in final line')
                break
            try:
                events.append(json.loads(text))
            except json.JSONDecodeError:
                torn = (offset, 'final line does not parse (torn append)')
                break
            offset += len(line) + 1
        if torn is None and raw and not raw.endswith(b'\n'):
            framing = True  # the last line parsed: complete, unframed
        return events, torn, framing

    def archived_events(self):
        """B3: every retired archive segment's events, in seq order.

        Rolls archive bytes, never history: the approval gate, the
        evidence window and the projection read the WHOLE plan record,
        archived plus live. A corrupt archive segment is an error, never
        silently skipped.
        """
        events = []
        for archive in self.archives():
            path = os.path.join(self.dir, archive['file'])
            with open(path, 'rb') as fh:
                raw = fh.read()
            for line in raw.split(b'\n'):
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line.decode('utf-8')))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise LedgerError(
                        'archive segment %s is corrupt (%s) — archived '
                        'history is never repaired in place; restore the '
                        'exported copy' % (archive['file'], exc))
        events.sort(key=lambda e: e.get('seq', 0))
        return events

    def snapshot_digest(self):
        """sha256 of the snapshot bytes, or None before the first project."""
        if not os.path.isfile(self.state_path):
            return None
        with open(self.state_path, 'rb') as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    ARCHIVE_RE = re.compile(r'^journal-archive-(\d{6})-(\d{6})\.ndjson$')

    def archives(self):
        """Roll archives beside the plan, oldest first (ranges from names)."""
        found = []
        if os.path.isdir(self.dir):
            for name in sorted(os.listdir(self.dir)):
                match = self.ARCHIVE_RE.match(name)
                if match:
                    found.append({'file': name,
                                  'first_seq': int(match.group(1)),
                                  'last_seq': int(match.group(2))})
        return found

    def archive_top_seq(self):
        """Highest seq any archive retired — the floor the live journal
        must continue above (a roll never resets the plan's seq)."""
        return max([a['last_seq'] for a in self.archives()] or [0])


# -------------------------------------------------------------------- lock

class CooperativeLock:
    """mkdir-based cooperative lock (v5 pattern); stale after TTL or dead pid."""

    def __init__(self, plan_dir, identity=LEDGER_IDENTITY,
                 stale_seconds=LOCK_STALE_SECONDS):
        self.path = os.path.join(plan_dir, LOCK_DIRNAME)
        self.identity = identity
        self.stale_seconds = stale_seconds
        self.held = False

    def _pid_alive(self, pid):
        if not isinstance(pid, int) or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # exists, but signaling it is not permitted
        except OSError:
            return False

    def acquire(self, force=False):
        for _ in range(2):
            try:
                os.mkdir(self.path)
                self._write_owner()
                self.held = True
                return self
            except FileExistsError:
                info = self._read_owner()
                if force or info is None or self._is_stale(info):
                    shutil.rmtree(self.path, ignore_errors=True)
                    continue
                raise LedgerError(
                    'another writer holds the plan lock: %s (started %s); '
                    'use --force only after verifying that writer is dead'
                    % (info.get('identity'), info.get('ts')))
        raise LedgerError('could not acquire the plan lock')

    def _is_stale(self, info):
        try:
            age = time.time() - float(info.get('epoch_ts', 0))
        except (TypeError, ValueError):
            return True
        if age > self.stale_seconds:
            return True
        pid = info.get('pid')
        if isinstance(pid, int) and pid != os.getpid() and not self._pid_alive(pid):
            return True
        return False

    def _write_owner(self):
        payload = {'identity': self.identity, 'pid': os.getpid(),
                   'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   'epoch_ts': time.time(),
                   'host': os.uname().nodename}
        with open(os.path.join(self.path, 'owner.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(payload, fh, sort_keys=True)

    def _read_owner(self):
        try:
            with open(os.path.join(self.path, 'owner.json'),
                      encoding='utf-8') as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def release(self):
        if self.held:
            shutil.rmtree(self.path, ignore_errors=True)
            self.held = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()


# ------------------------------------------- pure projection semantics
# These functions are the plan's satisfaction semantics with no writer, no
# lock and no filesystem: they consume (contract, events) and return state.
# Writer delegates to them, and scheduler.py imports them so the model and
# the deterministic core can never disagree about what "satisfied" means.

def task_start_seq_of(events, task_id):
    """The seq of the task's latest task_start event, or None."""
    start = None
    for event in events:
        if isinstance(event, dict) and event.get('type') == 'task_start' \
                and event.get('task') == task_id:
            seq = event.get('seq', 0)
            if start is None or seq > start:
                start = seq
    return start


def criterion_states(contract, events, task_id):
    """Satisfaction per criterion with in-window accepted evidence.

    D2-9b: only evidence recorded at or after the task's task_start
    position counts, with a trust label the criterion accepts.
    D3-6: boundary invariants are likewise evaluated at or after
    task-start; earlier items are recorded as stale, never satisfying.
    """
    task = None
    for candidate in contract.get('tasks', []):
        if candidate.get('id') == task_id:
            task = candidate
            break
    if task is None:
        raise LedgerError('task %r is not in the contract' % task_id)
    start = task_start_seq_of(events, task_id)
    accepted_by = {c['id']: c.get('accepted_evidence', [])
                   for c in contract['acceptance']['criteria']}
    states = []
    for intent in task.get('gate_intent', []):
        cid = intent.get('criterion')
        wanted = accepted_by.get(cid, [])
        best = None
        stale = []
        for event in events:
            if not isinstance(event, dict) or \
                    event.get('type') != 'gate_run' or \
                    event.get('criterion') != cid or \
                    event.get('task') != task_id:
                continue
            trust = event.get('trust')
            if start is None or event.get('seq', 0) < start:
                stale.append(event.get('seq'))
                continue
            if trust in wanted and event.get('exit_code') == 0 and \
                    (best is None or event['seq'] > best['via_seq']):
                best = {'criterion': cid, 'satisfied': True,
                        'via_seq': event['seq'], 'trust': trust,
                        'evidence_path': event.get('evidence_path')}
        states.append(best or {
            'criterion': cid, 'satisfied': False,
            'started_seq': start, 'stale_seqs': stale})
    return states


def task_complete(contract, events, task_id):
    """True when every gate_intent criterion has in-window accepted
    evidence (the same zero-test predicate complete_task enforces)."""
    return all(state.get('satisfied')
               for state in criterion_states(contract, events, task_id))


# ------------------------------------------------------------------ writer

class Writer:
    """The single journal writer + projector for one plan (lock required)."""

    def __init__(self, records, lock):
        if not lock.held:
            raise LedgerError('Writer requires a held lock')
        self.r = records
        self.lock = lock
        self.events, torn, framing = records.read_journal()
        # seq floor: archives may have retired events above anything the
        # live journal holds — seq is plan-wide and never goes backwards.
        # Set BEFORE any repair: repairs append, and appending reads it.
        self._seq_floor = records.archive_top_seq()
        # position baseline BEFORE repairs: both repair paths append and
        # each keeps the baseline correct itself (truncate → offset;
        # framing restore → new size)
        self._end_offset = self._journal_size()
        if torn is not None:
            self._repair_torn_tail(self.events, torn)
        if framing:
            self._restore_framing()
        # B3: archived events stay first-class plan history — approvals,
        # evidence windows and projections read archived + live together
        self.events = records.archived_events() + self.events

    def _journal_size(self):
        return os.path.getsize(self.r.journal_path) \
            if os.path.exists(self.r.journal_path) else 0

    def _restore_framing(self):
        """B2: the final event is complete but lost its newline.

        The newline is framing, not content: restore it and record the
        repair. The complete event itself is never deleted — only a
        final line that does not parse is treated as a torn append.
        """
        size = self._journal_size()
        with open(self.r.journal_path, 'ab') as fh:
            fh.write(b'\n')
            fh.flush()
            os.fsync(fh.fileno())
        # the framing byte joins the writer's position baseline; the
        # repair event appended below then advances it normally
        self._end_offset = self._journal_size()
        self._append_raw('journal_repair',
                         {'byte_offset': size,
                          'cause': 'final event complete, framing newline '
                                   'restored after an interrupted append'},
                         actor={'kind': 'helper', 'identity': LEDGER_IDENTITY},
                         ts=_utc_now(), note='complete events are durable; '
                         'only the framing byte was missing')

    def _repair_torn_tail(self, events, torn):
        """Truncate the torn tail and record a journal_repair event (4.3)."""
        offset, cause = torn
        with open(self.r.journal_path, 'rb+') as fh:
            fh.truncate(offset)
            fh.flush()
            os.fsync(fh.fileno())
        self.events = [e for e in events if isinstance(e, dict)]
        # the writer's position baseline is now the truncated length
        self._end_offset = offset
        self._append_raw('journal_repair',
                         {'byte_offset': offset, 'cause': cause},
                         actor={'kind': 'helper', 'identity': LEDGER_IDENTITY},
                         ts=_utc_now(), note='torn tail truncated; the '
                         'append-only rule binds complete events only')

    def last_seq(self):
        return max([e.get('seq', 0) for e in self.events if
                    isinstance(e, dict)] + [self._seq_floor] or [0])

    def _check_position(self):
        """D2-9c: refuse when the journal grew behind this writer."""
        if self._journal_size() != self._end_offset:
            raise CollisionError(
                'journal changed size behind this writer (expected %d bytes, '
                'found %d) — another writer bypassed the lock; this session '
                'refuses to append rather than interleave histories' %
                (self._end_offset, self._journal_size()))

    def _append_raw(self, etype, payload, actor, ts, note=None,
                    extra=None, trust=None, evidence_path=None):
        event = dict(payload)
        event.update({
            'schema': contract_v6.JOURNAL_SCHEMA_URL,
            'type': etype,
            'seq': self.last_seq() + 1,
            'ts': ts,
            'plan': self.r.contract['plan'],
            'contract_id': self.r.contract_id,
            'actor': actor,
        })
        if note is not None:
            event['note'] = note
        if trust is not None:
            event['trust'] = trust
        if evidence_path is not None:
            event['evidence_path'] = evidence_path
        if extra:
            event.update(extra)
        errors = contract_v6.journal_event_errors(event, self.r.contract)
        if errors:
            raise LedgerError('refusing to append an invalid %s event: %s'
                              % (etype, errors[0]))
        line = json.dumps(event, sort_keys=True,
                          separators=(',', ':')) + '\n'
        raw = line.encode('utf-8')
        with open(self.r.journal_path, 'ab') as fh:
            fh.write(raw)
            fh.flush()
            os.fsync(fh.fileno())
        self.events.append(event)
        self._end_offset += len(raw)
        return event

    def append(self, etype, payload, actor=None, ts=None, note=None,
               idempotent=False, trust=None, evidence_path=None):
        """Append one event; validate; optional content-keyed dedup.

        With ``idempotent=True`` an existing event with identical content
        (same type + payload + actor identity, ignoring seq/ts/note) is
        returned without appending — repeated submissions do not duplicate
        work. Protocol events (task_start, approval) pass idempotent=True;
        gate history is never deduped — re-runs are history.
        """
        self._check_position()
        actor = actor or {'kind': 'agent', 'identity': 'caller'}
        ts = ts or _utc_now()
        self._enforce_mint_rules(etype, actor, trust, evidence_path)
        # M1: the approval gate runs BEFORE idempotent dedup — a replayed
        # task_start under an unapproved contract revision is refused,
        # never silently accepted as the old revision's event
        if etype == 'task_start':
            self._require_approval()
        if idempotent:
            body_key = _content_key(etype, payload, actor,
                                    self.r.contract_id)
            for prior in self.events:
                if _content_key(prior.get('type'), _payload_of(prior),
                                prior.get('actor'),
                                prior.get('contract_id')) == body_key:
                    return prior
        return self._append_raw(etype, payload, actor, ts, note,
                                trust=trust, evidence_path=evidence_path)

    def _enforce_mint_rules(self, etype, actor, trust, evidence_path):
        """B1/A1: `observed` is minted only by execution, never declared.

        gate_run records exist only through run_gate (the helper that
        executed the command). Outside the gate executor, observed is
        legal for exactly one case: host-adapter metering
        (resource_sample from a host_adapter actor citing an evidence
        artifact that exists). Every other caller-declared observed —
        and every observed/imported record whose pointer does not
        resolve — is refused here.
        """
        if etype == 'gate_run':
            raise LedgerError(
                'gate_run records are produced only by the gate executor '
                '(ledger.py gate) — a mediated write can never be '
                'observed evidence (A1)')
        if trust == 'observed':
            if etype != 'resource_sample':
                raise LedgerError(
                    'trust=observed is minted only by execution: the gate '
                    'executor for gate_run records, or host-adapter '
                    'metering for resource_sample records. Record this as '
                    'asserted with the mediation named (A1)')
            if (actor or {}).get('kind') != 'host_adapter':
                raise LedgerError(
                    'observed resource samples require a host_adapter '
                    'actor that read the meter — agent/helper writers '
                    'record asserted')
        if trust in ('observed', 'imported'):
            self._check_evidence_path(evidence_path)

    def _check_evidence_path(self, evidence_path):
        """An observed/imported record must cite a recoverable artifact."""
        if not evidence_path:
            raise LedgerError(
                'trust=%s requires evidence_path — a recoverable pointer, '
                'never a bare claim' % 'observed')
        candidates = [os.path.join(self.r.dir, evidence_path)]
        root = self.repo_root()
        if root:
            candidates.append(os.path.join(root, evidence_path))
        if os.path.isabs(evidence_path):
            candidates.insert(0, evidence_path)
        if not any(os.path.isfile(c) for c in candidates):
            raise LedgerError(
                'evidence_path %r does not resolve inside the plan or the '
                'repository — observed/imported records must cite an '
                'artifact that exists' % evidence_path)

    def _require_approval(self):
        """D3-7/D2-3: task_start is refused until an approval event cites
        the live contract_id. The refusal is itself recorded (section 5)."""
        for event in self.events:
            if event.get('type') == 'approval' and \
                    event.get('contract_id') == self.r.contract_id:
                return
        self._append_raw('refusal',
                         {'subject': 'task_start',
                          'stage': 'task_start',
                          'reason': 'no approval event cites the live '
                                    'contract_id %s' % self.r.contract_id[:12]},
                         actor={'kind': 'helper',
                                'identity': LEDGER_IDENTITY},
                         ts=_utc_now())
        raise ApprovalMissing(
            'task_start refused: no approval event cites the live '
            'contract_id — record the materialization-time approval first '
            '(mechanism: plan_authorship or pre_authorization)')

    # -- gate execution (the only source of `observed`) --------------------

    def repo_root(self):
        """The repo root is the directory that contains this plan's .dwp/."""
        up = os.path.dirname(self.r.dir)          # .../PLAN_x -> .dwp/plans
        up = os.path.dirname(up)                  # -> .dwp
        if os.path.basename(up) == '.dwp':
            return os.path.dirname(up)
        return os.path.dirname(self.r.dir)

    def fingerprint(self, task_id, command, selection=None):
        """Content fingerprint over the declared check inputs (A1 runner).

        The gate's working directory is the plan's repository root — derived
        from the plan location, never the caller's shell — so the same gate
        run from any directory yields the same fingerprint and the same
        recorded cwd (reuse identity holds by construction).
        """
        task = self._task(task_id)
        gate_cwd = self.repo_root()
        files = {}
        for rel in task.get('touched_surface', []):
            path = rel if os.path.isabs(rel) else \
                os.path.join(gate_cwd, rel)
            files[rel] = _hash_file(path)
        payload = {
            'command': command,
            'cwd': os.path.basename(os.path.abspath(gate_cwd)),
            'env': _env_subset(),
            'toolchain': {'python': sys.version.split()[0],
                          'platform': sys.platform},
            'selection': selection or '',
            'files': files,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True,
                       separators=(',', ':')).encode('utf-8')).hexdigest()

    def _task(self, task_id):
        for task in self.r.contract.get('tasks', []):
            if task.get('id') == task_id:
                return task
        raise LedgerError('task %r is not in the contract' % task_id)

    def evidence_lookup(self, fingerprint, task_id=None, criterion=None):
        """Prior result on an EXACT fingerprint match, else None.

        Reuse is sound only for the same (task, criterion) the evidence
        was recorded under: satisfaction is evaluated per (task,
        criterion), so replaying another linkage's cached result would
        mint no evidence for the requester and dead-loop its gate (every
        run would short-circuit into the cache). A cross-linkage run
        executes freshly and records its own result.
        """
        if not os.path.exists(self.r.evidence_path):
            return None
        with open(self.r.evidence_path, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue  # corrupt sidecar line: skip, never crash reads
                if rec.get('fingerprint') != fingerprint:
                    continue
                if task_id is not None and rec.get('task') != task_id:
                    continue
                if criterion is not None and \
                        rec.get('criterion') != criterion:
                    continue
                return rec
        return None

    def _evidence_put(self, rec):
        line = json.dumps(rec, sort_keys=True, separators=(',', ':')) + '\n'
        with open(self.r.evidence_path, 'a', encoding='utf-8') as fh:
            fh.write(line)

    def run_gate(self, task_id, command, criterion=None, timeout=600,
                 selection=None, reuse=True, log_dir=None):
        """Execute a gate command and record an OBSERVED gate_run event.

        The helper itself executes the command (declared cwd, timeout,
        captured outputs) — this is the A1 definition of observed. Output
        goes to a recoverable log under gates/. An exact fingerprint match
        returns the cached result without re-running (equivalent-input
        reuse); a changed input is a new fingerprint and re-runs.
        """
        self._check_position()
        task = self._task(task_id)
        # M5: a gate run is bound to the contract's declared intent —
        # the criterion must be one this task declares, the task must
        # have started (observed evidence exists only inside an
        # attempt, D2-9b), and the command must be inside the declared
        # command classes where the contract declares them.
        intents = {i.get('criterion')
                   for i in task.get('gate_intent', [])}
        if not criterion:
            raise LedgerError(
                'gate runs require a criterion from the task gate_intent — '
                '"some command exited 0" is not acceptance evidence')
        if criterion not in intents:
            raise LedgerError(
                'criterion %r is not declared in task %s gate_intent %s — '
                'the linkage cannot be chosen after the run' %
                (criterion, task_id, sorted(intents)))
        start = task_start_seq_of(self.events, task_id)
        if start is None:
            raise LedgerError(
                'gate refused for %s: the task has no task_start — '
                'observed evidence is only recorded inside a task '
                'attempt, never before it' % task_id)
        declared = self.r.contract.get('scope', {}).get(
            'allowed_command_classes') or []
        if declared:
            head = command if isinstance(command, str) else ' '.join(command)
            head = head.split()[0] if head.split() else ''
            if os.path.basename(head) not in declared:
                raise LedgerError(
                    'gate command %r is outside the contract declared '
                    'command classes %s' % (head, sorted(declared)))
        fp = self.fingerprint(task_id, command, selection)
        if reuse:
            prior = self.evidence_lookup(fp, task_id, criterion)
            if prior is not None:
                return {'reused': True, 'fingerprint': fp,
                        'exit_code': prior['exit_code'],
                        'log': prior['log'], 'seq': prior.get('seq')}
        gate_cwd = self.repo_root()
        log_dir = log_dir or os.path.join(self.r.gates_dir, task_id)
        os.makedirs(log_dir, exist_ok=True)
        slug = re.sub(r'[^A-Za-z0-9._-]+', '-',
                      command if isinstance(command, str)
                      else ' '.join(command))[:40].strip('-')
        log_path = os.path.join(log_dir, '%03d-%s.log'
                                % (self.last_seq() + 1, slug or 'gate'))
        try:
            proc = subprocess.run(command, shell=isinstance(command, str),
                                  cwd=gate_cwd, capture_output=True,
                                  text=True, timeout=timeout)
            exit_code, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            out = (exc.stdout or b'').decode('utf-8', 'replace') \
                if isinstance(exc.stdout, bytes) else (exc.stdout or '')
            err = 'timeout after %ss' % timeout
        except FileNotFoundError:
            raise LedgerError('gate command not found: %r — no event is '
                              'recorded for a command that never ran'
                              % (command,))
        with open(log_path, 'w', encoding='utf-8') as fh:
            fh.write('$ %s\n\n--- stdout ---\n%s\n--- stderr ---\n%s\n'
                     '--- exit %d ---\n' % (command, out, err, exit_code))
        payload = {'command': command if isinstance(command, str)
                   else ' '.join(command),
                   'cwd': os.path.abspath(gate_cwd),
                   'timeout_seconds': timeout,
                   'exit_code': exit_code,
                   'task': task_id,
                   'criterion': criterion}
        event = self._append_raw('gate_run', payload,
                                 actor={'kind': 'helper',
                                        'identity': LEDGER_IDENTITY},
                                 ts=_utc_now(), trust='observed',
                                 evidence_path=os.path.relpath(
                                     log_path, self.r.dir))
        self._evidence_put({'fingerprint': fp, 'task': task_id,
                            'criterion': criterion,
                            'exit_code': exit_code,
                            'log': os.path.relpath(log_path, self.r.dir),
                            'seq': event['seq'], 'ts': event['ts']})
        return {'reused': False, 'fingerprint': fp,
                'exit_code': exit_code,
                'log': os.path.relpath(log_path, self.r.dir),
                'seq': event['seq']}

    def migrated_gate(self, task_id, criterion, command, exit_code,
                      evidence_path, source, cwd=None, timeout=600,
                      trust='imported'):
        """Migration-only IMPORT of a matched v5 gate record (RFC 9.3).

        A1 is untouched: ``observed`` is still minted only by execution,
        and the generic ``append`` path still refuses ``gate_run`` outright.
        This method is the one narrow opening the v5->v6 migration needs:
        ``shared/migrate_v6.py`` - deterministic code, never an agent -
        imports a record that already exists in the v5 plan state
        (command, exit code, evidence pointer) under the label the
        taxonomy gives a matched external source: ``imported``, with the
        v5 source digest as provenance, and only when the evidence
        pointer still resolves on disk. A record the v5 state kept
        without a pointer may be imported as ``asserted`` history - it
        can never satisfy a criterion whose bar was not set to accept
        it. ``observed`` is refused here like everywhere else.
        """
        self._check_position()
        if trust not in ('imported', 'asserted'):
            raise LedgerError(
                'migrated_gate imports a v5 record as imported (pointer '
                'resolves) or asserted (no pointer) - %r is not a '
                'migration label, and observed is minted only by '
                'execution (A1)' % trust)
        if trust == 'imported':
            if not evidence_path:
                raise LedgerError(
                    'an imported gate record requires evidence_path - the '
                    'v5 pointer IS the provenance (A1)')
            self._check_evidence_path(evidence_path)
        task = self._task(task_id)
        intents = {i.get('criterion')
                   for i in task.get('gate_intent', [])}
        if criterion not in intents:
            raise LedgerError(
                'criterion %r is not declared in task %s gate_intent - a '
                'migrated record is bound to the declared intent like any '
                'gate run (M5)' % (criterion, task_id))
        if task_start_seq_of(self.events, task_id) is None:
            raise LedgerError(
                'migrated gate refused for %s: the task has no task_start '
                '- evidence lives inside the task attempt window '
                '(D2-9b)' % task_id)
        for prior in self.events:
            if prior.get('type') != 'gate_run' or \
                    prior.get('task') != task_id or \
                    prior.get('criterion') != criterion or \
                    prior.get('command') != command or \
                    prior.get('exit_code') != exit_code or \
                    prior.get('evidence_path') != (evidence_path or None):
                continue
            return prior  # one v5 record, one event: re-running is a no-op
        payload = {'command': command,
                   'cwd': os.path.abspath(cwd or self.repo_root()
                                          or self.r.dir),
                   'timeout_seconds': timeout,
                   'exit_code': exit_code,
                   'task': task_id,
                   'criterion': criterion}
        return self._append_raw(
            'gate_run', payload,
            actor={'kind': 'helper', 'identity': 'migrate_v6.py'},
            ts=_utc_now(), note=('migrated: %s' % source)[:500],
            trust=trust, evidence_path=evidence_path)

    # -- control-pair execution (the second observed executor, U2/A6) -------

    def _run_leg(self, command, cwd, timeout, log_path):
        """Execute one control leg; returns (exit_code, ran)."""
        try:
            proc = subprocess.run(command, shell=isinstance(command, str),
                                  cwd=cwd, capture_output=True,
                                  text=True, timeout=timeout)
            exit_code, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            out = (exc.stdout or b'').decode('utf-8', 'replace') \
                if isinstance(exc.stdout, bytes) else (exc.stdout or '')
            err = 'timeout after %ss' % timeout
        except FileNotFoundError:
            return None, False
        with open(log_path, 'w', encoding='utf-8') as fh:
            fh.write('$ %s (cwd %s)\n\n--- stdout ---\n%s\n--- stderr ---'
                     '\n%s\n--- exit %s ---\n'
                     % (command, cwd, out, err, exit_code))
        return exit_code, True

    def _git(self, args, cwd):
        """Run one git command; returns (stdout, ok)."""
        try:
            proc = subprocess.run(['git'] + args, cwd=cwd,
                                  capture_output=True, text=True, timeout=30)
            return proc.stdout.strip(), proc.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError,
                OSError):
            return '', False

    def start_task(self, task_id, actor=None):
        """Record task_start WITH the starting fingerprint (D2-6).

        The fingerprint is the task's starting world - current HEAD plus
        the section-2-row-16 dirty-state comparison string - captured HERE,
        at task start, while the working tree still IS the starting state.
        A control pair's old leg materializes this revision later; it
        cannot be captured at control time, when the tree carries the very
        work being verified. Hosts without git record revision 'none' and
        every control on the attempt is honestly unavailable. Content-keyed
        idempotence: an unchanged world de-duplicates, a changed world is
        a new task_start (and reopens the evidence window, D2-9b/M4).
        """
        self._check_position()
        task = self._task(task_id)
        del task  # presence check only; the payload carries the id
        root = self.repo_root()
        revision, rev_ok = self._git(['rev-parse', 'HEAD'], root)
        dirty, _dirty_ok = self._git(['status', '--porcelain'], root)
        payload = {'task': task_id,
                   'fingerprint': {'revision': revision if rev_ok
                                                  and revision else 'none',
                                   'dirty': dirty or ''}}
        return self.append('task_start', payload,
                           actor=actor or {'kind': 'agent',
                                           'identity': 'caller'},
                           idempotent=True)

    def run_control(self, task_id, criterion, command, artifacts,
                    timeout=600):
        """Execute BOTH legs of a declared control and record the pair.

        Mechanical residency (U2, closing A6): the helper itself executes
        the old leg (a detached worktree at the recorded starting revision
        carrying exactly the declared check artifacts, D2-6/D3-4) and the
        new leg (the working tree), then records the observed
        ``control_pair`` with the verdict the legs produced:

          * (old FAIL, new PASS) -> discriminating - the only pass;
          * any other available pair -> non_discriminating, never rounded;
          * a non-empty dirty starting fingerprint (D3-3), a missing git
            or a non-repository host -> control_unavailable with
            old_leg.available=false - never a synthesized old outcome.
        """
        self._check_position()
        task = self._task(task_id)
        intents = {i.get('criterion')
                   for i in task.get('gate_intent', [])}
        if criterion not in intents:
            raise LedgerError(
                'control pair refused: criterion %r is not declared in '
                'task %s gate_intent %s' %
                (criterion, task_id, sorted(intents)))
        # the criterion must DECLARE a behavioral control - exempt
        # criteria close on ordinary evidence, never on a pair
        declared = None
        for crit in self.r.contract.get('acceptance', {}).get('criteria',
                                                              []):
            if crit.get('id') == criterion:
                declared = crit
                break
        control = (declared or {}).get('control') or {}
        if control.get('kind') not in ('regression', 'discrimination'):
            raise LedgerError(
                'control pair refused: criterion %s declares control '
                'kind %r - exempt/undeclared criteria close on ordinary '
                'accepted evidence with the recorded reason, never on a '
                'pair' % (criterion, control.get('kind')))
        start_event = None
        for event in self.events:
            if event.get('type') == 'task_start' and \
                    event.get('task') == task_id:
                if start_event is None or \
                        event.get('seq', 0) > start_event.get('seq', 0):
                    start_event = event
        if start_event is None:
            raise LedgerError(
                'control pair refused for %s: the task has no task_start '
                '- observed evidence exists only inside a task attempt'
                % task_id)
        root = self.repo_root()
        log_dir = os.path.join(self.r.gates_dir, task_id)
        os.makedirs(log_dir, exist_ok=True)
        seq = self.last_seq() + 1
        old_log = os.path.join(log_dir, '%03d-control-%s-old.log'
                               % (seq, criterion))
        new_log = os.path.join(log_dir, '%03d-control-%s-new.log'
                               % (seq, criterion))
        # D2-6: the old leg materializes the RECORDED starting
        # fingerprint - captured at task_start, not now. The current tree
        # may legitimately be dirty with the work being verified (that is
        # the new leg); what D3-3 refuses is a DIRTY STARTING state,
        # which no worktree can faithfully replay.
        fingerprint = start_event.get('fingerprint') or {}
        revision = fingerprint.get('revision') or 'none'
        dirty = fingerprint.get('dirty') or ''
        old_leg = {'available': False}
        verdict = 'control_unavailable'
        why = 'old leg unavailable'
        if not fingerprint:
            why = ('the attempt recorded no starting fingerprint - the old '
                   'leg cannot be materialized from a guess')
        elif revision == 'none':
            why = ('the attempt started on a non-git host - an old leg '
                   'cannot be materialized from a fingerprint alone')
        elif dirty:
            why = ('starting fingerprint carries a dirty component - the '
                   'old leg cannot be faithfully materialized (D3-3)')
        else:
            worktree = os.path.join(tempfile.mkdtemp(
                prefix='dwp-control-'), 'old-leg')
            try:
                _out, add_ok = self._git(['worktree', 'add', '--detach',
                                          worktree, revision], root)
                if add_ok:
                    # D3-4: exactly the declared check artifacts travel
                    # back; product files stay at their starting state.
                    for rel in artifacts:
                        src = os.path.join(root, rel)
                        if not os.path.isfile(src):
                            raise LedgerError(
                                'declared check artifact %r does not '
                                'exist in the working tree' % rel)
                        dst = os.path.join(worktree, rel)
                        os.makedirs(os.path.dirname(dst) or worktree,
                                    exist_ok=True)
                        shutil.copyfile(src, dst)
                    old_exit, ran = self._run_leg(command, worktree,
                                                  timeout, old_log)
                    if not ran:
                        why = 'old-leg command not found'
                    else:
                        old_leg = {'available': True,
                                   'outcome': 'PASS' if old_exit == 0
                                              else 'FAIL',
                                   'log': os.path.relpath(old_log,
                                                          self.r.dir)}
                else:
                    why = 'worktree materialization failed'
            finally:
                if os.path.isdir(worktree):
                    self._git(['worktree', 'remove', '--force', worktree],
                              root)
        new_exit, new_ran = self._run_leg(command, root, timeout, new_log)
        if not new_ran:
            raise LedgerError('new-leg command not found: %r - no event '
                              'is recorded for a check that never ran'
                              % (command,))
        new_leg = {'outcome': 'PASS' if new_exit == 0 else 'FAIL',
                   'log': os.path.relpath(new_log, self.r.dir)}
        if old_leg.get('available'):
            verdict = ('discriminating'
                       if old_leg['outcome'] == 'FAIL' and
                       new_leg['outcome'] == 'PASS'
                       else 'non_discriminating')
            why = 'only (old FAIL, new PASS) discriminates (A6/U2)'
        payload = {'criterion': criterion,
                   'check_artifacts': list(artifacts),
                   'starting_fingerprint': {'revision': revision,
                                            'dirty': dirty},
                   'old_leg': old_leg,
                   'new_leg': new_leg,
                   'verdict': verdict}
        event = self._append_raw('control_pair', payload,
                                 actor={'kind': 'helper',
                                        'identity': LEDGER_IDENTITY},
                                 ts=_utc_now(), trust='observed',
                                 evidence_path=os.path.relpath(old_log if
                                                               old_leg.get(
                                                                   'available')
                                                               else new_log,
                                                               self.r.dir),
                                 note=why)
        return {'verdict': verdict, 'old': old_leg, 'new': new_leg,
                'reason': why, 'seq': event['seq']}

    # -- projection ---------------------------------------------------------

    def task_start_seq(self, task_id):
        return task_start_seq_of(self.events, task_id)

    def criterion_state(self, task_id):
        # The pure module-level semantics; the writer adds only the lock.
        return criterion_states(self.r.contract, self.events, task_id)

    def task_status(self, task_id):
        """Derived, never declared: no task_start -> pending; every
        gate_intent criterion satisfied in-window -> completed (the same
        zero-test predicate the scheduler selects by); otherwise
        in_progress. A restart reopens the evidence window, so a
        restarted task derives in_progress again until fresh evidence
        lands."""
        if self.task_start_seq(task_id) is None:
            return 'pending'
        if task_complete(self.r.contract, self.events, task_id):
            return 'completed'
        return 'in_progress'

    def project(self):
        """Rebuild state.json deterministically from journal + contract.

        Determinism: every timestamp in the snapshot is derived from event
        ts values, never the wall clock — replaying the same journal bytes
        yields byte-identical snapshots. Provenance events (view_render)
        are excluded from positions: a render's own bookkeeping must never
        advance the snapshot a view is anchored to, or re-rendering
        unchanged records would diverge from itself. Positions the journal
        cannot support after a reconciliation are recorded
        ``regenerated``, never fabricated (D2-8) — and are ignored for
        roll bounding.
        """
        positions = {}
        for event in self.events:
            etype = event.get('type')
            if etype in PROVENANCE_TYPES:
                continue
            seq = event.get('seq', 0)
            if etype and seq > positions.get(etype, {}).get('seq', 0):
                positions[etype] = {'seq': seq}
        state = {
            'schema': STATE_SCHEMA_URL,
            'plan': self.r.contract['plan'],
            'contract_id': self.r.contract_id,
            'contract_revision': self.r.contract.get('revision', 1),
            'generated_by': LEDGER_IDENTITY,
            'updated_at': max([e.get('ts') for e in self.events] or ['']),
            'tasks': [],
            'positions': positions,
            'resources': self._resource_totals(),
            'checkpoint': self._last_authority_question(),
            'blocker': None,
        }
        archives = self.r.archives()
        if archives:
            state['archives'] = archives
        for task in self.r.contract.get('tasks', []):
            state['tasks'].append({
                'id': task['id'],
                'title': task.get('title'),
                'status': self.task_status(task['id']),
                'started_seq': self.task_start_seq(task['id']),
                'criteria': self.criterion_state(task['id']),
            })
        blob = json.dumps(state, sort_keys=True, indent=2) + '\n'
        _atomic_write(self.r.state_path, blob)
        return state

    def _resource_totals(self):
        limits = self.r.contract.get('resource_envelope', {}).get('limits', [])
        samples = {}
        for event in self.events:
            if event.get('type') == 'resource_sample':
                samples[event.get('limit_id')] = {
                    'value': event.get('value'),
                    'seq': event.get('seq'),
                    'trust': event.get('trust'),
                }
        return {'limits': limits, 'latest_samples': samples}

    def _last_authority_question(self):
        for event in reversed(self.events):
            if event.get('type') == 'intervention' and \
                    event.get('category') == 'new_authority':
                return event.get('question')
        return None

    # -- completion ---------------------------------------------------------

    def complete_task(self, task_id, actor=None):
        """Refuse completion unless every gate_intent criterion has
        in-window accepted evidence (zero-test control)."""
        self._check_position()
        states = self.criterion_state(task_id)
        missing = [s for s in states if not s.get('satisfied')]
        if missing:
            self._append_raw('refusal',
                             {'subject': task_id, 'stage': 'gate',
                              'reason': 'criteria without in-window accepted '
                                        'evidence: %s' %
                                        ', '.join(s['criterion'] for s
                                                  in missing)},
                             actor={'kind': 'helper',
                                    'identity': LEDGER_IDENTITY},
                             ts=_utc_now())
            raise CompletionRefused(
                'completion of %s refused: %d criterion(s) lack in-window '
                'accepted evidence (zero-test control)' %
                (task_id, len(missing)))
        return states

    # -- durability ---------------------------------------------------------

    def export(self, dest):
        """A10: copy journal + snapshot + contract chain with digests."""
        os.makedirs(dest, exist_ok=True)
        manifest = {'exported_by': LEDGER_IDENTITY,
                    'plan': self.r.contract['plan'],
                    'contract_id': self.r.contract_id,
                    'files': {}}
        sources = [self.r.journal_path, self.r.state_path]
        chain_dir = os.path.join(self.r.dir, 'contracts')
        if os.path.isdir(chain_dir):
            for name in sorted(os.listdir(chain_dir)):
                if name.endswith('.json'):
                    sources.append(os.path.join(chain_dir, name))
        single = os.path.join(self.r.dir, 'contract.json')
        if os.path.isfile(single):
            sources.append(single)
        # M2: the export is the durability posture — it must carry the
        # evidence chain its own snapshot cites. Archives (the journal
        # history after rolls), the reuse cache, every gates/ log and
        # every evidence_path cited by a record are part of the export;
        # a cited pointer that does not resolve is recorded missing,
        # never silently dropped.
        for archive in self.r.archives():
            sources.append(os.path.join(self.r.dir, archive['file']))
        cache = os.path.join(self.r.dir, 'evidence.jsonl')
        if os.path.isfile(cache):
            sources.append(cache)
        cited = []
        for event in self.events:
            pointer = event.get('evidence_path')
            if isinstance(pointer, str) and pointer:
                cited.append(pointer)
        if os.path.isfile(self.r.state_path):
            with open(self.r.state_path, encoding='utf-8') as fh:
                snapshot = json.load(fh)
            for t in snapshot.get('tasks', []):
                for c in t.get('criteria', []):
                    pointer = c.get('evidence_path')
                    if isinstance(pointer, str) and pointer:
                        cited.append(pointer)
        missing = []
        for pointer in sorted(set(cited)):
            local = os.path.join(self.r.dir, pointer)
            root = self.repo_root()
            alt = os.path.join(root, pointer) if root else None
            picked = None
            for cand in (local, alt):
                if cand and os.path.isfile(cand):
                    picked = cand
                    break
            if picked is None:
                missing.append(pointer)
            elif picked not in sources:
                sources.append(picked)
        gates_dir = getattr(self.r, 'gates_dir',
                            os.path.join(self.r.dir, 'gates'))
        if os.path.isdir(gates_dir):
            for base, _dirs, names in os.walk(gates_dir):
                for name in sorted(names):
                    sources.append(os.path.join(base, name))
        for src in sources:
            if not os.path.isfile(src):
                continue
            with open(src, 'rb') as fh:
                raw = fh.read()
            rel = os.path.relpath(src, self.r.dir)
            target = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as fh:
                fh.write(raw)
            manifest['files'][rel] = hashlib.sha256(raw).hexdigest()
        if missing:
            manifest['missing_evidence'] = missing
        manifest_path = os.path.join(dest, 'EXPORT_MANIFEST.json')
        with open(manifest_path, 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, sort_keys=True, indent=2)
        return manifest

    def roll(self):
        """Q2: archive the journal beside the plan; nothing is deleted.

        The live journal restarts at seq+1; the snapshot records the
        archive range so snapshot-cited positions stay addressable (a roll
        never discards them, D2-8). OFF by default — export is the default
        durability posture.
        """
        self._check_position()
        if not os.path.exists(self.r.journal_path):
            raise LedgerError('nothing to roll')
        if not self.events:
            raise LedgerError('nothing to roll: the live journal is empty')
        first = self.events[0].get('seq', 1)
        last = self.last_seq()
        if last <= self._seq_floor:
            raise LedgerError('nothing to roll: live events are all '
                              'retired above seq %d' % self._seq_floor)
        archive = os.path.join(
            self.r.dir, 'journal-archive-%06d-%06d.ndjson' % (first, last))
        shutil.copyfile(self.r.journal_path, archive)
        os.remove(self.r.journal_path)
        with open(self.r.journal_path, 'w', encoding='utf-8'):
            pass
        # B3: only the LIVE segment is retired — self.events keeps the
        # full plan history (archived + live), so approvals, evidence
        # windows and projections survive the roll
        self._end_offset = 0
        # the archive's top becomes the floor: the next append continues
        # the plan-wide seq, never restarting at 1 (seq never regresses)
        self._seq_floor = last
        self.project()
        return archive


# ---------------------------------------------------------------- helpers

def _utc_now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _hash_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _env_subset():
    keep = ('PATH', 'LANG', 'LC_ALL', 'PYTHONDONTWRITEBYTECODE', 'TERM',
            'VIRTUAL_ENV', 'PYTHONPATH')
    env = {k: os.environ.get(k, '') for k in keep}
    env['interpreter'] = os.path.basename(sys.executable or '')
    return env


def _parse_command(raw):
    """A gate command arrives as JSON: a string (run through the shell) or
    an argv array (executed directly, no shell). Returns None if neither."""
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, list) and value and all(
            isinstance(item, str) and item.strip() for item in value):
        return value
    return None


_PAYLOAD_KEYS = None


def _payload_of(event):
    """Envelope keys stripped; payload fields only (for content identity)."""
    envelope = {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                'actor', 'note'}
    return {k: v for k, v in event.items() if k not in envelope}


def _content_key(etype, payload, actor, contract_id=None):
    """M1: content identity includes the contract revision — a replay
    under a different contract is new content, never the old event."""
    body = {'type': etype, 'payload': payload,
            'actor_identity': (actor or {}).get('identity'),
            'contract_id': contract_id}
    return hashlib.sha256(json.dumps(body, sort_keys=True,
                                     separators=(',', ':'))
                          .encode('utf-8')).hexdigest()


# ---------------------------------------------------------------- selftest

def self_test():
    """In-memory probes: crash, collision, idempotence, staleness, identity."""
    failures = []
    probes = [0]

    def check(label, ok, detail=''):
        probes[0] += 1
        if not ok:
            failures.append('%s%s' % (label, (': ' + detail) if detail else ''))

    with tempfile.TemporaryDirectory() as tmp:
        plan = os.path.join(tmp, 'PLAN_selftest_v6')
        os.makedirs(plan)
        contract = _sibling_module()._selftest_contract()
        cid = contract_v6.compute_contract_id(contract)
        with open(os.path.join(plan, 'contract.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(dict(contract, contract_id=cid), fh)
        # touched-surface file for fingerprinting
        src = os.path.join(tmp, 'src_file.txt')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write('v1')
        contract['tasks'][0]['touched_surface'] = [src]
        with open(os.path.join(plan, 'contract.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(dict(contract, contract_id=contract_v6
                           .compute_contract_id(contract)), fh)

        rec = PlanRecords(plan)
        # 1. task_start before approval is refused AND recorded
        lock = CooperativeLock(plan).acquire()
        writer = Writer(rec, lock)
        try:
            writer.append('task_start', {'task': 'T-implement'},
                          actor={'kind': 'agent', 'identity': 'selftest'},
                          idempotent=True)
            check('task_start without approval must refuse', False)
        except ApprovalMissing:
            refusals = [e for e in writer.events
                        if e['type'] == 'refusal']
            check('refusal recorded', len(refusals) == 1)
        # 2. approval then idempotent task_start
        writer.append('approval',
                      {'authority': 'selftest', 'mechanism':
                       'plan_authorship', 'plan_digest': 'a' * 64},
                      actor={'kind': 'human', 'identity': 'selftest'},
                      idempotent=True)
        ts1 = writer.append('task_start', {'task': 'T-implement'},
                            actor={'kind': 'agent', 'identity': 'selftest'},
                            idempotent=True)
        ts2 = writer.append('task_start', {'task': 'T-implement'},
                            actor={'kind': 'agent', 'identity': 'selftest'},
                            idempotent=True)
        check('duplicate task_start is idempotent',
              ts1['seq'] == ts2['seq'],
              'seq %r vs %r' % (ts1.get('seq'), ts2.get('seq')))
        # 2.5 start_task captures the starting fingerprint at task start
        # (D2-6): no git in this scratch dir -> revision 'none', and the
        # content key makes a repeat call on the same world a dedup
        ts3 = writer.start_task('T-implement',
                                actor={'kind': 'agent',
                                       'identity': 'selftest'})
        ts4 = writer.start_task('T-implement',
                                actor={'kind': 'agent',
                                       'identity': 'selftest'})
        check('start_task records a starting fingerprint',
              (ts3.get('fingerprint') or {}).get('revision') == 'none' and
              (ts3.get('fingerprint') or {}).get('dirty') == '',
              repr(ts3.get('fingerprint')))
        check('start_task on an unchanged world dedups',
              ts3['seq'] == ts4['seq'],
              'seq %r vs %r' % (ts3.get('seq'), ts4.get('seq')))
        # 3. B1: append can never mint gate_run records or observed
        # trust outside host-adapter metering
        try:
            writer.append('gate_run',
                          {'command': 'true', 'cwd': tmp,
                           'timeout_seconds': 30, 'exit_code': 0,
                           'criterion': 'AC-one', 'task': 'T-implement'},
                          actor={'kind': 'helper',
                                 'identity': LEDGER_IDENTITY},
                          ts=_utc_now(), trust='observed',
                          evidence_path='gates/x.log')
            check('append gate_run must refuse', False)
        except LedgerError:
            check('append gate_run refused (only the executor mints)',
                  True)
        try:
            writer.append('observation', {'statement': 'forged'},
                          actor={'kind': 'helper',
                                 'identity': LEDGER_IDENTITY},
                          trust='observed',
                          evidence_path='analysis_results/real.log')
            check('append observed must refuse', False)
        except LedgerError:
            check('append observed refused (A1)', True)
        meter_dir = os.path.join(plan, 'analysis_results')
        os.makedirs(meter_dir, exist_ok=True)
        with open(os.path.join(meter_dir, 'meter.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump({'spend_usd': 1.25}, fh)
        try:
            writer.append('resource_sample',
                          {'source': 'selftest-meter',
                           'limit_id': 'spend_usd', 'value': 1.25,
                           'unit': 'USD'},
                          actor={'kind': 'agent', 'identity': 'selftest'},
                          trust='observed',
                          evidence_path='analysis_results/meter.json')
            check('observed metering requires a host_adapter', False)
        except LedgerError:
            check('observed metering requires a host_adapter', True)
        writer.append('resource_sample',
                      {'source': 'selftest-meter', 'limit_id': 'spend_usd',
                       'value': 1.25, 'unit': 'USD'},
                      actor={'kind': 'host_adapter',
                             'identity': 'selftest-meter'},
                      trust='observed',
                      evidence_path='analysis_results/meter.json')
        # 3b. M5: a gate run binds to the declared intent
        try:
            writer.run_gate('T-implement', 'true', criterion='AC-missing')
            check('gate criterion must bind to gate_intent', False)
        except LedgerError:
            check('gate criterion bound to gate_intent', True)
        # 3c. the real executor produces the observed record and it
        # satisfies in-window
        run = writer.run_gate('T-implement', 'true', criterion='AC-one')
        check('gate executor ran and recorded',
              run.get('reused') is False and run.get('exit_code') == 0,
              repr(run))
        # 3c-bis. reuse is per (task, criterion): another linkage with an
        # identical command executes fresh and records its own evidence —
        # replaying the cached result would mint nothing for the requester
        # and dead-loop its gate.
        orig_contract = writer.r.contract
        again = writer.run_gate('T-implement', 'true', criterion='AC-one')
        check('same (task, criterion) replays from the cache',
              again.get('reused') is True and
              again.get('exit_code') == run.get('exit_code'))
        contract_two = json.loads(json.dumps(writer.r.contract))
        contract_two['acceptance']['criteria'].append(
            {'id': 'AC-two', 'statement': 'Second criterion',
             'observable_check': 'true exits 0',
             'accepted_evidence': ['observed']})
        contract_two['tasks'][0]['gate_intent'].append(
            {'criterion': 'AC-two', 'check': 'true exits 0'})
        writer.r.contract = contract_two
        fresh = writer.run_gate('T-implement', 'true', criterion='AC-two')
        check('a different criterion never replays another linkage',
              fresh.get('reused') is False and fresh.get('exit_code') == 0,
              repr(fresh))
        writer.r.contract = orig_contract
        states = writer.criterion_state('T-implement')
        check('in-window observed evidence satisfies',
              states and states[0].get('satisfied'))
        rec2 = PlanRecords(plan)
        lock.release()
        lock2 = CooperativeLock(plan).acquire()
        writer2 = Writer(rec2, lock2)
        stale = [e for e in writer2.events if e['type'] == 'gate_run']
        writer2.events = [dict(e, seq=e['seq'] + 100)
                          for e in writer2.events]
        # simulate pre-start evidence by moving start later
        for e in writer2.events:
            if e['type'] == 'task_start':
                e['seq'] = 10 ** 6
        states2 = writer2.criterion_state('T-implement')
        check('pre-start evidence is stale, never satisfying',
              states2 and not states2[0].get('satisfied'))
        # 4. torn tail repair
        lock2.release()
        with open(rec2.journal_path, 'ab') as fh:
            fh.write(b'{"schema": "https://deepworkplan.com/schema/journa')
        rec3 = PlanRecords(plan)
        lock3 = CooperativeLock(plan).acquire()
        writer3 = Writer(rec3, lock3)
        repairs = [e for e in writer3.events
                   if e['type'] == 'journal_repair']
        check('torn tail repaired with journal_repair', len(repairs) == 1)
        # 5. determinism: identical journal -> identical snapshot bytes
        snap1 = writer3.project()
        lock3.release()
        with open(os.path.join(plan, 'state.json'), 'rb') as fh:
            bytes1 = fh.read()
        rec4 = PlanRecords(plan)
        lock4 = CooperativeLock(plan).acquire()
        writer4 = Writer(rec4, lock4)
        writer4.project()
        lock4.release()
        with open(os.path.join(plan, 'state.json'), 'rb') as fh:
            bytes2 = fh.read()
        check('projection is deterministic', bytes1 == bytes2)
        # 6. fingerprint sensitivity
        rec5 = PlanRecords(plan)
        lock5 = CooperativeLock(plan).acquire()
        writer5 = Writer(rec5, lock5)
        fp1 = writer5.fingerprint('T-implement', 'true')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write('v2 — changed input')
        fp2 = writer5.fingerprint('T-implement', 'true')
        check('changed input changes the fingerprint', fp1 != fp2)
        # 7. fingerprint is invariant to the caller's cwd (reuse identity
        # holds no matter which directory the helper is invoked from)
        caller_cwd = os.getcwd()
        try:
            os.chdir(os.path.join(plan, os.pardir))
            fp3 = writer5.fingerprint('T-implement', 'true')
        finally:
            os.chdir(caller_cwd)
        check('fingerprint invariant to caller cwd', fp2 == fp3)
        # 8. roll archives and the next append continues the plan-wide seq
        top = writer5.last_seq()
        archive = writer5.roll()
        check('roll writes an archive beside the plan',
              os.path.isfile(archive))
        post = writer5.append('observation', {'statement': 'post-roll'},
                              actor={'kind': 'agent', 'identity': 'selftest'},
                              trust='asserted')
        check('seq continues above the archive after a roll',
              post['seq'] == top + 1,
              'seq %r, expected %d' % (post.get('seq'), top + 1))
        state = json.load(open(rec5.state_path, encoding='utf-8')) \
            if os.path.isfile(rec5.state_path) else {}
        check('snapshot records the archive range',
              state.get('archives') == [{
                  'file': os.path.basename(archive),
                  'first_seq': 1, 'last_seq': top}])
        # 9. B3: after a roll the plan continues — the archived approval
        # still binds and a replayed task_start dedups against the
        # archive instead of being refused as unapproved
        replay = writer5.append('task_start', {'task': 'T-implement'},
                                actor={'kind': 'agent',
                                       'identity': 'selftest'},
                                idempotent=True)
        check('post-roll replay dedups against the archive',
              replay.get('seq') == ts1['seq'],
              'seq %r, original task_start seq %r' % (replay.get('seq'),
                                                      ts1['seq']))
        snap = json.load(open(rec5.state_path, encoding='utf-8'))
        inprog = [t for t in snap.get('tasks', [])
                  if t['id'] == 'T-implement']
        check('post-roll projection keeps task positions (status derives '
              'completed once every criterion is in-window satisfied)',
              bool(inprog) and inprog[0].get('status') == 'completed'
              and inprog[0].get('started_seq') is not None,
              repr(inprog))
        lock5.release()
        del snap1
        # 10. M1: a replayed task_start under an UNAPPROVED revision is
        # refused — the approval gate runs before dedup and the content
        # key carries the contract id
        rev2 = json.loads(json.dumps(contract))
        rev2['revision'] = 2
        rev2['parent_contract_id'] = cid
        rev2['tasks'][0]['touched_surface'] = [src]
        cid2 = contract_v6.compute_contract_id(rev2)
        with open(os.path.join(plan, 'contract.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(dict(rev2, contract_id=cid2), fh)
        rec6 = PlanRecords(plan)
        lock6 = CooperativeLock(plan).acquire()
        writer6 = Writer(rec6, lock6)
        try:
            writer6.append('task_start', {'task': 'T-implement'},
                           actor={'kind': 'agent', 'identity': 'selftest'},
                           idempotent=True)
            check('cross-revision replay must refuse', False)
        except ApprovalMissing:
            check('cross-revision replay refused (gate before dedup)',
                  True)
        except LedgerError:
            check('cross-revision replay refused (gate before dedup)',
                  True)
        # 11. B2: a complete final event that lost only its framing
        # newline is restored, never deleted
        writer6.append('observation', {'statement': 'framing probe'},
                       actor={'kind': 'agent', 'identity': 'selftest'},
                       trust='asserted')
        lock6.release()
        with open(rec6.journal_path, 'rb') as fh:
            raw = fh.read()
        if raw.endswith(b'\n'):
            with open(rec6.journal_path, 'wb') as fh:
                fh.write(raw[:-1])
        rec7 = PlanRecords(plan)
        lock7 = CooperativeLock(plan).acquire()
        writer7 = Writer(rec7, lock7)
        framing_repairs = [e for e in writer7.events
                           if e['type'] == 'journal_repair' and
                           'framing' in e.get('cause', '')]
        kept = [e for e in writer7.events
                if e.get('statement') == 'framing probe']
        with open(rec7.journal_path, 'rb') as fh:
            ends_nl = fh.read().endswith(b'\n')
        check('framing repair restores the newline, keeps the event',
              len(framing_repairs) == 1 and len(kept) == 1 and ends_nl,
              'repairs=%d kept=%d ends_nl=%s' %
              (len(framing_repairs), len(kept), ends_nl))
        # reopening again is stable: no second repair of any kind
        total_repairs = [e for e in writer7.events
                         if e['type'] == 'journal_repair']
        lock7.release()
        rec8 = PlanRecords(plan)
        lock8 = CooperativeLock(plan).acquire()
        writer8 = Writer(rec8, lock8)
        repairs_now = [e for e in writer8.events
                       if e['type'] == 'journal_repair']
        check('second open after framing repair is stable',
              len(repairs_now) == len(total_repairs),
              '%d repairs now vs %d before' %
              (len(repairs_now), len(total_repairs)))
        lock8.release()

        # 14-19. materialization: manifest -> contract -> approval (A12)
        plan2 = os.path.join(tmp, 'PLAN_selftest_materialize')
        os.makedirs(plan2)
        with open(os.path.join(plan2, 'README.md'), 'w',
                  encoding='utf-8') as fh:
            fh.write('# Plan selftest materialize\n\nplan markdown\n')
        contract2 = _sibling_module()._selftest_contract()
        contract2['plan'] = 'PLAN_selftest_materialize'
        contract2['tasks'][0]['touched_surface'] = [src]
        draft = os.path.join(tmp, 'draft-contract.json')
        with open(draft, 'w', encoding='utf-8') as fh:
            json.dump(contract2, fh)
        result = materialize_plan(plan2, draft, authority='selftest')
        cid2 = contract_v6.compute_contract_id(contract2)
        manifest = json.load(open(os.path.join(plan2, 'manifest.json')))
        check('materialize writes the manifest with the contract pointer',
              manifest == {'schema': MANIFEST_SCHEMA_URL,
                           'plan': 'PLAN_selftest_materialize',
                           'contract': {'id': cid2,
                                        'path': 'contract.json'}},
              repr(manifest))
        stamped2 = json.load(open(os.path.join(plan2, 'contract.json')))
        check('materialize stamps the contract and approval citing it',
              stamped2.get('contract_id') == cid2 and
              result['contract_id'] == cid2 and
              result['approval_seq'] is not None)
        digest2 = plan_markdown_digest(plan2)
        check('the approval digests the plan markdown',
              len(digest2) == 64 and digest2 != 'a' * 64)
        # resume: a re-run with the same inputs is idempotent
        again = materialize_plan(plan2, draft, authority='selftest')
        check('re-running materialize resumes, never duplicates',
              again['resumed'] and
              again['approval_seq'] == result['approval_seq'])
        # task_start now opens (the approval cites the live contract)
        lockm = CooperativeLock(plan2).acquire()
        writerm = Writer(PlanRecords(plan2), lockm)
        approvals = [e for e in writerm.events if e['type'] == 'approval']
        tsm = writerm.start_task('T-implement',
                                 actor={'kind': 'agent',
                                        'identity': 'selftest'})
        lockm.release()
        check('a materialized plan passes the approval gate',
              len(approvals) == 1 and tsm.get('task') == 'T-implement')
        # a manifest-only crash completes on re-run; a DIFFERENT contract
        # never rewrites what landed
        plan3 = os.path.join(tmp, 'PLAN_selftest_crash')
        os.makedirs(plan3)
        with open(os.path.join(plan3, 'README.md'), 'w',
                  encoding='utf-8') as fh:
            fh.write('# crash window\n')
        contract3 = json.loads(json.dumps(contract2))
        contract3['plan'] = 'PLAN_selftest_crash'
        draft3 = os.path.join(tmp, 'draft3.json')
        json.dump(contract3, open(draft3, 'w', encoding='utf-8'))
        cid3 = contract_v6.compute_contract_id(contract3)
        with open(os.path.join(plan3, 'manifest.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump({'schema': MANIFEST_SCHEMA_URL,
                       'plan': 'PLAN_selftest_crash',
                       'contract': {'id': cid3, 'path': 'contract.json'}},
                      fh)
        resumed3 = materialize_plan(plan3, draft3, authority='selftest')
        kept_manifest = json.load(open(os.path.join(plan3,
                                                    'manifest.json')))
        check('a crash between manifest and contract resumes cleanly',
              os.path.isfile(os.path.join(plan3, 'contract.json')) and
              kept_manifest['contract']['id'] == cid3 and
              resumed3['contract_id'] == cid3,
              repr(kept_manifest))
        try:
            materialize_plan(plan3, draft, authority='selftest')
            check('a different contract never rewrites the plan', False)
        except LedgerError as exc:
            check('a different contract never rewrites the plan',
                  'never rewrites' in str(exc) or
                  'does not match' in str(exc))
        contract2b = json.loads(json.dumps(contract2))
        contract2b['outcome']['statement'] += ' (variant content)'
        draft2b = os.path.join(tmp, 'draft2b.json')
        json.dump(contract2b, open(draft2b, 'w', encoding='utf-8'))
        try:
            materialize_plan(plan2, draft2b, authority='selftest')
            check('a pointer mismatch is refused, never edited', False)
        except LedgerError as exc:
            check('a pointer mismatch is refused, never edited',
                  'does not match this contract' in str(exc))
        try:
            materialize_plan(plan2, draft3, authority='selftest')
            check('a contract naming another folder is refused', False)
        except LedgerError as exc:
            check('a contract naming another folder is refused',
                  'does not match the plan folder' in str(exc))
        with open(os.path.join(plan3, 'manifest.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump({'schema': 'https://deepworkplan.com/schema/'
                                 'plan-manifest/v5.json'}, fh)
        try:
            materialize_plan(plan3, draft3, authority='selftest')
            check('a v5-generation manifest is never rewritten', False)
        except LedgerError as exc:
            check('a v5-generation manifest is never rewritten',
                  'never rewritten' in str(exc))
        empty = os.path.join(tmp, 'PLAN_no_markdown')
        os.makedirs(empty)
        contract4 = json.loads(json.dumps(contract3))
        contract4['plan'] = 'PLAN_no_markdown'
        draft4 = os.path.join(tmp, 'draft4.json')
        json.dump(contract4, open(draft4, 'w', encoding='utf-8'))
        try:
            materialize_plan(empty, draft4, authority='selftest')
            check('no plan markdown means no approval', False)
        except LedgerError as exc:
            check('no plan markdown means no approval',
                  'not approvable' in str(exc))
    return (not failures, failures, probes[0])


# --------------------------------------------------------------------- CLI

def _writer_for(args, force=False):
    plan = find_plan_dir(args.plan)
    rec = PlanRecords(plan)
    lock = CooperativeLock(plan, identity='%s pid:%d' %
                           (LEDGER_IDENTITY, os.getpid()))
    lock.acquire(force=force)
    return rec, lock, Writer(rec, lock)


def main(argv):
    usage = ('usage: ledger.py --plan DIR {materialize --contract FILE '
             '[--authority WHO] [--mechanism plan_authorship|'
             'pre_authorization] [--note TEXT] | append|start|gate|reuse|'
             'project|complete|export|roll|inspect|self-test} [options]')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--plan')
    parser.add_argument('command')
    parser.add_argument('--json')
    parser.add_argument('--type')
    parser.add_argument('--task')
    parser.add_argument('--criterion')
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--no-reuse', action='store_true')
    parser.add_argument('--selection')
    parser.add_argument('--actor-kind', default='agent')
    parser.add_argument('--actor-identity', default='caller')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--dest')
    parser.add_argument('--idempotent', action='store_true')
    parser.add_argument('--trust')
    parser.add_argument('--evidence-path')
    parser.add_argument('--note')
    parser.add_argument('--contract')
    parser.add_argument('--authority')
    parser.add_argument('--mechanism')
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
        print('self-test: %s (%d probes)' % ('OK' if ok else 'FAILED', probes))
        return 0 if ok else 1
    if args.command == 'materialize' and not (args.plan and args.contract):
        print('materialize requires --plan and --contract')
        return 2
    if not args.plan:
        print(usage)
        return 2
    try:
        if args.command == 'materialize':
            # Inside the handler set: an invalid or injected draft must
            # print the named refusal, not escape as a traceback.
            result = materialize_plan(
                find_plan_dir(args.plan), args.contract,
                authority=args.authority or 'developer',
                mechanism=args.mechanism or 'plan_authorship',
                note=args.note)
            print('OK: materialized %s contract %s (manifest, contract, '
                  'approval seq %s)%s' %
                  (result['plan'], result['contract_id'][:12],
                   result['approval_seq'],
                   ' — resumed an interrupted materialization'
                   if result['resumed'] else ''))
            return 0
        if args.command == 'inspect':
            rec = PlanRecords(find_plan_dir(args.plan))
            events, torn, _framing = rec.read_journal()
            print('plan %s contract %s (%d events%s)'
                  % (rec.contract['plan'], rec.contract_id[:12], len(events),
                     '; TORN TAIL' if torn else ''))
            for event in events:
                print('%4d %s %s' % (event.get('seq', 0), event.get('type'),
                                     event.get('task') or
                                     event.get('criterion') or ''))
            return 0
        if args.command == 'append':
            if not args.type or not args.json:
                print('append requires --type and --json')
                return 2
            rec, lock, writer = _writer_for(args, args.force)
            try:
                payload = json.loads(args.json)
                event = writer.append(
                    args.type, payload,
                    actor={'kind': args.actor_kind,
                           'identity': args.actor_identity},
                    note=args.note, idempotent=args.idempotent,
                    trust=args.trust, evidence_path=args.evidence_path)
                print('OK: appended %s seq %d' % (event['type'],
                                                  event['seq']))
                return 0
            finally:
                lock.release()
        if args.command == 'start':
            if not args.task:
                print('start requires --task')
                return 2
            rec, lock, writer = _writer_for(args, args.force)
            try:
                event = writer.start_task(
                    args.task,
                    actor={'kind': args.actor_kind,
                           'identity': args.actor_identity})
                fp = event.get('fingerprint') or {}
                print('OK: task_start %s at seq %s (starting fingerprint '
                      '%s, dirty %r)'
                      % (args.task, event.get('seq'),
                         (fp.get('revision') or 'none')[:12],
                         fp.get('dirty', '')))
                return 0
            finally:
                lock.release()
        if args.command == 'gate':
            if not args.task or not args.json:
                print('gate requires --task and --json (the command)')
                return 2
            command = _parse_command(args.json)
            if command is None:
                print("gate --json must be a JSON string (run through the "
                      'shell) or a JSON array of argv (executed directly, '
                      'no shell)')
                return 2
            rec, lock, writer = _writer_for(args, args.force)
            try:
                result = writer.run_gate(
                    args.task, command, criterion=args.criterion,
                    timeout=args.timeout, selection=args.selection,
                    reuse=not args.no_reuse)
                print('%s: exit %s%s (fingerprint %s, log %s)'
                      % ('REUSED' if result['reused'] else 'RAN',
                         result['exit_code'],
                         ', seq %s' % result.get('seq', '?')
                         if not result['reused'] else '',
                         result['fingerprint'][:12], result['log']))
                return 0 if result['exit_code'] == 0 else 1
            finally:
                lock.release()
        if args.command == 'reuse':
            if not args.task or not args.json:
                print('reuse requires --task and --json')
                return 2
            command = _parse_command(args.json)
            if command is None:
                print('reuse --json must be a JSON string or argv array')
                return 2
            rec, lock, writer = _writer_for(args, args.force)
            try:
                fp = writer.fingerprint(args.task, command,
                                        args.selection)
                prior = writer.evidence_lookup(fp, args.task,
                                               args.criterion)
                if prior is None:
                    print('NO EVIDENCE for fingerprint %s' % fp[:12])
                    return 1
                print('EVIDENCE exit %s log %s seq %s'
                      % (prior['exit_code'], prior['log'],
                         prior.get('seq')))
                return 0
            finally:
                lock.release()
        if args.command == 'project':
            rec, lock, writer = _writer_for(args, args.force)
            try:
                state = writer.project()
                print('OK: state.json projected (%d tasks, %d types)'
                      % (len(state['tasks']), len(state['positions'])))
                return 0
            finally:
                lock.release()
        if args.command == 'complete':
            if not args.task:
                print('complete requires --task')
                return 2
            rec, lock, writer = _writer_for(args, args.force)
            try:
                states = writer.complete_task(args.task)
                print('OK: %s criteria satisfied: %s'
                      % (args.task, ', '.join(s['criterion']
                                             for s in states)))
                return 0
            finally:
                lock.release()
        if args.command == 'export':
            if not args.dest:
                print('export requires --dest')
                return 2
            rec, lock, writer = _writer_for(args, args.force)
            try:
                manifest = writer.export(args.dest)
                print('OK: exported %d file(s) to %s'
                      % (len(manifest['files']), args.dest))
                return 0
            finally:
                lock.release()
        if args.command == 'roll':
            rec, lock, writer = _writer_for(args, args.force)
            try:
                archive = writer.roll()
                print('OK: journal archived to %s (nothing deleted)'
                      % archive)
                return 0
            finally:
                lock.release()
    except ApprovalMissing as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 3
    except CompletionRefused as exc:
        print('REFUSED: %s' % exc, file=sys.stderr)
        return 4
    except CollisionError as exc:
        print('COLLISION: %s' % exc, file=sys.stderr)
        return 2
    except LedgerError as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
