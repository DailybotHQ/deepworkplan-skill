#!/usr/bin/env python3
"""Swarm autonomy helper: own-capacity decision and the handoff packet; stdlib only.

Guide §17 (``guide/swarm.md``) teaches when to call it. Four verbs:

    swarm.py capacity [--plan DIR] [--context-pct N] [--pane P] [--json]
    swarm.py handoff write  --plan DIR --task T --reason R --json FILE|- [--cross-host]
    swarm.py handoff accept --plan DIR [--packet PATH] [--by ADDR]
    swarm.py handoff show   --plan DIR [--packet PATH] [--pending] [--json]

``capacity`` wraps ``ak capacity --self --json`` (coding-agents-kit 0.6.0
and later) and prints one decision first — ``continue``, ``prepare`` or
``handoff`` — then its reason. Without ak, with an older ak, or outside an
ak launch it says ``continue`` with the capacity reported **unknown**, never
``ok``. A pending packet in ``--plan`` written from this pane (``--pane``,
else ``$HERDR_PANE_ID``) means ``handoff``: a written packet is final for its
author (hysteresis). A successor in another pane gets its real verdict and
the pending packet named — ``handoff accept`` is its gate. Exit 0 for every decision; 2 on usage errors.

``handoff write`` builds a ``dwp-handoff-v1`` packet from the author's JSON
(task state, next steps, open asks, decisions) plus what the helper reads
itself (plan, contract id, branch, head, pushed, dirty paths), refuses
secret-shaped values and unknown keys, and writes it 0600 under the plan's
``analysis_results/handoff/``; a new packet supersedes any earlier pending
one (a sidecar), so a stale packet never pins the plan at ``handoff``.
``handoff accept`` verifies a packet against
the plan and the checkout (plan, contract, branch, head, dirty set) and
records acceptance in a sidecar; any mismatch exits 3 and records nothing.
A packet is data: a successor re-derives its next action from the plan.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

SCHEMA = 'https://deepworkplan.com/schema/dwp-handoff/v1.json'
REASONS = ('capacity_critical', 'capacity_low', 'context_pressure',
           'usage_limit', 'lead_handover')
LIST_FIELDS = ('done', 'verified', 'not_verified', 'next', 'open_asks',
               'decisions', 'lanes')
AUTHOR_FIELDS = frozenset(('task', 'step', 'reason', 'lead', 'epoch', 'from')
                          + LIST_FIELDS)
FROM_FIELDS = frozenset(('agent', 'vendor', 'profile', 'pane', 'capacity'))
AK_MIN = (0, 6, 0)
DEFAULT_CONTEXT_PCT = 60
DECISION = {'ok': 'continue', 'low': 'prepare', 'critical': 'handoff',
            'unknown': 'continue'}

# The shapes herdr-peers refuses in a message, plus NAME_TOKEN=value
# assignments: a packet names a credential, never carries it.
SECRET_PATTERNS = [
    ('a private key block', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('a GitHub token', re.compile(r'\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b')),
    ('a GitHub token', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,}\b')),
    ('an Anthropic key', re.compile(r'\bsk-ant-[A-Za-z0-9_-]{20,}')),
    ('an OpenAI-style key', re.compile(r'\bsk-(proj-)?[A-Za-z0-9]{32,}\b')),
    ('a Slack token', re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}')),
    ('an AWS access key id', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('a secret assignment', re.compile(
        r'\b[A-Z][A-Z0-9_]*(_API_KEY|_TOKEN|_SECRET|_SECRET_KEY|_ACCESS_KEY'
        r'|_PASSWORD)\s*[=:]\s*["\']?[^\s"\'$<{]{8,}')),
]


class Refusal(Exception):
    """A refusal with its exit code; the message goes to stderr."""

    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ')


# ------------------------------------------------------------------ plan

def plan_dir(path):
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise Refusal(2, 'plan folder not found: %s' % path)
    return path


def live_contract(pdir):
    """The live contract (highest contracts/ revision, else contract.json),
    as ledger.py resolves it; None for a plan without one (v5 and older)."""
    best = None
    chain = os.path.join(pdir, 'contracts')
    if os.path.isdir(chain):
        for name in sorted(os.listdir(chain)):
            if name.endswith('.json'):
                doc = read_json(os.path.join(chain, name))
                rev = doc.get('revision', 0)
                if isinstance(rev, int) and (best is None
                                             or rev > best.get('revision', 0)):
                    best = doc
    single = os.path.join(pdir, 'contract.json')
    if best is None and os.path.isfile(single):
        best = read_json(single)
    return best


def live_contract_id(pdir):
    contract = live_contract(pdir)
    return contract.get('contract_id') if contract else None


def context_threshold(pdir):
    """The live contract's fresh_context handoff percentage, else 60."""
    contract = live_contract(pdir) if pdir else None
    handoff = ((contract or {}).get('scheduling') or {}).get('handoff') or {}
    match = re.search(r'(\d{1,3})\s*%', str(handoff.get('fresh_context', '')))
    return int(match.group(1)) if match else DEFAULT_CONTEXT_PCT


def read_json(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except ValueError as exc:
        raise Refusal(2, '%s is not valid JSON: %s' % (path, exc))


def handoff_dir(pdir):
    return os.path.join(pdir, 'analysis_results', 'handoff')


SIDECARS = ('.accepted.json', '.superseded.json')


def packets(pdir):
    """Packet paths, oldest first: names start with a microsecond UTC stamp."""
    hdir = handoff_dir(pdir)
    if not os.path.isdir(hdir):
        return []
    return [os.path.join(hdir, n) for n in sorted(os.listdir(hdir))
            if n.endswith('.json') and not n.endswith(SIDECARS)]


def sidecar(packet, kind):
    return packet[:-len('.json')] + '.%s.json' % kind


def accepted_path(packet):
    return sidecar(packet, 'accepted')


def pending(pdir):
    """Packets neither accepted nor superseded by a later packet."""
    return [p for p in packets(pdir)
            if not os.path.exists(sidecar(p, 'accepted'))
            and not os.path.exists(sidecar(p, 'superseded'))]


# ------------------------------------------------------------------ git

def git(cwd, *args):
    proc = subprocess.run(('git',) + args, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    return proc.returncode, proc.stdout.strip()


def checkout_state(start):
    code, top = git(start, 'rev-parse', '--show-toplevel')
    if code != 0:
        raise Refusal(2, 'not inside a git checkout: %s' % start)
    # The repository is named by its common git directory, so a linked
    # worktree reports the repository, not the worktree folder.
    _, common = git(top, 'rev-parse', '--git-common-dir')
    common = os.path.normpath(os.path.join(top, common))
    name = os.path.basename(common)
    if name == '.git':
        repo = os.path.basename(os.path.dirname(common))
    else:  # a bare repository: <name>.git
        repo = name[:-len('.git')] if name.endswith('.git') else name
    _, branch = git(top, 'rev-parse', '--abbrev-ref', 'HEAD')
    _, head = git(top, 'rev-parse', 'HEAD')
    up_code, _ = git(top, 'rev-parse', '--abbrev-ref', '@{u}')
    pushed = False
    if up_code == 0:
        pushed = git(top, 'merge-base', '--is-ancestor', 'HEAD', '@{u}')[0] == 0
    proc = subprocess.run(('git', 'status', '--porcelain', '-z',
                           '--untracked-files=all'), cwd=top,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dirty = set()
    entries = proc.stdout.decode('utf-8', 'replace').split('\0')
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in 'RC':
            i += 1  # the rename source follows; the destination is dirty
        path = entry[3:]
        if not (path == '.dwp' or path.startswith('.dwp/')):
            dirty.add(path)
    return {'repo': repo, 'checkout': top, 'branch': branch,
            'head': head, 'pushed': pushed, 'dirty': sorted(dirty)}


# ------------------------------------------------------------------ capacity

def ak_version(ak):
    try:
        proc = subprocess.run((ak, '--version'), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True,
                              timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', proc.stdout)
    return tuple(int(g) for g in match.groups()) if match else None


def unknown(reason, ak=None):
    return {'decision': 'continue', 'verdict': 'unknown',
            'reason': 'capacity unknown: %s; hand off on a CLI limit warning '
                      'or a usage_limit screen' % reason,
            'ak': ak}


def read_capacity():
    """The decision record from ak capacity --self --json (one call)."""
    version = ak_version('ak')
    if version is None:
        return unknown('ak not installed')
    label = '.'.join(str(v) for v in version)
    if version < AK_MIN:
        return unknown('ak %s has no capacity verb (0.6.0 and later); read '
                       'ak usage once by hand' % label, label)
    try:
        proc = subprocess.run(('ak', 'capacity', '--self', '--json'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return unknown('ak capacity failed (%s)' % type(exc).__name__, label)
    if proc.returncode == 3:
        return unknown('this session was not launched through ak', label)
    try:
        doc = json.loads(proc.stdout)
    except ValueError:
        doc = None
    if proc.returncode != 0 or not isinstance(doc, dict) \
            or doc.get('schema') != 'capacity-v1':
        return unknown('ak capacity exited %d without a capacity-v1 record'
                       % proc.returncode, label)
    verdict = doc.get('verdict')
    if verdict not in DECISION:
        return unknown('unrecognized verdict', label)
    record = {'decision': DECISION[verdict], 'verdict': verdict, 'ak': label}
    for key in ('headroom_pct', 'binding_window', 'resets_at', 'profile',
                'cli', 'source', 'capped', 'thresholds', 'leases'):
        if key in doc:
            record[key] = doc[key]
    room = '%s%% headroom' % doc['headroom_pct'] \
        if isinstance(doc.get('headroom_pct'), (int, float)) else 'headroom unknown'
    window = doc.get('binding_window')
    where = ' (%s window, resets %s)' % (window, doc.get('resets_at') or '?') \
        if window else ''
    record['reason'] = {
        'ok': 'capacity ok: %s%s' % (room, where),
        'low': 'capacity_low: %s%s — finish the current task, start none you '
               'cannot finish, report capacity=low' % (room, where),
        'critical': 'capacity_critical: %s%s — reach a safe point, write the '
                    'packet, notify the lead, stop' % (room, where),
        'unknown': 'capacity unknown: no quota source for this account; hand '
                   'off on a CLI limit warning or a usage_limit screen',
    }[verdict]
    return record


def authored_by(packet_path, pane):
    """True when the packet's from.pane names this caller's pane."""
    if not pane:
        return False
    sender = read_json(packet_path).get('from') or {}
    return isinstance(sender, dict) and sender.get('pane') == pane


def capacity(args):
    pdir = plan_dir(args.plan) if args.plan else None
    waiting = pending(pdir) if pdir else []
    # Hysteresis binds the packet's AUTHOR only: a successor (another pane)
    # gets its real verdict — `handoff accept` is its gate, not capacity.
    pane = args.pane or os.environ.get('HERDR_PANE_ID') or ''
    own = [p for p in waiting if authored_by(p, pane)]
    if own:
        record = {'decision': 'handoff', 'verdict': None,
                  'reason': 'hysteresis: your handoff packet is pending (%s); '
                            'the successor accepts it — never resume this task'
                            % os.path.relpath(own[-1], pdir)}
    elif args.context_pct is not None and \
            args.context_pct >= context_threshold(pdir):
        record = {'decision': 'handoff', 'verdict': None,
                  'reason': 'context_pressure: %d%% of context used (handoff at '
                            '%d%%)' % (args.context_pct, context_threshold(pdir))}
    else:
        record = read_capacity()
        if waiting:
            record['pending_packet'] = os.path.relpath(waiting[-1], pdir)
            record['reason'] += ('; a handoff packet from another pane is '
                                 'pending — accept it (handoff accept) before '
                                 'working')
    if args.json:
        print(json.dumps(record, sort_keys=True))
    else:
        print('%s: %s' % (record['decision'], record['reason']))
    return 0


# ------------------------------------------------------------------ packet

def scan_secrets(value, where='packet'):
    """Raise on the first secret-shaped string anywhere in value."""
    if isinstance(value, dict):
        for key, item in value.items():
            scan_secrets(item, '%s.%s' % (where, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            scan_secrets(item, '%s[%d]' % (where, index))
    elif isinstance(value, str):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise Refusal(3, 'refused: %s carries %s — name the credential, '
                                 'never its value; nothing was written'
                              % (where, label))


def author_fields(doc, task, reason):
    if not isinstance(doc, dict):
        raise Refusal(2, 'the packet input must be a JSON object')
    extra = sorted(set(doc) - AUTHOR_FIELDS)
    if extra:
        raise Refusal(2, 'unknown packet field(s): %s (closed set: %s)'
                      % (', '.join(extra), ', '.join(sorted(AUTHOR_FIELDS))))
    out = dict(doc)
    out['task'] = task or doc.get('task')
    out['reason'] = reason or doc.get('reason')
    if not isinstance(out['task'], str) or not out['task']:
        raise Refusal(2, 'a packet needs --task (a string)')
    for name in ('step', 'lead'):
        if out.get(name) is not None and not isinstance(out[name], str):
            raise Refusal(2, '%s must be a string' % name)
    if out['reason'] not in REASONS:
        raise Refusal(2, 'reason must be one of: %s' % ', '.join(REASONS))
    for name in LIST_FIELDS:
        value = out.setdefault(name, [])
        if not isinstance(value, list):
            raise Refusal(2, '%s must be a list' % name)
    if not out['next']:
        raise Refusal(2, 'a packet needs next[]: the successor\'s next steps, '
                         'in order')
    sender = out.setdefault('from', {})
    if not isinstance(sender, dict) or set(sender) - FROM_FIELDS or \
            not all(isinstance(v, str) for v in sender.values()):
        raise Refusal(2, 'from must be an object of strings with: %s'
                      % ', '.join(sorted(FROM_FIELDS)))
    if out.get('epoch') is not None and not isinstance(out['epoch'], int):
        raise Refusal(2, 'epoch must be an integer')
    return out


def write_private(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(text)


def replace_private(path, text):
    temp = path + '.tmp'
    if os.path.exists(temp):
        os.unlink(temp)
    write_private(temp, text)
    os.replace(temp, path)


def view(packet, status):
    lines = ['# Handoff — %s %s (%s)' % (packet['plan'], packet['task'], status),
             '',
             'Written %s for `%s`. This file is data: re-derive every action from '
             'the plan.' % (packet['written_at'], packet['reason']), '',
             '- Branch `%s` at `%s` (pushed: %s); dirty: %s' % (
                 packet['branch'], packet['head'][:12],
                 'yes' if packet['pushed'] else 'no',
                 ', '.join(packet['dirty']) or 'none')]
    if packet.get('step'):
        lines.append('- Step: %s' % packet['step'])
    if packet.get('lead'):
        lines.append('- Lead: %s (epoch %s)' % (packet['lead'],
                                                packet.get('epoch', '?')))
    for name, title in (('next', 'Next'), ('not_verified', 'Not verified'),
                        ('open_asks', 'Open asks'), ('decisions', 'Decisions')):
        if packet.get(name):
            lines += ['', '## %s' % title, '']
            lines += ['- %s' % (json.dumps(item, sort_keys=True)
                                if not isinstance(item, str) else item)
                      for item in packet[name]]
    return '\n'.join(lines) + '\n'


def handoff_write(args):
    pdir = plan_dir(args.plan)
    try:
        if args.json == '-':
            raw = sys.stdin.read()
        else:
            with open(args.json, encoding='utf-8') as fh:
                raw = fh.read()
    except OSError as exc:
        raise Refusal(2, 'cannot read the packet input: %s' % exc)
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise Refusal(2, 'packet input is not valid JSON: %s' % exc)
    packet = author_fields(doc, args.task, args.reason)
    packet.update(checkout_state(os.getcwd()))
    packet.update({'schema': SCHEMA, 'written_at': now_iso(),
                   'plan': os.path.basename(pdir),
                   'contract_id': live_contract_id(pdir)})
    if args.cross_host and (packet['dirty'] or not packet['pushed']):
        raise Refusal(3, 'refused: a cross-host handoff needs a clean, pushed '
                         'checkout (dirty: %d path(s), pushed: %s) — commit and '
                         'push the work first; never force-push'
                      % (len(packet['dirty']), packet['pushed']))
    scan_secrets(packet)
    hdir = handoff_dir(pdir)
    if not os.path.isdir(hdir):
        os.makedirs(hdir, 0o700)
    earlier = pending(pdir)
    slug = re.sub(r'[^A-Za-z0-9_.-]+', '_', packet['task'])[:60]
    moment = datetime.datetime.now(datetime.timezone.utc)
    path = None
    while path is None or os.path.exists(path):
        # a microsecond stamp keeps name order equal to write order
        path = os.path.join(hdir, '%s-%s.json' % (
            moment.strftime('%Y%m%dT%H%M%S%fZ'), slug))
        moment += datetime.timedelta(microseconds=1)
    write_private(path, json.dumps(packet, indent=2, sort_keys=True) + '\n')
    # The newest packet is the one a successor accepts; an earlier pending
    # packet (one that no longer matches the checkout) is superseded so it
    # can never pin capacity at handoff or block resume.
    for old in earlier:
        write_private(sidecar(old, 'superseded'), json.dumps(
            {'superseded_at': packet['written_at'],
             'by': os.path.basename(path)}, sort_keys=True) + '\n')
    replace_private(os.path.join(hdir, 'HANDOFF.md'), view(packet, 'pending'))
    print(os.path.relpath(path))
    return 0


def select_packet(pdir, explicit, want_pending):
    if explicit:
        path = os.path.abspath(explicit)
        if os.path.dirname(path) != os.path.abspath(handoff_dir(pdir)) or \
                not path.endswith('.json') or path.endswith(SIDECARS):
            raise Refusal(2, 'a packet is a .json file in %s'
                          % handoff_dir(pdir))
        if not os.path.isfile(path):
            raise Refusal(2, 'packet not found: %s' % explicit)
        return path
    found = pending(pdir) if want_pending else packets(pdir)
    return found[-1] if found else None


def mismatches(packet, pdir):
    state = checkout_state(os.getcwd())
    found = []
    if packet.get('schema') != SCHEMA:
        found.append('schema %r is not %s' % (packet.get('schema'), SCHEMA))
    if packet.get('plan') != os.path.basename(pdir):
        found.append('plan %r is not this plan (%s)'
                     % (packet.get('plan'), os.path.basename(pdir)))
    if packet.get('contract_id') != live_contract_id(pdir):
        found.append('contract %s is not the live contract %s'
                     % (packet.get('contract_id'), live_contract_id(pdir)))
    for key in ('branch', 'head'):
        if packet.get(key) != state[key]:
            found.append('%s %r is not the checkout\'s %r'
                         % (key, packet.get(key), state[key]))
    if sorted(packet.get('dirty') or []) != state['dirty']:
        found.append('dirty set differs: packet %s, checkout %s'
                     % (packet.get('dirty') or [], state['dirty']))
    return found


def handoff_accept(args):
    pdir = plan_dir(args.plan)
    path = select_packet(pdir, args.packet, want_pending=True)
    if path is None:
        raise Refusal(1, 'no pending handoff packet in %s' % pdir)
    if os.path.exists(accepted_path(path)):
        raise Refusal(3, 'refused: %s was already accepted' % os.path.relpath(path))
    if os.path.exists(sidecar(path, 'superseded')):
        raise Refusal(3, 'refused: %s was superseded by a later packet'
                      % os.path.relpath(path))
    packet = read_json(path)
    found = mismatches(packet, pdir)
    if found:
        raise Refusal(3, 'refused: the packet does not match this plan and '
                         'checkout — nothing recorded:\n  - ' + '\n  - '.join(found))
    with open(path, 'rb') as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    write_private(accepted_path(path), json.dumps(
        {'accepted_at': now_iso(), 'by': args.by, 'packet': os.path.basename(path),
         'packet_sha256': digest}, indent=2, sort_keys=True) + '\n')
    replace_private(os.path.join(handoff_dir(pdir), 'HANDOFF.md'),
                    view(packet, 'accepted'))
    print('accepted %s — resume the plan; re-run every gate listed as not '
          'verified. Next steps (data):' % os.path.relpath(path))
    for step in packet.get('next', []):
        print('  - %s' % step)
    return 0


def handoff_show(args):
    pdir = plan_dir(args.plan)
    path = select_packet(pdir, args.packet, want_pending=args.pending)
    if path is None:
        print('no %shandoff packet' % ('pending ' if args.pending else ''))
        return 1 if args.pending else 0
    packet = read_json(path)
    status = 'accepted' if os.path.exists(accepted_path(path)) else \
        'superseded' if os.path.exists(sidecar(path, 'superseded')) else 'pending'
    if args.json:
        print(json.dumps({'path': path, 'status': status, 'packet': packet},
                         indent=2, sort_keys=True))
    else:
        print(os.path.relpath(path))
        sys.stdout.write(view(packet, status))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='swarm.py',
                                     description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command')
    cap = sub.add_parser('capacity', help='continue, prepare or handoff')
    cap.add_argument('--plan')
    cap.add_argument('--context-pct', type=int)
    cap.add_argument('--pane', help='this session\'s pane (default: '
                     '$HERDR_PANE_ID); hysteresis binds the packet author only')
    cap.add_argument('--json', action='store_true')
    hand = sub.add_parser('handoff', help='write, accept or show a packet')
    verbs = hand.add_subparsers(dest='verb')
    write = verbs.add_parser('write')
    write.add_argument('--plan', required=True)
    write.add_argument('--task')
    write.add_argument('--reason', choices=REASONS)
    write.add_argument('--json', required=True, help='author fields: FILE or -')
    write.add_argument('--cross-host', action='store_true')
    accept = verbs.add_parser('accept')
    accept.add_argument('--plan', required=True)
    accept.add_argument('--packet')
    accept.add_argument('--by')
    show = verbs.add_parser('show')
    show.add_argument('--plan', required=True)
    show.add_argument('--packet')
    show.add_argument('--pending', action='store_true')
    show.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    handlers = {'capacity': capacity}
    if args.command == 'handoff':
        handlers = {'write': handoff_write, 'accept': handoff_accept,
                    'show': handoff_show}
        key = args.verb
    else:
        key = args.command
    if key not in handlers:
        parser.print_help()
        return 2
    try:
        return handlers[key](args)
    except Refusal as exc:
        sys.stderr.write('swarm.py: %s\n' % exc.message)
        return exc.code


if __name__ == '__main__':
    sys.exit(main())
