#!/usr/bin/env python3
"""Write or refresh the structured header of a v8 plan's PROGRESS.md.

The header is four fixed lines directly under the file's title, so a
reader (resume, the herdr-peers fleet, a daemon) finds the plan's state
without scraping prose (spec/LOOP_ENGINEERING.md section 3.2):

    Goal: <one line>
    Current task: <T-id> - <title> (<status>) | none - plan complete
    Next action: <one line>
    Needs: none | <class> (<resolver>): <needs>

`Current task` and `Needs` are derived from the plan's records (the
ledger's read-only snapshot: the blocked task first, else the first task
not completed in contract order; the active blocker's class, resolver and
needs). `Goal` and `Next action` are the caller's words: passed with
--goal / --next, otherwise kept from the existing header. Everything below
the header is the agents' own working index and is never touched.

Stdlib only (Python 3.9+). Writes exactly one file, PROGRESS.md, atomically.

Usage:
  progress_header.py --plan PLAN_DIR [--goal TEXT] [--next TEXT] [--check]

--check prints the header the records imply and exits 1 when the file's
header differs (writes nothing).

Exit codes: 0 written/current · 1 refused or out of date · 2 usage.
"""
import argparse
import os
import re
import sys
import tempfile

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

import contract_v6  # noqa: E402  (sibling modules, same directory)
import ledger  # noqa: E402

KEYS = ('Goal', 'Current task', 'Next action', 'Needs')
LINE_MAX = 300      # the caller's lines (Goal, Next action): refused beyond
TITLE_MAX = 200     # a task title is shortened to this; id and status never
_KEY_LINE = re.compile(r'^(%s): ?(.*)$' % '|'.join(re.escape(k) for k in KEYS))


def _one_line(text, label):
    text = ' '.join(str(text or '').split())
    if not text:
        raise ValueError('%s must be a non-empty line' % label)
    if len(text) > LINE_MAX:
        raise ValueError('%s exceeds %d characters' % (label, LINE_MAX))
    return text


def derived(snapshot):
    """(current task, needs) lines from a v8 snapshot."""
    tasks = snapshot.get('tasks') or []
    blocker = snapshot.get('blocker')
    current = None
    if isinstance(blocker, dict):
        current = next((t for t in tasks if t.get('id') == blocker.get('task')),
                       None)
    if current is None:
        current = next((t for t in tasks if t.get('status') != 'completed'),
                       None)
    if current is None:
        task_line = 'none - plan complete'
    else:
        # Only the title may be shortened: the id and the status are what a
        # reader acts on, so they are never cut.
        title = ' '.join(str(current.get('title') or '').split())
        if len(title) > TITLE_MAX:
            title = title[:TITLE_MAX - 3].rstrip() + '...'
        task_line = '%s%s (%s)' % (current.get('id'),
                                   ' - %s' % title if title else '',
                                   current.get('status'))
    if isinstance(blocker, dict):
        # Never truncated: the ledger bounds needs to one line of at most
        # 500 characters (LOOP_ENGINEERING.md section 3.1), and the unblock
        # instruction is the line's whole purpose.
        needs_line = '%s (%s): %s' % (blocker.get('class'),
                                      blocker.get('resolver') or 'human',
                                      ' '.join(str(blocker.get('needs')
                                                   or '').split()))
    else:
        needs_line = 'none'
    return task_line, needs_line


def split_header(text):
    """(before, header dict, after) - the title stays in `before`."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].startswith('# '):
        start = 1
    while start < len(lines) and not lines[start].strip():
        start += 1
    found = {}
    end = start
    while end < len(lines):
        match = _KEY_LINE.match(lines[end])
        if not match or match.group(1) in found:
            break
        found[match.group(1)] = match.group(2).strip()
        end += 1
    if not found:
        end = start
    title = lines[:1] if lines and lines[0].startswith('# ') else []
    return title, found, lines[end:] if found else lines[len(title):]


def render(title, values, rest):
    body = ['%s: %s' % (key, values[key]) for key in KEYS]
    while rest and not rest[0].strip():
        rest = rest[1:]
    out = list(title) + ([''] if title else []) + body + \
        ([''] + rest if rest else [])
    return '\n'.join(out) + '\n'


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--plan', required=True)
    parser.add_argument('--goal')
    parser.add_argument('--next', dest='next_action')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        plan_dir = ledger.find_plan_dir(args.plan)
        records = ledger.PlanRecords(plan_dir)
        generation = contract_v6.contract_generation(records.contract)
        if not contract_v6.generation_at_least(generation, 'v8'):
            print('progress_header: this plan is %s - the structured header '
                  'is written from v8 (older plans keep their PROGRESS.md)'
                  % generation, file=sys.stderr)
            return 1
        snapshot = ledger.read_only_snapshot(records)
    except (ledger.LedgerError, OSError, ValueError) as exc:
        print('progress_header: %s' % exc, file=sys.stderr)
        return 1
    path = os.path.join(plan_dir, 'PROGRESS.md')
    try:
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
    except FileNotFoundError:
        text = '# %s - progress\n' % records.contract['plan']
    title, found, rest = split_header(text)
    task_line, needs_line = derived(snapshot)
    try:
        values = {
            'Goal': _one_line(args.goal if args.goal is not None
                              else found.get('Goal'), 'Goal (--goal)'),
            'Current task': task_line,
            'Next action': _one_line(args.next_action
                                     if args.next_action is not None
                                     else found.get('Next action'),
                                     'Next action (--next)'),
            'Needs': needs_line,
        }
    except ValueError as exc:
        print('progress_header: %s' % exc, file=sys.stderr)
        return 1
    rendered = render(title, values, rest)
    if args.check:
        print('\n'.join('%s: %s' % (k, values[k]) for k in KEYS))
        return 0 if rendered == text else 1
    if rendered == text:
        print('OK: PROGRESS.md header current')
        return 0
    fd, tmp = tempfile.mkstemp(dir=plan_dir, prefix='.PROGRESS.md.',
                               suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(rendered)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print('OK: PROGRESS.md header written (%s; needs %s)'
          % (task_line, needs_line))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
