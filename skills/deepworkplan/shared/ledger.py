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
                with open(os.path.join(chain_dir, name), encoding='utf-8') as fh:
                    doc = json.load(fh)
                rev = doc.get('revision', 0)
                if not isinstance(rev, int):
                    continue
                if best is None or rev > best.get('revision', 0):
                    best = doc
        if best is not None:
            return best
        single = os.path.join(self.dir, 'contract.json')
        if os.path.isfile(single):
            with open(single, encoding='utf-8') as fh:
                return json.load(fh)
        raise LedgerError('no contract.json and no contracts/ chain in %s'
                          % self.dir)

    @property
    def contract_id(self):
        stamped = self.contract.get('contract_id')
        return stamped or contract_v6.compute_contract_id(self.contract)

    def read_journal(self):
        """Return (events, torn) where torn is (byte_offset, cause) or None.

        A final line that does not parse — or a file not ending in a
        newline — is a torn tail from a crash mid-append (section 4.3).
        """
        if not os.path.exists(self.journal_path):
            return [], None
        with open(self.journal_path, 'rb') as fh:
            raw = fh.read()
        events = []
        offset = 0
        torn = None
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
            torn = (offset - 1, 'journal does not end in a newline')
        return events, torn

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


# ------------------------------------------------------------------ writer

class Writer:
    """The single journal writer + projector for one plan (lock required)."""

    def __init__(self, records, lock):
        if not lock.held:
            raise LedgerError('Writer requires a held lock')
        self.r = records
        self.lock = lock
        self.events, torn = records.read_journal()
        # seq floor: archives may have retired events above anything the
        # live journal holds — seq is plan-wide and never goes backwards
        self._seq_floor = records.archive_top_seq()
        self._end_offset = self._journal_size()
        if torn is not None:
            self._repair_torn_tail(self.events, torn)
            if self._journal_size() != self._end_offset:
                raise LedgerError(
                    'journal repair left the file at %d bytes, expected %d'
                    % (self._journal_size(), self._end_offset))

    def _journal_size(self):
        return os.path.getsize(self.r.journal_path) \
            if os.path.exists(self.r.journal_path) else 0

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
        if idempotent:
            body_key = _content_key(etype, payload, actor)
            for prior in self.events:
                if _content_key(prior.get('type'), _payload_of(prior),
                                prior.get('actor')) == body_key:
                    return prior
        if etype == 'task_start':
            self._require_approval()
        return self._append_raw(etype, payload, actor, ts, note,
                                trust=trust, evidence_path=evidence_path)

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

    def _payload_of(self, event):
        raise NotImplementedError  # replaced by module function use

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

    def evidence_lookup(self, fingerprint):
        """Prior result on an EXACT fingerprint match, else None."""
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
                if rec.get('fingerprint') == fingerprint:
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
        fp = self.fingerprint(task_id, command, selection)
        if reuse:
            prior = self.evidence_lookup(fp)
            if prior is not None:
                return {'reused': True, 'fingerprint': fp,
                        'exit_code': prior['exit_code'],
                        'log': prior['log'], 'seq': prior.get('seq')}
        task = self._task(task_id)
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
                   'exit_code': exit_code}
        if criterion:
            payload['criterion'] = criterion
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

    # -- projection ---------------------------------------------------------

    def task_start_seq(self, task_id):
        for event in self.events:
            if event.get('type') == 'task_start' and \
                    event.get('task') == task_id:
                return event['seq']
        return None

    def criterion_state(self, task_id):
        """Satisfaction per criterion with in-window accepted evidence.

        D2-9b: only evidence recorded at or after the task's task_start
        position counts, with a trust label the criterion accepts.
        D3-6: boundary invariants are likewise evaluated at or after
        task-start; earlier items are recorded as stale, never satisfying.
        """
        task = self._task(task_id)
        start = self.task_start_seq(task_id)
        accepted_by = {c['id']: c.get('accepted_evidence', [])
                       for c in self.r.contract['acceptance']['criteria']}
        states = []
        for intent in task.get('gate_intent', []):
            cid = intent.get('criterion')
            wanted = accepted_by.get(cid, [])
            best = None
            stale = []
            for event in self.events:
                if event.get('type') != 'gate_run' or \
                        event.get('criterion') != cid:
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

    def task_status(self, task_id):
        if self.task_start_seq(task_id) is None:
            return 'pending'
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
            'checkpoint': self._last_field('note'),
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
        tmp = self.r.state_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(blob)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.r.state_path)
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

    def _last_field(self, _field):
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
        for src in sources:
            if not os.path.isfile(src):
                continue
            with open(src, 'rb') as fh:
                raw = fh.read()
            target = os.path.join(dest, os.path.basename(src))
            with open(target, 'wb') as fh:
                fh.write(raw)
            manifest['files'][os.path.basename(src)] = \
                hashlib.sha256(raw).hexdigest()
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
        self.events = []
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
    keep = ('PATH', 'LANG', 'LC_ALL', 'PYTHONDONTWRITEBYTECODE', 'TERM')
    return {k: os.environ.get(k, '') for k in keep}


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


def _content_key(etype, payload, actor):
    body = {'type': etype, 'payload': payload,
            'actor_identity': (actor or {}).get('identity')}
    return hashlib.sha256(json.dumps(body, sort_keys=True,
                                     separators=(',', ':'))
                          .encode('utf-8')).hexdigest()


# ---------------------------------------------------------------- selftest

def self_test():
    """In-memory probes: crash, collision, idempotence, staleness, identity."""
    import tempfile
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
        # 3. observed gate evidence in-window satisfies; stale does not
        writer.append('gate_run', {'command': 'true', 'cwd': tmp,
                                   'timeout_seconds': 30, 'exit_code': 0,
                                   'criterion': 'AC-one'},
                      actor={'kind': 'helper', 'identity': LEDGER_IDENTITY},
                      ts=_utc_now(), trust='observed',
                      evidence_path='gates/x.log')
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
        lock5.release()
        del snap1
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
    usage = ('usage: ledger.py --plan DIR {append|gate|reuse|project|'
             'complete|export|roll|inspect|self-test} [options]')
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
    if not args.plan:
        print(usage)
        return 2
    try:
        if args.command == 'inspect':
            rec = PlanRecords(find_plan_dir(args.plan))
            events, torn = rec.read_journal()
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
                prior = writer.evidence_lookup(fp)
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
